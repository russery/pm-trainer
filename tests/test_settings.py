import unittest
import tempfile
import os
from src.settings import Settings

class TestSettings(unittest.TestCase):
    def setUp(self):
        self.cfg = Settings()

    def test_read_write_settings(self):
        self.cfg.set("setting1", "value1")
        self.assertEqual(self.cfg.get("setting1"), "value1")
        with tempfile.NamedTemporaryFile() as tmp_log:
            self.cfg.write_settings(tmp_log.name)
            cfg2 = Settings()
            cfg2.load_settings(filename=tmp_log.name)
            self.assertEqual(cfg2.get("setting1"), "value1")

    def test_read_defaults(self):
        dfts = {"setting2": "value2"}
        self.cfg.load_settings(defaults=dfts)
        self.assertEqual(self.cfg.get("setting2"), "value2")

    def test_read_invalid(self):
        with self.assertRaises(KeyError):
            self.cfg.active_section = "invalidkey"
        with self.assertRaises(KeyError):
            _ = self.cfg.get("invalidkey")

    def test_add_section(self):
        name = "New Section"
        self.cfg.create_section(name, settings={"setting": "value"})
        self.cfg.active_section = "New Section"
        self.assertEqual(self.cfg.active_section, name)
        self.assertEqual(self.cfg.get("setting"), "value")

    def test_delete_key(self):
        self.cfg.set("new_setting", "new_value")
        val = self.cfg.get("new_setting")
        self.assertEqual(val, "new_value")
        self.cfg.delete("new_setting")
        with self.assertRaises(KeyError):
            self.cfg.get("new_setting")

    def test_init_settings_with_file(self):
        sample_file = os.path.dirname(__file__) + "/fixtures/sample_settings/default_settings.sampleini"
        config = Settings(filename=sample_file)
        with open(sample_file, "r") as f:
            sample_config = f.read()
        with tempfile.NamedTemporaryFile() as tmp_log:
            config.write_settings(tmp_log.name)
            with open(tmp_log.name, "r") as f:
                written_config = f.read()
            print("---")
            print(sample_config)
            print("---")
            print(written_config)
            print("---")
            self.assertEqual(sample_config, written_config)
