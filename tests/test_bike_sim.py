import unittest
from pmtrainer.bike_sim import BikeSim

class TestBikeSim(unittest.TestCase):

    def setUp(self):
        self.sim = BikeSim(weight_kg=80)

    def _pow_test(self, power, start_time=1, end_time=100):
        for i in range(start_time, end_time):
            self.sim.update(power, i)

    def test_physics(self):
        # Basic test of physics with hard-coded values
        self._pow_test(200)
        print('Steady-state speed for 200W: {:4.2f}mph'.format(self.sim.speed_miph))
        self.assertAlmostEqual(20.67, self.sim.speed_miph, places=2)

    def test_neg_power(self):
        self._pow_test(-100, 1, 100)
        # Negative power allowed, but should result in zero speed
        self.assertAlmostEqual(0.0, self.sim.speed_miph, places=2)
        self._pow_test(200, 101, 200)
        self._pow_test(-100, 1, 100)
        # After positive power is applied resulting in positive speed,
        # negative power should slow bike down.
        self.assertAlmostEqual(0.0, self.sim.speed_miph, places=2)
        print('Steady-state speed: {:4.2f}mph'.format(self.sim.speed_miph))
        # Negative power allowed, but should result in zero speed
        self.assertAlmostEqual(0.0, self.sim.speed_miph, places=2)

    def test_high_power(self):
        # Simulator should reject unreasonably large power inputs
        with self.assertRaises(ValueError):
            self._pow_test(10001)

    def test_properties(self):
        # Test that all property accessors work as expected
        self.assertEqual(0.0, self.sim.speed_mps)
        self.assertEqual(0.0, self.sim.speed_miph)
        self.assertEqual(0.0, self.sim.total_distance_m)
        self.assertEqual(0.0, self.sim.total_distance_mi)
        self._pow_test(200)
        self.assertNotEqual(0.0, self.sim.speed_mps)
        self.assertNotEqual(0.0, self.sim.speed_miph)
        self.assertNotEqual(0.0, self.sim.total_distance_m)
        self.assertNotEqual(0.0, self.sim.total_distance_mi)
