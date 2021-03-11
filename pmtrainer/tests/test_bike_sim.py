import unittest
from ..pmtrainer.bike_sim import *

class TestBikeSim(unittest.TestCase):

    def setUp(self):
        self.sim = BikeSim(weight_kg=80)
            
    def test_basic(self):
        # Basic test of hard-coded values
        for i in range(1,100):
            self.sim.update(200, i)
        print('Steady-state speed for 200W: {:4.2f}mph'.format(self.sim.speed_miph))
        unittest.assertIn(self.sim.speed_miph, range(20.5,21.7))

if __name__ == '__main__':
    unittest.main()