"""信道模拟器单元测试（对应验收点 T-09、T-10、T-11）。

T-09：在帧的第 3 位（下标 2）注入错误，方案应判为“检出”。
T-10：批量实验同一 seed 跑两次，结果完全一致。
T-11：空数据、非法位串返回 ok=False，不抛异常。
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.channel import SCHEMES, batch_compare, compare_schemes, inject_error


class TestInjectError(unittest.TestCase):
    def test_flip_target_position(self):
        result = inject_error("1011001", 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["flipped_positions"], [2])
        # 下标 2 原来是 1，翻成 0
        self.assertEqual(result["result"]["corrupted"], "1001001")

    def test_duplicate_position_flips_once(self):
        result = inject_error("1011001", [2, 2])
        self.assertEqual(result["result"]["flipped_positions"], [2])

    def test_out_of_range_rejected(self):
        self.assertFalse(inject_error("101", 5)["ok"])

    def test_empty_bits_rejected(self):
        self.assertFalse(inject_error("", 0)["ok"])

    def test_no_injection_keeps_frame(self):
        result = inject_error("1011", None)
        self.assertEqual(result["result"]["corrupted"], "1011")
        self.assertEqual(result["result"]["flipped_positions"], [])


class TestCompareSchemes(unittest.TestCase):
    DATA = "1011001"

    def test_t09_third_bit_detected_by_parity(self):
        result = compare_schemes(self.DATA, positions=2)
        self.assertTrue(result["ok"])
        by_key = {s["key"]: s for s in result["result"]["schemes"]}
        self.assertTrue(by_key["parity"]["detected"])
        self.assertEqual(result["result"]["injected_positions"], [2])

    def test_clean_baseline_all_pass(self):
        result = compare_schemes(self.DATA)
        for scheme in result["result"]["schemes"]:
            self.assertFalse(scheme["detected"], f"{scheme['name']} 干净帧不应报错")

    def test_all_five_schemes_present(self):
        result = compare_schemes(self.DATA)
        self.assertEqual({s["key"] for s in result["result"]["schemes"]}, set(SCHEMES))

    def test_empty_data_rejected(self):
        self.assertFalse(compare_schemes("")["ok"])

    def test_illegal_bits_rejected(self):
        self.assertFalse(compare_schemes("102")["ok"])

    def test_unknown_scheme_rejected(self):
        result = compare_schemes(self.DATA, scheme_keys=["nonexistent"])
        self.assertFalse(result["ok"])


class TestBatchReproducible(unittest.TestCase):
    def test_t10_same_seed_same_result(self):
        first = batch_compare("1011001", runs=60, error_rate=0.1, seed=2026)
        second = batch_compare("1011001", runs=60, error_rate=0.1, seed=2026)
        self.assertTrue(first["ok"])
        self.assertEqual(first["result"], second["result"])

    def test_stats_shape(self):
        result = batch_compare("1011001", runs=30, error_rate=0.2, seed=1)
        stats = result["result"]["stats"]
        for key in SCHEMES:
            stat = stats[key]
            self.assertEqual(stat["detected"] + stat["missed"], 30)
            self.assertIn("detection_rate", stat)

    def test_bad_parameters_rejected(self):
        self.assertFalse(batch_compare("101", runs=0)["ok"])
        self.assertFalse(batch_compare("101", error_rate=1.5)["ok"])
        self.assertFalse(batch_compare("")["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
