"""字符编码拆解：文本 -> 码点 -> UTF-8 / GBK 字节 -> 二进制位流。

对应编码工坊页面。UTF-8 与 GBK 是变长编码，同一个汉字在 UTF-8 占 3 字节、
GBK 占 2 字节，因此必须**逐字符**编码，不能整串编码后再按字节切。

本模块是纯函数，不依赖 Tkinter；返回 ``{ok, result, steps, message}``。
"""

from __future__ import annotations

from ..common import config
from ..common.bits import bytes_to_bitstr, bytes_to_hex

SUPPORTED_ENCODINGS = ("utf-8", "gbk")


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def _bytes_block(raw: bytes | None) -> dict:
    """把一组字节整理成界面展示用的字段；raw 为 None 表示该字符集编不了。"""
    if raw is None:
        return {"bytes": None, "hex": None, "bits": None, "byte_count": 0}
    return {
        "bytes": list(raw),
        "hex": bytes_to_hex(raw),
        "bits": bytes_to_bitstr(raw),
        "byte_count": len(raw),
    }


def encode_text(text: str, primary: str = config.DEFAULT_ENCODING) -> dict:
    """逐字符拆解一段文本的码点、UTF-8 / GBK 字节与位流。

    参数
    ----
    text: 用户输入的原始文本。
    primary: 主显示字符集（默认 UTF-8），只影响 message 里的口径，
             UTF-8 和 GBK 两组字节都会同时给出。

    返回
    ----
    {ok, result: {chars, total_utf8_bytes, total_gbk_bytes, total_utf8_bits,
                  total_gbk_bits, primary}, steps, message}
    ``chars`` 每项含 char、code_point、code_point_hex、utf8、gbk 两个字段块。
    某个字符 GBK 编不了时，gbk 块为 None 字段并在 steps / message 说明，
    其余字符照常处理，不会整页崩溃。
    """
    if not isinstance(text, str):
        return {"ok": False, "result": None, "steps": [], "message": "输入必须是文本字符串"}
    if not text:
        return {"ok": False, "result": None, "steps": [], "message": "输入为空，请先输入要编码的文本"}
    if len(text) > config.MAX_INPUT_CHARS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"输入超过上限 {config.MAX_INPUT_CHARS} 个字符，"
                           f"当前 {len(text)} 个，请删减后再试"}
    if primary not in SUPPORTED_ENCODINGS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"字符集只能是 {' / '.join(SUPPORTED_ENCODINGS)}，收到 {primary!r}"}

    chars: list[dict] = []
    total_utf8 = 0
    total_gbk = 0
    gbk_failed: list[str] = []
    steps = [_step("逐字符编码",
                   f"共 {len(text)} 个字符；UTF-8、GBK 分别逐字符编码后再拼位流")]

    for index, char in enumerate(text, start=1):
        code = ord(char)
        code_hex = f"U+{code:04X}"

        try:
            utf8_raw = char.encode("utf-8")
        except UnicodeEncodeError:
            utf8_raw = None
        try:
            gbk_raw: bytes | None = char.encode("gbk")
        except UnicodeEncodeError:
            gbk_raw = None
            gbk_failed.append(char)

        utf8_block = _bytes_block(utf8_raw)
        gbk_block = _bytes_block(gbk_raw)
        total_utf8 += utf8_block["byte_count"]
        total_gbk += gbk_block["byte_count"]

        chars.append({
            "index": index,
            "char": char,
            "code_point": code,
            "code_point_hex": code_hex,
            "utf8": utf8_block,
            "gbk": gbk_block,
        })
        gbk_note = "，GBK 无法编码" if gbk_raw is None else ""
        steps.append(_step(
            f"第 {index} 个字符 {char}",
            f"码点 {code_hex}（十进制 {code}）；UTF-8 = {utf8_block['hex']} "
            f"（{utf8_block['byte_count']} 字节）；GBK = {gbk_block['hex'] or '—'}"
            f"（{gbk_block['byte_count']} 字节）{gbk_note}",
        ))

    utf8_bits = total_utf8 * 8
    gbk_bits = total_gbk * 8

    if gbk_failed:
        note = "；以下字符 GBK 无法表示：" + "、".join(gbk_failed)
    else:
        note = ""
    steps.append(_step("汇总",
                       f"UTF-8 共 {total_utf8} 字节 {utf8_bits} 位；"
                       f"GBK 共 {total_gbk} 字节 {gbk_bits} 位" + note))

    return {
        "ok": True,
        "result": {
            "chars": chars,
            "total_utf8_bytes": total_utf8,
            "total_gbk_bytes": total_gbk,
            "total_utf8_bits": utf8_bits,
            "total_gbk_bits": gbk_bits,
            "primary": primary,
            "gbk_failed_chars": gbk_failed,
        },
        "steps": steps,
        "message": f"{len(text)} 个字符：UTF-8 {total_utf8} 字节 / {utf8_bits} 位，"
                   f"GBK {total_gbk} 字节 / {gbk_bits} 位" + note,
    }


def text_to_bitstream(text: str, encoding: str = config.DEFAULT_ENCODING) -> dict:
    """便捷函数：整段文本按指定字符集拼成一条位流（编码工坊主视图用）。

    返回 {ok, result: {bytes, hex, bits, byte_count, encoding}, steps, message}。
    """
    if encoding not in SUPPORTED_ENCODINGS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"字符集只能是 {' / '.join(SUPPORTED_ENCODINGS)}，收到 {encoding!r}"}
    if not text:
        return {"ok": False, "result": None, "steps": [], "message": "输入为空"}
    if len(text) > config.MAX_INPUT_CHARS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"输入超过上限 {config.MAX_INPUT_CHARS} 个字符"}
    try:
        raw = text.encode(encoding)
    except UnicodeEncodeError as exc:
        return {"ok": False, "result": None, "steps": [],
                "message": f"当前字符集 {encoding} 无法编码部分内容：{exc}"}

    bits = bytes_to_bitstr(raw)
    return {
        "ok": True,
        "result": {"bytes": list(raw), "hex": bytes_to_hex(raw), "bits": bits,
                   "byte_count": len(raw), "encoding": encoding},
        "steps": [
            _step("按字符集编码", f"文本按 {encoding} 编码成 {len(raw)} 字节"),
            _step("拼成位流", f"每个字节补满 8 位，共 {len(bits)} 位：{bits}"),
        ],
        "message": f"{len(raw)} 字节，{len(bits)} 位（{encoding}）",
    }
