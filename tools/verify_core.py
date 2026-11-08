"""命令行验收脚本：证明 A（组长）交付的五个校验函数都是对的。

用法（在项目根目录）：
    python tools/verify_core.py

它会依次跑一遍 3.1 ~ 3.5 的验收点，逐条打印“期望 / 实际 / 结论”。
这个脚本就是 A 交给 C 的“交接证据”：界面还没写，也能证明算法可用。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common.bits import flip_bit
from app.core.checksum import checksum_frame, inet_verify
from app.core.crc import crc_check, crc_of_text
from app.core.hamming import hamming_decode, hamming_encode
from app.core.matrix import matrix_check, matrix_encode
from app.core.parity import parity_check, parity_encode

PASS = "通过"
FAIL = "不通过"
_results = []


def check(name: str, expected, actual) -> bool:
    ok = expected == actual
    _results.append(ok)
    print(f"  [{PASS if ok else FAIL}] {name}")
    if not ok:
        print(f"        期望: {expected}")
        print(f"        实际: {actual}")
    return ok


def section(title: str):
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)


def main() -> int:
    print("NetCodec Lab —— 校验算法验收（3.1 ~ 3.5）")
    print("对应验收清单 3.1 ~ 3.5 的验收点")

    # ---------------------------------------------------------------- 3.1
    section("3.1 奇偶校验：1011001 奇校验补 1、偶校验补 0")
    odd = parity_encode("1011001", "odd")
    even = parity_encode("1011001", "even")
    print(f"  数据 1011001 中 1 的个数 = {odd['result']['ones']}")
    print(f"  奇校验帧 = {odd['result']['frame']}（补 {odd['result']['parity']}，"
          f"整帧 {odd['result']['total_ones']} 个 1）")
    print(f"  偶校验帧 = {even['result']['frame']}（补 {even['result']['parity']}，"
          f"整帧 {even['result']['total_ones']} 个 1）")
    check("奇校验补 1", "1", odd["result"]["parity"])
    check("偶校验补 0", "0", even["result"]["parity"])
    broken = flip_bit(odd["result"]["frame"], 2)
    print(f"  把第 3 位翻成 {broken[2]} -> 接收帧 {broken}")
    check("翻 1 位后 check 报错", True, parity_check(broken, "odd")["detected"])
    print(f"  接收端提示：{parity_check(broken, 'odd')['message']}")

    # ---------------------------------------------------------------- 3.2
    section("3.2 二维奇偶校验：任翻 1 位都能定位并改回来")
    data = "1011001101010101"
    encoded = matrix_encode(data, 4, 4)
    matrix = encoded["result"]["matrix"]
    print(f"  数据 {data} 排成 4×4 方阵，加行列校验后为 5×5：")
    for row in matrix:
        print("      " + " ".join(row))
    located = 0
    for row in range(4):
        for col in range(4):
            target = [r[:] for r in matrix]
            target[row][col] = "1" if target[row][col] == "0" else "0"
            result = matrix_check(target)
            if result["error_pos"] == (row, col) and result["corrected"] == matrix:
                located += 1
    print(f"  逐个翻转 16 个数据位，能正确定位并纠正的个数 = {located}")
    check("16 个数据位全部可定位并纠正", 16, located)
    two = [r[:] for r in matrix]
    two[0][0] = "1" if two[0][0] == "0" else "0"
    two[2][3] = "1" if two[2][3] == "0" else "0"
    two_result = matrix_check(two)
    print(f"  同时翻 2 位 -> {two_result['message']}")
    check("2 位错误不瞎改", None, two_result["corrected"])
    check("2 位错误仍能检出", True, two_result["detected"])

    # ---------------------------------------------------------------- 3.3
    section('3.3 CRC：123456789 用 0x1021、初值 0xFFFF 应得 0x29B1')
    crc = crc_of_text("123456789", preset="CRC-16/CCITT")
    print(f"  数据 '123456789' = {len(crc['result']['data'])} 位")
    for step in crc["steps"]:
        if step["title"].startswith("移入"):
            print(f"    {step['title']} -> {step['detail']}")
    print(f"  最终余数 = {crc['result']['crc_hex']}")
    check("CRC = 0x29B1", "0x29B1", crc["result"]["crc_hex"])
    verify = crc_check(crc["result"]["frame"], preset="CRC-16/CCITT", data_len=72)
    print(f"  接收端把数据+CRC 再除一次 -> 余数 {verify['result']['remainder_hex']}")
    check("干净帧余数为 0", "0x0000", verify["result"]["remainder_hex"])
    bad = crc_check(flip_bit(crc["result"]["frame"], 5), preset="CRC-16/CCITT", data_len=72)
    check("翻 1 位后检出", True, bad["detected"])

    # ---------------------------------------------------------------- 3.4
    section("3.4 Internet 校验和：接收端整体求和应为 0xFFFF")
    payload = b"NetCodec"
    frame = checksum_frame(payload)
    print(f"  数据 {payload!r} -> {len(payload)} 字节")
    for step in frame["steps"]:
        if step["title"].startswith("累加"):
            print(f"    {step['title']}：{step['detail']}")
    print(f"  校验和 = 0x{frame['result']['checksum']:04X}")
    result = inet_verify(frame["result"]["frame"])
    print(f"  接收端整体求和 = {result['result']['sum_hex']}")
    check("接收端求和 = 0xFFFF", "0xFFFF", result["result"]["sum_hex"])
    raw = bytearray(frame["result"]["frame"])
    raw[3] ^= 0x01
    check("改 1 字节后检出", True, inet_verify(bytes(raw))["detected"])

    # ---------------------------------------------------------------- 3.5
    section("3.5 汉明码 (7,4)：翻任意一位，伴随式指出出错位并纠正")
    encoded_h = hamming_encode("1011")
    codeword = encoded_h["result"]["frame"]
    print(f"  数据 1011 -> 码字 {codeword}（p1 p2 d1 p4 d2 d3 d4）")
    fixed = 0
    for index in range(7):
        target = flip_bit(codeword, index)
        result = hamming_decode(target)
        s4, s2, s1 = result["syndrome"]
        mark = "√" if (result["error_pos"] == index + 1
                       and result["corrected_frame"] == codeword) else "×"
        print(f"    {mark} 翻第 {index + 1} 位 {target} -> 伴随式 {s4}{s2}{s1}"
              f"（十进制 {s4 * 4 + s2 * 2 + s1}）-> 定位第 {result['error_pos']} 位"
              f" -> 纠正回 {result['corrected_frame']}")
        if mark == "√":
            fixed += 1
    check("7 个位置全部定位并纠正", 7, fixed)
    clean = hamming_decode(codeword)
    check("无错时伴随式为 0", (0, 0, 0), clean["syndrome"])

    # ---------------------------------------------------------------- 汇总
    section("汇总")
    passed = sum(1 for item in _results if item)
    print(f"  共 {len(_results)} 项验收，通过 {passed} 项，失败 {len(_results) - passed} 项")
    if passed == len(_results):
        print("\n  五个校验函数全部符合验收标准，可以交接给界面负责人张鑫渝。")
        return 0
    print("\n  存在未通过项，请按上面的“期望 / 实际”逐条排查。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
