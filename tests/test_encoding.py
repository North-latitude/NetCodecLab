"""字符编码拆解单元测试（对应验收点 T-01、T-02、T-11）。

T-01：输入 ``Net`` -> 24 位位流。
T-02：输入 ``中文`` -> GBK 4 字节、UTF-8 6 字节。
T-11：空输入、超长输入要有提示且程序不退出（返回 ok=False）。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.common import config
from app.core.encoding import encode_text, text_to_bitstream


class TestEncodeText(unittest.TestCase):
    def test_t01_net_24_bits(self):
        result = encode_text("Net")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["total_utf8_bytes"], 3)
        self.assertEqual(result["result"]["total_utf8_bits"], 24)
        self.assertEqual(len(result["result"]["chars"]), 3)

    def test_t02_chinese_byte_counts(self):
        result = encode_text("中文")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["total_utf8_bytes"], 6)
        self.assertEqual(result["result"]["total_gbk_bytes"], 4)

    def test_code_point_fields(self):
        result = encode_text("A")
        char = result["result"]["chars"][0]
        self.assertEqual(char["code_point"], 65)
        self.assertEqual(char["code_point_hex"], "U+0041")

    def test_emoji_gbk_fails_but_utf8_ok(self):
        result = encode_text("😀")
        self.assertTrue(result["ok"])
        self.assertIsNone(result["result"]["chars"][0]["gbk"]["bytes"])
        self.assertIsNotNone(result["result"]["chars"][0]["utf8"]["bytes"])
        self.assertIn("😀", result["result"]["gbk_failed_chars"])

    def test_t11_empty_input(self):
        self.assertFalse(encode_text("")["ok"])

    def test_t11_too_long_input(self):
        long_text = "中" * (config.MAX_INPUT_CHARS + 1)
        result = encode_text(long_text)
        self.assertFalse(result["ok"])
        self.assertIn("上限", result["message"])

    def test_bad_encoding_rejected(self):
        self.assertFalse(encode_text("abc", primary="latin1")["ok"])


class TestBitstream(unittest.TestCase):
    def test_net_utf8_bitstream(self):
        result = text_to_bitstream("Net", "utf-8")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["byte_count"], 3)
        self.assertEqual(len(result["result"]["bits"]), 24)

    def test_gbk_bitstream_for_chinese(self):
        result = text_to_bitstream("中文", "gbk")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["byte_count"], 4)

    def test_empty_and_too_long(self):
        self.assertFalse(text_to_bitstream("")["ok"])
        self.assertFalse(text_to_bitstream("x" * (config.MAX_INPUT_CHARS + 1))["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
