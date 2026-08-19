#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MR76 / U-Radar auxiliary radar interface.

IMPORTANT
=========

This interface uses ONLY:

    u_radar.dbc

Never:

    mr76.dbc

Current OpenDBC CANParser API on this system:

    CANParser(
      dbc_name,
      messages,
      bus,
    )

For example:

    CANParser(
      "u_radar",
      [
        ("RadarState", 10),
        ("Status", 10),
        ("ObjectData", 20),
      ],
      0,
    )

DO NOT use:

    ("Byte0", "ObjectData")

because in the current parser API the first element is interpreted
as the DBC message name.

This module is deliberately conservative.

MR76/U-Radar data is NOT injected into:

    RadarData.points
    leadOne
    leadTwo
    longitudinal control

The purpose of this interface is currently:

    CAN
      |
      v
    u_radar.dbc
      |
      v
    CANParser
      |
      v
    diagnostic / verified raw state

The normal OEM radar/control chain remains untouched.
"""

from __future__ import annotations

import math
from typing import Any


from cereal import car

from opendbc.can.parser import CANParser
from opendbc.car.interfaces import RadarInterfaceBase


# ============================================================================
# Configuration
# ============================================================================

MR76_DBC = "u_radar"

MR76_BUS = 0

MR76_RADAR_STATE = "RadarState"
MR76_STATUS = "Status"
MR76_OBJECT_DATA = "ObjectData"

MR76_RADAR_STATE_ADDR = 0x201
MR76_STATUS_ADDR = 0x60A
MR76_OBJECT_DATA_ADDR = 0x60B


# Parser expected frequencies.
#
# These are parser checks only.
# They do NOT transmit CAN.
#
# ObjectData has historically been observed at approximately 20 Hz.
MR76_MESSAGES = [
  (MR76_RADAR_STATE, 10),
  (MR76_STATUS, 10),
  (MR76_OBJECT_DATA, 20),
]


# Conservative diagnostic limits.
#
# These are NOT used to create RadarData points.
MAX_TARGETS = 10

MAX_DISTANCE = 150.0
MIN_DISTANCE = 1.5

MAX_LATERAL = 50.0

MAX_MISSING_FRAMES = 5


# ============================================================================
# Helpers
# ============================================================================

def _safe_float(
  value: Any,
  default: float = 0.0,
) -> float:

  try:
    value = float(value)

    if not math.isfinite(value):
      return default

    return value

  except Exception:
    return default


def _safe_int(
  value: Any,
  default: int = 0,
) -> int:

  try:
    return int(round(float(value)))

  except Exception:
    return default


def _get_signal(
  values: Any,
  names: tuple[str, ...],
  default: Any = 0,
) -> Any:
  """
  Read a decoded DBC signal.

  No CAN bit decoding is performed here.

  CANParser/u_radar.dbc is responsible for:

    start bit
    length
    endian
    signedness
    factor
    offset
  """

  if values is None:
    return default

  for name in names:

    try:

      if isinstance(values, dict):

        if name in values:
          return values[name]

      elif hasattr(values, name):

        return getattr(values, name)

    except Exception:
      pass

  return default


def _distance(
  longitudinal: float,
  lateral: float,
) -> float:

  try:

    value = math.sqrt(
      longitudinal * longitudinal
      +
      lateral * lateral
    )

    if math.isfinite(value):
      return value

  except Exception:
    pass

  return 0.0


# ============================================================================
# Track
# ============================================================================

class MR76Track:

  def __init__(
    self,
    track_id: int,
  ) -> None:

    self.id = int(track_id)

    self.dRel = 0.0
    self.yRel = 0.0

    self.vRel = 0.0
    self.yvRel = 0.0

    self.cls = 0
    self.dyn_prop = 0

    self.rcs = 0.0

    self.age = 0
    self.missing = 0

  # --------------------------------------------------------------------------
  # Update
  # --------------------------------------------------------------------------

  def update(
    self,
    dRel: float,
    yRel: float,
    vRel: float,
    yvRel: float,
    dyn_prop: int,
    cls: int,
    rcs: float,
  ) -> None:

    self.dRel = float(dRel)
    self.yRel = float(yRel)

    self.vRel = float(vRel)
    self.yvRel = float(yvRel)

    self.dyn_prop = int(dyn_prop)
    self.cls = int(cls)

    self.rcs = float(rcs)

    self.age += 1
    self.missing = 0

  # --------------------------------------------------------------------------
  # Missing
  # --------------------------------------------------------------------------

  def mark_missing(self) -> None:

    self.missing += 1

  # --------------------------------------------------------------------------
  # Validity
  # --------------------------------------------------------------------------

  def valid(self) -> bool:

    if not math.isfinite(self.dRel):
      return False

    if not math.isfinite(self.yRel):
      return False

    if self.dRel < MIN_DISTANCE:
      return False

    if self.dRel > MAX_DISTANCE:
      return False

    if abs(self.yRel) > MAX_LATERAL:
      return False

    return True


# ============================================================================
# Radar Interface
# ============================================================================

class RadarInterface(RadarInterfaceBase):

  def __init__(
    self,
    CP,
  ) -> None:

    self.CP = CP

    self.frame = 0

    self.tracks: dict[int, MR76Track] = {}

    # ------------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------------

    self.last_error = ""

    self.parser_updates = 0
    self.parser_errors = 0

    self.radar_state_frames = 0
    self.status_frames = 0
    self.object_frames = 0

    self.total_can_updates = 0

    self.last_object_values: dict[str, Any] = {}
    self.last_status_values: dict[str, Any] = {}
    self.last_radar_state_values: dict[str, Any] = {}

    self.last_object_id = 0

    self.parser = None

    # ------------------------------------------------------------------------
    # IMPORTANT
    #
    # Current OpenDBC parser API:
    #
    #     CANParser(
    #       dbc_name,
    #       messages,
    #       bus,
    #     )
    #
    # NOT:
    #
    #     signals = [
    #       ("Byte0", "ObjectData"),
    #       ...
    #     ]
    #
    # The latter causes:
    #
    #     could not find message 'Byte0'
    #
    # because "Byte0" is interpreted as a DBC message name.
    # ------------------------------------------------------------------------

    self._init_parser()

  # ==========================================================================
  # Parser initialization
  # ==========================================================================

  def _init_parser(
    self,
  ) -> None:

    try:

      self.parser = CANParser(
        MR76_DBC,
        MR76_MESSAGES,
        MR76_BUS,
      )

      self.last_error = ""

    except Exception as e:

      self.parser = None

      self.last_error = (
        f"MR76 CANParser initialization failed: {e}"
      )

      # ----------------------------------------------------------------------
      # IMPORTANT
      #
      # RadarInterface must not make the entire car process fail.
      # ----------------------------------------------------------------------

      try:

        from openpilot.common.swaglog import cloudlog

        cloudlog.exception(
          "MR76 CANParser initialization failed"
        )

      except Exception:
        pass

  # ==========================================================================
  # Parser values
  # ==========================================================================

  def _get_values(
    self,
    message_name: str,
  ) -> dict[str, Any]:

    if self.parser is None:
      return {}

    try:

      values = self.parser.vl.get(
        message_name,
        {},
      )

      if values is None:
        return {}

      return dict(values)

    except Exception as e:

      self.last_error = (
        f"MR76 parser values failed: {e}"
      )

      return {}

  # ==========================================================================
  # RadarState
  # ==========================================================================

  def _process_radar_state(
    self,
    values: dict[str, Any],
  ) -> None:

    if not values:
      return

    self.radar_state_frames += 1

    self.last_radar_state_values = dict(values)

  # ==========================================================================
  # Status
  # ==========================================================================

  def _process_status(
    self,
    values: dict[str, Any],
  ) -> None:

    if not values:
      return

    self.status_frames += 1

    self.last_status_values = dict(values)

  # ==========================================================================
  # ObjectData
  # ==========================================================================

  def _process_object_data(
    self,
    values: dict[str, Any],
  ) -> None:
    """
    Process DBC-decoded ObjectData.

    IMPORTANT:

    The signal values come directly from:

        u_radar.dbc

    No raw-byte decoding is performed here.

    At this stage the decoded target is stored only for diagnostics.

    It is NOT inserted into RadarData.points.
    """

    if not values:
      return

    self.object_frames += 1

    self.last_object_values = dict(values)

    # ------------------------------------------------------------------------
    # ID
    # ------------------------------------------------------------------------

    target_id = _safe_int(
      _get_signal(
        values,
        (
          "ID",
          "TargetID",
          "ObjectID",
        ),
        0,
      )
    )

    target_id &= 0xFF

    self.last_object_id = target_id

    # ------------------------------------------------------------------------
    # The following values are read only when the DBC actually provides
    # these names.
    #
    # They are NOT assumed to be correct merely because a name exists.
    # ------------------------------------------------------------------------

    dRel = _safe_float(
      _get_signal(
        values,
        (
          "DistLong",
          "DistanceLong",
          "LongDistance",
        ),
        0.0,
      )
    )

    yRel = _safe_float(
      _get_signal(
        values,
        (
          "DistLat",
          "DistanceLat",
          "LatDistance",
        ),
        0.0,
      )
    )

    vRel = _safe_float(
      _get_signal(
        values,
        (
          "VRelLong",
          "VRelLongitudinal",
          "RelativeVelocityLong",
        ),
        0.0,
      )
    )

    yvRel = _safe_float(
      _get_signal(
        values,
        (
          "VRelLat",
          "VRelLateral",
          "RelativeVelocityLat",
        ),
        0.0,
      )
    )

    dyn_prop = _safe_int(
      _get_signal(
        values,
        (
          "DynProp",
          "DynamicProperty",
          "DynamicProp",
        ),
        0,
      )
    )

    cls = _safe_int(
      _get_signal(
        values,
        (
          "Class",
          "TargetClass",
          "ObjectClass",
        ),
        0,
      )
    )

    rcs = _safe_float(
      _get_signal(
        values,
        (
          "RCS",
          "Rcs",
          "RadarCrossSection",
        ),
        0.0,
      )
    )

    # ------------------------------------------------------------------------
    # If the DBC does not currently expose confirmed target geometry,
    # do not create a track.
    #
    # This is intentional.
    # ------------------------------------------------------------------------

    if (
      not math.isfinite(dRel)
      or
      not math.isfinite(yRel)
    ):

      return

    if (
      dRel <= 0.0
      and
      yRel == 0.0
    ):

      return

    # ------------------------------------------------------------------------
    # Conservative validation.
    # ------------------------------------------------------------------------

    if (
      dRel < MIN_DISTANCE
      or
      dRel > MAX_DISTANCE
      or
      abs(yRel) > MAX_LATERAL
    ):

      return

    # ------------------------------------------------------------------------
    # Store diagnostic track.
    #
    # Still NOT exported to RadarData.
    # ------------------------------------------------------------------------

    track = self.tracks.get(target_id)

    if track is None:

      if len(self.tracks) >= MAX_TARGETS:

        # Remove the oldest / weakest track.
        oldest_id = min(
          self.tracks,
          key=lambda k: self.tracks[k].age,
        )

        self.tracks.pop(
          oldest_id,
          None,
        )

      track = MR76Track(
        target_id
      )

      self.tracks[target_id] = track

    track.update(
      dRel=dRel,
      yRel=yRel,
      vRel=vRel,
      yvRel=yvRel,
      dyn_prop=dyn_prop,
      cls=cls,
      rcs=rcs,
    )

  # ==========================================================================
  # Track maintenance
  # ==========================================================================

  def _maintain_tracks(
    self,
  ) -> None:

    remove_ids = []

    for track_id, track in self.tracks.items():

      track.mark_missing()

      if track.missing > MAX_MISSING_FRAMES:

        remove_ids.append(
          track_id
        )

    for track_id in remove_ids:

      self.tracks.pop(
        track_id,
        None,
      )

  # ==========================================================================
  # CAN update
  # ==========================================================================

  def update(
    self,
    can_strings,
  ):
    """
    Update MR76 parser.

    Returns an empty RadarData message.

    This is deliberate.

    MR76 currently remains an auxiliary diagnostic radar and does not
    participate in the normal RadarData/control chain.
    """

    self.frame += 1
    self.total_can_updates += 1

    if can_strings is None:
      return None

    if self.parser is None:
      return self.make_radar_msg()

    # ------------------------------------------------------------------------
    # Feed CANParser.
    # ------------------------------------------------------------------------

    try:

      updated = self.parser.update_strings(
        can_strings
      )

      self.parser_updates += 1

      # Some OpenDBC versions return False when no relevant frame arrived.
      if updated is False:

        self._maintain_tracks()

        return self.make_radar_msg()

    except Exception as e:

      self.parser_errors += 1

      self.last_error = (
        f"MR76 CANParser update failed: {e}"
      )

      try:

        from openpilot.common.swaglog import cloudlog

        cloudlog.exception(
          "MR76 CANParser update failed"
        )

      except Exception:
        pass

      return self.make_radar_msg()

    # ------------------------------------------------------------------------
    # Read decoded DBC messages.
    # ------------------------------------------------------------------------

    try:

      radar_state_values = self._get_values(
        MR76_RADAR_STATE
      )

      status_values = self._get_values(
        MR76_STATUS
      )

      object_values = self._get_values(
        MR76_OBJECT_DATA
      )

      if radar_state_values:

        self._process_radar_state(
          radar_state_values
        )

      if status_values:

        self._process_status(
          status_values
        )

      if object_values:

        self._process_object_data(
          object_values
        )

    except Exception as e:

      self.parser_errors += 1

      self.last_error = (
        f"MR76 decoded data processing failed: {e}"
      )

    return self.make_radar_msg()

  # ==========================================================================
  # RadarData
  # ==========================================================================

  def make_radar_msg(
    self,
  ):
    ret = car.RadarData.new_message()

    ret.errors.canError = False
    ret.errors.radarFault = False
    ret.errors.wrongConfig = False
    ret.errors.radarUnavailableTemporary = False

    return ret

  # ==========================================================================
  # Diagnostics
  # ==========================================================================

  def get_debug_info(
    self,
  ) -> dict[str, Any]:

    return {

      "dbc_name":
        MR76_DBC,

      "bus":
        MR76_BUS,

      "parser_available":
        self.parser is not None,

      "frame":
        self.frame,

      "total_can_updates":
        self.total_can_updates,

      "parser_updates":
        self.parser_updates,

      "parser_errors":
        self.parser_errors,

      "radar_state_frames":
        self.radar_state_frames,

      "status_frames":
        self.status_frames,

      "object_frames":
        self.object_frames,

      "track_count":
        len(self.tracks),

      "last_object_id":
        self.last_object_id,

      "last_error":
        self.last_error,

      "last_object_values":
        dict(self.last_object_values),

      "last_status_values":
        dict(self.last_status_values),

      "last_radar_state_values":
        dict(self.last_radar_state_values),

    }


# ============================================================================
# Compatibility helpers
# ============================================================================

def get_mr76_debug_info(
  radar: RadarInterface,
) -> dict[str, Any]:

  try:

    return radar.get_debug_info()

  except Exception as e:

    return {
      "parser_available": False,
      "last_error": str(e),
    }


# ============================================================================
# Self-test
# ============================================================================

def _self_test() -> bool:

  print("=" * 70)
  print("U-RADAR CANPARSER TEST")
  print("=" * 70)

  print(
    "DBC:",
    MR76_DBC,
  )

  print(
    "Bus:",
    MR76_BUS,
  )

  print(
    "Messages:",
    MR76_MESSAGES,
  )

  try:

    parser = CANParser(
      MR76_DBC,
      MR76_MESSAGES,
      MR76_BUS,
    )

    print(
      "CANParser: OK"
    )

    print(
      "Parser:",
      parser,
    )

    try:

      print(
        "RadarState:",
        dict(
          parser.vl.get(
            MR76_RADAR_STATE,
            {},
          )
        ),
      )

      print(
        "Status:",
        dict(
          parser.vl.get(
            MR76_STATUS,
            {},
          )
        ),
      )

      print(
        "ObjectData:",
        dict(
          parser.vl.get(
            MR76_OBJECT_DATA,
            {},
          )
        ),
      )

    except Exception as e:

      print(
        "Initial values unavailable:",
        e,
      )

    print("=" * 70)

    return True

  except Exception as e:

    print(
      "CANParser: FAILED"
    )

    print(
      type(e).__name__,
      e,
    )

    print("=" * 70)

    return False


if __name__ == "__main__":
  _self_test()
