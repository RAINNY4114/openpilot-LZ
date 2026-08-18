#!/usr/bin/env python3

import math
import numpy as np

from collections import deque

from cereal import messaging, log, car

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.params import Params
from openpilot.common.realtime import DT_MDL, Priority, config_realtime_process
from openpilot.common.swaglog import cloudlog
from openpilot.common.simple_kalman import KF1D

from opendbc.can.parser import CANParser


# ============================================================================
# Original DragonPilot RadarD parameters
# ============================================================================

_LEAD_ACCEL_TAU = 1.5

SPEED = 0
ACCEL = 1

V_EGO_STATIONARY = 4.0

RADAR_TO_CENTER = 2.7
RADAR_TO_CAMERA = 1.52

LEAD_HOLD_TIME_S = 0.4
LEAD_HOLD_MAX_SPEED = 12.0


# ============================================================================
# MR76 / U-Radar configuration
# ============================================================================
#
# IMPORTANT
#
# This implementation uses ONLY:
#
#   u_radar
#
# and therefore resolves:
#
#   opendbc/dbc/u_radar.dbc
#
# It MUST NOT use mr76.dbc.
#
# Current OpenDBC CANParser API:
#
#   CANParser(dbc_name, messages, bus)
#
# Messages confirmed in u_radar.dbc:
#
#   0x201 = RadarState
#   0x60A = Status
#   0x60B = ObjectData
#
# ============================================================================

MR76_ENABLE = True
MR76_DBC = "u_radar"

# Your successful direct CANParser test used bus 0.
MR76_BUS = 0

MR76_STATUS_ID = 0x60A
MR76_OBJECT_ID = 0x60B
MR76_RADAR_STATE_ID = 0x201


# ============================================================================
# MR76 limits
# ============================================================================

MR76_MIN_DISTANCE = 2.0
MR76_MAX_DISTANCE = 150.0
MR76_MAX_LATERAL = 50.0

MR76_MAX_TARGETS = 10

MR76_MIN_CONFIRM_COUNT = 2

MR76_TIMEOUT = 5


# ============================================================================
# MR76 continuity validation
# ============================================================================

MR76_MAX_DT = 0.30

MR76_MAX_DREL_RATE = 100.0
MR76_MAX_YREL_RATE = 80.0
MR76_MAX_VREL_RATE = 80.0

MR76_MAX_DREL_JUMP = 30.0
MR76_MAX_YREL_JUMP = 15.0
MR76_MAX_VREL_JUMP = 20.0


# ============================================================================
# MR76 radarState point ID namespace
# ============================================================================

MR76_TRACK_ID_OFFSET = 1000


# ============================================================================
# Debug
# ============================================================================

MR76_DEBUG = True

MR76_DEBUG_EVERY_N_FRAMES = 50


# ============================================================================
# MR76 track
# ============================================================================

