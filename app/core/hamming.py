"""汉明码（7, 4）：4 位数据 + 3 位校验，能定位并纠正 1 位错误。

位号约定（从 1 开始，2 的幂位置放校验位）：
    第 1 位 p1   第 2 位 p2   第 3 位 d1   第 4 位 p4
    第 5 位 d2   第 6 位 d3   第 7 位 d4
校验关系（偶校验）：
    p1 覆盖 1,3,5,7     p2 覆盖 2,3,6,7     p4 覆盖 4,5,6,7
接收端重算三个校验方程得到伴随式 (s4 s2 s1)，它的十进制值就是出错位号，
把该位取反即可纠正。
"""

from __future__ import annotations

from ..common.bits import normalize_bits, pad_to_multiple

BLOCK_DATA = 4
BLOCK_TOTAL = 7


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def _encode_block(data4: str) -> tuple[str, dict]:
    """把 4 位数据编码成一个 7 位码字，返回 (码字, 中间量)。"""
    d1, d2, d3, d4 = (int(ch) for ch in data4)
    p1 = d1 ^ d2 ^ d4          # 覆盖第 3、5、7 位
    p2 = d1 ^ d3 ^ d4          # 覆盖第 3、6、7 位
    p4 = d2 ^ d3 ^ d4          # 覆盖第 5、6、7 位
    codeword = f"{p1}{p2}{d1}{p4}{d2}{d3}{d4}"
    return codeword, {"p1": p1, "p2": p2, "p4": p4, "d1": d1, "d2": d2, "d3": d3, "d4": d4}


def _syndrome(bits7: str) -> tuple[int, int, int]:
    """算出伴随式 (s4, s2, s1)。全 0 表示没有检测到错误。"""
    b = [int(ch) for ch in bits7]
    # b 下标 0..6 对应第 1..7 位
    s1 = b[0] ^ b[2] ^ b[4] ^ b[6]
    s2 = b[1] ^ b[2] ^ b[5] ^ b[6]
    s4 = b[3] ^ b[4] ^ b[5] ^ b[6]
    return s4, s2, s1


def hamming_encode(data_bits: str) -> dict:
    """发送端：把数据按 4 位一组编码成 (7,4) 汉明码。

    数据不足 4 的倍数时在尾部补 0，并在 steps 里说明补了几位。

    {ok, result: {frame, blocks, data, padding}, steps, message}
    """
    try:
        data = normalize_bits(data_bits)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    padded, padding = pad_to_multiple(data, BLOCK_DATA)
    blocks = []
    codewords = []
    steps = [
        _step("分组", f"数据 {data}，每 {BLOCK_DATA} 位一组"
                      + (f"；末尾补了 {padding} 个 0 凑齐整组" if padding else "")),
    ]
    for index in range(0, len(padded), BLOCK_DATA):
        chunk = padded[index:index + BLOCK_DATA]
        codeword, parts = _encode_block(chunk)
        blocks.append({"data": chunk, "codeword": codeword, **parts})
        codewords.append(codeword)
        steps.append(_step(
            f"第 {index // BLOCK_DATA + 1} 组 {chunk}",
            f"p1 = d1⊕d2⊕d4 = {parts['d1']}⊕{parts['d2']}⊕{parts['d4']} = {parts['p1']}；"
            f"p2 = d1⊕d3⊕d4 = {parts['d1']}⊕{parts['d3']}⊕{parts['d4']} = {parts['p2']}；"
            f"p4 = d2⊕d3⊕d4 = {parts['d2']}⊕{parts['d3']}⊕{parts['d4']} = {parts['p4']} "
            f"-> 码字 {codeword}（p1 p2 d1 p4 d2 d3 d4）",
        ))

    frame = "".join(codewords)
    steps.append(_step("组帧", f"拼接 {len(codewords)} 组码字，整帧 {len(frame)} 位"))
    return {
        "ok": True,
        "result": {
            "data": data,
            "padded_data": padded,
            "padding": padding,
            "blocks": blocks,
            "frame": frame,
        },
        "steps": steps,
        "message": f"汉明码 (7,4)：{len(blocks)} 组，整帧 {len(frame)} 位",
    }


