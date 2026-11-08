"""CRC 循环冗余校验：模 2 除法（逐位异或的竖式），不使用查表法、不做位反射。

为什么不用查表法：本项目是教学演示，要在界面上把“每一次移位、每一次异或”
都画出来；查表法只保留结果，过程就看不见了。位反射（refin/refout）同样会
让竖式对不上，所以这里统一采用“高位在前、MSB first”的教科书写法。

常用参数（width, poly, init）：
    CRC-8          : 8,  0x07,   0x00
    CRC-16/IBM     : 16, 0x8005, 0x0000
    CRC-16/CCITT   : 16, 0x1021, 0xFFFF   -> "123456789" 的结果是 0x29B1
"""

from __future__ import annotations

from ..common.bits import normalize_bits

# 预置方案：名字 -> (poly, width, init)
CRC_PRESETS = {
    "CRC-8": (0x07, 8, 0x00),
    "CRC-16/IBM": (0x8005, 16, 0x0000),
    "CRC-16/CCITT": (0x1021, 16, 0xFFFF),
}

# 界面上的中文名
PRESET_LABELS = {
    "CRC-8": "CRC-8（多项式 0x07，初值 0x00）",
    "CRC-16/IBM": "CRC-16/IBM（多项式 0x8005，初值 0x0000）",
    "CRC-16/CCITT": "CRC-16/CCITT（多项式 0x1021，初值 0xFFFF）",
}


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def _mask(width: int) -> int:
    """宽度为 width 位的全 1 掩码，用来把寄存器截断在 w 位内。"""
    return (1 << width) - 1


def _top_bit(width: int) -> int:
    """寄存器的最高位（第 width-1 位），模 2 除法就是拿它决定是否异或。"""
    return 1 << (width - 1)


def crc_remainder(bits: str, poly: int, width: int, init: int,
                  keep_trace: bool = False) -> tuple[int, list[dict]]:
    """对位串做模 2 除法，返回余数。

    bits  : 数据位串（不含 CRC 本身）
    poly  : 生成多项式，只取低 width 位
    width : 寄存器宽度，也是 CRC 位数
    init  : 寄存器初值

    keep_trace=True 时同时返回逐位的中间过程，供界面做“竖式”展示。
    """
    if width <= 0:
        raise ValueError("width 必须是正整数")
    if poly <= 0:
        raise ValueError("poly 必须是正整数")
    if not 0 <= init <= _mask(width):
        raise ValueError(f"init 必须在 0..0x{_mask(width):X} 之间")

    register = init & _mask(width)
    trace: list[dict] = []
    for index, bit in enumerate(bits):
        # 取出最高位，再和数据位比：两者不同才需要在左移后异或生成多项式，
        # 这正是模 2 除法里“够除就商 1、异或掉”的那一步。
        top = 1 if register & _top_bit(width) else 0
        if top ^ int(bit):
            register = ((register << 1) ^ poly) & _mask(width)
            did_xor = True
        else:
            register = (register << 1) & _mask(width)
            did_xor = False
        if keep_trace:
            trace.append({
                "index": index,
                "bit": bit,
                "top": top,
                "register": register,
                "xor": did_xor,
            })
    return register, trace


