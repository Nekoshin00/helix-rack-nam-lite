import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "sharc"))
import nam_lite
import nam_pack


def capture_with_layers(count):
    weights = nam_lite.placeholder()
    offset = nam_lite.C
    for i, kernel in enumerate(nam_pack.KERNEL):
        length = 3 * nam_lite.C + nam_lite.C ** 2 * (kernel + 1)
        if i >= count:
            weights[offset:offset + length] = [0.0] * length
        offset += length
    return weights


class LightCaptureTests(unittest.TestCase):
    def test_layer_header_and_legacy_payload(self):
        for count in (0, 1, 14, 16, 20, 23):
            with self.subTest(count=count):
                weights = capture_with_layers(count)
                legacy = nam_lite.ir_samples(weights)
                tagged = nam_lite.ir_samples(weights, include_layer_count=True)
                self.assertEqual(nam_lite.layer_count(weights), count)
                self.assertEqual(tagged[:7], legacy[:7])
                self.assertEqual(tagged[8:], legacy[8:])
                expected = count / 32.0 if 0 < count < 23 else 0.0
                self.assertEqual(struct.unpack("<f", struct.pack("<I", tagged[7]))[0], expected)
                self.assertEqual(legacy[7], 0)

    def test_internal_zero_layer_does_not_hide_later_layers(self):
        weights = capture_with_layers(16)
        first_length = 3 * nam_lite.C + nam_lite.C ** 2 * (nam_pack.KERNEL[0] + 1)
        weights[nam_lite.C:nam_lite.C + first_length] = [0.0] * first_length
        self.assertEqual(nam_lite.layer_count(weights), 16)

    def test_converter_flag_encodes_light_capture(self):
        import json

        model = {
            "architecture": "WaveNet",
            "config": {"layers": [{"channels": 3}]},
            "weights": capture_with_layers(16),
            "sample_rate": 48000,
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "capture.nam"
            source.write_text(json.dumps(model), encoding="utf-8")
            outputs = []
            for args in ([], ["--layers"]):
                output = Path(directory) / f"capture{len(outputs)}.wav"
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "nam2ir.py"), str(source),
                     "-o", str(output), *args],
                    check=True, capture_output=True, text=True,
                )
                outputs.append(output.read_bytes())
            self.assertEqual(outputs[0][:44 + 7 * 4], outputs[1][:44 + 7 * 4])
            self.assertEqual(outputs[0][44 + 8 * 4:], outputs[1][44 + 8 * 4:])
            self.assertEqual(struct.unpack_from("<f", outputs[1], 44 + 7 * 4)[0], 0.5)
            self.assertIn("current Rack firmware does not skip layers", result.stdout)


if __name__ == "__main__":
    unittest.main()
