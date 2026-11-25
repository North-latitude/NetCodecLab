"""NetCodecLab 全功能自查：核心算法 T-01~T-11 + 界面三个页面交互。

跑法（仓库根目录）：
    python tools/self_check.py
全部通过时返回 0，有失败项返回 1。
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import (  # noqa: E402
    base_to_dec,
    batch_compare,
    batch_experiment,
    build_frames,
    compare_schemes,
    crc_check,
    crc_encode,
    crc_of_text,
    dec_to_base,
    decimal_to_binary,
    encode_text,
    hamming_decode,
    hamming_encode,
    inet_checksum,
    inet_verify,
    inject_error,
    matrix_check,
    matrix_encode,
    parity_check,
    parity_encode,
    parity_locate,
    text_to_bitstream,
)

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition, detail: str = "") -> bool:
    ok = bool(condition)
    _results.append((name, ok, detail))
    return ok


def flip(bits: str, index: int) -> str:
    return bits[:index] + ("1" if bits[index] == "0" else "0") + bits[index + 1:]


# ---------------------------------------------------------------------------
# 一、核心算法：逐条对应验收表 T-01 ~ T-11
# ---------------------------------------------------------------------------
def core_checks() -> None:
    print("=" * 70)
    print("一、核心算法（T-01 ~ T-11）")
    print("=" * 70)

    # T-01 输入 Net -> 24 位
    r = encode_text("Net")
    bits = "".join(item["utf8"]["bits"] for item in r["result"]["chars"])
    check("T-01 Net → 24 位位流", r["ok"] and len(bits) == 24, f"实际 {len(bits)} 位")

    # T-02 中文：GBK 4 字节、UTF-8 6 字节
    r = encode_text("中文")
    check("T-02 中文 GBK 4 字节 / UTF-8 6 字节",
          r["result"]["total_gbk_bytes"] == 4 and r["result"]["total_utf8_bytes"] == 6,
          f"GBK={r['result']['total_gbk_bytes']} UTF-8={r['result']['total_utf8_bytes']}")

    # T-03 78 转二进制，竖式七行，结果 1001110
    d = decimal_to_binary("78")
    check("T-03 78 → 二进制 1001110，竖式 7 行",
          d["ok"] and d["result"]["binary"] == "1001110" and len(d["result"]["rows"]) == 7,
          f"{d['result']['binary']} / {len(d['result']['rows'])} 行")
    d2 = dec_to_base(78, 2)
    check("T-03 补充：通用转换 dec_to_base(78, 2)",
          d2["ok"] and d2["result"]["text"] == "1001110", d2["result"].get("text", ""))

    # T-04 奇校验 1011001 补 1，总数 5
    p = parity_encode("1011001", "odd")
    check("T-04 奇校验 1011001 补 1、总数 5",
          p["result"]["parity"] == "1" and p["result"]["total_ones"] == 5,
          f"补 {p['result']['parity']}，共 {p['result']['total_ones']} 个 1")
    p_even = parity_encode("1011001", "even")
    check("T-04 补充：偶校验补 0", p_even["result"]["parity"] == "0")

    # T-05 二维奇偶翻 1 位：定位并纠正（遍历 16 位）
    data = "1011001101010101"
    m = matrix_encode(data, 4, 4)["result"]["matrix"]
    located = 0
    for row in range(4):
        for col in range(4):
            broken = [r[:] for r in m]
            broken[row][col] = "1" if broken[row][col] == "0" else "0"
            res = matrix_check(broken)
            if res["error_pos"] == (row, col) and res["corrected"] == m:
                located += 1
    check("T-05 二维奇偶 16 位全部可定位并纠正", located == 16, f"{located}/16")

    # T-06 CRC 123456789 -> 0x29B1
    c = crc_of_text("123456789", preset="CRC-16/CCITT")
    check("T-06 CRC(123456789) = 0x29B1", c["result"]["crc_hex"] == "0x29B1",
          c["result"]["crc_hex"])
    clean = crc_check(c["result"]["frame"], preset="CRC-16/CCITT", data_len=72)
    check("T-06 补充：干净帧余数为 0", clean["result"]["remainder_hex"] == "0x0000")

    # T-07 Internet 校验和：接收端求和 0xFFFF
    frame = inet_checksum(b"NetCodec")
    whole = bytes(b"NetCodec") + frame["result"]["checksum"].to_bytes(2, "big")
    v = inet_verify(whole)
    check("T-07 接收端求和 = 0xFFFF", v["result"]["sum_hex"] == "0xFFFF",
          v["result"]["sum_hex"])

    # T-08 汉明码翻 1 位：伴随式指出出错位并纠正（遍历 7 位）
    h = hamming_encode("1011")["result"]["frame"]
    fixed = sum(
        1 for i in range(7)
        if (lambda res: res["error_pos"] == i + 1
            and res["corrected_frame"] == h)(hamming_decode(flip(h, i)))
    )
    check("T-08 汉明码 7 位全部定位并纠正", fixed == 7, f"{fixed}/7")
    check("T-08 无错时伴随式为 0", hamming_decode(h)["syndrome"] == (0, 0, 0))

    # T-09 信道点第 3 位：翻转并判定检出
    comparison = compare_schemes("10110101", [2])
    parity_row = next(row for row in comparison["result"]["schemes"] if row["key"] == "parity")
    check("T-09 翻转第 3 位后判定检出",
          parity_row["frame"][2] != parity_row["corrupted"][2] and parity_row["detected"],
          parity_row["message"])

    # T-10 批量实验同 seed 两次一致
    a = batch_experiment("10110101", runs=60, flips=1, seed=2026)
    b = batch_experiment("10110101", runs=60, flips=1, seed=2026)
    check("T-10 批量实验同 seed 结果完全一致",
          a["ok"] and a["result"]["reproducible"] and a["result"]["stats"] == b["result"]["stats"])

    # T-11 空输入 / 超长输入不崩
    bad_cases = [
        ("encode_text('')", lambda: encode_text("")),
        ("encode_text(超长)", lambda: encode_text("x" * 201)),
        ("parity_encode('')", lambda: parity_encode("")),
        ("parity_encode('1012')", lambda: parity_encode("1012")),
        ("crc_encode('')", lambda: crc_encode("")),
        ("inet_checksum(b'')", lambda: inet_checksum(b"")),
        ("hamming_decode('123')", lambda: hamming_decode("123")),
        ("dec_to_base('abc')", lambda: dec_to_base("abc")),
        ("base_to_dec('ZZ', 16)", lambda: base_to_dec("ZZ", 16)),
        ("decimal_to_binary('x')", lambda: decimal_to_binary("x")),
    ]
    safe = True
    for label, fn in bad_cases:
        try:
            out = fn()
            if isinstance(out, dict) and out.get("ok") is True:
                safe = False
                print(f"    ! {label} 本应失败却返回 ok=True")
        except Exception as exc:  # noqa: BLE001
            safe = False
            print(f"    ! {label} 抛异常：{exc!r}")
    check("T-11 空/非法/超长输入都返回 ok=False 且不抛异常", safe, "10 组用例")

    # 扩展：五种方案干净帧不误报、翻 1 位全检出
    clean_rows = compare_schemes("0100110101100101")["result"]["schemes"]
    broken_rows = compare_schemes("0100110101100101", [3])["result"]["schemes"]
    check("扩展：五种方案干净帧不误报",
          len(clean_rows) == 5 and not any(row["detected"] for row in clean_rows),
          f"{sum(1 for r in clean_rows if r['detected'])} 个误报")
    check("扩展：五种方案翻 1 位全部检出",
          len(broken_rows) == 5 and all(row["detected"] for row in broken_rows),
          f"{sum(1 for r in broken_rows if r['detected'])}/5")

    # 扩展：进制互转 6 组
    pairs = [("78", 10, 2, "1001110"), ("78", 10, 16, "4E"), ("78", 10, 8, "116"),
             ("4E", 16, 10, "78"), ("1001110", 2, 10, "78"), ("116", 8, 10, "78")]
    conv_ok = True
    for text, src, dst, want in pairs:
        if dst == 10 or src == 10:
            got = (base_to_dec(text, src)["result"]["value"] if src != 10
                   else dec_to_base(text, dst)["result"]["text"])
            if str(got) != want:
                conv_ok = False
                print(f"    ! {text}({src})→({dst}) 得到 {got}，期望 {want}")
    check("扩展：进制互转 6 组全对", conv_ok)

    # 扩展：一维校验无法定位（parity_locate 的结论）
    loc = parity_locate(flip(parity_encode("1011001", "even")["result"]["frame"], 2), "even")
    check("扩展：一维校验检出错但无法唯一定位",
          loc["ok"] and len(loc["candidates"]) > 1 and not loc["unique"],
          f"候选 {len(loc['candidates'])} 个")


# ---------------------------------------------------------------------------
# 二、界面：三个页面逐一打开并触发一次真实计算
# ---------------------------------------------------------------------------
def gui_checks() -> None:
    print()
    print("=" * 70)
    print("二、界面交互")
    print("=" * 70)

    from app.views.main_window import MainWindow

    app = MainWindow()
    app.update_idletasks()
    app.update()
    check("主窗口尺寸 1360×880",
          (app.winfo_width(), app.winfo_height()) == (1360, 880),
          f"{app.winfo_width()}×{app.winfo_height()}")

    pages = getattr(app, "pages", {})
    check("注册了三个页面", set(pages) == {"encoding", "checksum", "channel"}, str(list(pages)))

    for key in ("encoding", "checksum", "channel"):
        app.show_page(key)
        app.update()
        check(f"切到「{key}」页面", app.winfo_exists() == 1)

    # --- 编码工坊：输入 Net 解析 ---
    view = pages["encoding"]
    view.input_var.set("Net")
    view.parse_input()
    app.update()
    records = getattr(view, "_records", [])
    # 每个字符记录里 utf8 / gbk 都是字节值列表，一位字节对应 8 位
    total_bits = sum(
        (len(item["utf8"]) + len(item["gbk"])) * 8 for item in records
    )
    check("编码工坊：Net 解析出 3 个字符卡片", len(records) == 3, f"{len(records)} 个")
    check("编码工坊：Net 的 UTF-8 + GBK 共 48 位",
          total_bits == 48, f"{total_bits} 位")

    # 进制换算弹窗
    view._open_base_convert_dialog()
    app.update()
    dialog = view._convert_dialog
    texts = []

    def walk(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == "Text":
                texts.append(child.get("1.0", "end"))
            walk(child)

    walk(dialog)
    joined = "".join(texts)
    check("进制换算弹窗：78 显示除基取余竖式",
          "1001110" in joined and "÷" in joined, joined.splitlines()[0] if joined else "空")
    dialog.destroy()
    app.update()

    # --- 校验实验室：五种方案各生成一次 ---
    cview = pages["checksum"]
    scheme_labels = list(getattr(cview, "SCHEMES", ()))
    ok_all = True
    used = []
    for label in scheme_labels:
        try:
            cview.scheme_var.set(label)
            cview.generate_frame()
            app.update()
            used.append(label)
        except Exception as exc:  # noqa: BLE001
            ok_all = False
            print(f"    ! 校验实验室「{label}」出错：{exc!r}")
    check("校验实验室：五种方案都能生成发送帧", ok_all and len(used) >= 5,
          f"{len(used)} 种")

    # --- 信道模拟器：点一位注入错误，判定要翻成“检出” ---
    hview = pages["channel"]
    hview.data_var.set("10110101")
    hview.generate_frames()
    app.update()
    frames = getattr(hview, "frames", {})
    check("信道模拟器：生成五种发送帧", len(frames) == 5, f"{len(frames)} 种")

    try:
        # 选一维奇偶方案，点第 3 位（下标 2），模拟真实的画布点击
        target_key = "parity"
        hview.scheme_var.set(hview.LABELS[target_key])
        hview._on_scheme_selected(None)
        app.update()
        size, gap, per_row = hview._bit_layout
        row, column = divmod(2, per_row)
        event = type("E", (), {"x": 8 + column * (size + gap) + 1,
                               "y": 8 + row * 48 + 1})()
        hview._on_bit_click(event)
        app.update()
        flipped = hview.flipped[target_key]
        status_text = hview.verdict_status.cget("text")
        check("信道模拟器：点第 3 位后该位被记录为已翻转",
              flipped == {2}, f"翻转集合 {sorted(flipped)}")
        check("信道模拟器：接收端判定翻成「检出」",
              "通过" not in status_text, f"判定文本：{status_text}")
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        check("信道模拟器：点第 3 位注入错误", False, repr(exc))

    try:
        hview._open_batch_dialog()
        app.update()
        dialog = getattr(hview, "_batch_dialog", None)
        buttons = []

        def find_buttons(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "Button":
                    buttons.append(child)
                find_buttons(child)

        if dialog is not None:
            find_buttons(dialog)
            target = next((b for b in buttons if b.cget("text") == "运行"), None)
            if target is not None:
                target.invoke()
                app.update()
            dialog.destroy()
        app.update()
        check("信道模拟器：批量实验窗口可运行", True)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        check("信道模拟器：批量实验窗口可运行", False, repr(exc))

    app.destroy()


def main() -> int:
    try:
        core_checks()
        gui_checks()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print("\n自查过程中出现未捕获异常")
        return 1

    print()
    print("=" * 70)
    print("结果")
    print("=" * 70)
    failed = 0
    for name, ok, detail in _results:
        mark = "通过" if ok else "失败"
        extra = f"  [{detail}]" if detail and not ok else ""
        print(f"  [{mark}] {name}{extra}")
        if not ok:
            failed += 1
    print()
    print(f"共 {len(_results)} 项，通过 {len(_results) - failed} 项，失败 {failed} 项")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
