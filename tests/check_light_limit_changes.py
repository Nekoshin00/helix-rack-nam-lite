"""Check layer-limit enforcement when slots or their captures change."""
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "helix-rack" / "rack"), str(ROOT / "tools" / "sharc")]
os.environ["NAM_LAYERS"] = "1"
os.environ["NAM_GATHER"] = "1"

import nam_rack5 as kernel
from test_light_capture import capture_with_layers


def main():
    asm, layout = kernel.build(inst_bounds=kernel.RIG_BOUNDS)
    nm = kernel.nm
    nm.REP = layout.rep
    old_rig = nm.Rig
    nm.Rig = kernel.Rig
    try:
        check = nm.KernelCheck(asm, layout, capture_with_layers(14), nblk=3)
        rig = check.rig
        short = kernel.nam_lite.ir_samples(check.w, include_layer_count=True)
        full = kernel.nam_lite.ir_samples(capture_with_layers(23), include_layer_count=True)
        nm.set_ir(rig.sim, 1, short)
        nm.set_ir(rig.sim, 2, full)
        inst = rig.inst("limited", 0)
        rig.sim.wr(inst.i0 + kernel.P_LIM, kernel.LIM_TAG | 14)
        inst.knobs(model=1)
        check.start(inst, check.w, check.sig("initial", 8), "initial")
        check.play(inst, "initial", 3)
        assert rig.rep()[nm.REPW["R_LOADS"]] == 1

        inst.knobs(model=2)
        inst.pipe.cut()
        for n, signal in enumerate(check.sig("rejected", 20)):
            check.expect(inst, signal, f"over limit {n}", None)
        assert rig.sim.rd(layout.slot[0] + nm.S["S_SIG"]) == 0
        assert rig.rep()[nm.REPW["R_LOADS"]] == 1

        inst.knobs(model=1)
        check.start(inst, check.w, check.sig("valid again", 8), "valid again")
        check.play(inst, "valid again", 3)
        assert rig.rep()[nm.REPW["R_LOADS"]] == 2
        nm.set_ir(rig.sim, 1, full)
        for n, signal in enumerate(check.sig("replacement", nm.SIGCHK_N + 20)):
            inst.call(signal, f"replace with full {n}")
        assert rig.sim.rd(layout.slot[0] + nm.S["S_SIG"]) == 0
        assert rig.rep()[nm.REPW["R_LOADS"]] == 2

        nm.set_ir(rig.sim, 1, short)
        for n, signal in enumerate(check.sig("recovery", 4)):
            inst.call(signal, f"replace with light {n}")
        assert rig.rep()[nm.REPW["R_LOADS"]] == 3
        print("PASS: oversized captures are refused after slot change and replacement; valid capture recovers")
    finally:
        nm.Rig = old_rig


if __name__ == "__main__":
    main()
