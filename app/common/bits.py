"""位串工具：文本、字节、位串三者之间的互转。

本模块只做“形态转换”，不含任何校验逻辑，因此不依赖 Tkinter，
可以被单元测试单独导入。所有函数都是纯函数，出错时返回 None 或抛出
调用方可以捕获的 ValueError，由上层负责包装成 {ok, message}。
"""

from __future__ import annotations

# 每个字节固定 8 位，这是全项目统一的显示宽度
BITS_PER_BYTE = 8


def text_to_bytes(text: str, encoding: str = "utf-8") -> bytes:
    """把文本按指定字符集编码成字节串。

    编码失败（例如用 GBK 编码 emoji）时抛出 UnicodeEncodeError，
    由调用方决定是提示用户还是降级处理。
    """
    return text.encode(encoding)


def bytes_to_bitstr(data: bytes) -> str:
    """字节串 -> 位串。每个字节补足 8 位，高位在前。"""
    return "".join(format(byte, "08b") for byte in data)


def bitstr_to_bytes(bits: str) -> bytes:
    """位串 -> 字节串。位串长度必须是 8 的整数倍。"""
    if len(bits) % BITS_PER_BYTE != 0:
        raise ValueError(f"位串长度 {len(bits)} 不是 8 的整数倍，无法还原成字节")
    return bytes(int(bits[i:i + BITS_PER_BYTE], 2) for i in range(0, len(bits), BITS_PER_BYTE))


def bytes_to_hex(data: bytes, sep: str = " ") -> str:
    """字节串 -> 大写十六进制，默认用空格分隔，例如 '4E 65 74'。"""
    return sep.join(f"{byte:02X}" for byte in data)


def bits_to_hex(bits: str) -> str:
    """位串 -> 十六进制串（长度不足 8 位时按 8 位对齐补零）。"""
    padded = bits.ljust((len(bits) + 7) // 8 * 8, "0")
    return bytes_to_hex(bitstr_to_bytes(padded))


def normalize_bits(value: str) -> str:
    """清洗用户输入的位串：去掉空格、制表符、下划线，只保留 0/1。

    输入非法字符时抛出 ValueError，让界面能给出明确提示而不是静默出错。
    """
    cleaned = "".join(ch for ch in value if not ch.isspace() and ch not in "_-|")
    if not cleaned:
        raise ValueError("位串为空")
    bad = sorted({ch for ch in cleaned if ch not in "01"})
    if bad:
        raise ValueError("位串只能包含 0 和 1，发现非法字符：" + "、".join(repr(c) for c in bad))
    return cleaned


def count_ones(bits: str) -> int:
    """统计位串中 1 的个数，奇偶校验和各种校验都要用。"""
    return bits.count("1")


def group_bits(bits: str, size: int = 4, sep: str = " ") -> str:
    """按固定宽度分组的位串，方便界面阅读，例如 '0100 1110'。"""
    if size <= 0:
        return bits
    return sep.join(bits[i:i + size] for i in range(0, len(bits), size))


def pad_to_multiple(bits: str, multiple: int) -> tuple[str, int]:
    """在尾部补 0，使长度成为 multiple 的整数倍。

    返回 (补齐后的位串, 补了几个 0)。CRC 与汉明码都要求输入长度对齐。
    """
    if multiple <= 0:
        raise ValueError("multiple 必须是正整数")
    remainder = len(bits) % multiple
    if remainder == 0:
        return bits, 0
    padding = multiple - remainder
    return bits + "0" * padding, padding


def flip_bit(bits: str, position: int) -> str:
    """翻转指定下标（从 0 开始）的位，信道注入错误的最小操作。"""
    if not 0 <= position < len(bits):
        raise IndexError(f"位下标 {position} 超出范围 0..{len(bits) - 1}")
    target = "1" if bits[position] == "0" else "0"
    return bits[:position] + target + bits[position + 1:]


def to_display_bits(bits: str, size: int = 4) -> str:
    """界面展示用：每 size 位加一个空格，空串原样返回。"""
    if not bits:
        return ""
    return group_bits(bits, size)
