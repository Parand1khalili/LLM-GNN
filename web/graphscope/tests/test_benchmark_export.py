"""Offline adapter boundaries; no model/training/research imports."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('benchmark_export', Path(__file__).parents[1] / 'scripts/export_benchmark.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

class BenchmarkExportTests(unittest.TestCase):
    def test_numeric_boundary(self):
        for value in (True, float('nan'), float('inf'), -1, 101):
            with self.assertRaises(ValueError):
                adapter.number(value)

    def test_checksum_before_interpretation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'payload.json'
            path.write_bytes(b'{not even json}')
            with self.assertRaisesRegex(ValueError, 'hash/size conflict'):
                adapter.pinned(path, '0'*64)

    @unittest.skipUnless((adapter.ROOT / f'.local_artifacts/final_cora_gcn_v1/{adapter.MANIFEST}.json').exists(), 'Private pinned GT-free manifest unavailable')
    def test_reproduction_and_public_boundary(self):
        public, owner = adapter.build()
        self.assertEqual(adapter.encode(public), (adapter.HERE / 'public/data/benchmark.v3.json').read_bytes())
        self.assertEqual(public['ownerSHA'], adapter.digest(owner))
        self.assertEqual(len(owner['targetIds']), 140)
        self.assertEqual(len(public['arms']), 16)
        self.assertAlmostEqual(public['historicalWCE']['accuracy'], 74.37694704049844)
        for arm in public['arms']:
            self.assertNotIn('labels', arm)
            self.assertNotIn('targetIds', arm)
            self.assertNotIn('confidence', arm)
        self.assertEqual(set(owner), {'schema','manifestSHA','classOrder','targetIds','arms'})
        for arm in owner['arms']:
            self.assertEqual(set(arm), {'id','maskSHA','vectorSHA','labels','confidence'})

    @unittest.skipUnless((adapter.ROOT / f'.local_artifacts/final_cora_gcn_v1/{adapter.MANIFEST}.json').exists(), 'Private pinned GT-free manifest unavailable')
    def test_exact_repository_lf_bytes_are_portable(self):
        import json
        public, _ = adapter.build()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in public['sources']:
                path = root / source['path']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((adapter.ROOT / source['path']).read_bytes().replace(b'\r\n', b'\n'))
            name = f'.local_artifacts/final_cora_gcn_v1/{adapter.MANIFEST}.json'
            manifest = root / name
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_bytes((adapter.ROOT / name).read_bytes())
            with patch.object(adapter, 'ROOT', root):
                replay, _ = adapter.build()
                self.assertEqual(adapter.encode(public), adapter.encode(replay))
                bad = root / public['sources'][0]['path']
                bad.write_bytes(bad.read_bytes() + b'changed')
                with self.assertRaisesRegex(ValueError, 'hash/size conflict'):
                    adapter.build()

if __name__ == '__main__':
    unittest.main()