class MR76Track:

  def __init__(self, track_id):

    self.id = int(track_id)

    self.dRel = 0.0
    self.yRel = 0.0
    self.vRel = 0.0
    self.yvRel = 0.0

    self.dynProp = 0
    self.obj_class = 0
    self.rcs = 0.0

    self.age = 0
    self.missing = 0

    self.last_time_ns = 0

    self.continuous_updates = 0
    self.jump_count = 0

    self.max_drel_jump = 0.0
    self.max_yrel_jump = 0.0
    self.max_vrel_jump = 0.0

    self.continuity_valid = True

  def update(self, obj, timestamp_ns):

    d_rel = float(obj["dRel"])
    y_rel = float(obj["yRel"])
    v_rel = float(obj["vRel"])
    yv_rel = float(obj["yvRel"])

    dyn_prop = int(obj.get("dynProp", 0))
    obj_class = int(obj.get("class", 0))
    rcs = float(obj.get("rcs", 0.0))

    if self.age == 0:

      self.dRel = d_rel
      self.yRel = y_rel
      self.vRel = v_rel
      self.yvRel = yv_rel

      self.dynProp = dyn_prop
      self.obj_class = obj_class
      self.rcs = rcs

      self.last_time_ns = int(timestamp_ns)

      self.age = 1
      self.missing = 0

      self.continuity_valid = True

      return True

    dt = (
      float(timestamp_ns - self.last_time_ns)
      * 1e-9
    )

    if dt <= 0.0:
      dt = 0.05

    dt = min(dt, MR76_MAX_DT)

    dd = d_rel - self.dRel
    dy = y_rel - self.yRel
    dv = v_rel - self.vRel

    self.max_drel_jump = max(
      self.max_drel_jump,
      abs(dd)
    )

    self.max_yrel_jump = max(
      self.max_yrel_jump,
      abs(dy)
    )

    self.max_vrel_jump = max(
      self.max_vrel_jump,
      abs(dv)
    )

    expected_dd = self.vRel * dt

    residual_d = abs(
      dd - expected_dd
    )

    # Keep calculation for diagnostic continuity analysis.
    _ = residual_d

    d_rate = abs(dd) / dt
    y_rate = abs(dy) / dt
    v_rate = abs(dv) / dt

    jump = (

      abs(dd) > MR76_MAX_DREL_JUMP

      or

      abs(dy) > MR76_MAX_YREL_JUMP

      or

      abs(dv) > MR76_MAX_VREL_JUMP

      or

      d_rate > MR76_MAX_DREL_RATE

      or

      y_rate > MR76_MAX_YREL_RATE

      or

      v_rate > MR76_MAX_VREL_RATE

    )

    if jump:

      self.jump_count += 1
      self.continuity_valid = False

    else:

      self.continuous_updates += 1
      self.continuity_valid = True

    self.dRel = d_rel
    self.yRel = y_rel
    self.vRel = v_rel
    self.yvRel = yv_rel

    self.dynProp = dyn_prop
    self.obj_class = obj_class
    self.rcs = rcs

    self.last_time_ns = int(timestamp_ns)

    self.age += 1
    self.missing = 0

    return not jump

  def valid(self):

    if not math.isfinite(self.dRel):
      return False

    if not math.isfinite(self.yRel):
      return False

    if not math.isfinite(self.vRel):
      return False

    if not math.isfinite(self.yvRel):
      return False

    if self.dRel < MR76_MIN_DISTANCE:
      return False

    if self.dRel > MR76_MAX_DISTANCE:
      return False

    if abs(self.yRel) > MR76_MAX_LATERAL:
      return False

    return True

  def confirmed(self):

    return self.age >= MR76_MIN_CONFIRM_COUNT

  @property
  def radar_track_id(self):

    return (
      MR76_TRACK_ID_OFFSET
      +
      self.id
    )

  def as_dict(self):

    return {

      "id": self.id,

      "trackId": self.radar_track_id,

      "dRel": self.dRel,

      "yRel": self.yRel,

      "vRel": self.vRel,

      "yvRel": self.yvRel,

      "dynProp": self.dynProp,

      "class": self.obj_class,

      "rcs": self.rcs,

      "age": self.age,

      "missing": self.missing,

      "continuityValid": self.continuity_valid,

      "jumpCount": self.jump_count,

    }


# ============================================================================
# MR76 / U-Radar
# ============================================================================

