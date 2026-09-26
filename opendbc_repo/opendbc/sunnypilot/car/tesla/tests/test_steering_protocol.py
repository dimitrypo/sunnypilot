import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.tesla.carstate import CarState
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.teslacan import TeslaCAN
from opendbc.car.tesla.values import CAR, CANBUS, DBC, Ecu, FSD_14_FW, TeslaFlags, TeslaSafetyFlags
from opendbc.sunnypilot.car.interfaces import _initialize_coop_steering
from opendbc.sunnypilot.car.tesla.coop_steering import CoopSteeringCarController


class TestPersonalSteeringProtocol(unittest.TestCase):
  @staticmethod
  def params(candidate=CAR.TESLA_MODEL_3, markers=(), car_fw=(), alpha_long=False):
    fingerprint = gen_empty_fingerprint()
    for bus, address in markers:
      fingerprint[bus][address] = 8
    return CarInterface.get_params(candidate, fingerprint, list(car_fw), alpha_long, False, False)

  def assert_encoding(self, CP, enabled):
    self.assertEqual(bool(CP.flags & TeslaFlags.FSD_14.value), enabled)
    self.assertEqual(bool(CP.safetyConfigs[0].safetyParam & TeslaSafetyFlags.FSD_14.value), enabled)

  def test_each_fresh_can_marker_sets_both_encoding_flags(self):
    for marker in ((CANBUS.autopilot_party, 0x489), (CANBUS.party, 0x054)):
      for alpha_long in (False, True):
        with self.subTest(marker=marker, alpha_long=alpha_long):
          CP = self.params(markers=(marker,), alpha_long=alpha_long)
          self.assert_encoding(CP, True)
          self.assertEqual(bool(CP.safetyConfigs[0].safetyParam & TeslaSafetyFlags.LONG_CONTROL.value), alpha_long)
          self.assertEqual(CP.openpilotLongitudinalControl, alpha_long)

  def test_can_markers_override_missing_or_stale_eps_list(self):
    for car_fw in ([], [SimpleNamespace(ecu=Ecu.eps, fwVersion=b"older unlisted EPS version")]):
      with self.subTest(car_fw=car_fw):
        self.assert_encoding(self.params(markers=((CANBUS.party, 0x054),), car_fw=car_fw), True)

  def test_marker_on_wrong_bus_does_not_change_encoding(self):
    for marker in ((CANBUS.party, 0x489), (CANBUS.autopilot_party, 0x054), (1, 0x489), (1, 0x054)):
      with self.subTest(marker=marker):
        self.assert_encoding(self.params(markers=(marker,)), False)

  def test_legacy_eps_match_still_works_without_can_markers(self):
    known_eps = SimpleNamespace(ecu=Ecu.eps, fwVersion=FSD_14_FW[CAR.TESLA_MODEL_3][0])
    self.assert_encoding(self.params(car_fw=[known_eps]), True)
    self.assert_encoding(self.params(), False)

  def test_other_platforms_do_not_use_new_can_detection(self):
    markers = ((CANBUS.autopilot_party, 0x489), (CANBUS.party, 0x054))
    for candidate in (CAR.TESLA_MODEL_Y, CAR.TESLA_MODEL_X):
      with self.subTest(candidate=candidate):
        self.assert_encoding(self.params(candidate=candidate, markers=markers), False)

  def test_actual_cooperative_packet_is_lane_keep_on_three_bit_firmware(self):
    for marker in ((CANBUS.autopilot_party, 0x489), (CANBUS.party, 0x054)):
      with self.subTest(marker=marker):
        CP = self.params(markers=(marker,))
        CP_SP = structs.CarParamsSP()
        _initialize_coop_steering(CP, CP_SP, {"TeslaCoopSteering": "0"})
        mode = CoopSteeringCarController.coop_steering_status_update(CP_SP).control_type
        tesla_can = TeslaCAN(CP, CANPacker(DBC[CP.carFingerprint][Bus.party]))
        for active, expected_type in ((True, 2), (False, 0)):
          address, data, bus = tesla_can.create_steering_control(5.0, active, mode)
          self.assertEqual((address, bus), (0x488, CANBUS.party))
          self.assertEqual(data[2] >> 5, expected_type)
          self.assertEqual(data[2] & 0x20, 0)  # No new bit outside the prebuilt 2-bit mode field.

  def test_actual_legacy_cooperative_packet_is_unchanged(self):
    CP = self.params()
    tesla_can = TeslaCAN(CP, CANPacker(DBC[CP.carFingerprint][Bus.party]))
    _, data, _ = tesla_can.create_steering_control(0.0, True, 2)
    self.assertEqual(data[2] >> 6, 2)

  def test_three_bit_lane_keep_is_recognized_without_false_unknown_firmware_lockout(self):
    for detected in (False, True):
      with self.subTest(detected=detected):
        markers = [(CANBUS.autopilot_party, 0x293)]  # DAS_settings is available.
        if detected:
          markers.append((CANBUS.party, 0x054))
        CP = self.params(markers=markers)
        CP_SP = structs.CarParamsSP()
        car_state = CarState(CP, CP_SP)
        parsers = CarState.get_can_parsers(CP, CP_SP)
        # The unchanged two-bit DBC sees newer LANE_KEEP_ASSIST (010) as 1.
        parsers[Bus.ap_party].vl["DAS_steeringControl"]["DAS_steeringControlType"] = 1
        parsers[Bus.ap_party].vl["DAS_settings"]["DAS_autosteerEnabled"] = 0
        state, _ = car_state.update(parsers)
        self.assertEqual(state.stockLkas, detected)
        self.assertEqual(state.invalidLkasSetting, not detected)
        # CAN evidence must not bypass the requirement to disable stock Autosteer.
        parsers[Bus.ap_party].vl["DAS_settings"]["DAS_autosteerEnabled"] = 1
        state, _ = car_state.update(parsers)
        self.assertTrue(state.invalidLkasSetting)

  def test_diagnostic_distinguishes_fresh_can_from_eps_match(self):
    with patch("opendbc.car.tesla.interface.carlog.info") as log:
      self.params(markers=((CANBUS.party, 0x054),))
    log.assert_called_once_with({
      "event": "tesla_steering_protocol",
      "fingerprint": CAR.TESLA_MODEL_3,
      "eps_encoding_match": False,
      "redundant_braking_on_bus_2": False,
      "autonomy_health_on_bus_0": True,
      "legacy_fsd14_encoding_flag": True,
    })


if __name__ == "__main__":
  unittest.main()
