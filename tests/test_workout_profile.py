import unittest
import os
from pmtrainer.workout_profile import Workout, get_zone


class TestWorkoutProfile(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.dirname(__file__) + "/fixtures/sample_workouts/"
        self.workout = Workout(self.fixture_path + "test_workout.yaml")

    def test_simple_profile(self):
        time_s = -10
        self.assertEqual(self.workout.block_time_remaining(time_s), 450)
        self.assertAlmostEqual(self.workout.power_target(time_s), 0.5)
        time_s = 0
        self.assertEqual(self.workout.block_time_remaining(time_s), 450)
        self.assertAlmostEqual(self.workout.power_target(time_s), 0.5)
        time_s = 450
        self.assertEqual(self.workout.block_time_remaining(time_s), 0)
        self.assertAlmostEqual(self.workout.power_target(time_s), 0.85)
        time_s = 450.5
        self.assertEqual(self.workout.block_time_remaining(time_s), 1349.5)
        self.assertAlmostEqual(self.workout.power_target(time_s), 1.0)
        time_s = 1800
        self.assertEqual(self.workout.block_time_remaining(time_s), 0)
        self.assertAlmostEqual(self.workout.power_target(time_s), 1.0)
        time_s = 1800.5
        self.assertEqual(self.workout.block_time_remaining(time_s), 0)
        self.assertAlmostEqual(self.workout.power_target(time_s), 1.0)

    def test_zones(self):
        self.assertEqual(get_zone(0),0)
        self.assertEqual(get_zone(-0.001),0)
        self.assertEqual(get_zone(0.6),0)
        self.assertEqual(get_zone(0.60000001),1)
        self.assertEqual(get_zone(2),5)

    def test_out_of_range_inputs(self):
        pass

    def test_open_invalid_file(self):
        with self.assertRaises(FileNotFoundError):
            Workout("asdf")

    def test_invalid_duration(self):
        with self.assertRaises(Workout.WorkoutError):
            Workout(self.fixture_path + "test_invalid_duration_workout.yaml")

    def test_get_all_blocks(self):
        self.assertEqual(self.workout.get_all_blocks(), [(0.25, 0.5, 0.85), (0.75, 1.0, 1.0)])

    def test_min_max_power(self):
        minp, maxp = self.workout.get_min_max_power()
        self.assertEqual(minp, 0.5)
        self.assertEqual(maxp, 1.0)

    def test_properties(self):
        self.assertEqual(self.workout.duration_s, 1800)
        self.assertEqual(self.workout.name, "Test Workout")
        self.assertEqual(self.workout.description, "This is a test workout")