class MR76Radar:

  def __init__(self):

    self.tracks = {}

    self.targets = []

    self.frame = 0

    self.total_frames = 0

    self.parser_updates = 0

    self.last_timestamp_ns = 0

    self.initialized = False

    self.last_error = ""

    self.continuity_checks = 0
    self.continuity_good = 0
    self.continuity_bad = 0
    self.large_jumps = 0

    # Raw CAN diagnostic counters

    self.can_events = 0
    self.can_frames = 0

    self.radar_state_frames = 0
    self.status_frames = 0
    self.object_frames = 0

    # Number of decoded ObjectData messages

    self.decoded_objects = 0

    # Last decoded target

    self.last_decoded = None

    # Last values from status/radar state

    self.radar_state_values = {}
    self.status_values = {}

    # Debug throttling

    self._last_debug_frame = 0

    # ------------------------------------------------------------------------
    # Current OpenDBC CANParser API:
    #
    #   CANParser(dbc_name, messages, bus)
    #
    # Messages are specified by address, not signal name.
    # ------------------------------------------------------------------------

    try:

      self.parser = CANParser(

        MR76_DBC,

        [

          (
            MR76_RADAR_STATE_ID,
            10
          ),

          (
            MR76_STATUS_ID,
            10
          ),

          (
            MR76_OBJECT_ID,
            10
          ),

        ],

        MR76_BUS

      )

      self.initialized = True

      cloudlog.info(
        "MR76 U-Radar CANParser initialized: "
        f"dbc=u_radar, "
        f"bus={MR76_BUS}, "
        f"messages="
        f"[0x{MR76_RADAR_STATE_ID:X}, "
        f"0x{MR76_STATUS_ID:X}, "
        f"0x{MR76_OBJECT_ID:X}]"
      )

    except Exception as e:

      self.parser = None
      self.initialized = False
      self.last_error = str(e)

      cloudlog.exception(
        "MR76 U-Radar CANParser initialization failed"
      )

  # --------------------------------------------------------------------------
  # CAN event extraction
  # --------------------------------------------------------------------------

  @staticmethod
  def _extract_can_frames(can_msg):

    frames = []

    # --------------------------------------------------------------
    # Normal cereal CAN event:
    #
    # can_msg.can
    # --------------------------------------------------------------

    try:

      for frame in can_msg.can:

        frames.append(
          (
            int(frame.address),
            bytes(frame.dat),
            int(frame.src)
          )
        )

      return frames

    except Exception:
      pass

    # --------------------------------------------------------------
    # Already a list-like CAN representation.
    # --------------------------------------------------------------

    try:

      for frame in can_msg:

        address = getattr(
          frame,
          "address",
          None
        )

        data = getattr(
          frame,
          "dat",
          None
        )

        src = getattr(
          frame,
          "src",
          0
        )

        if address is None or data is None:
          continue

        frames.append(
          (
            int(address),
            bytes(data),
            int(src)
          )
        )

    except Exception:
      pass

    return frames

  # --------------------------------------------------------------------------
  # Read parser values
  # --------------------------------------------------------------------------

  def _get_parser_values(
    self,
    address
  ):

    if self.parser is None:
      return {}

    try:

      values = self.parser.vl.get(
        address,
        {}
      )

      if values is None:
        return {}

      return dict(values)

    except Exception:

      return {}

  # --------------------------------------------------------------------------
  # Signal compatibility helper
  # --------------------------------------------------------------------------

  @staticmethod
  def _get_signal(
    values,
    *names,
    default=0.0
  ):

    if not values:
      return default

    for name in names:

      try:

        if name in values:
          return values[name]

      except Exception:
        pass

    return default

  # --------------------------------------------------------------------------
  # ObjectData decode
  # --------------------------------------------------------------------------

  def _decode_object_values(
    self,
    values
  ):

    if not values:
      return None

    try:

      obj_id = int(
        round(
          float(
            self._get_signal(
              values,
              "ID",
              default=0.0
            )
          )
        )
      )

      d_rel = float(
        self._get_signal(
          values,
          "DistLong",
          default=0.0
        )
      )

      y_rel = float(
        self._get_signal(
          values,
          "DistLat",
          default=0.0
        )
      )

      v_rel = float(
        self._get_signal(
          values,
          "VRelLong",
          default=0.0
        )
      )

      yv_rel = float(
        self._get_signal(
          values,
          "VRelLat",
          default=0.0
        )
      )

      dyn_prop = int(
        round(
          float(
            self._get_signal(
              values,
              "DynProp",
              default=0.0
            )
          )
        )
      )

      # Some revisions use Class, some use TargetClass.
      obj_class = int(
        round(
          float(
            self._get_signal(
              values,
              "TargetClass",
              "Class",
              default=0.0
            )
          )
        )
      )

      rcs = float(
        self._get_signal(
          values,
          "RCS",
          default=0.0
        )
      )

    except Exception as e:

      self.last_error = (
        f"ObjectData decode: {e}"
      )

      return None

    # ------------------------------------------------------------------------
    # Sanity checks
    # ------------------------------------------------------------------------

    if not math.isfinite(d_rel):
      return None

    if not math.isfinite(y_rel):
      return None

    if not math.isfinite(v_rel):
      return None

    if not math.isfinite(yv_rel):
      return None

    if (
      d_rel < MR76_MIN_DISTANCE
      or
      d_rel > MR76_MAX_DISTANCE
    ):
      return None

    if abs(y_rel) > MR76_MAX_LATERAL:
      return None

    if obj_id < 0 or obj_id > 255:
      return None

    return {

      "id": obj_id,

      "dRel": d_rel,

      "yRel": y_rel,

      "vRel": v_rel,

      "yvRel": yv_rel,

      "dynProp": dyn_prop,

      "class": obj_class,

      "rcs": rcs,

    }

  # --------------------------------------------------------------------------
  # Update
  # --------------------------------------------------------------------------

  def update(
    self,
    can_msg,
    timestamp_ns
  ):

    if not MR76_ENABLE:
      return

    self.frame += 1
    self.total_frames += 1
    self.can_events += 1

    self.last_timestamp_ns = int(
      timestamp_ns
    )

    if not self.initialized or self.parser is None:
      return

    frames = self._extract_can_frames(
      can_msg
    )

    if not frames:
      return

    self.can_frames += len(frames)

    # ------------------------------------------------------------------------
    # Only U-Radar configured bus.
    # ------------------------------------------------------------------------

    radar_frames = [

      f

      for f in frames

      if f[2] == MR76_BUS

    ]

    if not radar_frames:
      return

    # ------------------------------------------------------------------------
    # Count received U-Radar messages.
    # ------------------------------------------------------------------------

    for address, data, src in radar_frames:

      _ = data
      _ = src

      if address == MR76_RADAR_STATE_ID:

        self.radar_state_frames += 1

      elif address == MR76_STATUS_ID:

        self.status_frames += 1

      elif address == MR76_OBJECT_ID:

        self.object_frames += 1

    # ------------------------------------------------------------------------
    # Feed CURRENT OpenDBC CANParser.
    #
    # Current API expects:
    #
    #   parser.update(
    #     [
    #       (
    #         timestamp_ns,
    #         frames
    #       )
    #     ]
    #   )
    #
    # No MR76-specific parser API is used.
    # ------------------------------------------------------------------------

    try:

      updated = self.parser.update(
        [
          (
            int(timestamp_ns),
            radar_frames
          )
        ]
      )

      self.parser_updates += 1

    except Exception as e:

      self.last_error = str(e)

      cloudlog.exception(
        "MR76 U-Radar CANParser update failed"
      )

      return

    # ------------------------------------------------------------------------
    # RadarState
    # ------------------------------------------------------------------------

    radar_state_values = self._get_parser_values(
      MR76_RADAR_STATE_ID
    )

    if radar_state_values:

      self.radar_state_values = (
        radar_state_values
      )

    # ------------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------------

    status_values = self._get_parser_values(
      MR76_STATUS_ID
    )

    if status_values:

      self.status_values = (
        status_values
      )

    # ------------------------------------------------------------------------
    # ObjectData
    # ------------------------------------------------------------------------
    #
    # Do not depend on:
    #
    #   "ObjectData" in updated
    #
    # because this OpenDBC CANParser instance is address keyed.
    #
    # The confirmed key is:
    #
    #   1547 / 0x60B
    #
    # ------------------------------------------------------------------------

    object_values = self._get_parser_values(
      MR76_OBJECT_ID
    )

    if not object_values:

      return

    obj = self._decode_object_values(
      object_values
    )

    if obj is None:

      return

    obj_id = obj["id"]

    self.decoded_objects += 1
    self.last_decoded = obj

    # ------------------------------------------------------------------------
    # Diagnostic output.
    #
    # Throttled so radar traffic does not flood cloudlog.
    # ------------------------------------------------------------------------

    if MR76_DEBUG:

      if (
        self.frame -
        self._last_debug_frame
      ) >= MR76_DEBUG_EVERY_N_FRAMES:

        self._last_debug_frame = self.frame

        cloudlog.info(

          "MR76 OBJECT RX: "

          f"id={obj_id} "

          f"dRel={obj['dRel']:.2f}m "

          f"yRel={obj['yRel']:.2f}m "

          f"vRel={obj['vRel']:.2f}m/s "

          f"yvRel={obj['yvRel']:.2f}m/s "

          f"class={obj['class']} "

          f"rcs={obj['rcs']:.2f} "

          f"objects={self.decoded_objects}"

        )

    # ------------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------------

    if obj_id not in self.tracks:

      self.tracks[obj_id] = MR76Track(
        obj_id
      )

    track = self.tracks[obj_id]

    continuity_ok = track.update(
      obj,
      timestamp_ns
    )

    self.continuity_checks += 1

    if continuity_ok:

      self.continuity_good += 1

    else:

      self.continuity_bad += 1
      self.large_jumps += 1

    track.missing = 0

    # ------------------------------------------------------------------------
    # Remove expired tracks.
    # ------------------------------------------------------------------------

    for tid in list(
      self.tracks.keys()
    ):

      if tid == obj_id:
        continue

      self.tracks[tid].missing += 1

      if (
        self.tracks[tid].missing
        >
        MR76_TIMEOUT
      ):

        self.tracks.pop(
          tid,
          None
        )

    # ------------------------------------------------------------------------
    # Confirmed targets.
    # ------------------------------------------------------------------------

    ordered = sorted(

      [

        t

        for t in self.tracks.values()

        if (

          t.valid()

          and

          t.confirmed()

          and

          t.missing <= MR76_TIMEOUT

        )

      ],

      key=lambda t: t.dRel

    )

    self.targets = ordered[
      :MR76_MAX_TARGETS
    ]

    if MR76_DEBUG:

      if (
        self.frame -
        self._last_debug_frame
      ) == 0:

        cloudlog.info(

          "MR76 TARGET TABLE: "

          f"tracks={len(self.tracks)} "

          f"confirmed={len(self.targets)} "

          f"objectFrames={self.object_frames} "

          f"decoded={self.decoded_objects}"

        )

  # --------------------------------------------------------------------------
  # status dictionary
  # --------------------------------------------------------------------------

  def status_dict(self):

    return {

      "initialized":
        self.initialized,

      "dbc":
        MR76_DBC,

      "bus":
        MR76_BUS,

      "frame":
        self.frame,

      "canEvents":
        self.can_events,

      "canFrames":
        self.can_frames,

      "radarStateFrames":
        self.radar_state_frames,

      "statusFrames":
        self.status_frames,

      "objectFrames":
        self.object_frames,

      "decodedObjects":
        self.decoded_objects,

      "parserUpdates":
        self.parser_updates,

      "tracks":
        len(self.tracks),

      "targets":
        len(self.targets),

      "continuityGood":
        self.continuity_good,

      "continuityBad":
        self.continuity_bad,

      "lastDecoded":
        self.last_decoded,

      "lastError":
        self.last_error,

    }


