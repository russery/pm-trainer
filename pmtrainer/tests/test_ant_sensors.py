import unittest
from unittest.mock import patch
from ..ant_sensors import AntSensors

class TestAntSensors(unittest.TestCase):
    @patch("ant.plus.power.BicyclePower")
    def test_initialization(self, antmock):
        sensors = AntSensors()

