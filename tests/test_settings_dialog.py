import os
import tempfile
import unittest
from src.settings import Settings
from src.settings_dialog import settings_dialog_popup, workout_selection_popup

class TestSettingsDialog(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.dirname(__file__) + "/fixtures/sample_settings/"
        self.config = Settings(filename=(self.fixture_path + "default_settings.sampleini"))

    def test_settings_popup(self):
        settings_dialog_popup(self.config)
        with tempfile.NamedTemporaryFile() as tmp:
            self.config.write_settings(tmp.name)
            # Allows manually verifying settings if changed in dialog
            print(open(tmp.name, "r").read())

    def test_workout_popup(self):
        workout_selection_popup(self.config.get("workout"))
