#!/usr/bin/env python3
import os
import time
import threading

import cereal.messaging as messaging

from cereal import car, log

from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog, ForwardingHandler

from opendbc.car import DT_CTRL, structs
from opendbc.car.can_definitions import CanData, CanRecvCallable, CanSendCallable
from opendbc.car.carlog import carlog
from opendbc.car.fw_versions import ObdCallback
from opendbc.car.car_helpers import get_car, interfaces
from opendbc.car.interfaces import CarInterfaceBase, RadarInterfaceBase
from openpilot.selfdrive.pandad import can_capnp_to_list, can_list_to_can_capnp
from openpilot.selfdrive.car.cruise import VCruiseHelper
from openpilot.selfdrive.car.car_specific import MockCarState
from opendbc.safety import ALTERNATIVE_EXPERIENCE


REPLAY = "REPLAY" in os.environ

EventName = log.OnroadEvent.EventName


# =============================================================================
# MR76 auxiliary radar
# =============================================================================
#
# MR76 is completely isolated from the original OpenPilot radar/control path.
#
# CAN:
#
#   0x201 RadarState
#   0x60A Status
#   0x60B ObjectData
#
# DBC:
#
#   u_radar.dbc
#
# Output:
#
#   Event.mr76State
#
# IMPORTANT:
#
#   MR76 does NOT:
#
#     - modify RadarDataT
#     - modify liveTracks
#     - replace self.RI
#     - modify CarState
#     - modify CarControl
#     - send CAN
#     - affect controls
#
# The only connection is:
#
#     CAN -> u_radar -> snapshot() -> mr76State
#
# =============================================================================


MR76_ENABLED = True


def _load_mr76():
  """
  Load the MR76 parser lazily.

  MR76 failure must never prevent the normal card process from
  starting or running.
  """
  if not MR76_ENABLED:
    return None

  try:
    from openpilot.selfdrive.mr76.u_radar import MR76Radar
    return MR76Radar

  except Exception:
    cloudlog.exception(
      "MR76: failed to import openpilot.selfdrive.mr76.u_radar"
    )
    return None


MR76Radar = _load_mr76()


# =============================================================================
# Forward card logs
# =============================================================================

carlog.addHandler(
  ForwardingHandler(cloudlog)
)


# =============================================================================
# OBD callback
# =============================================================================

def obd_callback(params: Params) -> ObdCallback:

  def set_obd_multiplexing(
    obd_multiplexing: bool,
  ):
    if (
      params.get_bool(
        "ObdMultiplexingEnabled"
      )
      != obd_multiplexing
    ):
      cloudlog.warning(
        f"Setting OBD multiplexing to {obd_multiplexing}"
      )

      params.remove(
        "ObdMultiplexingChanged"
      )

      params.put_bool(
        "ObdMultiplexingEnabled",
        obd_multiplexing,
      )

      params.get_bool(
        "ObdMultiplexingChanged",
        block=True,
      )

      cloudlog.warning(
        "OBD multiplexing set successfully"
      )

  return set_obd_multiplexing


# =============================================================================
# CAN communication callbacks
# =============================================================================

def can_comm_callbacks(
  logcan: messaging.SubSocket,
  sendcan: messaging.PubSocket,
) -> tuple[
  CanRecvCallable,
  CanSendCallable,
]:

  def can_recv(
    wait_for_one: bool = False,
  ) -> list[list[CanData]]:
    """
    Receive CAN packets from logcan.

    Returns:
      list[list[CanData]]
    """

    ret = []

    for can in messaging.drain_sock(
      logcan,
      wait_for_one=wait_for_one,
    ):

      ret.append([
        CanData(
          msg.address,
          msg.dat,
          msg.src,
        )
        for msg in can.can
      ])

    return ret

  def can_send(
    msgs: list[CanData],
  ) -> None:

    sendcan.send(
      can_list_to_can_capnp(
        msgs,
        msgtype="sendcan",
      )
    )

  return can_recv, can_send


