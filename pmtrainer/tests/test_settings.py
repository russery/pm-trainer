import unittest
import tempfile
from ..settings import Settings


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
