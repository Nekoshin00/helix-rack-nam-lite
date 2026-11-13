import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "helix-rack" / "rack"))
import stage_model
import stage_main


class LightModelTests(unittest.TestCase):
    def test_preset_ids_skip_unencodable_values(self):
        available = {380, 381, 382, 383, 516, 572}
        rows = [(0, pid, 0, 0) for pid in range(1, 833) if pid not in available]
        _, pids = stage_main.select_pids(rows, 4)
        self.assertEqual(pids, [380, 382, 516, 572])
        with self.assertRaises(AssertionError):
            stage_main.select_pids(rows, 5)

    def test_limit_initialization_preserves_parameter_map(self):
        params = [
            {'op': 10, 'pid': 2, 'slot': 1, 'default_word': 0x3f800000},
            {'op': 11, 'pid': 7, 'slot': 0, 'default_word': 3},
        ]
        original = stage_model.pa.nam_host_blob(0x600123, params)
        for limit in (23, 20, 16, 14):
            with self.subTest(limit=limit):
                value = 0x4e4c0000 | limit
                blob = stage_model.nam_host_blob_with_limit(0x600123, params, 16, value)
                tree, init, pmap, pmap_len, end, pins, pin_count = (
                    blob[2], blob[4], blob[6], blob[7], blob[8], blob[10], blob[11])
                self.assertEqual(blob[pmap:pmap + pmap_len],
                                 original[original[6]:original[6] + original[7]])
                self.assertEqual(blob[tree:tree + 4], original[original[2]:original[2] + 4])
                self.assertEqual(pin_count, original[11] + 1)
                self.assertEqual(blob[pins:pins + 4 * (pin_count - 1)],
                                 original[original[10]:original[10] + 4 * original[11]])
                path, pid, value_offset, kind = blob[pins + 4 * (pin_count - 1):pins + 4 * pin_count]
                self.assertEqual((path, pid, kind), (0x0e, 16, 2))
                self.assertEqual(blob[value_offset:value_offset + 2], [1, value])
                self.assertEqual(blob[init:end],
                                 [item for k in range(len(params))
                                  for item in (1, pmap + 0x18 + 20 * len(params) + 3 * k)]
                                 + [item for k in range(pin_count) for item in (1, pins + 4 * k)])


if __name__ == "__main__":
    unittest.main()
