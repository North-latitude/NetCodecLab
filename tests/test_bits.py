"""位串工具的单元测试。所有算法都依赖它，单独测一遍。

运行方式（在项目根目录）：
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common.bits import (
    bitstr_to_bytes,
    bytes_to_bitstr,
    count_ones,
    flip_bit,
    group_bits,
    normalize_bits,
    pad_to_multiple,
)


class TestNormalize(unittest.TestCase):
    def test_strip_spaces_and_underscores(self):
        self.assertEqual(normalize_bits("1010 0101"), "10100101")
        self.assertEqual(normalize_bits("1010_0101"), "10100101")
        self.assertEqual(normalize_bits(" 1010|0101 "), "10100101")

    def test_reject_illegal_characters(self):
        with self.assertRaises(ValueError):
            normalize_bits("1012")
        with self.assertRaises(ValueError):
            normalize_bits("   ")


class TestConvert(unittest.TestCase):
    def test_bitstr_round_trip(self):
        data = "Net".encode("utf-8")
        self.assertEqual(bitstr_to_bytes(bytes_to_bitstr(data)), data)

    def test_each_byte_is_eight_bits(self):
        self.assertEqual(bytes_to_bitstr(b"\x4e"), "01001110")

    def test_count_ones(self):
        self.assertEqual(count_ones("1011001"), 4)

    def test_group_bits(self):
        self.assertEqual(group_bits("01001110"), "0100 1110")

    def test_pad_to_multiple(self):
        self.assertEqual(pad_to_multiple("1011", 4), ("1011", 0))
        self.assertEqual(pad_to_multiple("101", 4), ("1010", 1))

    def test_flip_bit(self):
        self.assertEqual(flip_bit("1011", 0), "0011")
        self.assertEqual(flip_bit("1011", 3), "1010")
        with self.assertRaises(IndexError):
            flip_bit("1011", 9)

    def test_wrong_length_bytes(self):
        with self.assertRaises(ValueError):
            bitstr_to_bytes("101")


if __name__ == "__main__":
    unittest.main(verbosity=2)