# ============================================================================
# OEM Radar Kalman
# ============================================================================

class KalmanParams:

  def __init__(self, dt):

    assert (
      dt > 0.01
      and
      dt < 0.2
    )

    self.A = [

      [1.0, dt],

      [0.0, 1.0],

    ]

    self.C = [

      1.0,

      0.0,

    ]

    dts = [
      i * 0.01
      for i in range(1, 21)
    ]

    K0 = [

      0.12287673,
      0.14556536,
      0.16522756,
      0.18281627,
      0.19886890,
      0.21372394,
      0.22761098,
      0.24069424,
      0.25309600,
      0.26491023,
      0.27621103,
      0.28705801,
      0.29750003,
      0.30757767,
      0.31732515,
      0.32677158,
      0.33594201,
      0.34485814,
      0.35353899,
      0.36200124,

    ]

    K1 = [

      0.29666309,
      0.29330885,
      0.29042818,
      0.28787125,
      0.28555364,
      0.28342219,
      0.28144091,
      0.27958406,
      0.27783249,
      0.27617149,
      0.27458948,
      0.27307714,
      0.27162685,
      0.27023228,
      0.26888809,
      0.26758976,
      0.26633338,
      0.26511557,
      0.264,
      0.26278425,

    ]

    self.K = [

      [

        np.interp(
          dt,
          dts,
          K0
        )

      ],

      [

        np.interp(
          dt,
          dts,
          K1
        )

      ]

    ]


