"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import math
import time

import cereal.messaging as messaging
from cereal import log, custom

from opendbc.car import structs
from opendbc.car.lateral import get_max_angle_vm
from opendbc.car.tesla.carcontroller import get_safety_CP
from opendbc.car.tesla.values import CarControllerParams
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.sunnypilot import PARAMS_UPDATE_PERIOD
from openpilot.sunnypilot.livedelay.helpers import get_lat_delay
from openpilot.sunnypilot.modeld_v2.modeld_base import ModelStateBase
from openpilot.sunnypilot.selfdrive.controls.lib.blinker_pause_lateral import BlinkerPauseLateral
from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_v0 import LatControlTorque as LatControlTorqueV0
from openpilot.sunnypilot.selfdrive.controls.lib.tesla_hands_on import TeslaHandsOnMonitor
from openpilot.sunnypilot.selfdrive.controls.lib.tesla_steering_pause import TeslaSteeringPause


class ControlsExt(ModelStateBase):
  def __init__(self, CP: structs.CarParams, params: Params):
    ModelStateBase.__init__(self)
    self.CP = CP
    self.params = params
    self._param_update_time: float = 0.0
    self.blinker_pause_lateral = BlinkerPauseLateral()
    self.tesla_steering_pause = TeslaSteeringPause() if CP.carFingerprint == "TESLA_MODEL_3" else None
    self.tesla_safety_vm = VehicleModel(get_safety_CP()) if self.tesla_steering_pause is not None else None
    self.tesla_hands_on = TeslaHandsOnMonitor() if self.tesla_steering_pause is not None else None
    self.tesla_can_sock = messaging.sub_sock('can') if self.tesla_hands_on is not None else None
    self.tesla_pause_log_time = None

    cloudlog.info("controlsd_ext is waiting for CarParamsSP")
    self.CP_SP = messaging.log_from_bytes(params.get("CarParamsSP", block=True), custom.CarParamsSP)
    cloudlog.info("controlsd_ext got CarParamsSP")

    self.sm_services_ext = ['radarState', 'selfdriveStateSP']
    self.pm_services_ext = ['carControlSP']

  def initialize_lateral_control(self, lac, CI, dt):
    enforce_torque_control = self.params.get_bool("EnforceTorqueControl")
    torque_versions = self.params.get("TorqueControlTune")
    if not enforce_torque_control:
      if self.CP.lateralTuning.which() == 'torque':
        return LatControlTorqueV0(self.CP, self.CP_SP, CI, dt)  # FIXME-SP: revert when upstream fixes tuning issues with v1
      return lac

    if torque_versions == 0.0:  # v0
      return LatControlTorqueV0(self.CP, self.CP_SP, CI, dt)
    else:
      return lac

  def get_params_sp(self, sm: messaging.SubMaster) -> None:
    if time.monotonic() - self._param_update_time > PARAMS_UPDATE_PERIOD:
      self.blinker_pause_lateral.get_params()

      if self.CP.lateralTuning.which() == 'torque':
        self.lat_delay = get_lat_delay(self.params, sm["liveDelay"].lateralDelay)

      self._param_update_time = time.monotonic()

  def get_lat_active(self, sm: messaging.SubMaster) -> bool:
    if self.blinker_pause_lateral.update(sm['carState']):
      return False

    return self.get_lat_requested(sm)

  @staticmethod
  def get_lat_requested(sm: messaging.SubMaster) -> bool:
    ss_sp = sm['selfdriveStateSP']
    if ss_sp.mads.available:
      return bool(ss_sp.mads.active)

    # MADS not available, use stock state to engage
    return bool(sm['selfdriveState'].active)

  def apply_tesla_steering_pause(self, sm: messaging.SubMaster, lat_active: bool, planned_curvature: float) -> bool:
    if self.tesla_steering_pause is None:
      return lat_active

    CS = sm['carState']
    lp = sm['liveParameters']
    hands_on_zero_since = None
    if self.tesla_hands_on is not None:
      hands_on_zero_since = self.tesla_hands_on.update(messaging.drain_sock_raw(self.tesla_can_sock), time.monotonic_ns())
    # Use the live planner target, NOT the actuator output/current curvature that
    # deliberately tracks the measured wheel angle while lateral control is off.
    target_angle = math.degrees(self.VM.get_steer_from_curvature(-planned_curvature, CS.vEgo, lp.roll)) + lp.angleOffsetDeg
    plan_service = 'lateralManeuverPlan' if sm.valid['lateralManeuverPlan'] else 'modelV2'
    valid = sm.all_checks(['carState', 'liveParameters', plan_service]) and math.isfinite(CS.vEgoRaw)
    paused_before = self.tesla_steering_pause.paused
    hard_disengaged_before = self.tesla_steering_pause.hard_disengaged
    reason_before = self.tesla_steering_pause.reason
    resume_allowed = False
    if valid and math.isfinite(CS.steeringAngleDeg) and sm.all_checks(['carOutput']):
      # CarController clips the absolute angle AFTER its rate limiter. Outside
      # that envelope, automatic re-entry could request a large angle step that
      # Panda rejects. Wait for the wheel to enter the existing envelope instead.
      max_angle = min(get_max_angle_vm(max(CS.vEgoRaw, 1), self.tesla_safety_vm, CarControllerParams),
                      CarControllerParams.ANGLE_LIMITS.STEER_ANGLE_MAX)
      # The 50 Hz command can trail the 100 Hz measured angle by one frame.
      # Ensure the last applied inactive angle has entered the envelope too.
      applied_angle = sm['carOutput'].actuatorsOutput.steeringAngleDeg
      resume_allowed = (math.isfinite(max_angle) and math.isfinite(applied_angle) and
                        max(abs(CS.steeringAngleDeg), abs(applied_angle)) <= max_angle)
    active = self.tesla_steering_pause.update(
      # Fault/standstill/blinker gates must not erase an existing handover or hard
      # override latch. Only the upstream engagement state can reset it.
      CS, requested_active=self.get_lat_requested(sm), target_angle=target_angle,
      sample_time=sm.logMonoTime['carState'] * 1e-9, valid=valid, resume_allowed=resume_allowed,
      hands_on_zero_since=hands_on_zero_since,
    )
    sample_time = sm.logMonoTime['carState'] * 1e-9
    log_paused = self.tesla_steering_pause.paused and (self.tesla_pause_log_time is None or sample_time - self.tesla_pause_log_time >= 1.0)
    if (self.tesla_steering_pause.paused != paused_before or
        self.tesla_steering_pause.hard_disengaged != hard_disengaged_before or
        log_paused or
        (self.tesla_steering_pause.reason != reason_before and "angle_limit" in (reason_before, self.tesla_steering_pause.reason))):
      self.tesla_pause_log_time = sample_time
      cloudlog.event("tesla_steering_pause", paused=self.tesla_steering_pause.paused,
                     reason=self.tesla_steering_pause.reason,
                     eps_reports_released=hands_on_zero_since is not None,
                     resume_allowed=resume_allowed,
                     wheel_rate_deg_s=CS.steeringRateDeg if math.isfinite(CS.steeringRateDeg) else None,
                     torque_nm=CS.steeringTorque if math.isfinite(CS.steeringTorque) else None,
                     angle_error_deg=CS.steeringAngleDeg - target_angle if math.isfinite(CS.steeringAngleDeg - target_angle) else None)
    return lat_active and active

  @staticmethod
  def get_lead_data(_lead, src: log.RadarState.LeadData) -> None:
    _lead.dRel = src.dRel
    _lead.yRel = src.yRel
    _lead.vRel = src.vRel
    _lead.aRel = src.aRel
    _lead.vLead = src.vLead
    _lead.dPath = src.dPath
    _lead.vLat = src.vLat
    _lead.vLeadK = src.vLeadK
    _lead.aLeadK = src.aLeadK
    _lead.fcw = src.fcw
    _lead.status = src.status
    _lead.aLeadTau = src.aLeadTau
    _lead.modelProb = src.modelProb
    _lead.radar = src.radar
    _lead.radarTrackId = src.radarTrackId

  def state_control_ext(self, sm: messaging.SubMaster) -> custom.CarControlSP:
    CC_SP = custom.CarControlSP.new_message()

    self.get_lead_data(CC_SP.leadOne, sm['radarState'].leadOne)
    self.get_lead_data(CC_SP.leadTwo, sm['radarState'].leadTwo)

    # MADS state
    mads_src = sm['selfdriveStateSP'].mads
    CC_SP.mads.state = mads_src.state
    CC_SP.mads.enabled = mads_src.enabled
    CC_SP.mads.active = mads_src.active
    CC_SP.mads.available = mads_src.available

    # ICBM state
    icbm_src = sm['selfdriveStateSP'].intelligentCruiseButtonManagement
    CC_SP.intelligentCruiseButtonManagement.state = icbm_src.state
    CC_SP.intelligentCruiseButtonManagement.sendButton = icbm_src.sendButton
    CC_SP.intelligentCruiseButtonManagement.vTarget = icbm_src.vTarget

    return CC_SP

  @staticmethod
  def publish_ext(CC_SP: custom.CarControlSP, sm: messaging.SubMaster, pm: messaging.PubMaster) -> None:
    cc_sp_send = messaging.new_message('carControlSP')
    cc_sp_send.valid = sm['carState'].canValid
    cc_sp_send.carControlSP = CC_SP

    pm.send('carControlSP', cc_sp_send)

  def run_ext(self, sm: messaging.SubMaster, pm: messaging.PubMaster) -> None:
    CC_SP = self.state_control_ext(sm)
    self.publish_ext(CC_SP, sm, pm)