def crc_encode(bits: str, poly: int = 0x1021, width: int = 16,
               init: int = 0xFFFF, preset: str | None = None) -> dict:
    """发送端：算出 CRC 余数并附在数据后面组成帧。

    返回 {ok, result: {data, crc, crc_hex, frame, width, poly, init}, steps, trace, message}
    """
    try:
        data = normalize_bits(bits)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    if preset:
        if preset not in CRC_PRESETS:
            return {"ok": False, "result": None, "steps": [],
                    "message": f"未知的 CRC 预置方案 {preset!r}"}
        poly, width, init = CRC_PRESETS[preset]

    try:
        remainder, trace = crc_remainder(data, poly, width, init, keep_trace=True)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    crc_bits = format(remainder, f"0{width}b")
    frame = data + crc_bits

    # 按“每 8 位喂一次”的方式汇总，比逐位过程更适合界面逐行显示
    steps = [
        _step("确定参数",
              f"宽度 {width} 位，生成多项式 0x{poly:0{max(width // 4, 2)}X}，初值 0x{init:0{width // 4}X}"),
        _step("准备数据", f"数据 {data}，共 {len(data)} 位；寄存器置初值 "
                          f"0x{init:0{width // 4}X}"),
    ]
    register = init & _mask(width)
    for byte_no in range(0, len(data), 8):
        chunk = data[byte_no:byte_no + 8]
        start_register = register
        for bit in chunk:
            top = 1 if register & _top_bit(width) else 0
            if top ^ int(bit):
                register = ((register << 1) ^ poly) & _mask(width)
            else:
                register = (register << 1) & _mask(width)
        steps.append(_step(
            f"移入第 {byte_no // 8 + 1} 个字节 {chunk}",
            f"移入前 0x{start_register:0{width // 4}X}，逐位模 2 除完后余数 = "
            f"0x{register:0{width // 4}X}（二进制 {format(register, f'0{width}b')}）",
        ))
    steps.append(_step("取余数", f"全部数据移入后，余数 = 0x{remainder:0{width // 4}X}，"
                                 f"这就是 CRC 校验码 {crc_bits}"))
    steps.append(_step("附到帧尾", f"发送帧 = 数据 + CRC = {data} + {crc_bits}"))

    return {
        "ok": True,
        "result": {
            "data": data,
            "crc": crc_bits,
            "crc_value": remainder,
            "crc_hex": f"0x{remainder:0{width // 4}X}",
            "frame": frame,
            "width": width,
            "poly": poly,
            "init": init,
        },
        "steps": steps,
        "trace": trace,
        "message": f"CRC 余数 {f'0x{remainder:0{width // 4}X}'}，整帧 {len(frame)} 位",
    }


def crc_check(frame: str, poly: int = 0x1021, width: int = 16,
              init: int = 0xFFFF, data_len: int | None = None,
              preset: str | None = None) -> dict:
    """接收端：把“数据 + CRC”整体再做一次模 2 除法。

    余数为 0 说明传输出错的可能性极低（判定通过），否则判定数据损坏。

    {ok, detected, result: {remainder, expected_crc, received_crc, ...}, steps, message}
    """
    try:
        bits = normalize_bits(frame)
    except ValueError as exc:
        return {"ok": False, "detected": False, "result": None, "steps": [],
                "message": str(exc)}

    if preset:
        if preset not in CRC_PRESETS:
            return {"ok": False, "detected": False, "result": None, "steps": [],
                    "message": f"未知的 CRC 预置方案 {preset!r}"}
        poly, width, init = CRC_PRESETS[preset]

    if len(bits) <= width:
        return {"ok": False, "detected": False, "result": None, "steps": [],
                "message": f"帧长度 {len(bits)} 位不足以容纳 {width} 位 CRC"}

    if data_len is None:
        data_len = len(bits) - width
    data, received_crc = bits[:data_len], bits[data_len:]

    try:
        remainder, _ = crc_remainder(bits, poly, width, init)
        expected_remainder, _ = crc_remainder(data, poly, width, init)
    except ValueError as exc:
        return {"ok": False, "detected": False, "result": None, "steps": [],
                "message": str(exc)}

    expected_crc = format(expected_remainder, f"0{width}b")
    detected = remainder != 0
    steps = [
        _step("拆分帧", f"数据 {data}，收到的 CRC {received_crc}"),
        _step("整体再做一次模 2 除法",
              f"对整帧做模 2 除法，余数 = 0x{remainder:0{width // 4}X}"),
        _step("判定规则", "余数为 0 表示能被生成多项式整除，判定通过；不为 0 判定数据损坏"),
        _step("判定结果",
              "余数非 0 -> 检出错误" if detected else "余数为 0 -> 校验通过"),
    ]
    return {
        "ok": True,
        "detected": detected,
        "result": {
            "data": data,
            "received_crc": received_crc,
            "expected_crc": expected_crc,
            "remainder": remainder,
            "remainder_hex": f"0x{remainder:0{width // 4}X}",
        },
        "steps": steps,
        "message": (f"检出错误：余数 0x{remainder:0{width // 4}X} ≠ 0")
        if detected else "校验通过：余数为 0",
    }


def crc_of_text(text: str, encoding: str = "ascii", preset: str = "CRC-16/CCITT") -> dict:
    """便捷函数：直接对文本算 CRC，用于自检和演示（例如 "123456789" -> 0x29B1）。"""
    from ..common.bits import bytes_to_bitstr

    poly, width, init = CRC_PRESETS[preset]
    try:
        data = text.encode(encoding)
    except UnicodeEncodeError as exc:
        return {"ok": False, "result": None, "steps": [],
                "message": f"字符集 {encoding} 无法编码该文本：{exc}"}
    return crc_encode(bytes_to_bitstr(data), poly=poly, width=width, init=init)