# ============================================================================
# OEM Radar Track
# ============================================================================

class Track:

  def __init__(
    self,
    identifier,
    v_lead,
    kalman_params
  ):

    self.identifier = identifier

    self.cnt = 0

    self.aLeadTau = FirstOrderFilter(
      _LEAD_ACCEL_TAU,
      0.45,
      DT_MDL
    )

    self.K_A = kalman_params.A
    self.K_C = kalman_params.C
    self.K_K = kalman_params.K

    self.kf = KF1D(

      [
        [v_lead],
        [0.0],
      ],

      self.K_A,
      self.K_C,
      self.K_K,

    )

  def update(
    self,
    d_rel,
    y_rel,
    v_rel,
    v_lead,
    measured
  ):

    self.dRel = d_rel
    self.yRel = y_rel
    self.vRel = v_rel
    self.vLead = v_lead
    self.measured = measured

    if self.cnt > 0:

      self.kf.update(
        self.vLead
      )

    self.vLeadK = float(
      self.kf.x[SPEED][0]
    )

    self.aLeadK = float(
      self.kf.x[ACCEL][0]
    )

    if abs(self.aLeadK) < 0.5:

      self.aLeadTau.x = (
        _LEAD_ACCEL_TAU
      )

    else:

      self.aLeadTau.update(
        0.0
      )

    self.cnt += 1

  def get_RadarState(
    self,
    model_prob=0.0
  ):

    return {

      "dRel":
        float(self.dRel),

      "yRel":
        float(self.yRel),

      "vRel":
        float(self.vRel),

      "vLead":
        float(self.vLead),

      "vLeadK":
        float(self.vLeadK),

      "aLeadK":
        float(self.aLeadK),

      "aLeadTau":
        float(self.aLeadTau.x),

      "status":
        True,

      "fcw":
        self.is_potential_fcw(
          model_prob
        ),

      "modelProb":
        model_prob,

      "radar":
        True,

      "radarTrackId":
        self.identifier,

    }

  def potential_low_speed_lead(
    self,
    v_ego
  ):

    return (

      abs(self.yRel) < 1.0

      and

      v_ego < V_EGO_STATIONARY

      and

      0.75 < self.dRel < 25

    )

  def is_potential_fcw(
    self,
    model_prob
  ):

    return model_prob > 0.9


