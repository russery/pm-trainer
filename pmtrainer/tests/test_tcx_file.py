import unittest
import tempfile
import os
from ..tcx_file import Tcx, Point

class TestTcxFile(unittest.TestCase):
    def setUp(self):
        self.tcx = Tcx()
        self.fixture_path = os.path.dirname(__file__) + "/fixtures/sample_tcx_files/"

    def _assert_point_equal(self, p1, p2, check_time=False):
        '''
        Checks that two points p1 and p2 are equivalent, optionally excluding timestamp.
        '''
        self.assertAlmostEqual(p1.lat_deg, p2.lat_deg, places=7)
        self.assertAlmostEqual(p1.lon_deg, p2.lon_deg, places=7)
        self.assertAlmostEqual(p1.altitude_m, p2.altitude_m, places=4)
        self.assertAlmostEqual(p1.distance_m, p2.distance_m, places=4)
        self.assertAlmostEqual(p1.heartrate_bpm, p2.heartrate_bpm, places=4)
        self.assertAlmostEqual(p1.cadence_rpm, p2.cadence_rpm, places=4)
        self.assertAlmostEqual(p1.speed_mps, p2.speed_mps, places=4)
        self.assertAlmostEqual(p1.power_watts, p2.power_watts, places=4)
        self.assertAlmostEqual(p1.distance_m, p2.distance_m, places=4)
        self.assertAlmostEqual(p1.distance_m, p2.distance_m, places=4)
        self.assertAlmostEqual(p1.distance_m, p2.distance_m, places=4)
        self.assertAlmostEqual(p1.distance_m, p2.distance_m, places=4)
        if check_time:
            self.assertEqual(p1.time, p2.time)

    def test_point_and_file_creation(self):
        test_point_full = Point(
                time = "2021-03-11T21:26:53Z",
                lat_deg=51.5014600,
                lon_deg=-0.1402330,
                altitude_m=12.2,
                distance_m=2.0,
                heartrate_bpm=92,
                cadence_rpm=39,
                speed_mps=0.0,
                power_watts=92)
        test_point_min = Point(
                heartrate_bpm=180,
                cadence_rpm=80,
                power_watts=105)
        test_point_none = Point()

        with tempfile.NamedTemporaryFile() as tmp_log:
            self.tcx.start_log(tmp_log.name)
            self.tcx.start_activity(activity_type=Tcx.ActivityType.OTHER)

            # Add a few points
            self.tcx.add_point(test_point_full) # Point with all attrs set
            self.tcx.add_point(test_point_min) # Point with basic attrs set
            self.tcx.add_point(test_point_none) # Blank point with no attrs set

            # Write the logfile to disk
            self.tcx.flush()
            print(open(tmp_log.name).read())

            # Read the logfile back in and check that the points are as expected
            self.tcx = Tcx()
            self.tcx.open_log(tmp_log.name)
            for p in [test_point_full, test_point_min, test_point_none]:
                read_point = self.tcx.get_next_point() # Read points back
                self.assertIsNotNone(read_point)
                print(read_point)
                if p == test_point_full:
                    # Check time field for this point since we set it explicitly
                    self._assert_point_equal(p, read_point, check_time=True)
                else:
                    self._assert_point_equal(p, read_point)

    def test_open_file(self):
        # Read in a TCX file generated from a Strava activity
        self.tcx.open_log(self.fixture_path + "Jon_s_Mix.tcx")
        p = self.tcx.get_next_point()
        while p is not None:
            print(p)
            self.assertIsNotNone(p.time)
            p = self.tcx.get_next_point()
