# the internal development record: a download that does not fit is reported as such, not as "package not found".
from importlib import import_module, util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if "freenasOS" not in sys.modules:
    spec = util.spec_from_file_location("freenasOS", LIB_DIR / "__init__.py", submodule_search_locations=[str(LIB_DIR)])
    module = util.module_from_spec(spec)
    sys.modules["freenasOS"] = module
    spec.loader.exec_module(module)

Configuration = import_module("freenasOS.Configuration")
Exceptions = import_module("freenasOS.Exceptions")
# FindPackageFile imports these two sentinels from freenasOS.Update, which runs zpool at import time; off a FreeBSD
# box a stand-in carries just them. The stand-in is in sys.modules only for the duration of each call
# (mock.patch.dict restores it): left there, it shadowed the real module for the tests that run after this file
# (test_manifest_signature_policy patches Update.Configuration).
Update = sys.modules.get("freenasOS.Update")
if Update is None:
    Update = types.ModuleType("freenasOS.Update")
    Update.PkgFileDeltaOnly, Update.PkgFileFullOnly = object(), object()


def package():
    pkg = mock.Mock()
    pkg.Name.return_value = "base-os"
    pkg.FileName.return_value = "base-os-15.2-MASTER.tgz"
    pkg.Checksum.return_value = None
    return pkg


def find(error):
    configuration = object.__new__(Configuration.Configuration)
    configuration._package_dir = None
    configuration.TryGetNetworkFile = mock.Mock(side_effect=error)
    with mock.patch.dict(sys.modules, {"freenasOS.Update": Update}):
        return configuration.FindPackageFile(package(), save_dir="/var/db/system/update", pkg_type=Update.PkgFileFullOnly)


class FindPackageFileSpaceTests(unittest.TestCase):
    def test_insufficient_space_reaches_the_caller(self):
        error = Exceptions.UpdateInsufficientSpace(
            "Not enough free space for the update: base-os-15.2-MASTER.tgz needs 1600 MiB in /var/db/system/update. "
            "Free space on the pool that holds it and try again."
        )
        with self.assertRaises(Exceptions.UpdateInsufficientSpace) as raised:
            find(error)
        self.assertIn("1600 MiB", str(raised.exception))

    def test_any_other_failure_is_still_package_not_found(self):
        with self.assertRaises(Exceptions.UpdatePackageNotFound) as raised:
            find(OSError("connection reset"))
        self.assertEqual(str(raised.exception), "base-os")


if __name__ == "__main__":
    unittest.main()
