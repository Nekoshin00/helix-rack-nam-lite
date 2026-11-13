#!/usr/bin/env python3
"""EXPERIMENTAL personal build: Helix Rack 3.80.0 with NAM A2 Lite, ported from the
Floor pipeline. NAM audio has been tested on a Rack; long-term stability remains unverified.

usage: build_rack.py <Helix_Rack_v3.80.0_0x7d01f5efb.hxf> [-o out.hxf]   (run from anywhere)
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # helix-rack/
TOOLS = os.path.join(os.path.dirname(ROOT), "tools")
STOCK_MD5 = "4ef2fdf2e5a45e80ccf3ccdf23cf017d"


def run(*a):
    print("$", *[os.path.basename(x) for x in a[:1]], *a[1:], flush=True)
    subprocess.run([sys.executable, *a], check=True, cwd=ROOT, env=os.environ)


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit(__doc__)
    if os.environ.get("NAM_LAYERS") == "1":
        sys.exit("NAM_LAYERS is experimental and not supported by the firmware build yet.")
    stock = os.path.abspath(argv[0])
    got = hashlib.md5(open(stock, "rb").read()).hexdigest()
    assert got == STOCK_MD5, f"MD5 {got} is not the stock Helix Rack 3.80.0 file"
    b = os.path.join(ROOT, "build")
    out = os.path.abspath(argv[argv.index("-o") + 1]) if "-o" in argv else \
        os.path.join(b, "Helix_Rack_v3.80.0_NAM2_PERSONAL.hxf")
    os.makedirs(b, exist_ok=True)
    s = [os.path.join(b, f"rack_{n}.l6ia") for n in ("stock", "s1", "s2", "s3", "s4")]
    os.environ.update(PYTHONUTF8="1", NAM_KERNEL="nam_rack5", NAM_MAX_BLOCKS="16", NAM_MAX_STEADY="60000")
    run(os.path.join(TOOLS, "hxf.py"), "unpack", stock, s[0])
    for i, st in enumerate(("stage_slots2", "stage_model", "stage_kernel", "stage_main")):
        run(os.path.join(HERE, st + ".py"), s[i], s[i + 1])
    for k in ("NAM_KERNEL", "NAM_MAX_BLOCKS"):      # the guard tests use the 13-cap rule set
        del os.environ[k]
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "l6ia_verify.py"), s[4]], capture_output=True, text=True)
    assert "ALL OK" in r.stdout, r.stdout[-2000:]
    run(os.path.join(HERE, "test_arm_guards.py"))
    run(os.path.join(HERE, "test_ir_title.py"))
    run(os.path.join(HERE, "floor_hxf.py"), "pack", s[4], out, "--donor", stock)
    for f in s[1:4]:
        os.remove(f)
    print(f"\nDone: {out}\nMD5 {hashlib.md5(open(out, 'rb').read()).hexdigest()}\n"
          "EXPERIMENTAL: long-term stability not verified on hardware. Do not distribute.")


if __name__ == "__main__":
    main()
