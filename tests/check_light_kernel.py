"""Run the experimental layer-aware Rack kernel in the SHARC simulator."""
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "helix-rack" / "rack"), str(ROOT / "tools" / "sharc")]
os.environ["NAM_LAYERS"] = "1"
os.environ["NAM_GATHER"] = "1"

import nam_rack5 as kernel
from test_light_capture import capture_with_layers


def check_audio(asm, layout, count):
    nm = kernel.nm
    old_rig = nm.Rig
    nm.Rig = kernel.Rig
    try:
        weights = capture_with_layers(count)
        check = nm.KernelCheck(asm, layout, weights, nblk=3)
        for slot, model, dbu in (
            (1, check.w, None), (3, check.w2, 15.0),
            (7, check.w3, 6.0), (9, check.w4, None),
        ):
            words = kernel.nam_lite.ir_samples(model, dbu, include_layer_count=True)
            nm.set_ir(check.rig.sim, slot, words)
        check.silence_fixed_point()
        check.two_models_load()
        check.two_models_play()
        instructions = sum(cycles for _, cycles in check.steady) / len(check.steady)
        check.model_change_crossfades()
        print(f"{count} layers: two models and model change match the reference; "
              f"steady mean {instructions:.0f} simulated instructions")
        return instructions
    finally:
        nm.Rig = old_rig


def check_limit(asm, layout, count, limit, tagged, expected_load):
    nm = kernel.nm
    rig = kernel.Rig(asm, layout)
    instance = rig.inst("limit", 0)
    words = kernel.nam_lite.ir_samples(capture_with_layers(count), include_layer_count=tagged)
    nm.set_ir(rig.sim, 1, words)
    rig.sim.wr(instance.i0 + kernel.P_LIM, kernel.LIM_TAG | limit)
    instance.knobs(model=1)
    output = instance.call([0] * 16, "layer limit")
    loads = rig.rep()[nm.REPW["R_LOADS"]]
    assert loads == expected_load, (count, limit, tagged, loads)
    if not expected_load:
        assert output == [0] * 16, (count, limit, output)
    print(f"{count} layers, limit {limit}, tagged={tagged}: loads={loads}")


def main():
    asm, layout = kernel.build(inst_bounds=kernel.RIG_BOUNDS)
    kernel.nm.REP = layout.rep
    assert layout.rg.spare()["RX"] == kernel.REGIONS3["RX"][1] - kernel.REGIONS3["RX"][0]
    instructions = {count: check_audio(asm, layout, count) for count in (23, 20, 16, 14)}
    assert instructions[14] < instructions[16] < instructions[20] < instructions[23], instructions
    for count, limit, tagged, expected in (
        (14, 14, True, 1), (16, 14, True, 0), (23, 14, False, 0),
        (20, 20, True, 1), (20, 16, True, 0),
    ):
        check_limit(asm, layout, count, limit, tagged, expected)


if __name__ == "__main__":
    main()
