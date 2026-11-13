#!/usr/bin/env python3
"""Staged test images for the Helix Rack (same method as the Floor's build_staged.py / test2c): test one
risk at a time, never flash the full build first. PC only, never share.

  test1_seg0_only.hxf   stock, except Entry 0's seg0 grown by the full build's amount, zero-filled
                        (does the bootloader take the bigger seg0 and does the Rack run normally?)
  test2c_slots.hxf      stock + stage_slots2 (Entry 5 last big slot per path -> normal, Entry 2 heaps a/b
                        shrunk): the layout that booted on the Floor. 13-block presets, 2 amps, preset changes.
Then the full build (build_rack.py). Needs build/rack_stock.l6ia and build/rack_s4.l6ia from build_rack.py.

usage: build_staged_rack.py <stock Helix_Rack_v3.80.0 .hxf>
"""
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from upstream import TOOLS  # noqa: E402
sys.path.insert(0, TOOLS)
import l6ia  # noqa: E402
import patch_amp as pa  # noqa: E402
import floor_hxf  # noqa: E402
import stage_main  # noqa: E402
from build_floor import SLOT_BYTES  # noqa: E402


def grow_seg0(e0, n):
    segs = stage_main.segments(e0)
    h0, p0, l0, d0, n0 = segs[0]
    out = bytearray(e0[:n0]) + bytes(n) + e0[n0:]
    struct.pack_into('<3I', out, h0, l0 + n, d0, n0 + n)
    for h, p, l, d, nx in segs[1:]:
        struct.pack_into('<3I', out, h + n, l, d, nx + n)
    struct.pack_into('<I', out, 4, len(out))
    return l6ia.fix_internal_crcs(bytes(out))


def check_and_pack(img, name, stock_raw):
    ents = l6ia.parse(img)
    for i, cap in SLOT_BYTES.items():
        assert ents[i]['payload_len'] <= cap, f"{name}: Entry {i} over its partition"
    path = os.path.join(ROOT, "build", "l6ia.tmp")
    open(path, "wb").write(img)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "l6ia_verify.py"), path],
                       capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"})
    os.remove(path)
    assert "ALL OK" in r.stdout, f"{name}: checksums"
    out = os.path.join(ROOT, "build", name)
    open(out, "wb").write(floor_hxf.pack(img, stock_raw))
    print(f"{name}: checksums ALL OK, partitions fit, MD5 {hashlib.md5(open(out, 'rb').read()).hexdigest()}")


def main():
    stock = sys.argv[1]
    raw = open(stock, "rb").read()
    assert hashlib.md5(raw).hexdigest() == floor_hxf.FLOOR_MD5
    data, _ = pa.load_l6ia_from_any(stock)
    full, _ = pa.load_l6ia_from_any(os.path.join(ROOT, "build", "rack_s4.l6ia"))
    e0, f0 = pa.get_entry_swapped(data, 0), pa.get_entry_swapped(full, 0)
    n = stage_main.segments(f0)[0][2] - stage_main.segments(e0)[0][2]
    g0 = grow_seg0(e0, n)
    assert stage_main.segments(g0)[0][2] == stage_main.segments(f0)[0][2]
    img, _, _ = l6ia.rebuild_archive(data, {0: g0})
    assert pa.get_entry_swapped(img, 1) == e0
    print(f"test 1: seg0 +{n} bytes of zeros (as the full build), Entry 1 stock")
    check_and_pack(img, "test1_seg0_only.hxf", raw)
    s0 = os.path.join(ROOT, "build", "rack_stock.l6ia")
    s1 = os.path.join(ROOT, "build", "test2c.l6ia")
    r = subprocess.run([sys.executable, os.path.join(HERE, "stage_slots2.py"), s0, s1], capture_output=True, text=True,
                       env={**os.environ, "PYTHONUTF8": "1"})
    assert r.returncode == 0, r.stderr
    print("test 2c: stage_slots2 only\n" + r.stdout.strip())
    check_and_pack(open(s1, "rb").read(), "test2c_slots.hxf", raw)
    os.remove(s1)


if __name__ == "__main__":
    main()