# ============================================================================
# Vision matching
# ============================================================================

def laplacian_pdf(
  x,
  mu,
  b
):

  b = max(
    b,
    1e-4
  )

  return math.exp(
    -abs(x - mu) / b
  )


def match_vision_to_track(
  v_ego,
  lead,
  tracks
):

  offset_vision_dist = (

    lead.x[0]

    -

    RADAR_TO_CAMERA

  )

  def prob(track):

    try:
      x_std = float(
        lead.xStd[0]
      )
    except Exception:
      x_std = 6.0

    try:
      y_std = float(
        lead.yStd[0]
      )
    except Exception:
      y_std = 1.0

    try:
      v_std = float(
        lead.vStd[0]
      )
    except Exception:
      v_std = 6.0

    x_std = np.clip(
      x_std,
      0.5,
      6.0
    )

    y_std = np.clip(
      y_std,
      0.2,
      1.2
    )

    v_std = np.clip(
      v_std,
      0.5,
      6.0
    )

    return (

      laplacian_pdf(
        track.dRel,
        offset_vision_dist,
        x_std
      )

      *

      laplacian_pdf(
        track.yRel,
        -lead.y[0],
        y_std
      )

      *

      laplacian_pdf(
        track.vRel + v_ego,
        lead.v[0],
        v_std
      )

    )

  if not tracks:
    return None

  track = max(
    tracks.values(),
    key=prob
  )

  if (

    abs(
      track.dRel - offset_vision_dist
    )

    <

    max(
      offset_vision_dist * 0.25,
      5.0
    )

  ):

    return track

  return None


# ============================================================================
# Vision-only RadarState
# ============================================================================

def get_RadarState_from_vision(
  lead_msg,
  v_ego,
  model_v_ego,
):

  v_rel = (

    lead_msg.v[0]

    -

    model_v_ego

  )

  return {

    "dRel":
      float(
        lead_msg.x[0]
        -
        RADAR_TO_CAMERA
      ),

    "yRel":
      float(
        -lead_msg.y[0]
      ),

    "vRel":
      float(v_rel),

    "vLead":
      float(
        v_ego + v_rel
      ),

    "vLeadK":
      float(
        v_ego + v_rel
      ),

    "aLeadK":
      float(
        lead_msg.a[0]
      ),

    "aLeadTau":
      0.3,

    "fcw":
      False,

    "modelProb":
      float(
        lead_msg.prob
      ),

    "status":
      True,

    "radar":
      False,

    "radarTrackId":
      -1,

  }


# ============================================================================
# Lead selection
# ============================================================================

def get_lead(
  v_ego,
  ready,
  tracks,
  lead_msg,
  model_v_ego,
  low_speed_override=True,
  match_prob_min=0.5,
  vision_prob_min=0.5,
  allow_radar_only=False,
):

  _ = allow_radar_only

  track = None

  if (

    len(tracks) > 0

    and

    ready

    and

    lead_msg.prob > match_prob_min

  ):

    track = match_vision_to_track(
      v_ego,
      lead_msg,
      tracks
    )

  lead_dict = {
    "status":
      False
  }

  if track is not None:

    lead_dict = track.get_RadarState(
      lead_msg.prob
    )

  elif (

    ready

    and

    lead_msg.prob > vision_prob_min

  ):

    lead_dict = get_RadarState_from_vision(
      lead_msg,
      v_ego,
      model_v_ego,
    )

  if low_speed_override:

    candidates = [

      t

      for t in tracks.values()

      if t.potential_low_speed_lead(
        v_ego
      )

    ]

    if len(candidates):

      closest = min(
        candidates,
        key=lambda x: x.dRel
      )

      if (

        not lead_dict["status"]

        or

        closest.dRel < lead_dict["dRel"]

      ):

        lead_dict = closest.get_RadarState()

  return lead_dict