# =============================================================================
# Car
# =============================================================================

class Car:

  CI: CarInterfaceBase
  RI: RadarInterfaceBase
  CP: car.CarParams

  # ===========================================================================
  # Initialization
  # ===========================================================================

  def __init__(
    self,
    CI=None,
    RI=None,
  ) -> None:

    # -------------------------------------------------------------------------
    # CAN socket
    # -------------------------------------------------------------------------

    self.can_sock = messaging.sub_sock(
      "can",
      timeout=20,
    )

    # -------------------------------------------------------------------------
    # subscriptions
    # -------------------------------------------------------------------------

    self.sm = messaging.SubMaster([
      "pandaStates",
      "carControl",
      "onroadEvents",
    ])

    # -------------------------------------------------------------------------
    # publications
    # -------------------------------------------------------------------------

    self.pm = messaging.PubMaster([
      "sendcan",
      "carState",
      "carParams",
      "carOutput",
      "liveTracks",

      # MR76 auxiliary radar
      "mr76State",
    ])

    # -------------------------------------------------------------------------
    # normal card state
    # -------------------------------------------------------------------------

    self.can_rcv_cum_timeout_counter = 0

    self.CC_prev = (
      car.CarControl.new_message()
    )

    self.CS_prev = (
      car.CarState.new_message()
    )

    self.initialized_prev = False

    self.last_actuators_output = (
      structs.CarControl.Actuators()
    )

    self.params = Params()

    self.can_callbacks = can_comm_callbacks(
      self.can_sock,
      self.pm.sock["sendcan"],
    )

    # =========================================================================
    # MR76 initialization
    # =========================================================================

    self.mr76 = None

    self.mr76_enabled = False

    self.mr76_last_error_log = 0.0

    self.mr76_update_count = 0

    self.mr76_publish_count = 0

    if (
      MR76_ENABLED
      and MR76Radar is not None
    ):

      try:

        self.mr76 = MR76Radar(
          dbc_name="u_radar",
          bus=0,
        )

        self.mr76_enabled = True

        cloudlog.info(
          "MR76: auxiliary radar parser initialized "
          "(DBC=u_radar, bus=0)"
        )

      except TypeError:

        # Compatibility with positional constructor
        try:

          self.mr76 = MR76Radar(
            "u_radar",
            0,
          )

          self.mr76_enabled = True

          cloudlog.info(
            "MR76: auxiliary radar parser initialized "
            "(positional args)"
          )

        except Exception:

          cloudlog.exception(
            "MR76: parser initialization failed"
          )

      except Exception:

        cloudlog.exception(
          "MR76: parser initialization failed"
        )

    elif MR76Radar is None:

      cloudlog.warning(
        "MR76: u_radar module unavailable; "
        "continuing without auxiliary radar"
      )

    # =========================================================================
    # Normal OpenPilot initialization
    # =========================================================================

    is_release = self.params.get_bool(
      "IsReleaseBranch"
    )

    dp_params = 0

    if CI is None:

      print(
        "Waiting for CAN messages..."
      )

      while True:

        can = messaging.recv_one_retry(
          self.can_sock
        )

        if len(can.can) > 0:
          break

      alpha_long_allowed = (
        self.params.get_bool(
          "AlphaLongitudinalEnabled"
        )
      )

      num_pandas = len(
        messaging.recv_one_retry(
          self.sm.sock["pandaStates"]
        ).pandaStates
      )

      cached_params = None

      cached_params_raw = (
        self.params.get(
          "CarParamsCache"
        )
      )

      if cached_params_raw is not None:

        with car.CarParams.from_bytes(
          cached_params_raw
        ) as _cached_params:

          cached_params = _cached_params

      # -----------------------------------------------------------------------
      # DragonPilot flags
      # -----------------------------------------------------------------------

      if self.params.get_bool(
        "dp_lat_alka"
      ):
        dp_params |= (
          structs.DPFlags.LateralALKA
        )

      if self.params.get_bool(
        "dp_toyota_door_auto_lock_unlock"
      ):
        dp_params |= (
          structs.DPFlags.ToyotaLockCtrl
        )

      if self.params.get_bool(
        "dp_toyota_tss1_sng"
      ):
        dp_params |= (
          structs.DPFlags.ToyotaTSS1SnG
        )

      if self.params.get_bool(
        "dp_toyota_stock_lon"
      ):
        dp_params |= (
          structs.DPFlags.ToyotaStockLon
        )

      if self.params.get_bool(
        "dp_vag_a0_sng"
      ):
        dp_params |= (
          structs.DPFlags.VagA0SnG
        )

      if self.params.get_bool(
        "dp_vag_pq_steering_patch"
      ):
        dp_params |= (
          structs.DPFlags.VAGPQSteeringPatch
        )

      if self.params.get_bool(
        "dp_vag_avoid_eps_lockout"
      ):
        dp_params |= (
          structs.DPFlags.VagAvoidEPSLockout
        )

      dp_fingerprint = str(
        self.params.get(
          "dp_dev_model_selected"
        ) or ""
      )

      # -----------------------------------------------------------------------
      # Normal vehicle interface
      # -----------------------------------------------------------------------

      self.CI = get_car(
        *self.can_callbacks,
        obd_callback(self.params),
        alpha_long_allowed,
        is_release,
        num_pandas,
        dp_params,
        cached_params,
        dp_fingerprint=dp_fingerprint,
      )

      self.RI = interfaces[
        self.CI.CP.carFingerprint
      ].RadarInterface(
        self.CI.CP
      )

      self.CP = self.CI.CP

      self.params.put_bool(
        "FirmwareQueryDone",
        True,
      )

    else:

      self.CI = CI

      self.CP = CI.CP

      self.RI = RI

    # =========================================================================
    # Optional DragonPilot external radar
    # =========================================================================

    if self.params.get_bool(
      "dp_lon_ext_radar"
    ):

      from opendbc.car.radar_interface import (
        RadarInterface,
      )

      self.RI = RadarInterface(
        self.CI.CP
      )

    # =========================================================================
    # Safety
    # =========================================================================

    self.CP.alternativeExperience = 0

    if (
      dp_params
      & structs.DPFlags.LateralALKA
    ):

      self.CP.alternativeExperience |= (
        ALTERNATIVE_EXPERIENCE.ALKA
      )

    openpilot_enabled_toggle = (
      self.params.get_bool(
        "OpenpilotEnabledToggle"
      )
    )

    controller_available = (
      self.CI.CC is not None
      and openpilot_enabled_toggle
      and not self.CP.dashcamOnly
    )

    self.CP.passive = (
      not controller_available
      or self.CP.dashcamOnly
    )

    if self.CP.passive:

      safety_config = (
        structs.CarParams.SafetyConfig()
      )

      safety_config.safetyModel = (
        structs.CarParams.SafetyModel.noOutput
      )

      self.CP.safetyConfigs = [
        safety_config
      ]

    # =========================================================================
    # SecOC
    # =========================================================================

    if (
      self.CP.secOcRequired
      and not is_release
    ):

      try:

        with open(
          "/cache/params/SecOCKey"
        ) as f:

          user_key = (
            f.readline().strip()
          )

          if len(user_key) == 32:

            self.params.put(
              "SecOCKey",
              user_key,
            )

      except Exception:
        pass

      secoc_key = (
        self.params.get(
          "SecOCKey"
        )
      )

      if secoc_key is not None:

        saved_secoc_key = bytes.fromhex(
          secoc_key.strip()
        )

        if len(saved_secoc_key) == 16:

          self.CP.secOcKeyAvailable = True

          self.CI.CS.secoc_key = (
            saved_secoc_key
          )

          if controller_available:

            self.CI.CC.secoc_key = (
              saved_secoc_key
            )

        else:

          cloudlog.warning(
            "Saved SecOC key is invalid"
          )

    # =========================================================================
    # CarParams
    # =========================================================================

    prev_cp = self.params.get(
      "CarParamsPersistent"
    )

    if prev_cp is not None:

      self.params.put(
        "CarParamsPrevRoute",
        prev_cp,
      )

    cp_bytes = self.CP.to_bytes()

    self.params.put(
      "CarParams",
      cp_bytes,
    )

    self.params.put_nonblocking(
      "CarParamsCache",
      cp_bytes,
    )

    self.params.put_nonblocking(
      "CarParamsPersistent",
      cp_bytes,
    )

    # =========================================================================
    # Other state
    # =========================================================================

    self.mock_carstate = MockCarState()

    self.v_cruise_helper = VCruiseHelper(
      self.CP
    )

    self.is_metric = (
      self.params.get_bool(
        "IsMetric"
      )
    )

    self.experimental_mode = (
      self.params.get_bool(
        "ExperimentalMode"
      )
    )

    # =========================================================================
    # Ratekeeper
    # =========================================================================

    self.rk = Ratekeeper(
      100,
      print_delay_threshold=None,
    )

  # ===========================================================================
  # MR76 CAN update
  # ===========================================================================

  def update_mr76(
    self,
    can_list,
  ) -> None:
    """
    Feed the already decoded CAN list into MR76.

    IMPORTANT:

      card.py already performs:

        can_strs
          |
          v
        can_capnp_to_list()
          |
          v
        can_list

      Therefore MR76 receives exactly the same CAN representation
      that CI.update() and RI.update() receive.

    MR76 is completely isolated from the original radar/control chain.
    """

    if (
      not self.mr76_enabled
      or self.mr76 is None
    ):
      return

    try:

      # -----------------------------------------------------------------------
      # Current u_radar.py API
      #
      #     MR76Radar.update(can_strings)
      #
      # This is the API used by the supplied u_radar.py.
      # -----------------------------------------------------------------------

      update_method = getattr(
        self.mr76,
        "update",
        None,
      )

      if callable(update_method):

        update_method(
          can_list
        )

        self.mr76_update_count += 1

        return

      # -----------------------------------------------------------------------
      # Optional compatibility API.
      #
      # Only used if another MR76 implementation exposes
      # update_strings().
      # -----------------------------------------------------------------------

      update_strings = getattr(
        self.mr76,
        "update_strings",
        None,
      )

      if callable(update_strings):

        update_strings(
          can_list
        )

        self.mr76_update_count += 1

        return

      # -----------------------------------------------------------------------
      # No supported API
      # -----------------------------------------------------------------------

      now = time.monotonic()

      if (
        now
        - self.mr76_last_error_log
        > 10.0
      ):

        cloudlog.error(
          "MR76: parser has neither "
          "update() nor update_strings()"
        )

        self.mr76_last_error_log = now

    except Exception:

      now = time.monotonic()

      # Do not spam card log at 100 Hz.
      if (
        now
        - self.mr76_last_error_log
        > 10.0
      ):

        cloudlog.exception(
          "MR76: update failed"
        )

        self.mr76_last_error_log = now

  # ===========================================================================
  # MR76 state acquisition
  # ===========================================================================

  def _mr76_get_state(self):
    """
    Get a snapshot from u_radar.py.

    Current MR76 implementation exposes:

      radar.snapshot()

    Compatibility is retained for:

      get_state()
      state
    """

    if (
      not self.mr76_enabled
      or self.mr76 is None
    ):
      return None

    try:

      # -----------------------------------------------------------------------
      # Current u_radar.py
      # -----------------------------------------------------------------------

      snapshot = getattr(
        self.mr76,
        "snapshot",
        None,
      )

      if callable(snapshot):

        return snapshot()

      # -----------------------------------------------------------------------
      # Compatibility implementation
      # -----------------------------------------------------------------------

      get_state = getattr(
        self.mr76,
        "get_state",
        None,
      )

      if callable(get_state):

        return get_state()

      # -----------------------------------------------------------------------
      # Compatibility property
      # -----------------------------------------------------------------------

      if hasattr(
        self.mr76,
        "state",
      ):

        return self.mr76.state

    except Exception:

      now = time.monotonic()

      if (
        now
        - self.mr76_last_error_log
        > 10.0
      ):

        cloudlog.exception(
          "MR76: failed to get state"
        )

        self.mr76_last_error_log = now

    return None

  # ===========================================================================
  # MR76 value helper
  # ===========================================================================

  @staticmethod
  def _mr76_value(
    obj,
    *names,
    default=None,
  ):
    """
    Read a value from either:

      dict
      dataclass/object
    """

    if obj is None:
      return default

    for name in names:

      try:

        if isinstance(
          obj,
          dict,
        ):

          if name in obj:

            return obj[name]

        if hasattr(
          obj,
          name,
        ):

          return getattr(
            obj,
            name,
          )

      except Exception:
        pass

    return default

  # ===========================================================================
  # MR76 state publication
  # ===========================================================================

  def publish_mr76_state(
    self,
  ) -> None:
    """
    Publish MR76 telemetry.

    This function does NOT modify:

      RadarDataT
      liveTracks
      CarState
      CarControl

    It does NOT send CAN.
    """

    if not self.mr76_enabled:

      # MR76 module unavailable.
      #
      # We deliberately do not publish fake valid data.
      return

    try:

      msg = messaging.new_message(
        "mr76State"
      )

      state_msg = msg.mr76State

      state = self._mr76_get_state()

      # =======================================================================
      # No state
      # =======================================================================

      if state is None:

        state_msg.valid = False

        msg.valid = False

        self.pm.send(
          "mr76State",
          msg,
        )

        return

      # =======================================================================
      # Top-level validity
      # =======================================================================

      state_msg.valid = bool(
        self._mr76_value(
          state,
          "valid",
          default=False,
        )
      )

      state_msg.radarStateValid = bool(
        self._mr76_value(
          state,
          "radarStateValid",
          "radar_state_valid",
          default=False,
        )
      )

      state_msg.statusValid = bool(
        self._mr76_value(
          state,
          "statusValid",
          "status_valid",
          default=False,
        )
      )

      state_msg.objectDataValid = bool(
        self._mr76_value(
          state,
          "objectDataValid",
          "object_data_valid",
          default=False,
        )
      )

      # =======================================================================
      # RadarState
      # =======================================================================

      state_msg.nvmReadStatus = int(
        self._mr76_value(
          state,
          "nvmReadStatus",
          "nvm_read_status",
          default=0,
        )
      )

      state_msg.nvmWriteStatus = int(
        self._mr76_value(
          state,
          "nvmWriteStatus",
          "nvm_write_status",
          default=0,
        )
      )

      state_msg.maxDistance = float(
        self._mr76_value(
          state,
          "maxDistance",
          "max_distance",
          default=0.0,
        )
      )

      state_msg.radarPower = int(
        self._mr76_value(
          state,
          "radarPower",
          "radar_power",
          default=0,
        )
      )

      state_msg.sensorId = int(
        self._mr76_value(
          state,
          "sensorId",
          "sensor_id",
          default=0,
        )
      )

      state_msg.sortIndex = int(
        self._mr76_value(
          state,
          "sortIndex",
          "sort_index",
          default=0,
        )
      )

      state_msg.outputType = int(
        self._mr76_value(
          state,
          "outputType",
          "output_type",
          default=0,
        )
      )

      state_msg.qualityInfo = bool(
        self._mr76_value(
          state,
          "qualityInfo",
          "quality_info",
          default=False,
        )
      )

      state_msg.extInfo = bool(
        self._mr76_value(
          state,
          "extInfo",
          "ext_info",
          default=False,
        )
      )

      state_msg.canBaudRate = int(
        self._mr76_value(
          state,
          "canBaudRate",
          "can_baud_rate",
          default=0,
        )
      )

      state_msg.interfaceType = int(
        self._mr76_value(
          state,
          "interfaceType",
          "interface_type",
          default=0,
        )
      )

      state_msg.rcsThreshold = int(
        self._mr76_value(
          state,
          "rcsThreshold",
          "rcs_threshold",
          default=0,
        )
      )

      state_msg.calibrationEnabled = int(
        self._mr76_value(
          state,
          "calibrationEnabled",
          "calibration_enabled",
          default=0,
        )
      )

      # =======================================================================
      # Status
      # =======================================================================

      state_msg.numObjects = int(
        self._mr76_value(
          state,
          "numObjects",
          "num_objects",
          default=0,
        )
      )

      state_msg.measCount = int(
        self._mr76_value(
          state,
          "measCount",
          "meas_count",
          default=0,
        )
      )

      state_msg.interfaceVersion = int(
        self._mr76_value(
          state,
          "interfaceVersion",
          "interface_version",
          default=0,
        )
      )

      # =======================================================================
      # Objects
      # =======================================================================

      objects = self._mr76_value(
        state,
        "objects",
        "targets",
        default=[],
      )

      if objects is None:
        objects = []

      try:
        objects = list(objects)
      except Exception:
        objects = []

      object_count = min(
        len(objects),
        20,
      )

      state_msg.objectCount = (
        object_count
      )

      # -----------------------------------------------------------------------
      # cereal list initialization
      # -----------------------------------------------------------------------

      target_builders = state_msg.init(
        "objects",
        object_count,
      )

      # -----------------------------------------------------------------------
      # Targets
      # -----------------------------------------------------------------------

      for i, target in enumerate(
        objects[:object_count]
      ):

        out = target_builders[i]

        out.id = (
          int(
            self._mr76_value(
              target,
              "target_id",
              "id",
              default=0,
            )
          )
          & 0xFF
        )

        out.distLong = float(
          self._mr76_value(
            target,
            "dist_long",
            "distLong",
            default=0.0,
          )
        )

        out.distLat = float(
          self._mr76_value(
            target,
            "dist_lat",
            "distLat",
            default=0.0,
          )
        )

        out.vRelLong = float(
          self._mr76_value(
            target,
            "vrel_long",
            "vRelLong",
            default=0.0,
          )
        )

        out.vRelLat = float(
          self._mr76_value(
            target,
            "vrel_lat",
            "vRelLat",
            default=0.0,
          )
        )

        out.dynProp = (
          int(
            self._mr76_value(
              target,
              "dyn_prop",
              "dynProp",
              default=5,
            )
          )
          & 0xFF
        )

        out.targetClass = (
          int(
            self._mr76_value(
              target,
              "target_class",
              "targetClass",
              default=0,
            )
          )
          & 0xFF
        )

        out.rcs = float(
          self._mr76_value(
            target,
            "rcs",
            default=0.0,
          )
        )

        # ---------------------------------------------------------------------
        # Distance
        # ---------------------------------------------------------------------

        distance = self._mr76_value(
          target,
          "distance",
          default=None,
        )

        if distance is None:

          try:

            distance = (
              float(out.distLong) ** 2
              + float(out.distLat) ** 2
            ) ** 0.5

          except Exception:

            distance = 0.0

        out.distance = float(
          distance
        )

        # ---------------------------------------------------------------------
        # Timestamp
        #
        # u_radar.snapshot() returns:
        #
        #   lastUpdateMonoTime
        #
        # for each target.
        #
        # ---------------------------------------------------------------------

        out.lastUpdateMonoTime = int(
          self._mr76_value(
            target,
            "lastUpdateMonoTime",
            "last_update",
            default=0,
          )
        )

      # =======================================================================
      # Overall timestamp
      # =======================================================================

      last_update = self._mr76_value(
        state,
        "lastUpdateMonoTime",
        "last_update_mono_time",
        default=0,
      )

      try:

        last_update = int(
          last_update
        )

      except Exception:

        last_update = 0

      if last_update <= 0:

        last_update = (
          time.monotonic_ns()
        )

      state_msg.lastUpdateMonoTime = (
        last_update
      )

      # =======================================================================
      # Publish
      # =======================================================================

      msg.valid = bool(
        state_msg.valid
      )

      self.pm.send(
        "mr76State",
        msg,
      )

      self.mr76_publish_count += 1

    except Exception:

      now = time.monotonic()

      if (
        now
        - self.mr76_last_error_log
        > 10.0
      ):

        cloudlog.exception(
          "MR76: failed to publish mr76State"
        )

        self.mr76_last_error_log = now

  # ===========================================================================
  # State update
  # ===========================================================================

  def state_update(
    self,
  ) -> tuple[
    car.CarState,
    structs.RadarDataT | None,
  ]:
    """
    Main CAN-driven state update.

    Order:

      CAN
       |
       +--> can_list
       |
       +--> CI.update()
       |
       +--> RI.update()
       |
       +--> MR76.update()
       |
       +--> MR76.snapshot()/mr76State

    MR76 never enters RI/RadarDataT.
    """

    # -------------------------------------------------------------------------
    # Receive raw CAN
    # -------------------------------------------------------------------------

    can_strs = (
      messaging.drain_sock_raw(
        self.can_sock,
        wait_for_one=True,
      )
    )

    # -------------------------------------------------------------------------
    # Convert CAN exactly once
    # -------------------------------------------------------------------------

    can_list = (
      can_capnp_to_list(
        can_strs
      )
    )

    # =========================================================================
    # Original OpenPilot CAN -> CarState
    # =========================================================================

    CS = self.CI.update(
      can_list
    )

    if self.CP.brand == "mock":

      CS = self.mock_carstate.update(
        CS
      )

    # =========================================================================
    # Original OpenPilot radar
    # =========================================================================

    RD: structs.RadarDataT | None = (
      self.RI.update(
        can_list
      )
    )

    # =========================================================================
    # MR76 auxiliary radar
    #
    # IMPORTANT:
    #
    # MR76 gets the same can_list but has no connection to RD.
    # =========================================================================

    self.update_mr76(
      can_list
    )

    # Publish isolated telemetry.
    self.publish_mr76_state()

    # =========================================================================
    # SubMaster
    # =========================================================================

    self.sm.update(
      0
    )

    can_rcv_valid = (
      len(can_strs) > 0
    )

    if not can_rcv_valid:

      self.can_rcv_cum_timeout_counter += 1

    if (
      can_rcv_valid
      and REPLAY
    ):

      self.can_log_mono_time = (
        messaging.log_from_bytes(
          can_strs[0]
        ).logMonoTime
      )

    # =========================================================================
    # Cruise
    # =========================================================================

    self.v_cruise_helper.update_v_cruise(
      CS,
      self.sm["carControl"].enabled,
      self.is_metric,
    )

    if (
      self.sm["carControl"].enabled
      and not self.CC_prev.enabled
    ):

      self.v_cruise_helper.initialize_v_cruise(
        self.CS_prev,
        self.experimental_mode,
      )

    CS.vCruise = float(
      self.v_cruise_helper.v_cruise_kph
    )

    CS.vCruiseCluster = float(
      self.v_cruise_helper.v_cruise_cluster_kph
    )

    return CS, RD

  # ===========================================================================
  # Normal OpenPilot state publication
  # ===========================================================================

  def state_publish(
    self,
    CS: car.CarState,
    RD: structs.RadarDataT | None,
  ):

    # =========================================================================
    # carParams
    # =========================================================================

    if (
      self.sm.frame
      % int(50. / DT_CTRL)
      == 0
    ):

      cp_send = (
        messaging.new_message(
          "carParams"
        )
      )

      cp_send.valid = True

      cp_send.carParams = self.CP

      self.pm.send(
        "carParams",
        cp_send,
      )

    # =========================================================================
    # carOutput
    # =========================================================================

    co_send = (
      messaging.new_message(
        "carOutput"
      )
    )

    co_send.valid = (
      self.sm.all_checks([
        "carControl"
      ])
    )

    co_send.carOutput.actuatorsOutput = (
      self.last_actuators_output
    )

    self.pm.send(
      "carOutput",
      co_send,
    )

    # =========================================================================
    # carState
    # =========================================================================

    cs_send = (
      messaging.new_message(
        "carState"
      )
    )

    cs_send.valid = CS.canValid

    cs_send.carState = CS

    cs_send.carState.canErrorCounter = (
      self.can_rcv_cum_timeout_counter
    )

    cs_send.carState.cumLagMs = (
      -self.rk.remaining * 1000.
    )

    self.pm.send(
      "carState",
      cs_send,
    )

    # =========================================================================
    # Original liveTracks
    #
    # MR76 does NOT touch this.
    # =========================================================================

    if RD is not None:

      tracks_msg = (
        messaging.new_message(
          "liveTracks"
        )
      )

      tracks_msg.valid = not any(
        RD.errors.to_dict().values()
      )

      tracks_msg.liveTracks = RD

      self.pm.send(
        "liveTracks",
        tracks_msg,
      )

  # ===========================================================================
  # Controls
  # ===========================================================================

  def controls_update(
    self,
    CS: car.CarState,
    CC: car.CarControl,
  ):
    """
    Normal vehicle control path.

    MR76 is intentionally absent here.
    """

    if not self.initialized_prev:

      self.CI.init(
        self.CP,
        *self.can_callbacks,
      )

      self.params.put_bool_nonblocking(
        "ControlsReady",
        True,
      )

    if self.sm.all_alive([
      "carControl"
    ]):

      now_nanos = (
        self.can_log_mono_time
        if REPLAY
        else int(
          time.monotonic() * 1e9
        )
      )

      (
        self.last_actuators_output,
        can_sends,
      ) = self.CI.apply(
        CC,
        now_nanos,
      )

      self.pm.send(
        "sendcan",
        can_list_to_can_capnp(
          can_sends,
          msgtype="sendcan",
          valid=CS.canValid,
        )
      )

      self.CC_prev = CC

  # ===========================================================================
  # Main step
  # ===========================================================================

  def step(self):

    CS, RD = (
      self.state_update()
    )

    self.state_publish(
      CS,
      RD,
    )

    initialized = (
      not any(
        e.name
        == EventName.selfdriveInitializing
        for e in self.sm["onroadEvents"]
      )
      and self.sm.seen[
        "onroadEvents"
      ]
    )

    if (
      not self.CP.passive
      and initialized
    ):

      self.controls_update(
        CS,
        self.sm["carControl"],
      )

    self.initialized_prev = (
      initialized
    )

    self.CS_prev = CS

  # ===========================================================================
  # Params thread
  # ===========================================================================

  def params_thread(
    self,
    evt,
  ):

    while not evt.is_set():

      self.is_metric = (
        self.params.get_bool(
          "IsMetric"
        )
      )

      self.experimental_mode = (
        self.params.get_bool(
          "ExperimentalMode"
        )
        and self.CP.openpilotLongitudinalControl
      )

      time.sleep(
        0.1
      )

  # ===========================================================================
  # Card thread
  # ===========================================================================

  def card_thread(self):

    e = threading.Event()

    t = threading.Thread(
      target=self.params_thread,
      args=(e,),
    )

    try:

      t.start()

      while True:

        self.step()

        self.rk.monitor_time()

    finally:

      e.set()

      t.join()


# =============================================================================
# Main
# =============================================================================

def main():

  config_realtime_process(
    3,
    Priority.CTRL_HIGH,
  )

  car = Car()

  car.card_thread()


if __name__ == "__main__":
  main()
