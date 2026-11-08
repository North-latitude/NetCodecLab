"""奇偶校验的单元测试（对应验收点 3.1）。

验收标准：
    1011001 奇校验补 1、偶校验补 0；随便翻一位后 check 要报错。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common.bits import flip_bit
from app.core.parity import parity_bit_for, parity_check, parity_encode


class TestParityEncode(unittest.TestCase):
    def test_odd_parity_appends_one(self):
        result = parity_encode("1011001", "odd")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["parity"], "1")
        self.assertEqual(result["result"]["frame"], "10110011")
        self.assertEqual(result["result"]["total_ones"], 5)

    def test_even_parity_appends_zero(self):
        result = parity_encode("1011001", "even")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["parity"], "0")
        self.assertEqual(result["result"]["total_ones"], 4)

    def test_all_zeros(self):
        self.assertEqual(parity_encode("0000", "odd")["result"]["frame"], "00001")
        self.assertEqual(parity_encode("0000", "even")["result"]["frame"], "00000")

    def test_single_one(self):
        self.assertEqual(parity_encode("0001", "odd")["result"]["frame"], "00010")
        self.assertEqual(parity_encode("0001", "even")["result"]["frame"], "00011")

    def test_parity_bit_helper(self):
        self.assertEqual(parity_bit_for("1011001", "odd"), "1")
        self.assertEqual(parity_bit_for("1011001", "even"), "0")


class TestParityCheck(unittest.TestCase):
    def test_clean_frame_passes(self):
        frame = parity_encode("1011001", "even")["result"]["frame"]
        self.assertFalse(parity_check(frame, "even")["detected"])

    def test_flip_one_bit_is_detected(self):
        frame = parity_encode("1011001", "odd")["result"]["frame"]
        for index in range(len(frame)):
            broken = flip_bit(frame, index)
            self.assertTrue(parity_check(broken, "odd")["detected"],
                            f"翻转第 {index + 1} 位未被检出")

    def test_two_bit_errors_slip_through(self):
        """两位同时翻转时 1 的个数不变，奇偶校验必然漏检（写进文档的已知缺陷）。"""
        frame = parity_encode("1011001", "even")["result"]["frame"]
        broken = flip_bit(flip_bit(frame, 0), 1)
        self.assertFalse(parity_check(broken, "even")["detected"])

    def test_three_bit_errors_detected_again(self):
        frame = parity_encode("1011001", "even")["result"]["frame"]
        broken = flip_bit(flip_bit(flip_bit(frame, 0), 1), 2)
        self.assertTrue(parity_check(broken, "even")["detected"])


class TestParityErrors(unittest.TestCase):
    def test_illegal_bits(self):
        self.assertFalse(parity_encode("1012", "even")["ok"])

    def test_illegal_mode(self):
        self.assertFalse(parity_encode("1011", "both")["ok"])
        self.assertFalse(parity_check("10110", "both")["ok"])

    def test_empty_input(self):
        self.assertFalse(parity_encode("", "even")["ok"])

    def test_frame_too_short(self):
        self.assertFalse(parity_check("1", "even")["ok"])

    def test_steps_have_title_and_detail(self):
        for step in parity_encode("1011", "even")["steps"]:
            self.assertIn("title", step)
            self.assertIn("detail", step)


if __name__ == "__main__":
    unittest.main(verbosity=2)
