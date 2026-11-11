"""进制转换竖式：十进制 ⇄ 二进制（八进制 / 十六进制同理）。

对应编码工坊的“进制互转”页面。两种课本算法：

- 除基取余（十进制 -> 任意进制）：反复除以基数，余数从下往上读；
- 按权展开（任意进制 -> 十进制）：每一位乘 ``基数^位权`` 再求和。

本模块是纯函数，不依赖 Tkinter；返回结构与算法层其他模块一致：
``{ok, result, steps, message}``，界面只负责把 ``steps`` 逐行画出来。
"""

from __future__ import annotations

BASES = {2: "二进制", 8: "八进制", 10: "十进制", 16: "十六进制"}
_DIGITS = "0123456789ABCDEF"


def _step(title: str, detail: str) -> dict:
    """统一步骤结构，界面的步骤表直接吃这个格式。"""
    return {"title": title, "detail": detail}


def _check_base(base: int) -> None:
    if base not in BASES:
        raise ValueError(f"基数只能是 2、8、10、16，收到 {base}")


def _digit_value(ch: str) -> int:
    """单个字符对应的数值；非法时抛出 ValueError。"""
    if ch.isdigit():
        return int(ch)
    if "A" <= ch <= "F":
        return ord(ch) - ord("A") + 10
    raise ValueError(f"非法数字字符 {ch!r}")


def dec_to_base(decimal, base: int = 2) -> dict:
    """十进制整数转任意进制，返回除基取余的完整竖式。

    参数
    ----
    decimal: 整数，或可解析为非负整数的字符串。
    base: 目标基数，2 / 8 / 10 / 16。

    返回
    ----
    {ok, result: {value, base, base_name, digits, text, remainders}, steps, message}
    ``digits`` 是高位在前的数字字符列表；``remainders`` 是除法过程中
    余数出现的先后顺序（低位在前），界面可据此画出“从下往上读”的竖式。
    """
    try:
        _check_base(base)
        number = int(str(decimal).strip(), 10)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    if number < 0:
        return {"ok": False, "result": None, "steps": [],
                "message": "本模块只演示非负整数的进制转换，负数请先取绝对值再处理符号位"}
    if base == 10:
        return {
            "ok": True,
            "result": {"value": number, "base": 10, "base_name": BASES[10],
                        "digits": list(str(number)), "text": str(number),
                        "remainders": []},
            "steps": [_step("十进制转十进制", f"{number} 本身就是十进制，结果为 {number}")],
            "message": f"{number} 的十进制表示就是 {number}",
        }

    if number == 0:
        return {
            "ok": True,
            "result": {"value": 0, "base": base, "base_name": BASES[base],
                        "digits": ["0"], "text": "0", "remainders": [0]},
            "steps": [_step("除基取余", "被除数为 0，商直接记 0，结果就是单个 0")],
            "message": "0 转成 " + BASES[base] + " 仍为 0",
        }

    remainders: list[int] = []
    quotient = number
    rows: list[dict] = []
    while quotient > 0:
        remainder = quotient % base
        remainders.append(remainder)
        rows.append({"quotient": quotient, "remainder": remainder,
                     "digit": _DIGITS[remainder]})
        quotient //= base

    digits = [row["digit"] for row in reversed(rows)]
    text = "".join(digits)

    steps = [_step("除基取余", f"把 {number} 反复除以 {base}，记录每一步的余数（余数从下往上读）")]
    for index, row in enumerate(rows, start=1):
        steps.append(_step(
            f"第 {index} 次除 {base}",
            f"{row['quotient']} ÷ {base} = {row['quotient'] // base} … 余 "
            f"{row['remainder']}（写成 {row['digit']}）",
        ))
    steps.append(_step("逆序读取",
                       "余数依次为 " + "、".join(str(r) for r in remainders) +
                       "，从最后一个余数往回读 -> " + text))

    return {
        "ok": True,
        "result": {"value": number, "base": base, "base_name": BASES[base],
                   "digits": digits, "text": text, "remainders": remainders},
        "steps": steps,
        "message": f"{number}（十进制）= {text}（{BASES[base]}）",
    }


def base_to_dec(number: str, base: int = 2) -> dict:
    """任意进制整数转十进制，返回按权展开的逐步求和过程。

    返回 {ok, result: {base, base_name, value, digits, terms}, steps, message}
    ``terms`` 是每一位的 ``(字符, 位权, 该位贡献)``，界面可画成展开式。
    """
    try:
        _check_base(base)
        raw = str(number).strip().upper().replace(" ", "")
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    if not raw:
        return {"ok": False, "result": None, "steps": [], "message": "待转换的数字为空"}

    if base == 10:
        try:
            value = int(raw, 10)
        except ValueError as exc:
            return {"ok": False, "result": None, "steps": [], "message": str(exc)}
        return {
            "ok": True,
            "result": {"base": 10, "base_name": BASES[10], "value": value,
                       "digits": list(raw), "terms": []},
            "steps": [_step("按权展开", f"{raw} 本身就是十进制，结果为 {value}")],
            "message": f"{raw}（十进制）= {value}",
        }

    digits = list(raw)
    terms: list[tuple[str, int, int]] = []
    running = 0
    weight = len(digits) - 1
    bad: list[str] = []
    for ch in digits:
        try:
            value = _digit_value(ch)
        except ValueError:
            bad.append(ch)
            continue
        if value >= base:
            bad.append(ch)
            continue
        contribution = value * (base ** weight)
        terms.append((ch, weight, contribution))
        running += contribution
        weight -= 1

    if bad:
        return {"ok": False, "result": None, "steps": [],
                "message": f"{BASES[base]}中不能出现字符：" + "、".join(repr(c) for c in bad)}

    steps = [_step("按权展开",
                   f"{BASES[base]}数 {raw} 从左到右位权依次为 "
                   + "、".join(str(w) for _, w, _ in reversed(terms)))]
    for ch, weight, contribution in terms:
        steps.append(_step(
            f"位权 {weight}（数字 {ch}）",
            f"{ch} × {base}^{weight} = {ch} × {base ** weight} = {contribution}",
        ))
    expression = " + ".join(str(c) for _, _, c in terms)
    steps.append(_step("求和", f"{expression} = {running}"))

    return {
        "ok": True,
        "result": {"base": base, "base_name": BASES[base], "value": running,
                    "digits": digits, "terms": terms},
        "steps": steps,
        "message": f"{raw}（{BASES[base]}）= {running}（十进制）",
    }
