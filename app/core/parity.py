"""奇偶校验与二维奇偶校验。

一维奇偶校验：在数据后面补 1 位，使整帧中 1 的个数为偶数或奇数。
二维奇偶校验：把数据排成方阵，每行、每列各补 1 位，行列交叉处再补 1 位。
它能定位 1 位错误（行校验和列校验同时报错 -> 交叉点就是错位），
但对 2 位错误只能报告“无法纠正”，因为两个交叉点同时报错，分不清哪一个是真错。
"""

from __future__ import annotations

from ..common.bits import count_ones, normalize_bits

MODE_EVEN = "even"
MODE_ODD = "odd"
MODE_NAMES = {MODE_EVEN: "偶校验", MODE_ODD: "奇校验"}


def _step(title: str, detail: str) -> dict:
    """统一步骤结构，界面的步骤表直接吃这个格式。"""
    return {"title": title, "detail": detail}


def _check_mode(mode: str) -> str:
    if mode not in MODE_NAMES:
        raise ValueError(f"mode 只能是 'even' 或 'odd'，收到 {mode!r}")
    return mode


def parity_bit_for(data_bits: str, mode: str = MODE_EVEN) -> str:
    """算出应该补的校验位（'0' 或 '1'）。"""
    _check_mode(mode)
    ones = count_ones(data_bits)
    # 偶校验：1 的个数要为偶数；奇校验：要为奇数
    need_odd = mode == MODE_ODD
    parity_is_one = (ones % 2 == 1) != need_odd
    return "1" if parity_is_one else "0"


def parity_encode(bits: str, mode: str = MODE_EVEN) -> dict:
    """发送端：给数据补 1 位校验位，返回整帧。

    参数
    ----
    bits: 数据位串，例如 '1011001'
    mode: 'even'（偶校验）或 'odd'（奇校验）

    返回
    ----
    {ok, result: {data, parity, frame, ones, mode}, steps, message}
    """
    try:
        data = normalize_bits(bits)
        _check_mode(mode)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    ones = count_ones(data)
    parity = parity_bit_for(data, mode)
    frame = data + parity
    total = count_ones(frame)
    target = "奇数" if mode == MODE_ODD else "偶数"

    steps = [
        _step("读入数据位", f"数据位 {data}，长度 {len(data)} 位，其中 1 的个数 = {ones}"),
        _step(
            "判断需要补什么",
            f"{MODE_NAMES[mode]}要求整帧中 1 的个数为{target}，"
            f"当前 {ones} 个 1 已经是{'奇数' if ones % 2 else '偶数'}"
            f" -> 校验位补 {parity}",
        ),
        _step("组帧", f"帧 = 数据位 + 校验位 = {data} + {parity} = {frame}"),
        _step("复核", f"整帧 1 的个数 = {total}（{target}），校验位正确"),
    ]
    return {
        "ok": True,
        "result": {
            "data": data,
            "parity": parity,
            "frame": frame,
            "ones": ones,
            "total_ones": total,
            "mode": mode,
        },
        "steps": steps,
        "message": f"{MODE_NAMES[mode]}：数据 {len(data)} 位，补校验位 {parity}，整帧 {len(frame)} 位",
    }


def parity_check(frame: str, mode: str = MODE_EVEN) -> dict:
    """接收端：重新统计 1 的个数，判断整帧是否符合约定。

    返回 {ok, detected, result: {ones, expected, frame}, steps, message}
    detected=True 表示“发现错误”。
    """
    try:
        bits = normalize_bits(frame)
        _check_mode(mode)
    except ValueError as exc:
        return {"ok": False, "detected": False, "result": None, "steps": [], "message": str(exc)}

    if len(bits) < 2:
        return {"ok": False, "detected": False, "result": None, "steps": [],
                "message": "帧长度不足 2 位，至少要 1 位数据 + 1 位校验位"}

    data, parity = bits[:-1], bits[-1]
    ones = count_ones(bits)
    want_odd = mode == MODE_ODD
    # 奇校验要求 1 的个数为奇数，偶校验要求为偶数
    passed = (ones % 2 == 1) == want_odd
    detected = not passed
    expected_parity = parity_bit_for(data, mode)

    steps = [
        _step("拆分帧", f"数据位 {data}，收到的校验位 {parity}"),
        _step(
            "重新统计",
            f"整帧 1 的个数 = {ones}，{MODE_NAMES[mode]}要求为{'奇数' if want_odd else '偶数'}",
        ),
        _step(
            "比对校验位",
            f"按收到的数据重算，校验位应为 {expected_parity}，实际收到 {parity}，"
            f"{'一致' if expected_parity == parity else '不一致'}",
        ),
        _step(
            "判定",
            "校验通过，数据视为未损坏" if passed else "校验失败，判定数据在传输中损坏",
        ),
    ]
    return {
        "ok": True,
        "detected": detected,
        "result": {"data": data, "parity": parity, "ones": ones,
                   "expected_parity": expected_parity, "frame": bits},
        "steps": steps,
        "message": ("检出错误：1 的个数不符合" + MODE_NAMES[mode] + "约定")
        if detected else "校验通过：1 的个数符合" + MODE_NAMES[mode] + "约定",
    }


def parity_locate(frame: str, mode: str = MODE_EVEN) -> dict:
    """接收端：枚举“翻转后能通过校验”的候选错误位，用于说明一维校验的定位能力。

    一维奇偶校验只携带 1 位校验信息，无法唯一确定出错位：
    - 未出错时，翻转任意一位都会失败，候选为空；
    - 单比特错误时，翻转任意一位都会让奇偶性重新满足约定，候选为全部位置；
    - 多位错误时，可能没有任何单比特翻转能让校验通过，候选为空。

    返回 {ok, candidates, total, unique, corrected, steps, message}
    candidates 为 0 起的位下标列表；unique 表示是否能唯一定位。
    """
    try:
        bits = normalize_bits(frame)
        _check_mode(mode)
    except ValueError as exc:
        return {"ok": False, "candidates": [], "total": 0, "unique": False,
                "corrected": None, "steps": [], "message": str(exc)}

    want_odd = mode == MODE_ODD
    candidates = []
    for index in range(len(bits)):
        flipped = bits[:index] + ("1" if bits[index] == "0" else "0") + bits[index + 1:]
        if (count_ones(flipped) % 2 == 1) == want_odd:
            candidates.append(index)

    unique = len(candidates) == 1
    corrected = None
    if unique:
        index = candidates[0]
        corrected = bits[:index] + ("1" if bits[index] == "0" else "0") + bits[index + 1:]

    steps = [
        _step("枚举候选位",
              f"逐个翻转 1 位后重新校验，能通过{MODE_NAMES[mode]}的位置共 {len(candidates)} 个"),
        _step("唯一性判定",
              "候选只有 1 个，可唯一定位" if unique
              else f"候选 {len(candidates)} 个，一维校验信息不足，无法唯一定位"),
    ]
    return {
        "ok": True,
        "candidates": candidates,
        "total": len(bits),
        "unique": unique,
        "corrected": corrected,
        "steps": steps,
        "message": (f"可唯一定位第 {candidates[0] + 1} 位" if unique
                    else f"候选错误位 {len(candidates)} 个，无法唯一定位"),
    }
