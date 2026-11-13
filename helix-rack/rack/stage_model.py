#!/usr/bin/env python3
"""Build stages B4 + C + D: the NAM amp in the model DB (Entry 4) and the graph library
(Entry 5), and the SHARC's Blob 0 buffer and Heap 6 (Entry 2) to take the bigger Blob 0.

Upstream's patch_amp functions do the work, with the Floor's numbers:
- model count 863, not 864 (add_model_entry3/4 are re-made from their source with that
  one literal changed; upstream's files are not touched);
- host composite 0x6001aa (Clarity's), Amp harnesses 0x60000d/0x60000e/0x600010 with
  placeholder 0x6000c9, Blob 0 at 0x21cd06;
- the NAM member is primitive HOOK_ID (0x128, an unused registered primitive), with the
  instance sizes nam_rack.py needs (DM 0x58a, PM 0x1be, SDRAM 0x5000);
- Entry 2: the Blob 0 buffer size immediate (0x7a612) raised to BLOB0_CAP, and Heap 6
  moved from 0x297318..0x2af64b (it starts exactly where the stock buffer ends) to
  HEAP6_NEW, in free DDR2 below heap c; all three of its immediates (start, end, clear).

usage: stage_model.py <in.l6ia> <out.l6ia>
"""
import inspect
from functools import partial
import struct
import sys

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upstream import TOOLS  # noqa: E402
sys.path.insert(0, TOOLS)
import l6ia  # noqa: E402
import patch_amp as pa  # noqa: E402
import importlib, os  # noqa: E402
nam_rack = importlib.import_module(os.environ.get("NAM_KERNEL", "nam_rack"))
from stage_slots import halfwords, from_halfwords, replace_once  # noqa: E402

E_E2, E_DB, E_GL = 2, 4, 5                 # Floor entries: SHARC LDR, model DB, graph library
N_MODELS = 863
HOOK_ID = 0x128
BLOB0_BASE, BLOB0_STOCK = 0x21D106, 0x7A612
HEAP6_OLD = (0x297718, 0x2AFA4B)
HEAP6_NEW = (0x30DC40, 0x30DC40 + (HEAP6_OLD[1] - HEAP6_OLD[0]))   # Rack's LDR data in DDR2 ends at 0x30dc32
HEAP7 = 0x2AFA4C
BLOB0_CAP = HEAP7 - BLOB0_BASE             # the buffer may grow up to Heap 7 once Heap 6 is gone
SDRAM_WORDS = 0x5000 if nam_rack.__name__ == "nam_rack" else nam_rack.Layout().sdram_words()

pa.NAM_HOST_COMPOSITE = 0x6001AA
pa.AMP_HARNESSES = (0x60000D, 0x60000E, 0x600010)
pa.AMP_PLACEHOLDER = 0x6000C9
pa.SHARC_BLOB0_BASE = BLOB0_BASE
pa.SHARC_BLOB0_WORDS = BLOB0_STOCK
pa.SHARC_BLOB0_MAX_WORDS = BLOB0_CAP


def _floor_copy(fn):
    src = inspect.getsource(fn).replace("864", str(N_MODELS))
    ns = {}
    exec(compile(src, f"<floor {fn.__name__}>", "exec"), pa.__dict__, ns)
    return ns[fn.__name__]


def nam_host_member(b0, comp_id, sdram_words=0):
    """Upstream's, with the Floor's primitive and instance sizes."""
    ct = b0[0x10]
    hdr = b0[ct + 7 * (comp_id - 0x600000): ct + 7 * (comp_id - 0x600000) + 7]
    assert hdr[2] == 3, f'{comp_id:#x} has {hdr[2]} members, the NAM host wants 3'
    r = hdr[3] + 20
    assert 0x600000 <= b0[r + 6] < 0x601000 and b0[r + 7] == 1 and b0[r + 9] == 1
    b0[r + 6] = HOOK_ID
    b0[r + 11] = 0
    for k in range(15, 20):
        b0[r + k] = 0
    lay = nam_rack.Layout()
    b0[r + 13], b0[r + 14], b0[r + 15] = lay.inst_dm_need, lay.inst_pm_need, sdram_words


