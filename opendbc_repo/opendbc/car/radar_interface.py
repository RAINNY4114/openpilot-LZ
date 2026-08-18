#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MR76 Auxiliary Radar Interface

Stage 1:
    - Verify MR76 CANParser startup
    - Parse confirmed MR76 0x60B ObjectData frame
    - Do NOT assume 0x60C~0x614 are object frames
    - Do NOT invent DistLong / DistLat / VRel fields
    - Do NOT create leadOne
    - Do NOT control longitudinal

Confirmed from rlog forensic analysis:

    SRC 1
    0x60A -> 6 frames
    0x60B -> 398 frames
    0x60B -> 8 bytes

Current stage:
    Raw CAN verification only.

The actual 0x60B Motorola/Intel bit-field decoding
will be added after forensic analysis.
"""

from __future__ import annotations

import math
from typing import Dict

from cereal import car

from opendbc.can.parser import CANParser
from opendbc.car.interfaces import RadarInterfaceBase


# ============================================================
# Configuration
# ============================================================

MR76_STATUS_MSG = 0x60A
MR76_OBJECT_MSG = 0x60B

MAX_TARGETS = 10

MAX_DISTANCE = 150.0
MIN_DISTANCE = 1.5
MAX_LATERAL = 50.0

MAX_MISSING_FRAMES = 5


# ============================================================
# Track
# ============================================================

class MR76Track:

  def __init__(self, track_id: int):
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

  def update(
      self,
      dRel: float,
      yRel: float,
      vRel: float,
      yvRel: float,
      dyn_prop: int,
      cls: int,
      rcs: float,
  ):
    self.dRel = float(dRel)
    self.yRel = float(yRel)
    self.vRel = float(vRel)
    self.yvRel = float(yvRel)

    self.dyn_prop = int(dyn_prop)
    self.cls = int(cls)
    self.rcs = float(rcs)

    self.age += 1
    self.missing = 0

  def valid(self):

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


# ============================================================
# Radar Interface
# ============================================================

class RadarInterface(RadarInterfaceBase):

  def __init__(self, CP):

    self.CP = CP
    self.frame = 0

    self.tracks: Dict[int, MR76Track] = {}

    # --------------------------------------------------------
    # IMPORTANT
    #
    # This DragonPilot CANParser expects:
    #
    #     (signal_name, message_name)
    #
    # NOT:
    #
    #     (signal_name, message_name, message_id)
    #
    # --------------------------------------------------------

    signals = [
      ("Byte0", "ObjectData"),
      ("Byte1", "ObjectData"),
      ("Byte2", "ObjectData"),
      ("Byte3", "ObjectData"),
      ("Byte4", "ObjectData"),
      ("Byte5", "ObjectData"),
      ("Byte6", "ObjectData"),
      ("Byte7", "ObjectData"),
    ]

    checks = [
      ("ObjectData", 20),
    ]

    self.rcp = CANParser(
      "u_radar",
      signals,
      checks,
    )

  # ==========================================================
  # CAN update
  # ==========================================================

  def update(self, can_strings):

    self.frame += 1

    if not self.rcp.update_strings(can_strings):
      return None

    # --------------------------------------------------------
    # Stage 1:
    #
    # We intentionally do NOT decode these bytes into:
    #
    #     DistLong
    #     DistLat
    #     VRelLong
    #     VRelLat
    #     DynProp
    #     Class
    #     RCS
    #
    # because the 0x60B bit layout has not yet been proven.
    #
    # --------------------------------------------------------

    return self.make_radar_msg()

  # ==========================================================
  # RadarData
  # ==========================================================

  def make_radar_msg(self):

    ret = car.RadarData.new_message()

    ret.errors = []

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # No RadarData.points are created yet.
    #
    # This prevents unverified MR76 data from entering
    # radarState / longitudinal control.
    #
    # OEM radar remains the lead source.
    #
    # --------------------------------------------------------

    return ret
