"""信道模拟器：错误注入、五种校验方案横向对比、批量可复现统计。

对应信道模拟器页面。思路（与需求文档 R-2 一致）：数据位流 -> 各方案组帧 ->
在帧上指定位翻转 -> 复用算法层的 ``*_check`` 判定是否检出。本模块只做
“编排 + 对比 + 统计”，不重写任何校验算法。

- 单次：``inject_error`` 注入错误；``compare_schemes`` 跑五种方案对比。
- 批量：``batch_compare`` 用固定随机种子反复抽样，同一 seed 两次结果完全一致。

返回结构仍为 ``{ok, result, steps, message}``，纯函数、不依赖 Tkinter。
"""

from __future__ import annotations

import math
import random

from ..common import config
from ..common.bits import flip_bit, normalize_bits
from . import checksum, crc, hamming, matrix, parity

# 方案标识 -> 界面中文名。顺序即界面展示顺序。
SCHEMES: dict[str, str] = {
    "parity": "一维奇偶校验",
    "matrix": "二维奇偶校验",
    "crc": "CRC-16/CCITT",
    "inet": "Internet 校验和",
    "hamming": "汉明码 (7,4)",
}

CRC_PRESET = "CRC-16/CCITT"


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def _clean_positions(positions, length: int) -> list[int]:
    """规范化翻转下标：去重、排序、校验范围；非法时抛 ValueError。"""
    if positions is None:
        return []
    if isinstance(positions, int):
        positions = [positions]
    cleaned = sorted({int(p) for p in positions})
    for p in cleaned:
        if not 0 <= p < length:
            raise IndexError(f"位下标 {p} 超出范围 0..{length - 1}")
    return cleaned


def inject_error(bits: str, positions) -> dict:
    """在帧的指定位置注入比特翻转（下标从 0 开始，界面显示时 +1）。

    返回 {ok, result: {original, corrupted, flipped_positions, corrupted_bits},
          steps, message}。重复出现的同一位置只翻转一次（翻两次等于没翻）。
    """
    try:
        original = normalize_bits(bits)
        target = _clean_positions(positions, len(original))
    except (ValueError, IndexError) as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    corrupted = original
    for p in target:
        corrupted = flip_bit(corrupted, p)

    steps = [_step("原始帧", f"长度 {len(original)} 位：{original}")]
    if target:
        desc = "、".join(f"第 {p + 1} 位（下标 {p}）" for p in target)
        steps.append(_step("注入错误", f"翻转 {desc}"))
        steps.append(_step("受损帧", f"翻转后：{corrupted}"))
    else:
        steps.append(_step("未注入错误", "本次不翻转任何位，作为干净帧基线"))

    return {
        "ok": True,
        "result": {"original": original, "corrupted": corrupted,
                   "flipped_positions": target, "corrupted_bits": corrupted},
        "steps": steps,
        "message": ("已翻转 " + "、".join(str(p + 1) for p in target) + " 位" if target
                    else "干净帧，未注入错误"),
    }


# --------------------------------------------------------------------------- #
# 各方案的“组帧 / 判定”适配。输入统一是数据位串，输出干净帧与判定结果。
# --------------------------------------------------------------------------- #
def _build_parity(data: str) -> dict:
    enc = parity.parity_encode(data, "even")
    return {"frame": enc["result"]["frame"], "data_len": len(data),
            "check": lambda frame: parity.parity_check(frame, "even")}


def _build_matrix(data: str) -> dict:
    side = max(1, math.ceil(math.sqrt(len(data))))
    padded, padding = _pad(data, side * side)
    enc = matrix.matrix_encode(padded, side, side, "even")
    width = side + 1

    def _check(frame: str) -> dict:
        grid = [list(frame[i:i + width]) for i in range(0, len(frame), width)]
        return matrix.matrix_check(grid, "even")

    return {"frame": enc["result"]["frame"], "side": side, "padding": padding,
            "check": _check}


def _build_crc(data: str) -> dict:
    enc = crc.crc_encode(data, preset=CRC_PRESET)
    data_len = len(data)
    return {"frame": enc["result"]["frame"], "data_len": data_len,
            "check": lambda frame: crc.crc_check(frame, preset=CRC_PRESET,
                                                 data_len=data_len)}


def _build_inet(data: str) -> dict:
    # Internet 校验和按 16 位字处理，数据不足 2 字节时尾部补 0 对齐，
    # 保证“数据 + 2 字节校验和”满足接收端至少 4 字节的要求。
    padded = data.ljust(max(len(data), 16), "0")
    data_bytes = checksum.frame_bits_to_bytes(padded)
    enc = checksum.checksum_frame(data_bytes)
    frame_bits = enc["result"]["frame_bits"]

    def _check(frame: str) -> dict:
        received = checksum.frame_bits_to_bytes(frame)
        return checksum.inet_verify(received)

    return {"frame": frame_bits, "check": _check}


def _build_hamming(data: str) -> dict:
    enc = hamming.hamming_encode(data)
    return {"frame": enc["result"]["frame"],
            "check": lambda frame: hamming.hamming_decode(frame)}


_BUILDERS = {
    "parity": _build_parity,
    "matrix": _build_matrix,
    "crc": _build_crc,
    "inet": _build_inet,
    "hamming": _build_hamming,
}


def _pad(bits: str, multiple: int) -> tuple[str, int]:
    remainder = len(bits) % multiple
    if remainder == 0:
        return bits, 0
    padding = multiple - remainder
    return bits + "0" * padding, padding


