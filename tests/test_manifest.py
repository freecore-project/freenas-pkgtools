from importlib import import_module, util
from pathlib import Path
import sys
import unittest
from unittest import mock

import OpenSSL.crypto as Crypto


LIB_DIR = Path(__file__).resolve().parents[1] / 'lib'
SPEC = util.spec_from_file_location(
    'freenasOS', LIB_DIR / '__init__.py', submodule_search_locations=[str(LIB_DIR)],
)
freenasOS = util.module_from_spec(SPEC)
sys.modules['freenasOS'] = freenasOS
SPEC.loader.exec_module(freenasOS)
Manifest = import_module('freenasOS.Manifest')


class VerifySignatureTest(unittest.TestCase):

    def test_certificate_read_failure_returns_false(self):
        manifest = Manifest.Manifest(configuration=mock.Mock())
        manifest.SetSignature('signature-is-not-reached')
        root_file = mock.mock_open(read_data='root certificate').return_value

        with (
            mock.patch.object(freenasOS, 'IX_ROOT_CA_FILE', '/test/update-ca.pem'),
            mock.patch.object(
                Manifest, 'VerificationCertificateFile', return_value='/test/train.pem',
            ),
            mock.patch.object(Manifest.os.path, 'isfile', return_value=True),
            mock.patch('builtins.open', side_effect=[root_file, OSError('certificate read failed')]),
            mock.patch.object(Crypto, 'X509Store') as store,
            mock.patch.object(Crypto, 'load_certificate', return_value=mock.Mock()),
        ):
            self.assertIs(manifest.VerifySignature(), False)
            store.return_value.add_cert.assert_called_once()


if __name__ == '__main__':
    unittest.main()
