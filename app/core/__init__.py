"""算法层统一出口：界面层只从这里 import，不直接碰子模块。

约定（写进交接说明，C 和 D 照着这个调）：
    所有函数都返回 {ok, result, steps, message}
    steps 是 [{'title': ..., 'detail': ...}, ...]，界面按行显示即可
"""

from .checksum import checksum_frame, inet_checksum, inet_verify  # noqa: F401
from .channel import SCHEMES, batch_compare, compare_schemes, inject_error  # noqa: F401
from .convert import base_to_dec, dec_to_base  # noqa: F401
from .crc import CRC_PRESETS, PRESET_LABELS, crc_check, crc_encode, crc_of_text  # noqa: F401
from .encoding import encode_text, text_to_bitstream  # noqa: F401
from .hamming import hamming_decode, hamming_encode  # noqa: F401
from .matrix import matrix_check, matrix_encode, matrix_frame_to_text  # noqa: F401
from .parity import (  # noqa: F401
    MODE_EVEN,
    MODE_NAMES,
    MODE_ODD,
    parity_bit_for,
    parity_check,
    parity_encode,
)

__all__ = [
    "parity_encode", "parity_check", "parity_bit_for",
    "MODE_EVEN", "MODE_ODD", "MODE_NAMES",
    "matrix_encode", "matrix_check", "matrix_frame_to_text",
    "crc_encode", "crc_check", "crc_of_text", "CRC_PRESETS", "PRESET_LABELS",
    "inet_checksum", "inet_verify", "checksum_frame",
    "hamming_encode", "hamming_decode",
    "dec_to_base", "base_to_dec",
    "encode_text", "text_to_bitstream",
    "inject_error", "compare_schemes", "batch_compare", "SCHEMES",
]
