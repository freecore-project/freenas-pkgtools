import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest import mock


LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
PACKAGE_SPEC = importlib.util.spec_from_file_location(
    "freenasOS",
    LIB_DIR / "__init__.py",
    submodule_search_locations=[str(LIB_DIR)],
)
if "freenasOS" in sys.modules:
    freenasOS = sys.modules["freenasOS"]
else:
    freenasOS = importlib.util.module_from_spec(PACKAGE_SPEC)
    sys.modules["freenasOS"] = freenasOS
    PACKAGE_SPEC.loader.exec_module(freenasOS)

from freenasOS import Configuration, Exceptions, Manifest  # noqa: E402

with mock.patch("subprocess.run") as subprocess_run:
    subprocess_run.return_value.stdout = ""
    from freenasOS import Update  # noqa: E402


ABSENT = object()


class UpdateConfiguration:
    def __init__(self, signed=True):
        self.signed = signed

    def UpdateServerSigned(self):
        return self.signed

    def UpdateServerName(self):
        return "test"

    def UpdateServerURL(self):
        return "https://updates.example.invalid/FreeCORE"


class ManifestFile(io.StringIO):
    mode = "r"


def make_manifest(require_signature, signature=ABSENT, server_signed=True):
    manifest = Manifest.Manifest(
        UpdateConfiguration(signed=server_signed),
        require_signature=require_signature,
    )
    manifest._dict = {
        Manifest.SEQUENCE_KEY: "test-sequence",
        Manifest.TRAIN_KEY: "FreeCORE-15.0-STABLE",
        Manifest.PACKAGES_KEY: [{"Name": "base-os", "Version": "test"}],
    }
    if signature is not ABSENT:
        manifest._dict[Manifest.SIGNATURE_KEY] = signature
    return manifest


class RequiredSignatureTests(unittest.TestCase):
    def test_missing_signature_fails_before_verification(self):
        manifest = make_manifest(require_signature=True)

        with mock.patch.object(manifest, "VerifySignature") as verify:
            with self.assertRaisesRegex(
                Exceptions.ManifestInvalidSignature,
                "unsigned",
            ):
                manifest.Validate()

        verify.assert_not_called()

    def test_null_and_empty_signatures_fail_before_verification(self):
        for signature in (None, ""):
            with self.subTest(signature=signature):
                manifest = make_manifest(
                    require_signature=True,
                    signature=signature,
                )
                with mock.patch.object(manifest, "VerifySignature") as verify:
                    with self.assertRaises(Exceptions.ManifestInvalidSignature):
                        manifest.Validate()
                verify.assert_not_called()

    def test_present_invalid_signature_fails(self):
        manifest = make_manifest(
            require_signature=True,
            signature="invalid-signature",
        )

        with mock.patch.object(manifest, "VerifySignature", return_value=False):
            with self.assertRaisesRegex(
                Exceptions.ManifestInvalidSignature,
                "verification failed",
            ):
                manifest.Validate()

    def test_present_valid_signature_passes(self):
        manifest = make_manifest(
            require_signature=True,
            signature="valid-signature",
        )

        with mock.patch.object(manifest, "VerifySignature", return_value=True):
            self.assertTrue(manifest.Validate())

    def test_unsigned_server_setting_cannot_weaken_requirement(self):
        manifest = make_manifest(
            require_signature=True,
            server_signed=False,
        )

        with self.assertRaises(Exceptions.ManifestInvalidSignature):
            manifest.Validate()

    def test_legacy_failure_switch_cannot_weaken_requirement(self):
        manifest = make_manifest(require_signature=True)

        with mock.patch.object(freenasOS, "SIGNATURE_FAILURE", False):
            with self.assertRaises(Exceptions.ManifestInvalidSignature):
                manifest.Validate()

    def test_load_file_rejects_unsigned_manifest(self):
        manifest = make_manifest(require_signature=True)
        manifest_file = ManifestFile(
            Manifest.MakeString({
                Manifest.SEQUENCE_KEY: "test-sequence",
                Manifest.TRAIN_KEY: "FreeCORE-15.0-STABLE",
                Manifest.PACKAGES_KEY: [
                    {"Name": "base-os", "Version": "test"},
                ],
            })
        )

        with self.assertRaises(Exceptions.ManifestInvalidSignature):
            manifest.LoadFile(manifest_file)


class OptionalSignatureTests(unittest.TestCase):
    def test_unsigned_manifest_passes_when_signature_is_optional(self):
        manifest = make_manifest(require_signature=False)

        self.assertTrue(manifest.Validate())

    def test_unsigned_server_compatibility_remains_optional_only(self):
        manifest = make_manifest(
            require_signature=False,
            server_signed=False,
        )

        self.assertTrue(manifest.Validate())


class ConsumerPathTests(unittest.TestCase):
    def test_network_latest_rejects_unsigned_manifest_by_default(self):
        config = mock.Mock()
        config.SystemManifest.return_value = None
        config.TryGetNetworkFile.return_value = ManifestFile(
            Manifest.MakeString({
                Manifest.SEQUENCE_KEY: "test-sequence",
                Manifest.TRAIN_KEY: "FreeCORE-15.0-STABLE",
                Manifest.PACKAGES_KEY: [
                    {"Name": "base-os", "Version": "test"},
                ],
            })
        )

        with self.assertRaises(Exceptions.ManifestInvalidSignature):
            Configuration.Configuration.FindLatestManifest(
                config,
                train="FreeCORE-15.0-STABLE",
            )

    def test_download_stops_before_cache_or_package_work(self):
        config = mock.Mock()
        config.SystemManifest.return_value = mock.Mock()
        config.FindLatestManifest.side_effect = (
            Exceptions.ManifestInvalidSignature("Manifest is unsigned")
        )

        with (
            mock.patch.object(
                Update.Configuration,
                "SystemConfiguration",
                return_value=config,
            ),
            mock.patch.object(Update, "VerifyUpdate") as verify_cache,
        ):
            with self.assertRaises(Exceptions.ManifestInvalidSignature):
                Update.DownloadUpdate(
                    "FreeCORE-15.0-STABLE",
                    "/nonexistent/update-cache",
                )

        verify_cache.assert_not_called()
        config.PackagePath.assert_not_called()


if __name__ == "__main__":
    unittest.main()
