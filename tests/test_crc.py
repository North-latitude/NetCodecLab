"""CRC 模 2 除法的单元测试（对应验收点 3.3）。

验收标准：
    "123456789" 用 0x1021、初值 0xFFFF，得 0x29B1。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common.bits import flip_bit
from app.core.crc import crc_check, crc_encode, crc_of_text, crc_remainder


class TestCRCStandardVectors(unittest.TestCase):
    """三个标准校验值，用来证明模 2 除法写对了。"""

    def test_ccitt_check_value(self):
        result = crc_of_text("123456789", preset="CRC-16/CCITT")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["crc_hex"], "0x29B1")

    def test_crc8_check_value(self):
        self.assertEqual(crc_of_text("123456789", preset="CRC-8")["result"]["crc_hex"], "0xF4")

    def test_ibm_check_value(self):
        self.assertEqual(crc_of_text("123456789", preset="CRC-16/IBM")["result"]["crc_hex"], "0xFEE8")


class TestCRCEncode(unittest.TestCase):
    def test_frame_is_data_plus_crc(self):
        result = crc_encode("01001101", poly=0x1021, width=16, init=0xFFFF)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["result"]["crc"]), 16)
        self.assertEqual(len(result["result"]["frame"]), 8 + 16)
        self.assertTrue(result["result"]["frame"].startswith("01001101"))

    def test_all_zero_data_with_zero_init(self):
        # 初值为 0、数据全 0 时寄存器一直是 0，余数必为 0
        result = crc_encode("00000000", poly=0x1021, width=16, init=0x0000)
        self.assertEqual(result["result"]["crc_hex"], "0x0000")

    def test_init_affects_result(self):
        # 初值不同，同样的数据应当算出不同的余数（印证 CRC 参数必须约定一致）
        zero_init = crc_encode("00000000", poly=0x1021, width=16, init=0x0000)
        ones_init = crc_encode("00000000", poly=0x1021, width=16, init=0xFFFF)
        self.assertNotEqual(zero_init["result"]["crc_hex"], ones_init["result"]["crc_hex"])

    def test_steps_show_intermediate_remainders(self):
        result = crc_encode("0100110101100101", poly=0x1021, width=16, init=0xFFFF)
        moved = [s for s in result["steps"] if "移入第" in s["title"]]
        self.assertEqual(len(moved), 2)
        for step in moved:
            self.assertIn("余数", step["detail"])

    def test_trace_is_recorded(self):
        result = crc_encode("01001101", poly=0x1021, width=16, init=0xFFFF)
        self.assertEqual(len(result["trace"]), 8)
        self.assertTrue(all("register" in row for row in result["trace"]))

    def test_remainder_helper_matches_encode(self):
        remainder, _ = crc_remainder("01001101", 0x1021, 16, 0xFFFF)
        self.assertEqual(remainder, crc_encode("01001101", 0x1021, 16, 0xFFFF)["result"]["crc_value"])


class TestCRCCheck(unittest.TestCase):
    def test_clean_frame_residue_is_zero(self):
        encoded = crc_of_text("123456789", preset="CRC-16/CCITT")
        check = crc_check(encoded["result"]["frame"], preset="CRC-16/CCITT", data_len=72)
        self.assertFalse(check["detected"])
        self.assertEqual(check["result"]["remainder_hex"], "0x0000")

    def test_single_bit_error_detected(self):
        encoded = crc_of_text("123456789", preset="CRC-16/CCITT")
        broken = flip_bit(encoded["result"]["frame"], 5)
        check = crc_check(broken, preset="CRC-16/CCITT", data_len=72)
        self.assertTrue(check["detected"])
        self.assertNotEqual(check["result"]["remainder_hex"], "0x0000")

    def test_every_single_bit_error_detected(self):
        encoded = crc_of_text("Net", preset="CRC-16/CCITT")
        frame = encoded["result"]["frame"]
        for index in range(len(frame)):
            broken = flip_bit(frame, index)
            check = crc_check(broken, preset="CRC-16/CCITT", data_len=24)
            self.assertTrue(check["detected"], f"第 {index + 1} 位翻转未被检出")


class TestCRCErrors(unittest.TestCase):
    def test_zero_poly(self):
        self.assertFalse(crc_encode("1010", poly=0, width=16)["ok"])

    def test_unknown_preset(self):
        self.assertFalse(crc_encode("1010", preset="CRC-99")["ok"])
        self.assertFalse(crc_check("1010" * 4, preset="CRC-99")["ok"])

    def test_frame_too_short(self):
        self.assertFalse(crc_check("1010", width=16)["ok"])

    def test_illegal_bits(self):
        self.assertFalse(crc_encode("10x0")["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