# ============================================================================
# MR76 -> RadarState point
# ============================================================================

def mr76_to_radar_point(
  track
):

  return {

    "trackId":
      int(track.radar_track_id),

    "dRel":
      float(track.dRel),

    "yRel":
      float(track.yRel),

    "vRel":
      float(track.vRel),

    "aRel":
      0.0,

    "yvRel":
      float(track.yvRel),

    "measured":
      True,

  }


# ============================================================================
# RadarD
# ============================================================================

class RadarD:

  def __init__(
    self,
    delay=0.0,
    CP=None,
  ):

    self.CP = CP

    self.current_time = 0.0

    self.tracks = {}

    self.kalman_params = KalmanParams(
      DT_MDL
    )

    self.mr76 = MR76Radar()

    self.mr76_targets = []

    self.v_ego = 0.0

    self.v_ego_hist = deque(

      [0.0],

      maxlen=max(
        1,
        int(
          round(
            delay / DT_MDL
          )
        ) + 1
      )

    )

    self.last_v_ego_frame = -1

    self.radar_state = None

    self.radar_state_valid = False

    self.ready = False

  # --------------------------------------------------------------------------
  # update
  # --------------------------------------------------------------------------

  def update(
    self,
    sm,
    rr,
  ):

    self.ready = sm.seen["modelV2"]

    # ------------------------------------------------------------------------
    # MR76 / U-Radar
    # ------------------------------------------------------------------------

    try:

      can_msg = sm["can"]

      can_timestamp = int(
        sm.logMonoTime["can"]
      )

      self.mr76.update(
        can_msg,
        can_timestamp
      )

      self.mr76_targets = [

        t.as_dict()

        for t in self.mr76.targets

      ]

    except Exception as e:

      cloudlog.error(
        f"MR76 U-Radar update failed: {e}"
      )

    # ------------------------------------------------------------------------
    # Ego speed
    # ------------------------------------------------------------------------

    if (

      sm.recv_frame["carState"]

      !=

      self.last_v_ego_frame

    ):

      self.v_ego = (
        sm["carState"].vEgo
      )

      self.v_ego_hist.append(
        self.v_ego
      )

      self.last_v_ego_frame = (
        sm.recv_frame["carState"]
      )

    # ------------------------------------------------------------------------
    # OEM Radar points
    # ------------------------------------------------------------------------

    ar_pts = {

      pt.trackId:

      [

        pt.dRel,

        pt.yRel,

        pt.vRel,

        pt.measured,

      ]

      for pt in rr.points

    }

    for tid in list(
      self.tracks.keys()
    ):

      if tid not in ar_pts:

        self.tracks.pop(
          tid,
          None
        )

    for tid, rpt in ar_pts.items():

      v_lead = (

        rpt[2]

        +

        self.v_ego_hist[0]

      )

      if tid not in self.tracks:

        self.tracks[tid] = Track(

          tid,

          v_lead,

          self.kalman_params

        )

      self.tracks[tid].update(

        rpt[0],

        rpt[1],

        rpt[2],

        v_lead,

        rpt[3]

      )

    # ------------------------------------------------------------------------
    # Create RadarState
    # ------------------------------------------------------------------------

    self.radar_state = (
      log.RadarState.new_message()
    )

    self.radar_state_valid = (
      sm.all_checks()
    )

    self.radar_state.mdMonoTime = (
      sm.logMonoTime["modelV2"]
    )

    self.radar_state.carStateMonoTime = (
      sm.logMonoTime["carState"]
    )

    self.radar_state.radarErrors = (
      rr.errors
    )

    # ------------------------------------------------------------------------
    # OEM Radar points
    # ------------------------------------------------------------------------

    try:

      self.radar_state.points = [

        {

          "trackId":
            int(pt.trackId),

          "dRel":
            float(pt.dRel),

          "yRel":
            float(pt.yRel),

          "vRel":
            float(pt.vRel),

          "aRel":
            0.0,

          "measured":
            bool(pt.measured),

        }

        for pt in rr.points

      ]

    except Exception:

      cloudlog.exception(
        "Unable to populate OEM radarState.points"
      )

    # ------------------------------------------------------------------------
    # Append MR76 points
    # ------------------------------------------------------------------------

    try:

      mr76_points = [

        mr76_to_radar_point(
          track
        )

        for track in self.mr76.targets

      ]

      if mr76_points:

        current_points = list(
          self.radar_state.points
        )

        self.radar_state.points = (

          current_points

          +

          mr76_points

        )

    except Exception:

      cloudlog.exception(
        "Unable to append MR76 radarState.points"
      )

    # ------------------------------------------------------------------------
    # Lead selection
    #
    # MR76 does NOT replace OEM radar lead selection.
    # ------------------------------------------------------------------------

    if len(
      sm["modelV2"].velocity.x
    ):

      model_v_ego = (
        sm["modelV2"].velocity.x[0]
      )

    else:

      model_v_ego = self.v_ego

    leads = sm["modelV2"].leadsV3

    if len(leads) > 1:

      lead_one = get_lead(

        self.v_ego,

        self.ready,

        self.tracks,

        leads[0],

        model_v_ego,

        low_speed_override=True,

        match_prob_min=0.5,

        vision_prob_min=0.5,

        allow_radar_only=False,

      )

      lead_two = get_lead(

        self.v_ego,

        self.ready,

        self.tracks,

        leads[1],

        model_v_ego,

        low_speed_override=False,

        match_prob_min=0.5,

        vision_prob_min=0.5,

        allow_radar_only=False,

      )

      self.radar_state.leadOne = lead_one
      self.radar_state.leadTwo = lead_two

  # --------------------------------------------------------------------------
  # publish
  # --------------------------------------------------------------------------

  def publish(
    self,
    pm
  ):

    msg = messaging.new_message(
      "radarState"
    )

    msg.valid = (
      self.radar_state_valid
    )

    msg.radarState = (
      self.radar_state
    )

    # ------------------------------------------------------------------------
    # MR76 state is carried in the same radarState Event.
    # ------------------------------------------------------------------------

    try:

      state = msg.mr76State

      state.valid = bool(
        self.mr76.initialized
      )

      state.radarStateValid = bool(
        self.mr76.radar_state_frames > 0
      )

      state.statusValid = bool(
        self.mr76.status_frames > 0
      )

      state.objectDataValid = bool(
        self.mr76.object_frames > 0
      )

      state.nvmReadStatus = 0

      targets = self.mr76.targets

      state.init(
        "objects",
        len(targets)
      )

      for i, target in enumerate(
        targets
      ):

        obj = state.objects[i]

        obj.id = int(
          target.id
        )

        obj.distLong = float(
          target.dRel
        )

        obj.distLat = float(
          target.yRel
        )

        obj.vRelLong = float(
          target.vRel
        )

        obj.vRelLat = float(
          target.yvRel
        )

        obj.dynProp = int(
          target.dynProp
        )

        obj.targetClass = int(
          target.obj_class
        )

        obj.rcs = float(
          target.rcs
        )

        obj.distance = float(
          math.sqrt(
            target.dRel ** 2
            +
            target.yRel ** 2
          )
        )

        obj.lastUpdate = int(
          target.last_time_ns
        )

        obj.frameCount = int(
          target.age
        )

    except Exception:

      cloudlog.exception(
        "Unable to fill mr76State"
      )

    # ------------------------------------------------------------------------
    # Publish one radarState Event.
    # ------------------------------------------------------------------------

    pm.send(
      "radarState",
      msg
    )


# ============================================================================
# Main
# ============================================================================

def main():

  config_realtime_process(
    5,
    Priority.CTRL_LOW
  )

  cloudlog.info(
    "radard waiting for CarParams"
  )

  CP = messaging.log_from_bytes(

    Params().get(
      "CarParams",
      block=True
    ),

    car.CarParams,

  )

  cloudlog.info(
    "radard got CarParams"
  )

  sm = messaging.SubMaster(

    [

      "modelV2",
      "carState",
      "liveTracks",
      "can",

    ],

    poll="modelV2"

  )

  # --------------------------------------------------------------------------
  # Current cereal service table uses radarState.
  # --------------------------------------------------------------------------

  pm = messaging.PubMaster(

    [

      "radarState"

    ]

  )

  RD = RadarD(
    CP.radarDelay,
    CP
  )

  cloudlog.info(
    "MR76 U-Radar RadarD started: "
    f"dbc=u_radar, "
    f"bus={MR76_BUS}"
  )

  while True:

    sm.update()

    RD.update(
      sm,
      sm["liveTracks"]
    )

    RD.publish(
      pm
    )


if __name__ == "__main__":

  main()
