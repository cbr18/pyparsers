import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pyparsers"))

from api.che168.parser import Che168Parser


class _FakeProcess:
    def wait(self, timeout=None):
        return None


class _FakeService:
    process = _FakeProcess()


class _FakeDriver:
    service = _FakeService()

    def quit(self):
        return None


class Che168ParserTests(unittest.TestCase):
    def test_safe_quit_driver_tolerates_missing_temp_dir(self):
        parser = Che168Parser()
        parser.driver = _FakeDriver()
        parser._temp_dir = None

        parser._safe_quit_driver()

        self.assertIsNone(parser.driver)
        self.assertIsNone(parser._temp_dir)


if __name__ == "__main__":
    unittest.main()
