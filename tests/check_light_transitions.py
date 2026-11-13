"""Exercise mixed layer counts and DMA recovery in the SHARC simulator."""
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
        check = nm.KernelCheck(asm, layout, capture_with_layers(23), nblk=3)
        check.w2 = nm.variant(capture_with_layers(20), 2)
        check.w3 = nm.variant(capture_with_layers(14), 3)
        check.w4 = nm.variant(capture_with_layers(16), 4)
        check.dbu = {id(check.w): None, id(check.w2): 15.0,
                     id(check.w3): 6.0, id(check.w4): None}
        for slot, model, dbu in (
            (1, check.w, None), (3, check.w2, 15.0),
            (7, check.w3, 6.0), (9, check.w4, None),
        ):
            nm.set_ir(check.rig.sim, slot, kernel.nam_lite.ir_samples(
                model, dbu, include_layer_count=True))
        check.two_models_load()
        check.two_models_play()
        check.model_change_crossfades()
        check.B.knobs(model=3)
        check.start(check.B, check.w2, check.sig("B return", 18), "B to 20 layers")
        check.third_and_fourth()
        check.takeover()
        check.dma_timeout()
        check.busy_channel()
        check.capture_replaced()
        print("PASS: mixed 23/20/16/14 layers, transitions, slot takeover and DMA recovery")
    finally:
        nm.Rig = old_rig


if __name__ == "__main__":
    main()
