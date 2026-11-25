"""命令行验收脚本：证明周恩旭负责的编码 / 进制 / 信道函数都是对的。

用法（在项目根目录）：
    python tools/verify_encoding.py

对应需求文档验收点：
    T-01 输入 Net -> 24 位位流
    T-02 输入 中文 -> GBK 4 字节、UTF-8 6 字节
    T-03 78 转二进制 -> 竖式七行，结果 1001110
    T-09 信道点第 3 位 -> 该位翻转，方案判定“检出”
    T-10 批量实验同 seed 跑两次 -> 结果完全一致
    T-11 空输入、超长输入 -> 有提示，程序不退出
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common import config
from app.core.channel import batch_compare, compare_schemes, inject_error
from app.core.convert import base_to_dec, dec_to_base
from app.core.encoding import encode_text, text_to_bitstream

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
    print("NetCodec Lab —— 编码 / 进制 / 信道验收（T-01、T-02、T-03、T-09、T-10、T-11）")

    # --------------------------------------------------------------- T-01
    section("T-01 输入 Net -> 24 位位流（UTF-8）")
    net = encode_text("Net")
    print(f"  UTF-8 字节 = {net['result']['total_utf8_bytes']}，位 = {net['result']['total_utf8_bits']}")
    stream = text_to_bitstream("Net", "utf-8")
    print(f"  位流 = {stream['result']['bits']}")
    check("Net UTF-8 字节数 = 3", 3, net["result"]["total_utf8_bytes"])
    check("Net 位流长度 = 24", 24, stream["result"]["byte_count"] * 8)

    # --------------------------------------------------------------- T-02
    section("T-02 输入 中文 -> GBK 4 字节、UTF-8 6 字节")
    chinese = encode_text("中文")
    for char in chinese["result"]["chars"]:
        print(f"  {char['char']} {char['code_point_hex']}  UTF-8 {char['utf8']['hex']}  "
              f"GBK {char['gbk']['hex']}")
    check("中文 UTF-8 = 6 字节", 6, chinese["result"]["total_utf8_bytes"])
    check("中文 GBK = 4 字节", 4, chinese["result"]["total_gbk_bytes"])

    # --------------------------------------------------------------- T-03
    section("T-03 78 转二进制 -> 竖式七行，结果 1001110")
    conv = dec_to_base(78, 2)
    for step in conv["steps"]:
        print(f"    {step['title']}：{step['detail']}")
    divide_rows = [s for s in conv["steps"] if s["title"].startswith("第 ")]
    check("二进制结果 = 1001110", "1001110", conv["result"]["text"])
    check("除基取余竖式 = 7 行", 7, len(divide_rows))
    back = base_to_dec(conv["result"]["text"], 2)
    check("逆运算 1001110 -> 78", 78, back["result"]["value"])

    # --------------------------------------------------------------- T-09
    section("T-09 信道点第 3 位（下标 2）-> 翻转并检出")
    DATA = "1011001"
    injected = inject_error(DATA, 2)
    print(f"  原始 {injected['result']['original']} -> 受损 {injected['result']['corrupted']}")
    cmp_result = compare_schemes(DATA, positions=2)
    for scheme in cmp_result["result"]["schemes"]:
        mark = "检出" if scheme["detected"] else "漏检"
        print(f"    {scheme['name']}：{mark}（{scheme['message']}）")
    parity = next(s for s in cmp_result["result"]["schemes"] if s["key"] == "parity")
    check("一维奇偶校验检出第 3 位错误", True, parity["detected"])
    clean = compare_schemes(DATA)
    clean_pass = all(not s["detected"] for s in clean["result"]["schemes"])
    check("干净帧基线全部通过", True, clean_pass)

    # --------------------------------------------------------------- T-10
    section("T-10 批量实验同 seed 跑两次 -> 结果完全一致")
    first = batch_compare(DATA, runs=100, error_rate=0.1, seed=2026)
    second = batch_compare(DATA, runs=100, error_rate=0.1, seed=2026)
    for key, stat in first["result"]["stats"].items():
        print(f"    {stat['name']}：检出 {stat['detected']} / 100，检出率 {stat['detection_rate']:.1%}")
    check("同 seed 两次结果一致", first["result"], second["result"])

    # --------------------------------------------------------------- T-11
    section("T-11 空输入、超长输入 -> 有提示，程序不退出")
    empty_text = encode_text("")
    long_text = encode_text("中" * (config.MAX_INPUT_CHARS + 1))
    empty_bits = compare_schemes("")
    print(f"  空文本：ok={empty_text['ok']}，提示：{empty_text['message']}")
    print(f"  超长文本：ok={long_text['ok']}，提示：{long_text['message']}")
    print(f"  空位串：ok={empty_bits['ok']}，提示：{empty_bits['message']}")
    check("空文本被拦截", False, empty_text["ok"])
    check("超长文本被拦截", False, long_text["ok"])
    check("空位串被拦截", False, empty_bits["ok"])

    # --------------------------------------------------------------- 汇总
    section("汇总")
    passed = sum(1 for item in _results if item)
    print(f"  共 {len(_results)} 项验收，通过 {passed} 项，失败 {len(_results) - passed} 项")
    if passed == len(_results):
        print("\n  编码、进制、信道模块全部符合验收标准，可以交接给界面负责人张鑫渝。")
        return 0
    print("\n  存在未通过项，请按上面的“期望 / 实际”逐条排查。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
