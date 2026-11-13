import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "helix-rack" / "rack" / "build_light_stage1.py"
sys.path.insert(0, str(BUILDER.parent))
import build_light_stage1


class Stage1Tests(unittest.TestCase):
    def test_verifier_failure_is_not_treated_as_success(self):
        result = SimpleNamespace(returncode=1, stdout="ALL OK", stderr="verification failed")
        with patch.object(build_light_stage1.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "verification failed"):
                build_light_stage1.verify_image(Path("image.l6ia"), {})

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.hxf"
            output.write_bytes(b"keep")
            result = subprocess.run(
                [sys.executable, str(BUILDER), str(Path(directory) / "missing.hxf"),
                 "-o", str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Output already exists", result.stderr)
            self.assertEqual(output.read_bytes(), b"keep")

    def test_rejects_wrong_firmware(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "wrong.hxf"
            output = Path(directory) / "output.hxf"
            source.write_bytes(b"not Rack firmware")
            result = subprocess.run(
                [sys.executable, str(BUILDER), str(source), "-o", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("original Helix Rack 3.80.0", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