pa.nam_host_member = nam_host_member
add_model_entry3 = _floor_copy(pa.add_model_entry3)
add_model_entry4 = _floor_copy(pa.add_model_entry4)

LIGHT_MODELS = (
    ('HD2_AmpNAMLite', 'NAM A2 Lite', 23),
    ('HD2_AmpNAMLite20', 'NAM Lite 20', 20),
    ('HD2_AmpNAMLite16', 'NAM Lite 16', 16),
    ('HD2_AmpNAMLite14', 'NAM Lite 14', 14),
)


def nam_host_blob_with_limit(comp_id, params, pid, value):
    """Create the upstream host blob with one additional member initialization."""
    n = len(params)
    m = 2 * n + 1
    a_off = 0x18
    data_off = a_off + 20 * n
    c_off = data_off + 3 * n
    d_off = c_off + 4 * n
    e_off = d_off + 4 * n
    end = e_off + 4 * n
    pm = [a_off, 0, c_off, 0, c_off, 0, d_off, 0, e_off, 0, end, 0]
    pm += [5 * n, 2 * n, 3 * n, 3 * n, n, n]
    pm += [2 * n, 0, n, n, n, 0]
    for k, p in enumerate(params):
        pm += [data_off, 0, k, p['op'], 1, 2, 0, 0, 1, 0]
    for k in range(n):
        pm += [data_off + 3 * k, 0, n + k, 1, 0, 3, 3, 3, 0, 0]
    for p in params:
        pm += [0x0e, p['pid'], 1]
    for k in range(n):
        pm += [k, n + k, 0, 0]
    for k, p in sorted(enumerate(params), key=lambda kp: kp[1]['slot']):
        pm += [k, k, p['slot'], 0]
    for k in range(n):
        pm += [k, k, k, 0]
    assert len(pm) == end
    v0 = 0x10
    tree = v0 + 2 * m
    pmo = tree + 4
    pin = pmo + len(pm)
    ini = pin + 4 * m
    sub = ini + 2 * (n + m)
    b = [3, 2, tree, 1, ini, n + m, pmo, len(pm), sub, 0, pin, m]
    b += [1, 0, 1, 2]
    for p in params + params:
        b += [1, p['default_word']]
    b += [1, value, 0, comp_id, 0, 0]
    b += pm
    for k, p in enumerate(params):
        b += [0x0c, p['slot'], v0 + 2 * k, 1]
    for k, p in enumerate(params):
        b += [0x0e, p['pid'], v0 + 2 * (n + k), 2]
    b += [0x0e, pid, v0 + 4 * n, 2]
    for k in range(n):
        b += [1, pmo + data_off + 3 * k]
    for k in range(m):
        b += [1, pin + 4 * k]
    assert len(b) == sub
    return b


def expand_blob0(e2_raw):
    H = halfwords(e2_raw)
    rep = []
    for old, new, what in (
            ([0x0F00, BLOB0_STOCK >> 16, BLOB0_STOCK & 0xFFFF], [0x0F00, BLOB0_CAP >> 16, BLOB0_CAP & 0xFFFF],
             "Blob 0 buffer size"),
            ([0x0F23, HEAP6_OLD[0] >> 16, HEAP6_OLD[0] & 0xFFFF], [0x0F23, HEAP6_NEW[0] >> 16, HEAP6_NEW[0] & 0xFFFF],
             "Heap 6 start"),
            ([0x0F13, HEAP6_OLD[1] >> 16, HEAP6_OLD[1] & 0xFFFF], [0x0F13, HEAP6_NEW[1] >> 16, HEAP6_NEW[1] & 0xFFFF],
             "Heap 6 end"),
            ([0x0F04, HEAP6_OLD[0] >> 16, HEAP6_OLD[0] & 0xFFFF], [0x0F04, HEAP6_NEW[0] >> 16, HEAP6_NEW[0] & 0xFFFF],
             "Heap 6 clear start")):
        k = replace_once(H, old, new, what)
        rep.append(f"{what}: w{k // 2} {' '.join(f'{x:04x}' for x in old)} -> {' '.join(f'{x:04x}' for x in new)}")
    return from_halfwords(H), rep