def hamming_decode(code_bits: str) -> dict:
    """接收端：用伴随式定位出错位、纠正并还原数据。

    {ok, detected, result, syndrome, error_pos, corrected, steps, message}
    syndrome 是 (s4, s2, s1) 三元组，error_pos 是出错位号（1..7，0 表示无错）。
    """
    try:
        bits = normalize_bits(code_bits)
    except ValueError as exc:
        return {"ok": False, "detected": False, "result": None, "syndrome": None,
                "error_pos": None, "corrected": None, "steps": [], "message": str(exc)}

    if len(bits) % BLOCK_TOTAL != 0:
        return {"ok": False, "detected": False, "result": None, "syndrome": None,
                "error_pos": None, "corrected": None, "steps": [],
                "message": f"汉明码帧长必须是 {BLOCK_TOTAL} 的整数倍，当前 {len(bits)} 位"}

    blocks = []
    corrected_blocks = []
    data_out = []
    first_error = None
    first_syndrome = (0, 0, 0)
    detected_any = False
    steps = [_step("分组", f"整帧 {len(bits)} 位，按 {BLOCK_TOTAL} 位一组切分，共 {len(bits) // BLOCK_TOTAL} 组")]

    for block_index in range(0, len(bits), BLOCK_TOTAL):
        codeword = bits[block_index:block_index + BLOCK_TOTAL]
        s4, s2, s1 = _syndrome(codeword)
        syndrome_value = (s4 << 2) | (s2 << 1) | s1
        fixed = codeword
        if syndrome_value:
            detected_any = True
            position = syndrome_value - 1
            flipped = "1" if codeword[position] == "0" else "0"
            fixed = codeword[:position] + flipped + codeword[position + 1:]
            if first_error is None:
                first_error = syndrome_value
                first_syndrome = (s4, s2, s1)
        blocks.append({
            "codeword": codeword,
            "syndrome": (s4, s2, s1),
            "syndrome_value": syndrome_value,
            "error_pos": syndrome_value,
            "corrected": fixed,
            "data": fixed[2] + fixed[4] + fixed[5] + fixed[6],
        })
        corrected_blocks.append(fixed)
        # 数据位在第 3、5、6、7 位，下标 2、4、5、6
        data_out.append(fixed[2] + fixed[4] + fixed[5] + fixed[6])

        group_no = block_index // BLOCK_TOTAL + 1
        if syndrome_value:
            steps.append(_step(
                f"第 {group_no} 组 {codeword}",
                f"s1 = {int(codeword[0])}⊕{int(codeword[2])}⊕{int(codeword[4])}⊕{int(codeword[6])} = {s1}；"
                f"s2 = {int(codeword[1])}⊕{int(codeword[2])}⊕{int(codeword[5])}⊕{int(codeword[6])} = {s2}；"
                f"s4 = {int(codeword[3])}⊕{int(codeword[4])}⊕{int(codeword[5])}⊕{int(codeword[6])} = {s4} "
                f"-> 伴随式 (s4s2s1) = {s4}{s2}{s1} = {syndrome_value} -> 第 {syndrome_value} 位出错，取反后 {fixed}",
            ))
        else:
            steps.append(_step(f"第 {group_no} 组 {codeword}",
                               "伴随式 (s4s2s1) = 000，本组无错"))

    corrected_frame = "".join(corrected_blocks)
    data_bits = "".join(data_out)
    steps.append(_step("还原数据", f"取每组的第 3、5、6、7 位，得到数据 {data_bits}"))
    steps.append(_step("判定", "伴随式全为 0 -> 未检出错误" if not detected_any
                       else f"伴随式指出第 {first_error} 位出错，已取反纠正"))

    return {
        "ok": True,
        "detected": detected_any,
        "result": {
            "data": data_bits,
            "frame": bits,
            "corrected_frame": corrected_frame,
            "blocks": blocks,
        },
        "syndrome": first_syndrome,
        "error_pos": first_error or 0,
        "corrected": corrected_frame,
        "corrected_frame": corrected_frame,
        "steps": steps,
        "message": (f"检出并纠正错误：伴随式 = {first_syndrome and ''.join(map(str, first_syndrome))}"
                    f"（十进制 {first_error}），第 {first_error} 位被取反")
        if detected_any else "伴随式为 0，未检出错误",
    }