def compare_schemes(data_bits: str, positions=None, scheme_keys=None) -> dict:
    """对同一段数据跑五种方案：各自组帧 -> 注入错误 -> 判定是否检出。

    参数
    ----
    data_bits: 数据位串（0/1）。
    positions: 要翻转的下标列表（0 起）；None 表示不注入（干净基线）。
    scheme_keys: 只跑指定方案；None 表示五种全跑。

    返回
    ----
    {ok, result: {data, injected_positions, schemes: [...]}, steps, message}
    每个 scheme 项：{key, name, ok, frame, corrupted, detected, message}。
    """
    try:
        data = normalize_bits(data_bits)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}
    if not data:
        return {"ok": False, "result": None, "steps": [], "message": "数据位串为空，无法组帧"}
    if len(data) > config.MAX_FRAME_BITS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"数据超过帧长上限 {config.MAX_FRAME_BITS} 位，当前 {len(data)} 位"}

    keys = list(scheme_keys) if scheme_keys else list(SCHEMES)
    unknown = [k for k in keys if k not in _BUILDERS]
    if unknown:
        return {"ok": False, "result": None, "steps": [],
                "message": "未知方案：" + "、".join(unknown)}

    schemes_out: list[dict] = []
    steps: list[dict] = [_step("准备数据", f"数据 {data}，共 {len(data)} 位")]

    injected: list[int] = []
    for key in keys:
        try:
            built = _BUILDERS[key](data)
            frame = built["frame"]
            injected = _clean_positions(positions, len(frame))
            corrupted = frame
            for p in injected:
                corrupted = flip_bit(corrupted, p)
            verdict = built["check"](corrupted)
            detected = bool(verdict.get("detected", False))
            ok = bool(verdict.get("ok", True))
            schemes_out.append({
                "key": key,
                "name": SCHEMES[key],
                "ok": ok,
                "frame": frame,
                "corrupted": corrupted,
                "detected": detected,
                "message": verdict.get("message", ""),
            })
            state = "检出错误" if detected else ("校验通过" if ok else "方案执行失败")
            steps.append(_step(SCHEMES[key], f"帧长 {len(frame)} 位 -> {state}；{verdict.get('message', '')}"))
        except (ValueError, IndexError) as exc:
            schemes_out.append({
                "key": key, "name": SCHEMES[key], "ok": False,
                "frame": None, "corrupted": None, "detected": False,
                "message": str(exc),
            })
            steps.append(_step(SCHEMES[key], f"执行失败：{exc}"))

    detected_count = sum(1 for s in schemes_out if s["detected"])
    return {
        "ok": True,
        "result": {"data": data, "injected_positions": injected, "schemes": schemes_out},
        "steps": steps,
        "message": (f"注入 {len(injected)} 位错误，{detected_count}/{len(schemes_out)} 种方案检出")
                   if injected else f"干净基线：{len(schemes_out)} 种方案全部通过",
    }


def batch_compare(data_bits: str, runs: int | None = None,
                  error_rate: float | None = None, seed: int | None = None) -> dict:
    """批量实验：按固定种子随机翻转若干位，统计各方案检出率。

    同一 ``seed`` 跑两次，随机序列与统计结果完全一致（验收点 T-10）。

    返回
    ----
    {ok, result: {runs, seed, error_rate, stats: {key: {name, detected, missed,
      detection_rate}}}, steps, message}
    """
    try:
        data = normalize_bits(data_bits)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}
    if not data:
        return {"ok": False, "result": None, "steps": [], "message": "数据位串为空，无法批量实验"}

    runs = config.DEFAULT_BATCH_RUNS if runs is None else runs
    error_rate = config.DEFAULT_ERROR_RATE if error_rate is None else error_rate
    seed = config.DEFAULT_BATCH_SEED if seed is None else seed

    if not isinstance(runs, int) or runs <= 0:
        return {"ok": False, "result": None, "steps": [], "message": "实验次数必须是正整数"}
    if runs > config.MAX_BATCH_RUNS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"实验次数超过上限 {config.MAX_BATCH_RUNS}"}
    if not 0.0 <= error_rate <= 1.0:
        return {"ok": False, "result": None, "steps": [], "message": "错误率必须在 0.0 ~ 1.0 之间"}

    # 先把五种方案的干净帧与判定闭包建好（数据固定，帧只建一次）。
    built: dict[str, dict] = {}
    for key in SCHEMES:
        built[key] = _BUILDERS[key](data)

    rng = random.Random(seed)
    stats: dict[str, dict] = {
        key: {"name": SCHEMES[key], "detected": 0, "missed": 0} for key in SCHEMES
    }

    for _ in range(runs):
        for key, item in built.items():
            frame = item["frame"]
            positions = [i for i in range(len(frame)) if rng.random() < error_rate]
            corrupted = frame
            for p in positions:
                corrupted = flip_bit(corrupted, p)
            verdict = item["check"](corrupted)
            if verdict.get("detected"):
                stats[key]["detected"] += 1
            else:
                stats[key]["missed"] += 1

    steps = [
        _step("实验参数", f"种子 seed = {seed}，重复 {runs} 轮，每比特错误率 {error_rate}"),
        _step("抽样方式", "每轮对帧上每个比特独立按错误率决定是否翻转，再交给各方案判定"),
    ]
    for key in SCHEMES:
        stat = stats[key]
        rate = stat["detected"] / runs
        stat["detection_rate"] = round(rate, 4)
        steps.append(_step(SCHEMES[key],
                            f"检出 {stat['detected']} 次，漏检 {stat['missed']} 次，"
                            f"检出率 {rate:.1%}"))

    return {
        "ok": True,
        "result": {"runs": runs, "seed": seed, "error_rate": error_rate, "stats": stats},
        "steps": steps,
        "message": f"批量 {runs} 轮（seed={seed}，错误率 {error_rate}）完成，结果可复现",
    }
