import os
import tempfile
import unittest
from ..settings import Settings
from ..settings_dialog import *

class TestSettingsDialog(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.dirname(__file__) + "/fixtures/sample_settings/"
        self.config = Settings()
        self.config.load_settings(filename=(self.fixture_path + "default_settings.sampleini"))

    def test_settings_popup(self):
        settings_dialog_popup(self.config)
        with tempfile.NamedTemporaryFile() as tmp:
            self.config.write_settings(tmp.name)
            print(open(tmp.name, "r").read())

#    def test_workout_popup(self):
#        workout_selection_popup()
