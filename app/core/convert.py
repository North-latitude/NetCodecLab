"""进制转换：十进制整数转二进制，并给出除 2 取余的竖式过程。"""


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def decimal_to_binary(text: str, limit: int = 65535) -> dict:
    """把十进制整数字符串转成二进制，返回逐行竖式与最终位串。"""
    raw = str(text).strip()
    if not raw:
        return {"ok": False, "result": None, "steps": [],
                "message": "请输入一个十进制整数，例如 78。"}
    if not raw.isdigit():
        return {"ok": False, "result": None, "steps": [],
                "message": "只支持非负十进制整数，例如 78。"}

    value = int(raw)
    if value > limit:
        return {"ok": False, "result": None, "steps": [],
                "message": f"为了演示清晰，请输入 0～{limit} 的整数。"}

    rows = []
    current = value
    while current > 0:
        quotient, remainder = divmod(current, 2)
        rows.append({
            "dividend": current,
            "quotient": quotient,
            "remainder": remainder,
        })
        current = quotient
    if not rows:
        rows.append({"dividend": 0, "quotient": 0, "remainder": 0})

    binary = "".join(str(row["remainder"]) for row in reversed(rows))
    steps = [
        _step(f"{row['dividend']} ÷ 2",
              f"商 {row['quotient']}，余 {row['remainder']}")
        for row in rows
    ]
    steps.append(_step("从下往上读余数", f"拼接得到 {binary}"))
    return {
        "ok": True,
        "result": {
            "value": value,
            "binary": binary,
            "rows": rows,
            "width": len(binary),
        },
        "steps": steps,
        "message": f"{value} 的二进制是 {binary}（共 {len(binary)} 位）",
    }
