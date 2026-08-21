from importlib import import_module, util
from pathlib import Path
import sys
import unittest
from unittest import mock
import warnings


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = REPOSITORY_ROOT / "lib"
CONFIGURATION_SOURCE = LIB_DIR / "Configuration.py"
SPEC = util.spec_from_file_location(
    "freenasOS", LIB_DIR / "__init__.py", submodule_search_locations=[str(LIB_DIR)],
)
freenasOS = util.module_from_spec(SPEC)
if "freenasOS" not in sys.modules:
    sys.modules["freenasOS"] = freenasOS
    SPEC.loader.exec_module(freenasOS)
else:
    freenasOS = sys.modules["freenasOS"]

Configuration = import_module("freenasOS.Configuration")


class ConfigurationCompatibilityTests(unittest.TestCase):
    def test_configuration_source_has_no_syntax_warnings(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            compile(
                CONFIGURATION_SOURCE.read_bytes(),
                str(CONFIGURATION_SOURCE),
                "exec",
            )

    def test_available_trains_preserves_whitespace_parsing(self):
        configuration = object.__new__(Configuration.Configuration)
        configuration.TryGetNetworkFile = mock.Mock(return_value=[
            b"# ignored\n",
            b"FreeCORE-15.1-Nightlies Nightly builds\n",
            b"FreeCORE-15.1-STABLE\tStable builds\n",
            b"missing-description\n",
        ])

        self.assertEqual(
            configuration.AvailableTrains(),
            {
                "FreeCORE-15.1-Nightlies": "Nightly builds",
                "FreeCORE-15.1-STABLE": "Stable builds",
            },
        )


if __name__ == "__main__":
    unittest.main()
