#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DP 10.2 Scene Understanding
===========================

Lightweight scene-perception layer for DP 10.2.

REAL DP 10.2 INPUTS
-------------------

modelV2:
    laneLineProbs
    laneLines
    leadsV3
    velocity.x

liveTracks:
    dRel
    yRel
    vRel
    measured
    cnt
    trackId

mr76State:
    Existing MR76 auxiliary-radar object data.

DESIGN
------

This module is READ-ONLY.

It does not:

    - read modelV2 only
    - read liveTracks only
    - read mr76State only
    - does NOT publish radarState
    - create leadOne
    - create leadTwo
    - modify CarState
    - modify CarControl
    - send CAN
    - create threads
    - create timers
    - create Params

The result is only a normalized local scene representation.

IMPORTANT
---------

OEM radar source:
    liveTracks

Auxiliary radar:
    mr76State

Camera/model:
    modelV2

This module deliberately does not depend on any radar-source
field or radar track interface outside liveTracks.
"""

import math


class SceneUnderstanding:

  # ========================================================================
  # Scene types
  # ========================================================================

  SCENE_NORMAL = "normal"
  SCENE_OBSTACLE = "obstacle"
  SCENE_STATIC_OBSTACLE = "static_obstacle"
  SCENE_ONCOMING = "oncoming_vehicle"
  SCENE_SLOW_VEHICLE = "slow_vehicle"
  SCENE_OVERTAKE = "overtake_possible"
  SCENE_PEDESTRIAN = "pedestrian_area"
  SCENE_CONSTRUCTION = "construction_zone"

  # ========================================================================
  # Object types
  # ========================================================================

  OBJECT_UNKNOWN = -1
  OBJECT_CAR = 0
  OBJECT_BIKE = 1
  OBJECT_PEDESTRIAN = 2
  OBJECT_CONE = 3
  OBJECT_MOTORCYCLE = 4

  # ========================================================================
  # Sources
  # ========================================================================

  SOURCE_MODEL = "modelV2"
  SOURCE_LIVE_TRACKS = "liveTracks"
  SOURCE_MR76 = "mr76State"

  # ========================================================================
  # Model thresholds
  # ========================================================================

  MODEL_LEAD_PROB_MIN = 0.30
  MODEL_LANE_PROB_MIN = 0.50

  # ========================================================================
  # OEM radar thresholds
  # ========================================================================

  RADAR_MAX_DISTANCE = 150.0
  RADAR_MIN_DISTANCE = 0.5

  # A radar target must be sufficiently stable before being treated
  # as a strong scene target.
  RADAR_MIN_COUNT = 1

  # ========================================================================
  # MR76 thresholds
  # ========================================================================

  MR76_MAX_DISTANCE = 120.0
  MR76_MIN_CONFIDENCE = 0.55

  # ========================================================================
  # Scene thresholds
  # ========================================================================

  ONCOMING_DISTANCE = 80.0
  ONCOMING_LATERAL_MIN = 1.8
  ONCOMING_VREL_MAX = -8.0

  SLOW_VEHICLE_DISTANCE = 50.0
  SLOW_VEHICLE_VREL_MAX = -3.0

  STATIC_OBSTACLE_DISTANCE = 60.0
  STATIC_VREL_MAX = 1.0

  LANE_BLOCK_DISTANCE = 40.0
  LANE_LEFT_LIMIT = 2.0
  LANE_RIGHT_LIMIT = -2.0

  # ========================================================================
  # Fusion thresholds
  # ========================================================================

  # Deliberately conservative.  Fusion is only used to attach confirmation
  # metadata, not to rewrite the underlying perception source.
  FUSION_DISTANCE = 2.5
  FUSION_LATERAL = 1.5

  # ========================================================================
  # Initialization
  # ========================================================================

  def __init__(self):
    self.camera_objects = []
    self.radar_objects = []

    # MR76 independent multi-object cache.
    self.mr76_objects = []
    self.mr76_object_count = 0

    self.objects = []

    self.scene_type = self.SCENE_NORMAL

    self.object_counts = {
      "cars": 0,
      "pedestrians": 0,
      "bikes": 0,
      "motorcycles": 0,
      "cones": 0,
    }

    self.obstacle_distance = float("inf")

    self.slow_vehicle = False
    self.static_obstacle = False
    self.oncoming_vehicle = False

    self.avoid_required = False
    self.overtake_available = False

    self.left_blocked = False
    self.right_blocked = False

    # Model state
    self.model_velocity = 0.0

    self.left_lane_visible = False
    self.right_lane_visible = False
    self.lane_confidence = 0.0

    # Model lead is a hint only.
    self.model_lead_distance = float("inf")
    self.model_lead_lateral = 0.0
    self.model_lead_velocity = 0.0
    self.model_lead_probability = 0.0
    self.model_lead_valid = False

  # ========================================================================
  # Safe helpers
  # ========================================================================

  @staticmethod
  def _safe_float(value, default=0.0):
    try:
      value = float(value)
      if math.isfinite(value):
        return value
    except Exception:
      pass
    return default

  @staticmethod
  def _safe_int(value, default=-1):
    try:
      return int(value)
    except Exception:
      return default

  @staticmethod
  def _safe_bool(value, default=False):
    try:
      return bool(value)
    except Exception:
      return default

  @staticmethod
  def _safe_len(value):
    try:
      return len(value)
    except Exception:
      return 0

  @staticmethod
  def _get(obj, name, default=None):
    try:
      return getattr(obj, name)
    except Exception:
      return default

  @staticmethod
  def _distance(x1, y1, x2, y2):
    dx = x1 - x2
    dy = y1 - y2
    return math.sqrt(dx * dx + dy * dy)

  # ========================================================================
  # Main update
  # ========================================================================

  def update(self, sm):
    """
    Read current DP 10.2 perception state.

    Returns:

        (
          scene_type,
          objects,
          behavior_hint,
        )
    """

    self.camera_objects = self._process_model(sm)
    self.radar_objects = self._process_live_tracks(sm)
    self.mr76_objects = self._process_mr76(sm)

    self.objects = self._fuse_objects(
      self.camera_objects,
      self.radar_objects,
      self.mr76_objects,
    )

    self._update_statistics()
    self._detect_oncoming()
    self._detect_slow_vehicle()
    self._detect_static_obstacle()
    self._check_lane_block()

    self.scene_type = self._classify_scene()

    return (
      self.scene_type,
      self.objects,
      self.get_behavior_hint(),
    )

  # ========================================================================
  # ModelV2
  # ========================================================================

  def _process_model(self, sm):
    """
    Read only the confirmed DP 10.2 model fields:

        velocity.x
        laneLineProbs
        laneLines
        leadsV3

    laneLines are treated as geometry metadata only.
    """

    objects = []

    try:
      model = sm["modelV2"]
    except Exception:
      self._reset_model_state()
      return objects

    self._process_model_velocity(model)
    self._process_lane_lines(model)

    # laneLines are intentionally not converted into obstacle objects.
    self._process_model_lead(model, objects)

    return objects

  # ========================================================================
  # Model velocity
  # ========================================================================

  def _process_model_velocity(self, model):
    self.model_velocity = 0.0

    try:
      velocity = self._get(
        model,
        "velocity",
        None,
      )

      if velocity is None:
        return

      velocity_x = self._get(
        velocity,
        "x",
        None,
      )

      if self._safe_len(velocity_x) <= 0:
        return

      self.model_velocity = self._safe_float(
        velocity_x[0],
        0.0,
      )

    except Exception:
      self.model_velocity = 0.0

  # ========================================================================
  # Lane information
  # ========================================================================

  def _process_lane_lines(self, model):
    self.left_lane_visible = False
    self.right_lane_visible = False
    self.lane_confidence = 0.0

    try:
      probs = self._get(
        model,
        "laneLineProbs",
        None,
      )

      if self._safe_len(probs) < 4:
        return

      left_prob = self._safe_float(
        probs[1],
        0.0,
      )

      right_prob = self._safe_float(
        probs[2],
        0.0,
      )

      left_prob = min(
        max(left_prob, 0.0),
        1.0,
      )

      right_prob = min(
        max(right_prob, 0.0),
        1.0,
      )

      self.left_lane_visible = (
        left_prob >= self.MODEL_LANE_PROB_MIN
      )

      self.right_lane_visible = (
        right_prob >= self.MODEL_LANE_PROB_MIN
      )

      self.lane_confidence = (
        left_prob + right_prob
      ) * 0.5

    except Exception:
      self.left_lane_visible = False
      self.right_lane_visible = False
      self.lane_confidence = 0.0

  # ========================================================================
  # Model lead
  # ========================================================================

  def _process_model_lead(self, model, objects):
    """
    leadsV3 is a camera/model lead hint.

    It is never converted into a radar lead message.
    """

    self.model_lead_distance = float("inf")
    self.model_lead_lateral = 0.0
    self.model_lead_velocity = 0.0
    self.model_lead_probability = 0.0
    self.model_lead_valid = False

    try:
      leads = self._get(
        model,
        "leadsV3",
        None,
      )

      if self._safe_len(leads) <= 0:
        return

      lead = leads[0]

      probability = self._safe_float(
        self._get(
          lead,
          "prob",
          0.0,
        ),
        0.0,
      )

      if probability < self.MODEL_LEAD_PROB_MIN:
        return

      distance = self._safe_float(
        self._get(
          lead,
          "x",
          0.0,
        ),
        0.0,
      )

      lateral = self._safe_float(
        self._get(
          lead,
          "y",
          0.0,
        ),
        0.0,
      )

      velocity = self._safe_float(
        self._get(
          lead,
          "v",
          0.0,
        ),
        0.0,
      )

      if distance <= 0.0:
        return

      self.model_lead_distance = distance
      self.model_lead_lateral = lateral
      self.model_lead_velocity = velocity
      self.model_lead_probability = probability
      self.model_lead_valid = True

      objects.append({
        "x": distance,
        "y": lateral,
        "speed": velocity,
        "type": self.OBJECT_CAR,
        "confidence": probability,
        "source": self.SOURCE_MODEL,
        "model_lead": True,
      })

    except Exception:
      self.model_lead_distance = float("inf")
      self.model_lead_lateral = 0.0
      self.model_lead_velocity = 0.0
      self.model_lead_probability = 0.0
      self.model_lead_valid = False

  # ========================================================================
  # Model reset
  # ========================================================================

  def _reset_model_state(self):
    self.model_velocity = 0.0
    self.left_lane_visible = False
    self.right_lane_visible = False
    self.lane_confidence = 0.0

    self.model_lead_distance = float("inf")
    self.model_lead_lateral = 0.0
    self.model_lead_velocity = 0.0
    self.model_lead_probability = 0.0
    self.model_lead_valid = False

  # ========================================================================
  # liveTracks
  # ========================================================================

  def _process_live_tracks(self, sm):
    """
    Read the confirmed DP 10.2 OEM radar interface.

    Track fields:

        dRel
        yRel
        vRel
        measured
        cnt
        trackId
    """

    objects = []

    try:
      live_tracks = sm["liveTracks"]
    except Exception:
      return objects

    try:
      tracks = list(live_tracks)
    except Exception:
      return objects

    for track in tracks:
      try:
        d_rel = self._safe_float(
          self._get(
            track,
            "dRel",
            0.0,
          ),
          0.0,
        )

        if (
          d_rel < self.RADAR_MIN_DISTANCE
          or
          d_rel > self.RADAR_MAX_DISTANCE
        ):
          continue

        y_rel = self._safe_float(
          self._get(
            track,
            "yRel",
            0.0,
          ),
          0.0,
        )

        v_rel = self._safe_float(
          self._get(
            track,
            "vRel",
            0.0,
          ),
          0.0,
        )

        measured = self._safe_bool(
          self._get(
            track,
            "measured",
            False,
          ),
          False,
        )

        count = self._safe_int(
          self._get(
            track,
            "cnt",
            0,
          ),
          0,
        )

        track_id = self._safe_int(
          self._get(
            track,
            "trackId",
            -1,
          ),
          -1,
        )

        if count < self.RADAR_MIN_COUNT:
          continue

        confidence = 0.90

        if not measured:
          confidence = 0.75

        if count >= 3:
          confidence = min(
            confidence + 0.05,
            1.0,
          )

        objects.append({
          "x": d_rel,
          "y": y_rel,
          "speed": v_rel,
          "type": self.OBJECT_CAR,
          "confidence": confidence,
          "source": self.SOURCE_LIVE_TRACKS,
          "measured": measured,
          "cnt": count,
          "track_id": track_id,
          "oem_radar": True,
        })

      except Exception:
        continue

    return objects

  # ========================================================================
  # MR76
  # ========================================================================

  def _process_mr76(self, sm):
    """
    Read the existing MR76 state.

    MR76 remains auxiliary.

    Field aliases are intentionally limited to the fields already used
    by the existing MR76 implementation.
    """

    objects = []

    try:
      mr76 = sm["mr76State"]
    except Exception:
      return objects

    raw_objects = self._find_mr76_objects(mr76)

    if raw_objects is None:
      self.mr76_object_count = 0
      return objects

    try:
      raw_objects = list(raw_objects)
    except Exception:
      self.mr76_object_count = 0
      return objects

    for raw in raw_objects:
      try:
        distance = self._mr76_distance(raw)

        if (
          distance <= 0.0
          or
          distance > self.MR76_MAX_DISTANCE
        ):
          continue

        lateral = self._mr76_lateral(raw)
        velocity = self._mr76_velocity(raw)
        confidence = self._mr76_confidence(raw)

        if confidence < self.MR76_MIN_CONFIDENCE:
          continue

        obj_type = self._safe_int(
          self._get(
            raw,
            "type",
            self.OBJECT_CAR,
          ),
          self.OBJECT_CAR,
        )

        objects.append({
          "x": distance,
          "y": lateral,
          "speed": velocity,
          "type": obj_type,
          "confidence": confidence,
          "source": self.SOURCE_MR76,
          "mr76": True,
        })

      except Exception:
        continue

    return objects

  # ========================================================================
  # MR76 object list
  # ========================================================================

  def _find_mr76_objects(self, mr76):
    for field in (
      "objects",
      "tracks",
      "radarObjects",
    ):
      try:
        value = self._get(
          mr76,
          field,
          None,
        )

        if value is not None:
          return value

      except Exception:
        continue

    return None

  # ========================================================================
  # MR76 distance
  # ========================================================================

  def _mr76_distance(self, obj):
    for field in (
      "dRel",
      "distLong",
      "distance",
      "DistLong",
    ):
      value = self._get(
        obj,
        field,
        None,
      )

      if value is not None:
        return self._safe_float(
          value,
          999.0,
        )

    return 999.0

  # ========================================================================
  # MR76 lateral
  # ========================================================================

  def _mr76_lateral(self, obj):
    for field in (
      "yRel",
      "distLat",
      "lateral",
      "DistLat",
    ):
      value = self._get(
        obj,
        field,
        None,
      )

      if value is not None:
        return self._safe_float(
          value,
          0.0,
        )

    return 0.0

  # ========================================================================
  # MR76 relative velocity
  # ========================================================================

  def _mr76_velocity(self, obj):
    for field in (
      "vRel",
      "vRelLong",
      "VRelLong",
    ):
      value = self._get(
        obj,
        field,
        None,
      )

      if value is not None:
        return self._safe_float(
          value,
          0.0,
        )

    return 0.0

  # ========================================================================
  # MR76 confidence
  # ========================================================================

  def _mr76_confidence(self, obj):
    for field in (
      "confidence",
      "prob",
    ):
      value = self._get(
        obj,
        field,
        None,
      )

      if value is not None:
        return min(
          max(
            self._safe_float(
              value,
              0.65,
            ),
            0.0,
          ),
          1.0,
        )

    return 0.65

  # ========================================================================
  # Object fusion
  # ========================================================================

  def _fuse_objects(
      self,
      model_objects,
      radar_objects,
      mr76_objects):

    """
    Lightweight fusion.

    Important:

        This is local scene fusion only.

    liveTracks:
        primary radar object.

    MR76:
        auxiliary confirmation.

    modelV2:
        camera/model confirmation.

    No source message is modified.
    """

    fused = []

    # Primary ordering is intentional:
    #
    #   OEM radar first
    #   MR76 second
    #   model lead last
    #
    # This means the physical radar distance is available first.

    all_objects = (
      list(radar_objects)
      +
      list(mr76_objects)
      +
      list(model_objects)
    )

    for obj in all_objects:
      if not isinstance(obj, dict):
        continue

      ox = self._safe_float(
        obj.get("x", 999.0),
        999.0,
      )

      oy = self._safe_float(
        obj.get("y", 0.0),
        0.0,
      )

      if ox <= 0.0:
        continue

      match = None

      for target in fused:
        tx = self._safe_float(
          target.get("x", 999.0),
          999.0,
        )

        ty = self._safe_float(
          target.get("y", 0.0),
          0.0,
        )

        if (
          abs(ox - tx) <= self.FUSION_DISTANCE
          and
          abs(oy - ty) <= self.FUSION_LATERAL
        ):
          match = target
          break

      if match is None:
        copy = dict(obj)

        copy.setdefault(
          "confidence",
          0.0,
        )

        fused.append(copy)
        continue

      source = str(
        obj.get(
          "source",
          "",
        )
      )

      # ------------------------------------------------------------
      # OEM radar remains range authority.
      # ------------------------------------------------------------

      if source == self.SOURCE_LIVE_TRACKS:
        match["x"] = ox
        match["y"] = oy
        match["speed"] = self._safe_float(
          obj.get(
            "speed",
            match.get(
              "speed",
              0.0,
            ),
          ),
          0.0,
        )

        match["oem_radar"] = True

      # ------------------------------------------------------------
      # MR76 only confirms.
      # ------------------------------------------------------------

      elif source == self.SOURCE_MR76:
        match["mr76"] = True

      # ------------------------------------------------------------
      # Model only confirms.
      # ------------------------------------------------------------

      elif source == self.SOURCE_MODEL:
        match["model"] = True

      match["confidence"] = max(
        self._safe_float(
          match.get(
            "confidence",
            0.0,
          ),
          0.0,
        ),
        self._safe_float(
          obj.get(
            "confidence",
            0.0,
          ),
          0.0,
        ),
      )

      old_source = str(
        match.get(
          "source",
          "",
        )
      )

      if source and source not in old_source:
        match["source"] = (
          old_source +
          ("+" if old_source else "") +
          source
        )

    return fused

  # ========================================================================
  # Statistics
  # ========================================================================

  def _update_statistics(self):
    for key in self.object_counts:
      self.object_counts[key] = 0

    self.obstacle_distance = float("inf")

    for obj in self.objects:
      obj_type = self._safe_int(
        obj.get(
          "type",
          self.OBJECT_UNKNOWN,
        ),
        self.OBJECT_UNKNOWN,
      )

      if obj_type == self.OBJECT_CAR:
        self.object_counts["cars"] += 1

      elif obj_type == self.OBJECT_PEDESTRIAN:
        self.object_counts["pedestrians"] += 1

      elif obj_type == self.OBJECT_BIKE:
        self.object_counts["bikes"] += 1

      elif obj_type == self.OBJECT_MOTORCYCLE:
        self.object_counts["motorcycles"] += 1

      elif obj_type == self.OBJECT_CONE:
        self.object_counts["cones"] += 1

      source = str(
        obj.get(
          "source",
          "",
        )
      )

      if (
        self.SOURCE_LIVE_TRACKS in source
        or
        self.SOURCE_MR76 in source
      ):
        distance = self._safe_float(
          obj.get(
            "x",
            999.0,
          ),
          999.0,
        )

        if (
          0.0 < distance < self.obstacle_distance
        ):
          self.obstacle_distance = distance

  # ========================================================================
  # Oncoming vehicle
  # ========================================================================

  def _detect_oncoming(self):
    self.oncoming_vehicle = False

    for obj in self.objects:
      if obj.get("type") != self.OBJECT_CAR:
        continue

      source = str(
        obj.get(
          "source",
          "",
        )
      )

      # Oncoming detection should be radar-backed.
      if (
        self.SOURCE_LIVE_TRACKS not in source
        and
        self.SOURCE_MR76 not in source
      ):
        continue

      lateral = abs(
        self._safe_float(
          obj.get(
            "y",
            0.0,
          ),
          0.0,
        )
      )

      distance = self._safe_float(
        obj.get(
          "x",
          999.0,
        ),
        999.0,
      )

      velocity = self._safe_float(
        obj.get(
          "speed",
          0.0,
        ),
        0.0,
      )

      if (
        lateral > self.ONCOMING_LATERAL_MIN
        and
        distance < self.ONCOMING_DISTANCE
        and
        velocity < self.ONCOMING_VREL_MAX
      ):
        obj["oncoming"] = True
        obj["risk"] = "high"
        self.oncoming_vehicle = True

  # ========================================================================
  # Slow vehicle
  # ========================================================================

  def _detect_slow_vehicle(self):
    self.slow_vehicle = False

    for obj in self.objects:
      if obj.get("type") != self.OBJECT_CAR:
        continue

      source = str(
        obj.get(
          "source",
          "",
        )
      )

      if (
        self.SOURCE_LIVE_TRACKS not in source
        and
        self.SOURCE_MR76 not in source
      ):
        continue

      distance = self._safe_float(
        obj.get(
          "x",
          999.0,
        ),
        999.0,
      )

      velocity = self._safe_float(
        obj.get(
          "speed",
          0.0,
        ),
        0.0,
      )

      if (
        distance < self.SLOW_VEHICLE_DISTANCE
        and
        velocity < self.SLOW_VEHICLE_VREL_MAX
      ):
        obj["slow_vehicle"] = True
        self.slow_vehicle = True

  # ========================================================================
  # Static obstacle
  # ========================================================================

  def _detect_static_obstacle(self):
    self.static_obstacle = False

    for obj in self.objects:
      source = str(
        obj.get(
          "source",
          "",
        )
      )

      # Only OEM radar is trusted for this conservative trigger.
      if self.SOURCE_LIVE_TRACKS not in source:
        continue

      distance = self._safe_float(
        obj.get(
          "x",
          999.0,
        ),
        999.0,
      )

      velocity = self._safe_float(
        obj.get(
          "speed",
          0.0,
        ),
        0.0,
      )

      if (
        distance < self.STATIC_OBSTACLE_DISTANCE
        and
        abs(velocity) < self.STATIC_VREL_MAX
      ):
        obj["static_obstacle"] = True
        self.static_obstacle = True

  # ========================================================================
  # Lane block
  # ========================================================================

  def _check_lane_block(self):
    self.left_blocked = False
    self.right_blocked = False

    for obj in self.objects:
      distance = self._safe_float(
        obj.get(
          "x",
          999.0,
        ),
        999.0,
      )

      if distance > self.LANE_BLOCK_DISTANCE:
        continue

      source = str(
        obj.get(
          "source",
          "",
        )
      )

      if (
        self.SOURCE_LIVE_TRACKS not in source
        and
        self.SOURCE_MR76 not in source
      ):
        continue

      lateral = self._safe_float(
        obj.get(
          "y",
          0.0,
        ),
        0.0,
      )

      if lateral > self.LANE_LEFT_LIMIT:
        self.left_blocked = True

      if lateral < self.LANE_RIGHT_LIMIT:
        self.right_blocked = True

  # ========================================================================
  # Scene classification
  # ========================================================================

  def _classify_scene(self):

    if self.oncoming_vehicle:
      return self.SCENE_ONCOMING

    if self.static_obstacle:
      return self.SCENE_STATIC_OBSTACLE

    if self.slow_vehicle:
      return self.SCENE_SLOW_VEHICLE

    if self.object_counts["pedestrians"] > 2:
      return self.SCENE_PEDESTRIAN

    if self.object_counts["cones"] >= 3:
      return self.SCENE_CONSTRUCTION

    return self.SCENE_NORMAL

  # ========================================================================
  # Avoidance
  # ========================================================================

  def get_avoidance_request(self):
    self.avoid_required = (
      self.oncoming_vehicle
      or
      self.static_obstacle
    )

    return {
      "avoid": self.avoid_required,
      "left_blocked": self.left_blocked,
      "right_blocked": self.right_blocked,
      "oncoming": self.oncoming_vehicle,
    }

  # ========================================================================
  # Overtake
  # ========================================================================

  def get_overtake_request(self):
    self.overtake_available = False

    if (
      self.slow_vehicle
      and
      not self.left_blocked
      and
      not self.oncoming_vehicle
    ):
      self.overtake_available = True

    return {
      "overtake": self.overtake_available,
    }

  # ========================================================================
  # Behavior hint
  # ========================================================================

  def get_behavior_hint(self):
    avoidance = self.get_avoidance_request()
    overtake = self.get_overtake_request()

    return {
      "scene": self.scene_type,

      "slow_vehicle": self.slow_vehicle,

      "static_obstacle":
        self.static_obstacle,

      "oncoming":
        self.oncoming_vehicle,

      "avoid":
        avoidance["avoid"],

      "left_blocked":
        avoidance["left_blocked"],

      "right_blocked":
        avoidance["right_blocked"],

      "overtake":
        overtake["overtake"],
    }

  # ========================================================================
  # Scene information
  # ========================================================================

  def get_scene_info(self):
    return {
      "scene_type": self.scene_type,

      "objects": list(
        self.objects
      ),

      "object_counts": dict(
        self.object_counts
      ),

      "obstacle_distance":
        self.obstacle_distance,

      "slow_vehicle":
        self.slow_vehicle,

      "static_obstacle":
        self.static_obstacle,

      "oncoming_vehicle":
        self.oncoming_vehicle,

      "avoid_required":
        self.avoid_required,

      "overtake_available":
        self.overtake_available,

      "left_blocked":
        self.left_blocked,

      "right_blocked":
        self.right_blocked,

      "model_velocity":
        self.model_velocity,

      "model_lead_distance":
        self.model_lead_distance,

      "model_lead_lateral":
        self.model_lead_lateral,

      "model_lead_velocity":
        self.model_lead_velocity,

      "model_lead_probability":
        self.model_lead_probability,

      "model_lead_valid":
        self.model_lead_valid,

      "left_lane_visible":
        self.left_lane_visible,

      "right_lane_visible":
        self.right_lane_visible,

      "lane_confidence":
        self.lane_confidence,
    }