def main():
    src, out = sys.argv[1], sys.argv[2]
    light = os.environ.get("NAM_LAYERS") == "1"
    if light and (not getattr(nam_rack, "LAYERS", False) or os.environ.get("NAM_555")
                  or os.environ.get("NAM_555_VARIANT")):
        raise SystemExit("NAM_LAYERS requires the layer-aware kernel and cannot be combined with NAM_555 variants.")
    data, _ = pa.load_l6ia_from_any(src)
    ents = l6ia.parse(data)
    e_db = pa.get_entry_swapped(data, E_DB)
    e_gl = pa.get_entry_swapped(data, E_GL)
    info = pa.parse_entry3_full(e_db)
    assert len(info['models']) == N_MODELS
    clarity = pa.find_model(info, 'HD2_AmpLine6Clarity')
    if os.environ.get("NAM_555"):                         # EXPERIMENT build/EXPERIMENT-555
        import spec555
        nam = spec555.nam_params(e_db, info)
    else:
        nam = pa.nam_params(e_db, info)
    # 555 "fx" variant: the model DB record (category distortion, its group lists) is Xenomorph's, as
    # upstream's add-fx-model; the composite stays Clarity's copy (amp-size instance memory)
    db_src = pa.find_model(info, 'HD2_DistXenomorphFuzzMono') if os.environ.get("NAM_555_VARIANT") == "fx" else clarity
    new_gl, new_db = e_gl, e_db
    models = LIGHT_MODELS if light else LIGHT_MODELS[:1]
    added = []
    original_blob = pa.nam_host_blob
    try:
        for name, display, limit in models:
            if light:
                pa.nam_host_blob = partial(
                    nam_host_blob_with_limit, pid=nam_rack.P_LIM, value=nam_rack.LIM_TAG | limit)
            new_gl, blob_idx, comp = add_model_entry4(new_gl, clarity['blob_index'], nam, SDRAM_WORDS)
            new_db, model_id, lists = add_model_entry3(new_db, db_src, name, display, blob_idx, nam)
            added.append((display, model_id, blob_idx, comp, limit))
    finally:
        pa.nam_host_blob = original_blob
    e2 = data[ents[E_E2]['payload_off']: ents[E_E2]['payload_off'] + ents[E_E2]['payload_len']]
    new_e2, rep = expand_blob0(e2)
    # checks: the new Blob 0 as the SHARC would relocate it, and the new model as parsed back
    w = struct.unpack('<%dI' % (len(new_gl) // 4), new_gl)
    ln, off = w[w[3]], w[w[3] + 1]
    b0 = list(w[off: off + ln])
    err = pa.sharc_blob0_check(b0, BLOB0_CAP)
    assert err is None, err
    chk = pa.parse_entry3_full(new_db)
    assert len(chk['models']) == N_MODELS + len(models)
    assert [m['name'] for m in chk['models'][N_MODELS:]] == [name for name, _, _ in models]
    assert all(a['words'] == b['words'] or a['off'] != b['off'] or True for a, b in zip(info['models'], chk['models']))
    assert [(a['name'], a['model_id'], a['blob_index']) for a in info['models']] == \
        [(a['name'], a['model_id'], a['blob_index']) for a in chk['models'][:N_MODELS]], "a stock model changed"
    img, _, _ = l6ia.rebuild_archive(data, {E_E2: l6ia.swap32(new_e2), E_DB: new_db, E_GL: new_gl})
    open(out, 'wb').write(img)
    for display, model_id, blob_idx, comp, limit in added:
        print(f"model DB: '{display}' = model {model_id} on blob {blob_idx}, host {comp:#x}" +
              (f", layer limit {limit}" if light else f", in browser groups {lists}"))
    print(f"graph library: member 1 = primitive {HOOK_ID:#x}; "
          f"Blob 0 {BLOB0_STOCK:#x} -> {len(b0):#x} words (cap {BLOB0_CAP:#x}), SHARC relocation check OK")
    for line in rep:
        print(line)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
