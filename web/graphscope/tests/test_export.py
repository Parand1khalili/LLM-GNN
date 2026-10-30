"""Small negative boundary checks; synthetic values never enter the production export."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("atlas_export", Path(__file__).parents[1] / "scripts/export_data.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportBoundaryTests(unittest.TestCase):
    def test_hash_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text('{"safe":true}')
            with self.assertRaisesRegex(ValueError, "Hash conflict"):
                module.pinned(path, "0" * 64)

    def test_nonfinite_confidence_rejected(self):
        for value in (float("nan"), float("inf"), -1, 101, True):
            with self.assertRaises(ValueError):
                module.number(value, 0, 100)


if __name__ == "__main__":
    unittest.main()
