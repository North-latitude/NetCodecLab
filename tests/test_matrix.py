"""二维奇偶校验的单元测试（对应验收点 3.2）。

验收标准：
    任翻 1 位都能定位到行列交叉点并改回来；2 位错误只报“无法纠正”，不要瞎改。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.matrix import matrix_check, matrix_encode, matrix_frame_to_text

DATA = "1011001101010101"


class TestMatrixEncode(unittest.TestCase):
    def setUp(self):
        self.encoded = matrix_encode(DATA, 4, 4)
        self.matrix = self.encoded["result"]["matrix"]

    def test_shape(self):
        self.assertTrue(self.encoded["ok"])
        self.assertEqual(len(self.matrix), 5)       # 4 行数据 + 1 行列校验
        self.assertEqual(len(self.matrix[0]), 5)    # 4 列数据 + 1 行行校验
        self.assertEqual(len(self.encoded["result"]["frame"]), 25)

    def test_every_row_has_even_ones(self):
        for row in self.matrix:
            self.assertEqual(row.count("1") % 2, 0, f"行 {row} 的 1 的个数不是偶数")

    def test_frame_to_text(self):
        text = matrix_frame_to_text(self.encoded["result"]["frame"], 4, 4)
        self.assertEqual(len(text.splitlines()), 5)

    def test_odd_mode(self):
        encoded = matrix_encode(DATA, 4, 4, "odd")
        for row in encoded["result"]["matrix"]:
            self.assertEqual(row.count("1") % 2, 1)


class TestMatrixCheck(unittest.TestCase):
    def setUp(self):
        self.encoded = matrix_encode(DATA, 4, 4)
        self.matrix = self.encoded["result"]["matrix"]

    def test_clean_matrix_passes(self):
        self.assertFalse(matrix_check(self.matrix)["detected"])

    def test_every_data_bit_can_be_located_and_corrected(self):
        """这是二维奇偶校验的核心验收：任意 1 位都能定位并还原。"""
        for row in range(4):
            for col in range(4):
                broken = [r[:] for r in self.matrix]
                broken[row][col] = "1" if broken[row][col] == "0" else "0"
                result = matrix_check(broken)
                self.assertTrue(result["detected"], f"({row},{col}) 未被检出")
                self.assertEqual(result["error_pos"], (row, col),
                                 f"({row},{col}) 定位错误")
                self.assertEqual(result["corrected"], self.matrix,
                                 f"({row},{col}) 纠正后与原始方阵不一致")

    def test_parity_bit_error_is_reported(self):
        """校验位本身被翻时，交叉点落在校验区，只改校验位不动数据。"""
        broken = [r[:] for r in self.matrix]
        broken[0][4] = "1" if broken[0][4] == "0" else "0"   # 第 1 行的行校验位
        result = matrix_check(broken)
        self.assertTrue(result["detected"])
        self.assertEqual(result["error_pos"], (0, 4))
        self.assertTrue(result["result"]["error_in_parity"])

    def test_corner_bit_error(self):
        broken = [r[:] for r in self.matrix]
        broken[4][4] = "1" if broken[4][4] == "0" else "0"
        result = matrix_check(broken)
        self.assertTrue(result["detected"])
        self.assertEqual(result["error_pos"], (4, 4))

    def test_two_bit_errors_are_not_corrected(self):
        broken = [r[:] for r in self.matrix]
        broken[0][0] = "1" if broken[0][0] == "0" else "0"
        broken[2][3] = "1" if broken[2][3] == "0" else "0"
        result = matrix_check(broken)
        self.assertTrue(result["detected"])
        self.assertIsNone(result["corrected"])
        self.assertIn("无法纠正", result["message"])

    def test_two_errors_in_same_row(self):
        broken = [r[:] for r in self.matrix]
        broken[1][0] = "1" if broken[1][0] == "0" else "0"
        broken[1][2] = "1" if broken[1][2] == "0" else "0"
        result = matrix_check(broken)
        self.assertIsNone(result["corrected"])


class TestMatrixErrors(unittest.TestCase):
    def test_size_mismatch(self):
        self.assertFalse(matrix_encode("101", 4, 4)["ok"])

    def test_zero_rows(self):
        self.assertFalse(matrix_encode("1010", 0, 4)["ok"])

    def test_illegal_cell(self):
        result = matrix_check([["1", "0"], ["0", "2"]])
        self.assertFalse(result["ok"])

    def test_ragged_matrix(self):
        result = matrix_check([["1", "0"], ["0"]])
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
