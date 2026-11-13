#!/usr/bin/env python3
"""Build a Rack test image with only the experimental seg0 expansion.

The image is otherwise stock: it has no NAM blocks or light-capture kernel.
usage: build_light_stage1.py <stock Rack 3.80.0.hxf> [-o output.hxf]
"""
import argparse
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from upstream import TOOLS  # noqa: E402
sys.path.insert(0, TOOLS)
import hxf  # noqa: E402
import l6ia  # noqa: E402
import patch_amp as pa  # noqa: E402
import floor_hxf  # noqa: E402
import stage_main  # noqa: E402
from build_floor import SLOT_BYTES  # noqa: E402
from build_staged import grow_seg0  # noqa: E402


def run(script, *args, env):
    subprocess.run([sys.executable, str(script), *(str(arg) for arg in args)],
                   cwd=ROOT, env=env, check=True)


def verify_image(path, env):
    result = subprocess.run([sys.executable, str(Path(TOOLS) / "l6ia_verify.py"), str(path)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode or "ALL OK" not in result.stdout:
        raise RuntimeError(f"L6IA verification failed:\n{result.stdout}\n{result.stderr}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path)
    parser.add_argument("-o", "--output", type=Path,
                        default=HERE.parent / "build" / "Rack_light_test1_seg0_only.hxf")
    args = parser.parse_args()
    args.stock = args.stock.resolve()
    args.output = args.output.resolve()
    if args.output.exists():
        raise FileExistsError(f"Output already exists: {args.output}")
    raw = args.stock.read_bytes()
    if hashlib.md5(raw).hexdigest() != floor_hxf.FLOOR_MD5:
        raise ValueError("Input must be the original Helix Rack 3.80.0 firmware.")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("NAM_")}
    env.update(PYTHONUTF8="1", NAM_KERNEL="nam_rack5", NAM_LAYERS="1",
               NAM_GATHER="1", NAM_MAX_BLOCKS="16")
    with tempfile.TemporaryDirectory(prefix="rack-light-stage1-") as directory:
        temp = Path(directory)
        stock, slots, model, prototype = (temp / f"{name}.l6ia"
                                           for name in ("stock", "slots", "model", "prototype"))
        run(Path(TOOLS) / "hxf.py", "unpack", args.stock, stock, env=env)
        run(HERE / "stage_slots2.py", stock, slots, env=env)
        run(HERE / "stage_model.py", slots, model, env=env)
        run(HERE / "stage_main.py", model, prototype, env=env)
        run(ROOT / "tests" / "check_light_ui.py", prototype, env=env)
        verify_image(prototype, env)

        original = stock.read_bytes()
        prototype_data = prototype.read_bytes()
        e0 = pa.get_entry_swapped(original, 0)
        prototype_e0 = pa.get_entry_swapped(prototype_data, 0)
        old_segments = stage_main.segments(e0)
        new_segments = stage_main.segments(prototype_e0)
        old_size, new_size = old_segments[0][2], new_segments[0][2]
        growth = new_size - old_size
        if growth <= 0 or new_size > stage_main.CAVE_END - stage_main.SEG0[0]:
            raise ValueError(f"Unexpected experimental seg0 size: {new_size:#x}")
        expanded = grow_seg0(e0, growth)
        expanded_segments = stage_main.segments(expanded)
        if len(old_segments) != len(expanded_segments):
            raise ValueError("Segment count changed")
        for i, (old, new) in enumerate(zip(old_segments, expanded_segments)):
            if old[3] != new[3]:
                raise ValueError(f"Destination of segment {i} changed")
            old_data = e0[old[1]:old[1] + old[2]]
            new_data = expanded[new[1]:new[1] + new[2]]
            expected = old_data + bytes(growth) if i == 0 else old_data
            if new_data != expected:
                raise ValueError(f"Unexpected change in segment {i}")
        image, _, _ = l6ia.rebuild_archive(original, {0: expanded})
        original_entries, image_entries = l6ia.parse(original), l6ia.parse(image)
        if len(original_entries) != len(image_entries):
            raise ValueError("Archive entry count changed")
        if pa.get_entry_swapped(image, 0) != expanded:
            raise ValueError("Unexpected change in entry 0")
        for i in range(1, len(original_entries)):
            old, new = original_entries[i], image_entries[i]
            old_payload = original[old["payload_off"]:old["payload_off"] + old["payload_len"]]
            new_payload = image[new["payload_off"]:new["payload_off"] + new["payload_len"]]
            if old_payload != new_payload:
                raise ValueError(f"Unexpected change in entry {i}")
        for i, cap in SLOT_BYTES.items():
            if image_entries[i]["payload_len"] > cap:
                raise ValueError(f"Entry {i} exceeds its partition")
        test_image = temp / "test1.l6ia"
        test_image.write_bytes(image)
        verify_image(test_image, env)

        packed = floor_hxf.pack(image, raw)
        chunks = {cid: body for cid, _, _, body in hxf._chunks(packed)}
        if (struct.unpack_from(">I", packed, 4)[0] != len(packed) - 8
                or struct.unpack_from(">I", chunks[b"HEAD"], 16)[0] != len(image)
                or chunks[b"HEAD"][20:36] != hashlib.md5(image).digest()
                or struct.unpack_from(">I", chunks[b"dinf"], 12)[0] != len(image)
                or zlib.decompress(chunks[b"data"]) != image):
            raise ValueError("HXF container verification failed")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as output:
            output.write(packed)
        print(f"Stage 1 only: seg0 +{growth} zero bytes; all other entries stock.")
        print(f"NO NAM BLOCKS OR LIGHT-CAPTURE KERNEL: {args.output}")
        print(f"SHA-256 {hashlib.sha256(packed).hexdigest().upper()}")


if __name__ == "__main__":
    main()
