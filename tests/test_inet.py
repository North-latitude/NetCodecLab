"""Internet 校验和（RFC 1071）的单元测试（对应验收点 3.4）。

验收标准：
    接收端把校验和一起算，结果应为 0xFFFF。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.checksum import checksum_frame, inet_checksum, inet_verify


class TestInetChecksum(unittest.TestCase):
    def test_receiver_sum_is_ffff(self):
        frame = checksum_frame(b"NetCodec")
        self.assertTrue(frame["ok"])
        verify = inet_verify(frame["result"]["frame"])
        self.assertEqual(verify["result"]["sum"], 0xFFFF)
        self.assertFalse(verify["detected"])

    def test_known_vector(self):
        # RFC 1071 的例子：00 01 F2 03 F4 F5 F6 F7 -> 校验和 0x220D
        result = inet_checksum(bytes([0x00, 0x01, 0xF2, 0x03, 0xF4, 0xF5, 0xF6, 0xF7]))
        self.assertEqual(result["result"]["checksum_hex"], "0x220D")
        self.assertEqual(result["result"]["sum_hex"], "0xDDF2")

    def test_all_zero_words(self):
        self.assertEqual(inet_checksum(b"\x00\x00")["result"]["checksum_hex"], "0xFFFF")

    def test_all_ones(self):
        self.assertEqual(inet_checksum(b"\xff\xff")["result"]["checksum_hex"], "0x0000")

    def test_odd_length_is_padded(self):
        result = inet_checksum(b"abc")
        self.assertTrue(result["result"]["padded"])

    def test_steps_record_every_accumulation(self):
        result = inet_checksum(b"NetCodec")
        steps = [s for s in result["steps"] if "累加第" in s["title"]]
        self.assertEqual(len(steps), 4)          # 8 字节 = 4 个 16 位字

    def test_error_detected(self):
        frame = checksum_frame(b"NetCodec")
        raw = bytearray(frame["result"]["frame"])
        raw[3] ^= 0x01
        self.assertTrue(inet_verify(bytes(raw))["detected"])

    def test_every_single_byte_error_detected(self):
        frame = checksum_frame(b"NetCodec")
        raw = bytearray(frame["result"]["frame"])
        for index in range(len(raw)):
            broken = bytearray(raw)
            broken[index] ^= 0x01
            self.assertTrue(inet_verify(bytes(broken))["detected"],
                            f"第 {index + 1} 字节出错未被检出")


class TestInetErrors(unittest.TestCase):
    def test_empty_input(self):
        self.assertFalse(inet_checksum(b"")["ok"])

    def test_non_bytes_input(self):
        self.assertFalse(inet_checksum("not bytes")["ok"])
        self.assertFalse(inet_verify([1, 2, 3])["ok"])

    def test_frame_too_short(self):
        self.assertFalse(inet_verify(b"\x01\x02")["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
