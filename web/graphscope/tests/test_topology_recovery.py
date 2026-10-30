"""No pickle VM; test admission and the exact allowed ZIP read boundary."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recover_topology', ROOT / 'scripts/recover-cora-topology.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def test_wrong_archive_rejected_before_zip_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'untrusted.pt'
            path.write_bytes(b'not a trusted archive')
            with patch.object(recovery.zipfile, 'ZipFile') as opener:
                with self.assertRaisesRegex(ValueError, 'hash conflict'):
                    recovery.extract(path)
                opener.assert_not_called()

    @unittest.skipUnless((ROOT / '.qa/cora_random_sbert.pt').exists(), 'Original pinned archive not locally restored')
    def test_exact_archive_reads_no_gt_tensor(self):
        original = recovery.zipfile.ZipFile.read
        reads = []
        def audited(instance, name, *args, **kwargs):
            reads.append(name)
            return original(instance, name, *args, **kwargs)
        with patch.object(recovery.zipfile.ZipFile, 'read', audited):
            texts, edges, _ = recovery.extract(ROOT / '.qa/cora_random_sbert.pt')
        self.assertEqual(reads, ['cora_random_sbert/data.pkl', 'cora_random_sbert/data/1'])
        self.assertEqual(len(texts), 2708)
        self.assertEqual(len(edges), 10858)
        self.assertEqual(len({tuple(sorted(e)) for e in edges}), 5278)
