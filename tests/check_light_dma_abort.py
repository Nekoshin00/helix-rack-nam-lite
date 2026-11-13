"""Inject DMA status that remains busy after disabling the simulated channel."""
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "helix-rack" / "rack"), str(ROOT / "tools" / "sharc")]
os.environ["NAM_LAYERS"] = "1"
os.environ["NAM_GATHER"] = "1"
os.environ["NAM_P9_MODE"] = "nomask"
os.environ["NAM_PR1"] = "1"

import nam_rack5 as kernel
from test_light_capture import capture_with_layers


def probe(asm, layout, count, release_after):
    nm = kernel.nm
    rig = kernel.Rig(asm, layout)
    words = kernel.nam_lite.ir_samples(capture_with_layers(count), include_layer_count=True)
    nm.set_ir(rig.sim, 1, words)
    inst = rig.inst("abort", 0)
    inst.knobs(model=1)
    signal = [kernel.nf.ssim_f2b(0.15 * ((n * 7) % 11 - 5) / 5) for n in range(16)]
    for n in range(3):
        inst.call(signal, f"warmup {n}")
    assert rig.sim.rd(layout.slot[0] + layout.s_nskip) == 23 - count

    sim, dma = rig.sim, rig.dma
    dma.mode = "stall"
    rd0, wr0 = sim.rd, sim.wr
    polls, early, stopped, busy = 0, [], False, False
    before = rig.rep()[nm.REPW["R_TIMEOUTS"]]
    lrptl = kernel.sasm.UREG_CODE["LRPTL"]
    initial = nm.EP0IMSK | kernel.EP0LAT | 0x20080
    sim.set(lrptl, initial)
    busy_status = nm.DMAS | nm.CHS | nm.EXTS

    def read(address):
        nonlocal polls, busy
        value = rd0(address)
        if stopped and address == nm.DMAC0:
            if sim.pc == rig.syms["DA_W"]:
                polls += 1
                busy = release_after is None or polls <= release_after
            return (value | busy_status) if busy else (value & ~busy_status)
        return value

    def write(address, value):
        nonlocal stopped, busy
        if address == nm.DMAC0 and not value & nm.DEN and dma.active:
            stopped, busy = True, True
        if busy and address in (nm.ICEP0, nm.CPEP0):
            early.append((address, value))
        return wr0(address, value)

    sim.rd, sim.wr = read, write
    try:
        output = inst.call(signal, "post-disable DMA remains busy")
    finally:
        sim.rd, sim.wr = rd0, wr0
    assert stopped and not any(output)
    assert polls == (1000 if release_after is None else release_after + 1), polls
    assert not early, early
    assert sim.get(lrptl) == initial
    assert rig.rep()[nm.REPW["R_TIMEOUTS"]] == before + 1
    if release_after is None:
        dma.mode = "ok"
        dma.wr0(nm.DMAC0, busy_status)
        sim.dm[layout.rep + nm.REPW["R_BACKOFF"]] = 0
        dma.writes.clear()
        assert not any(inst.call(signal, "readmission while busy"))
        assert not dma.writes
        dma.wr0(nm.DMAC0, 0)
        sim.dm[layout.rep + nm.REPW["R_BACKOFF"]] = 0
        dma.writes.clear()
        for n in range(4):
            output = inst.call(signal, f"recovery {n}")
        assert any(output)
        assert dma.writes[:2] == [(nm.ICEP0, 0), (nm.CPEP0, 0)]
    print(f"PASS: {count} layers, release after {release_after}, polls {polls}", flush=True)


def main():
    asm, layout = kernel.build(inst_bounds=kernel.RIG_BOUNDS)
    kernel.nm.REP = layout.rep
    for count in (14, 23):
        for release_after in (None, 5, 999):
            probe(asm, layout, count, release_after)


if __name__ == "__main__":
    main()
