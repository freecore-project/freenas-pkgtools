from pathlib import Path
import unittest


RELEASE_SOURCE = (
    Path(__file__).parents[1] / "freenas-release/freenas-release.py"
).read_text(encoding="utf-8")


class ReleaseConfigCompatibilityTests(unittest.TestCase):
    def test_configparser_calls_are_supported_by_python_3_12(self):
        self.assertNotIn("SafeConfigParser", RELEASE_SOURCE)
        self.assertNotIn(".readfp(", RELEASE_SOURCE)
        self.assertEqual(RELEASE_SOURCE.count(".read_file("), 2)


if __name__ == "__main__":
    unittest.main()
