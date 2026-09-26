"""Personal Model 3 steering handover, below the unchanged EPS/Panda hard override.

Torque is an activity estimate, not a hand-contact sensor. These initial thresholds
need vehicle validation; the release timer must never be treated as proof of hands-off.
"""
import math


class TeslaSteeringPause:
  RELEASE_TORQUE = 0.2  # Nm
  HOLD_TORQUE = 0.3  # Nm; continued input while maintaining an offset
  PAUSE_TORQUE = 0.8  # Nm, together with steering motion or target disagreement
  STRONG_TORQUE = 1.5  # Nm; yield immediately, without waiting for motion
  ANGLE_DISAGREEMENT = 3.0  # steering-wheel degrees
  ALIGNMENT_ANGLE = 1.0  # steering-wheel degrees from the independent planner target
  STEERING_RATE = 5.0  # steering-wheel degrees/s
  ENTRY_DELAY = 0.05  # seconds of deliberate input; ignore isolated small spikes
  MAX_SAMPLE_GAP = 0.1  # a gap cannot count as evidence of continuous release
  RECOVERY_DELAYS = {"released": 0.2, "aligned": 0.2, "light": 0.5, "firm": 1.5}

  def __init__(self):
    self.reset()

  def reset(self):
    self.paused = False
    self.hard_disengaged = False
    self.last_sample_time = None
    self.entry_since = None
    self.quiet_since = None
    self.fast_since = None
    self.condition = None
    self.reason = "inactive"

  def update(self, CS, *, requested_active: bool, target_angle: float, sample_time: float, valid: bool, resume_allowed: bool) -> bool:
    """Return lateral permission only; never set engagement, cruise, or driver contact.

    sample_time comes from the carState message timestamp, so duplicate/stale
    samples cannot advance timers. requested_active excludes our own pause latch.
    """
    if not requested_active:
      self.reset()
      return False

    # A hard override must go through normal disengagement/re-engagement. Releasing
    # torque alone must not clear it while the upstream active state catches up.
    if CS.steeringDisengage:
      self.hard_disengaged = True
    if self.hard_disengaged:
      self.paused = True
      self.reason = "hard_disengage"
      return False

    signals = (CS.steeringTorque, CS.steeringRateDeg, CS.steeringAngleDeg, target_angle, sample_time)
    if not valid or not CS.canValid or CS.steerFaultTemporary or CS.steerFaultPermanent or not all(map(math.isfinite, signals)):
      self.paused = True
      self.entry_since = self.quiet_since = self.fast_since = self.condition = None
      self.last_sample_time = None
      self.reason = "unavailable"
      return False

    if self.last_sample_time is not None:
      if sample_time <= self.last_sample_time:
        if sample_time < self.last_sample_time:
          self.paused = True
          self.entry_since = self.quiet_since = self.fast_since = self.condition = None
          self.reason = "unavailable"
        return not self.paused
      if sample_time - self.last_sample_time > self.MAX_SAMPLE_GAP:
        self.paused = True
        self.entry_since = self.quiet_since = self.fast_since = self.condition = None
    self.last_sample_time = sample_time

    torque = abs(CS.steeringTorque)
    moving_wheel = abs(CS.steeringRateDeg) >= self.STEERING_RATE
    angle_error = abs(CS.steeringAngleDeg - target_angle)
    angle_disagreement = angle_error >= self.ANGLE_DISAGREEMENT
    strong_input = torque >= self.STRONG_TORQUE

    if not self.paused:
      deliberate_input = torque >= self.PAUSE_TORQUE and (moving_wheel or angle_disagreement)
      if deliberate_input:
        if self.entry_since is None:
          self.entry_since = sample_time
      else:
        self.entry_since = None
      if strong_input or (self.entry_since is not None and sample_time - self.entry_since >= self.ENTRY_DELAY - 1e-9):
        self.paused = True
        self.quiet_since = self.fast_since = self.condition = None
        self.reason = "driver_input"
      return not self.paused

    # Release has priority even if the freely returning wheel still moves or the
    # planner wants a different angle. Otherwise, steady force at an offset is
    # still an active correction, not evidence that the maneuver has finished.
    if torque <= self.RELEASE_TORQUE:
      condition = "released"
    elif strong_input or (torque >= self.HOLD_TORQUE and (moving_wheel or angle_disagreement)):
      self.quiet_since = self.fast_since = self.condition = None
      self.reason = "driver_input"
      return False
    else:
      condition = "light" if torque < self.PAUSE_TORQUE else "firm"

    if condition != self.condition:
      self.quiet_since = sample_time
      self.condition = condition

    # A settled wheel agreeing with the live plan can hand back while held.
    # Release and alignment share a continuous fast timer despite torque noise.
    # Keep the ordinary contact timer independent: jitter across the alignment
    # boundary must not repeatedly restart the longer light/firm recovery.
    aligned = not moving_wheel and angle_error <= self.ALIGNMENT_ANGLE
    fast_recovery = condition == "released" or aligned
    if not fast_recovery:
      self.fast_since = None
    elif self.fast_since is None:
      self.fast_since = sample_time
    self.reason = "aligned" if aligned and condition != "released" else condition
    fast_ready = self.fast_since is not None and sample_time - self.fast_since >= self.RECOVERY_DELAYS["aligned"] - 1e-9
    quiet_ready = sample_time - self.quiet_since >= self.RECOVERY_DELAYS[condition] - 1e-9
    if fast_ready or quiet_ready:
      if not resume_allowed:
        # Preserve the completed quiet period, but wait for an angle that the
        # existing actuator limits can accept without an abrupt absolute clamp.
        self.reason = "angle_limit"
        return False
      self.paused = False
      self.entry_since = self.quiet_since = self.fast_since = self.condition = None
    return not self.paused
