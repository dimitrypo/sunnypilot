"""Personal Model 3 steering handover, below the unchanged EPS/Panda hard override.

Torque and Tesla's EPS hands-on classification are activity estimates, not physical
contact sensors. Their release timers must never be treated as proof of hands-off.
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
  RECOVERY_DELAYS = {"released": 0.2, "light": 0.5}

  def __init__(self):
    self.reset()

  def reset(self):
    self.paused = False
    self.hard_disengaged = False
    self.last_sample_time = None
    self.entry_since = None
    self.quiet_since = None
    self.condition = None
    self.reason = "inactive"

  def update(self, CS, *, requested_active: bool, target_angle: float, sample_time: float, valid: bool, resume_allowed: bool,
             hands_on_zero_since: float | None = None, driver_override: bool = False) -> bool:
    """Return lateral permission only; never set engagement, cruise, or driver contact.

    sample_time comes from the carState message timestamp, so duplicate/stale
    samples cannot advance timers. requested_active excludes our own pause latch.
    hands_on_zero_since is supplied only by the fresh, read-only CAN monitor;
    it identifies the current uninterrupted EPS no-holding interval.
    driver_override is the fresh EPS level-3 inhibit, not a full disengagement.
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
      self.entry_since = self.quiet_since = self.condition = None
      self.last_sample_time = None
      self.reason = "unavailable"
      return False

    # Mirror the independent CarController/Panda inhibit. Even alignment cannot
    # request steering at EPS level 3; lowering the level permits normal recovery.
    if driver_override:
      self.paused = True
      self.entry_since = self.quiet_since = self.condition = None
      if self.last_sample_time is None or sample_time > self.last_sample_time:
        self.last_sample_time = sample_time
      self.reason = "eps_driver_override"
      return False

    if self.last_sample_time is not None:
      if sample_time <= self.last_sample_time:
        if sample_time < self.last_sample_time:
          self.paused = True
          self.entry_since = self.quiet_since = self.condition = None
          self.reason = "unavailable"
        return not self.paused
      if sample_time - self.last_sample_time > self.MAX_SAMPLE_GAP:
        self.paused = True
        self.entry_since = self.quiet_since = self.condition = None
    self.last_sample_time = sample_time

    torque = abs(CS.steeringTorque)
    moving_wheel = abs(CS.steeringRateDeg) >= self.STEERING_RATE
    angle_error = abs(CS.steeringAngleDeg - target_angle)
    angle_disagreement = angle_error >= self.ANGLE_DISAGREEMENT
    strong_input = torque >= self.STRONG_TORQUE
    # EPS level zero can recognize release despite residual torsion-bar torque.
    # Its filtered classification can lag renewed force, so current strong
    # input still vetoes this timed path (alignment below is the explicit exception).
    eps_released = (not strong_input and hands_on_zero_since is not None and math.isfinite(hands_on_zero_since) and
                    0 <= hands_on_zero_since <= sample_time)

    # Agreement with the independent plan takes priority over ordinary driver
    # force and movement, both when handing back and while already active. The
    # earlier hard-override/fault/data checks and re-entry envelope still apply.
    if angle_error <= self.ALIGNMENT_ANGLE:
      self.entry_since = self.quiet_since = self.condition = None
      if self.paused and not resume_allowed:
        self.reason = "angle_limit"
        return False
      self.paused = False
      self.reason = "aligned"
      return True

    if not self.paused:
      # Use the same confirmed release evidence after handback, otherwise the
      # residual torque that required EPS detection would immediately pause again.
      confirmed_eps_release = eps_released and sample_time - hands_on_zero_since >= self.RECOVERY_DELAYS["released"] - 1e-9
      deliberate_input = torque >= self.PAUSE_TORQUE and (moving_wheel or angle_disagreement) and not confirmed_eps_release
      if deliberate_input:
        if self.entry_since is None:
          self.entry_since = sample_time
      else:
        self.entry_since = None
      if strong_input or (self.entry_since is not None and sample_time - self.entry_since >= self.ENTRY_DELAY - 1e-9):
        self.paused = True
        self.quiet_since = self.condition = None
        self.reason = "driver_input"
      return not self.paused

    # Release has priority even if the freely returning wheel still moves or the
    # planner wants a different angle. Otherwise, steady force at an offset is
    # still an active correction, not evidence that the maneuver has finished.
    torque_released = torque <= self.RELEASE_TORQUE
    if torque_released or eps_released:
      condition = "released"
    elif torque >= self.PAUSE_TORQUE or moving_wheel or (torque >= self.HOLD_TORQUE and angle_disagreement):
      self.quiet_since = self.condition = None
      self.reason = "driver_input"
      return False
    else:
      condition = "light"

    if condition != self.condition:
      self.quiet_since = sample_time
      self.condition = condition

    if eps_released and not torque_released:
      # Do not reuse quiet time from before an intervening nonzero/invalid CAN
      # sample, or count a zero interval accumulated before this handover.
      self.quiet_since = max(self.quiet_since, hands_on_zero_since)
    self.reason = "released_eps" if eps_released and not torque_released else condition
    if sample_time - self.quiet_since >= self.RECOVERY_DELAYS[condition] - 1e-9:
      if not resume_allowed:
        # Preserve the completed quiet period, but wait for an angle that the
        # existing actuator limits can accept without an abrupt absolute clamp.
        self.reason = "angle_limit"
        return False
      self.paused = False
      self.entry_since = self.quiet_since = self.condition = None
    return not self.paused
