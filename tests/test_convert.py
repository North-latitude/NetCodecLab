"""进制转换单元测试（对应验收点 T-03）。

T-03：78 转二进制，除基取余竖式七行，结果 1001110。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.convert import base_to_dec, dec_to_base


class TestDecToBase(unittest.TestCase):
    def test_78_to_binary_seven_rows(self):
        result = dec_to_base(78, 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["text"], "1001110")
        # 除基取余共 7 步（78 -> 39 -> 19 -> 9 -> 4 -> 2 -> 1 -> 0）
        self.assertEqual(len(result["result"]["remainders"]), 7)
        # 竖式步骤：1 条说明 + 7 次除法 + 1 条逆序读取
        divide_steps = [s for s in result["steps"] if s["title"].startswith("第 ")]
        self.assertEqual(len(divide_steps), 7)

    def test_zero(self):
        self.assertEqual(dec_to_base(0, 2)["result"]["text"], "0")

    def test_hexadecimal(self):
        result = dec_to_base(255, 16)
        self.assertEqual(result["result"]["text"], "FF")

    def test_octal(self):
        self.assertEqual(dec_to_base(8, 8)["result"]["text"], "10")

    def test_negative_rejected(self):
        self.assertFalse(dec_to_base(-5, 2)["ok"])

    def test_bad_base_rejected(self):
        self.assertFalse(dec_to_base(10, 3)["ok"])

    def test_non_integer_rejected(self):
        self.assertFalse(dec_to_base("12.5", 2)["ok"])


class TestBaseToDec(unittest.TestCase):
    def test_binary_to_decimal(self):
        result = base_to_dec("1001110", 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["value"], 78)

    def test_hex_to_decimal(self):
        self.assertEqual(base_to_dec("FF", 16)["result"]["value"], 255)

    def test_digit_too_large_for_base(self):
        self.assertFalse(base_to_dec("102", 2)["ok"])

    def test_bad_character(self):
        self.assertFalse(base_to_dec("1G0", 16)["ok"])

    def test_empty(self):
        self.assertFalse(base_to_dec("", 2)["ok"])


class TestStepsShape(unittest.TestCase):
    def test_steps_have_title_and_detail(self):
        for fn in (lambda: dec_to_base(78, 2), lambda: base_to_dec("1010", 2)):
            for step in fn()["steps"]:
                self.assertIn("title", step)
                self.assertIn("detail", step)


if __name__ == "__main__":
    unittest.main(verbosity=2)
