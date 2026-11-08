"""汉明码 (7,4) 的单元测试（对应验收点 3.5）。

验收标准：
    翻转 7 个位置中任意一位，都能定位并纠正；无错时伴随式为 0。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common.bits import flip_bit
from app.core.hamming import hamming_decode, hamming_encode


class TestHammingEncode(unittest.TestCase):
    def setUp(self):
        self.encoded = hamming_encode("1011")
        self.codeword = self.encoded["result"]["frame"]

    def test_one_block_is_seven_bits(self):
        self.assertTrue(self.encoded["ok"])
        self.assertEqual(len(self.codeword), 7)

    def test_data_bits_at_positions_3_5_6_7(self):
        # 下标 2、4、5、6 对应第 3、5、6、7 位
        self.assertEqual([self.codeword[i] for i in (2, 4, 5, 6)], list("1011"))

    def test_padding_when_not_multiple_of_four(self):
        encoded = hamming_encode("101")           # 3 位数据，补 1 个 0
        self.assertEqual(encoded["result"]["padding"], 1)
        self.assertEqual(len(encoded["result"]["frame"]), 7)

    def test_multi_block(self):
        encoded = hamming_encode("10110011")
        self.assertEqual(len(encoded["result"]["frame"]), 14)
        self.assertEqual(len(encoded["result"]["blocks"]), 2)

    def test_steps_show_parity_equations(self):
        for step in self.encoded["steps"]:
            if "p1" in step["detail"]:
                self.assertIn("⊕", step["detail"])
                break
        else:
            self.fail("steps 里没有校验位方程")


class TestHammingDecode(unittest.TestCase):
    def setUp(self):
        self.encoded = hamming_encode("1011")
        self.codeword = self.encoded["result"]["frame"]

    def test_no_error_syndrome_is_zero(self):
        result = hamming_decode(self.codeword)
        self.assertFalse(result["detected"])
        self.assertEqual(result["syndrome"], (0, 0, 0))
        self.assertEqual(result["error_pos"], 0)
        self.assertEqual(result["result"]["data"], "1011")

    def test_all_seven_positions_can_be_corrected(self):
        """这是汉明码的核心验收：7 个位置任意翻一位都能定位并改回来。"""
        for index in range(7):
            broken = flip_bit(self.codeword, index)
            result = hamming_decode(broken)
            self.assertTrue(result["detected"], f"第 {index + 1} 位翻转未检出")
            self.assertEqual(result["error_pos"], index + 1, f"第 {index + 1} 位定位错误")
            self.assertEqual(result["result"]["data"], "1011", f"第 {index + 1} 位纠正后数据不对")
            self.assertEqual(result["corrected_frame"], self.codeword,
                             f"第 {index + 1} 位纠正后码字不对")

    def test_syndrome_decimal_equals_error_position(self):
        for index in range(7):
            broken = flip_bit(self.codeword, index)
            result = hamming_decode(broken)
            s4, s2, s1 = result["syndrome"]
            self.assertEqual(s4 * 4 + s2 * 2 + s1, index + 1)

    def test_two_blocks_corrected(self):
        encoded = hamming_encode("10110011")
        frame = encoded["result"]["frame"]
        broken = flip_bit(flip_bit(frame, 2), 9)      # 两组各翻一位
        result = hamming_decode(broken)
        self.assertEqual(result["corrected_frame"], frame)
        self.assertEqual(result["result"]["data"], "10110011")


class TestHammingErrors(unittest.TestCase):
    def test_wrong_length(self):
        self.assertFalse(hamming_decode("011001")["ok"])

    def test_illegal_bits(self):
        self.assertFalse(hamming_decode("0110012")["ok"])

    def test_empty(self):
        self.assertFalse(hamming_encode("")["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
