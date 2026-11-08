"""Internet 校验和（RFC 1071）。

IP / TCP / UDP 首部用的就是这个算法，步骤只有三步：
1. 把数据按 16 位（2 字节）一组切开，最后一组不足 16 位就补 0；
2. 所有 16 位字按“反码加法”累加：高位溢出的进位要加回到最低位（end-around carry）；
3. 把最终累加结果按位取反，就得到校验和。

接收端把包括校验和在内的全部数据再算一遍，结果应当正好是 0xFFFF。
"""

from __future__ import annotations

from ..common.bits import bytes_to_bitstr, bitstr_to_bytes

_MASK16 = 0xFFFF


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def _fold(sum_value: int) -> tuple[int, int]:
    """把超过 16 位的部分折叠回低 16 位，返回 (折叠后结果, 折叠次数)。"""
    folds = 0
    while sum_value >> 16:
        carry = sum_value >> 16
        sum_value = (sum_value & _MASK16) + carry
        folds += 1
    return sum_value, folds


def split_words(data: bytes) -> list[bytes]:
    """按 16 位分组；总长为奇数时在末尾补一个 0x00 字节。"""
    if len(data) % 2 == 1:
        data = data + b"\x00"
    return [data[i:i + 2] for i in range(0, len(data), 2)]


def inet_checksum(data: bytes) -> dict:
    """发送端：计算 16 位反码和，并返回它的反码（校验和）。

    返回
    ----
    {ok, result: {words, sum, checksum, checksum_hex, padded}, steps, message}
    """
    if not isinstance(data, (bytes, bytearray)):
        return {"ok": False, "result": None, "steps": [],
                "message": "inet_checksum 的输入必须是 bytes"}
    raw = bytes(data)
    if not raw:
        return {"ok": False, "result": None, "steps": [], "message": "数据为空，无法计算校验和"}

    padded = len(raw) % 2 == 1
    words = split_words(raw)
    running = 0
    steps = [
        _step("按 16 位分组",
              f"数据 {len(raw)} 字节 -> {len(words)} 个 16 位字"
              + ("（长度为奇数，末尾补了一个 0x00）" if padded else "")),
    ]

    for index, word in enumerate(words):
        value = int.from_bytes(word, "big")
        total = running + value
        folded, folds = _fold(total)
        steps.append(_step(
            f"累加第 {index + 1} 个字 0x{value:04X}",
            f"0x{running:04X} + 0x{value:04X} = 0x{total:05X}"
            + (f"，进位加回低位 -> 0x{folded:04X}" if folds else "")
            + f"；当前累加和 0x{folded:04X}",
        ))
        running = folded

    checksum = (~running) & _MASK16
    steps.append(_step("取反", f"累加和 0x{running:04X} 按位取反 -> 0x{checksum:04X}，这就是校验和"))
    steps.append(_step("组帧", f"把 0x{checksum:04X} 附在数据末尾一起发送"))

    return {
        "ok": True,
        "result": {
            "words": [f"0x{int.from_bytes(w, 'big'):04X}" for w in words],
            "sum": running,
            "sum_hex": f"0x{running:04X}",
            "checksum": checksum,
            "checksum_hex": f"0x{checksum:04X}",
            "padded": padded,
            "byte_length": len(raw),
        },
        "steps": steps,
        "message": f"16 位反码和 = 0x{running:04X}，取反得到校验和 0x{checksum:04X}",
    }


def inet_verify(frame: bytes) -> dict:
    """接收端：对“数据 + 校验和”整体求和，应得 0xFFFF。

    {ok, detected, result: {sum, sum_hex}, steps, message}
    """
    if not isinstance(frame, (bytes, bytearray)):
        return {"ok": False, "detected": False, "result": None, "steps": [],
                "message": "inet_verify 的输入必须是 bytes"}
    raw = bytes(frame)
    if len(raw) < 4:
        return {"ok": False, "detected": False, "result": None, "steps": [],
                "message": "帧太短，至少要 2 字节数据 + 2 字节校验和"}

    words = split_words(raw)
    running = 0
    for word in words:
        running, _ = _fold(running + int.from_bytes(word, "big"))
    total_with_checksum = running
    detected = total_with_checksum != _MASK16

    steps = [
        _step("整体再算一次",
              f"把数据和校验和一起按 16 位反码求和，得到 0x{total_with_checksum:04X}"),
        _step("判定规则", "结果等于 0xFFFF 说明校验和正确；否则数据在传输中被改动过"),
        _step("判定结果", "结果不是 0xFFFF -> 检出错误" if detected
              else "结果为 0xFFFF -> 校验通过"),
    ]
    return {
        "ok": True,
        "detected": detected,
        "result": {"sum": total_with_checksum, "sum_hex": f"0x{total_with_checksum:04X}"},
        "steps": steps,
        "message": (f"检出错误：整体求和 = 0x{total_with_checksum:04X}，不是 0xFFFF")
        if detected else "校验通过：整体求和 = 0xFFFF",
    }


def checksum_frame(data: bytes) -> dict:
    """把数据帧和校验和拼成一个 bytes，方便信道模拟器按位注入错误。"""
    calc = inet_checksum(data)
    if not calc["ok"]:
        return calc
    checksum = calc["result"]["checksum"]
    frame_bytes = bytes(data) + checksum.to_bytes(2, "big")
    return {
        "ok": True,
        "result": {
            "data": bytes(data),
            "checksum": checksum,
            "frame": frame_bytes,
            "frame_bits": bytes_to_bitstr(frame_bytes),
            "data_bits": bytes_to_bitstr(bytes(data)),
        },
        "steps": calc["steps"],
        "message": calc["message"],
    }


def frame_bits_to_bytes(bits: str) -> bytes:
    """位串 -> 字节，帧长度不是 8 的倍数时补 0。"""
    padded = bits.ljust((len(bits) + 7) // 8 * 8, "0")
    return bitstr_to_bytes(padded)
