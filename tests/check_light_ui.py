"""Verify an offline light-model L6IA; never creates an installable HXF."""
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "helix-rack" / "rack"), str(ROOT / "tools")]
import ir_title
import patch_amp as pa
import stage_main as main
import stage_model
from test_arm_guards import Cpu


def title_target(code, base, entry, category, pid, cave):
    cpu = Cpu(code, base)
    block = 0x20300000
    cpu.w32(block + 1, pid)
    cpu.w8(block + 12, category)
    cpu.r[6 if cave == "A" else 5] = block
    cpu.r[4] = 0x55
    return cpu.run(entry | 1) & ~1, cpu.r[4]


def check(path):
    data, _ = pa.load_l6ia_from_any(path)
    db = pa.parse_entry3_full(pa.get_entry_swapped(data, main.E_DB))
    stock = main.Image(pa.get_entry_swapped(data, main.E_COPY))
    im = main.Image(pa.get_entry_swapped(data, main.E_MAIN))
    graph_data = pa.get_entry_swapped(data, stage_model.E_GL)
    graph = struct.unpack('<%dI' % (len(graph_data) // 4), graph_data)
    models = []
    for name, display, limit in stage_model.LIGHT_MODELS:
        model = pa.find_model(db, name)
        models.append((model['words'][2], display))
        idx = model['blob_index']
        length, offset = graph[graph[3] + 2 * idx:graph[3] + 2 * idx + 2]
        blob = graph[offset:offset + length]
        pin, count = blob[10], blob[11]
        path, pid, value_offset, kind = blob[pin + 4 * (count - 1):pin + 4 * count]
        assert (path, pid, kind, blob[value_offset], blob[value_offset + 1]) == (
            0x0e, 16, 2, 1, 0x4e4c0000 | limit)
    stock1, stock2 = stock.u32(main.TAB1_BASE_PTRS[0]), stock.u32(main.TAB2_BASE_PTR)
    tab1, tab2 = im.u32(main.TAB1_BASE_PTRS[0]), im.u32(main.TAB2_BASE_PTR)
    assert im.rd(tab1, 823 * 12) == stock.rd(stock1, 823 * 12)
    assert im.rd(tab2, 823 * 44) == stock.rd(stock2, 823 * 44)
    stock_rows = [struct.unpack('<IHHI', stock.rd(stock1 + 12 * i, 12)) for i in range(823)]
    _, expected_pids = main.select_pids(stock_rows, len(models))
    assert expected_pids[0] == 380
    pids = []
    for k, (ni, display) in enumerate(models):
        row = struct.unpack('<IHHI', im.rd(tab1 + 12 * (823 + k), 12))
        assert row == (ni, expected_pids[k], 0, 3600), row
        pids.append(row[1])
        row2 = im.rd(tab2 + 44 * (823 + k), 44)
        assert struct.unpack_from('<I', row2)[0] == ni
        assert row2[4:20].rstrip(b'\0').decode('latin1') == display
    assert pa._decode_thumb_movw(im.rd(main.TAB1_CNT_INSN, 4))[1] == 827
    assert pa._decode_thumb_movw(im.rd(main.TAB2_CNT_INSN, 4))[1] == 827
    cat = main.FOLDER[0]
    sub = stock.u32(main.SUBCAT_CNT + 4 * cat)
    folder_idx = 4 * cat + sub
    assert im.u32(main.SUBCAT_CNT + 4 * cat) == sub + 1
    assert im.rd(main.SUBCAT_NAMES + 104 * cat + 26 * sub, 26).rstrip(b'\0') == b'NAM'
    checked = 0
    for idx in range(pa.E0_BLIST_SLOTS):
        before_ptr = stock.u32(main.BLIST_PTR_TAB + 4 * idx)
        before_count = stock.u32(main.BLIST_CNT_TAB + 4 * idx)
        after_ptr = im.u32(main.BLIST_PTR_TAB + 4 * idx)
        after_count = im.u32(main.BLIST_CNT_TAB + 4 * idx)
        if idx != folder_idx and (after_ptr, after_count) == (before_ptr, before_count):
            continue
        expected_prefix = 0 if idx == folder_idx else before_count
        assert after_count == expected_prefix + len(models)
        if expected_prefix:
            assert im.rd(after_ptr, 48 * expected_prefix) == stock.rd(before_ptr, 48 * expected_prefix)
        for k, ((ni, display), pid) in enumerate(zip(models, pids)):
            item = im.rd(after_ptr + 48 * (expected_prefix + k), 48)
            _, item_ni, ci, item_pid = struct.unpack_from('<IIiH', item)
            assert item_ni == ni and item[14:40].rstrip(b'\0').decode('latin1') == display
            if ci == -1:
                assert item_pid == pid
        checked += 1
    assert checked > 1, "no relocated browser lists found"
    ca = im.u32(ir_title.SITE_A + 4) & ~1
    cb = im.u32(ir_title.RELAY + 4) & ~1
    code = im.rd(ca, im.segs[0][3] + im.segs[0][2] - ca)
    for pid in pids:
        assert title_target(code, ca, ca, 12, pid, "A") == (ir_title.IR_NAME, 0)
        assert title_target(code, ca, cb, 12, pid, "B")[0] == ir_title.B_IR
        assert title_target(code, ca, ca, 11, pid, "A")[0] == ir_title.NON_IR
    assert title_target(code, ca, ca, 12, 77, "A")[0] == ir_title.NON_IR
    assert title_target(code, ca, cb, 12, 77, "B")[0] == ir_title.B_RET
    print(f"PASS: preset IDs {pids}; stock rows, {checked} browser lists and IR titles")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_light_ui.py <offline-light.l6ia>")
    check(sys.argv[1])
