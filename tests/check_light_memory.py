"""Exercise instance-memory and SDRAM boundaries in the SHARC simulator."""
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
    nm = kernel.nm
    _, default_layout = kernel.build(inst_bounds=kernel.RIG_BOUNDS)
    dm_lo, pm_lo = 0xB3000, 0x91000
    bounds = ((dm_lo, dm_lo + default_layout.inst_dm_need + 0x20),
              (pm_lo, pm_lo + default_layout.inst_pm_need + 0x20))
    asm, layout = kernel.build(inst_bounds=bounds)
    nm.REP = layout.rep
    signal = [kernel.nf.ssim_f2b(0.1 * ((n * 7) % 11 - 5)) for n in range(16)]
    dm_last = bounds[0][1] - layout.inst_dm_need
    pm_last = bounds[1][1] - layout.inst_pm_need
    cases = (
        ("DM first", dm_lo, pm_lo, layout.sdr_need, "load"),
        ("DM last", dm_last, pm_lo, layout.sdr_need, "load"),
        ("DM below", dm_lo - 1, pm_lo, layout.sdr_need, "silent"),
        ("DM above", dm_last + 1, pm_lo, layout.sdr_need, "silent"),
        ("PM last", dm_lo, pm_last, layout.sdr_need, "load"),
        ("PM below", dm_lo, pm_lo - 1, layout.sdr_need, "silent"),
        ("PM above", dm_lo, pm_last + 1, layout.sdr_need, "silent"),
        ("SDRAM short", dm_lo, pm_lo, layout.sdr_need - 1, "passthrough"),
    )
    for label, i0, i8, size, expected in cases:
        rig = kernel.Rig(asm, layout)
        nm.set_ir(rig.sim, 1, kernel.nam_lite.ir_samples(
            capture_with_layers(14), include_layer_count=True))
        inst = nm.Inst(rig, label, i0, i8, 0xB6000, 0x400000, layout.sdram_words())
        rig.sim.wr(inst.entry + 0x10 + 7, inst.sdram + size)
        inst.knobs(model=1)
        before = [rig.sim.rd(inst.sdram + i) for i in range(layout.sdram_words())]
        check_dma = rig.check_dma

        def check_exact_sdram(current, call_label):
            for _, ei, _, n, em, _ in rig.dma.log:
                e0, e1 = sorted((ei, ei + (n - 1) * em))
                if inst.sdram <= e0 < inst.sdram + layout.sdram_words():
                    assert e1 < inst.sdram + size, (call_label, hex(e0), hex(e1), size)
            check_dma(current, call_label)

        rig.check_dma = check_exact_sdram
        output = inst.call(signal, label)
        initialized = rig.sim.rd(layout.slot[0] + nm.S["S_INIT"])
        loads = rig.rep()[nm.REPW["R_LOADS"]]
        if expected == "load":
            assert initialized == 1 and loads == 1, (label, initialized, loads)
            assert rig.sim.rd(layout.slot[0] + layout.s_nskip) == 9
        else:
            assert initialized == 0 and loads == 0, (label, initialized, loads)
            assert output == (signal if expected == "passthrough" else [0] * 16), label
            assert before == [rig.sim.rd(inst.sdram + i) for i in range(layout.sdram_words())], label
        print(f"PASS: {label}: {expected}", flush=True)


if __name__ == "__main__":
    main()
