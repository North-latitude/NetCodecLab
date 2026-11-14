"""信道批量实验：同一随机种子可复现的错误注入与方案统计。"""

import math
import random

from app.common.bits import normalize_bits

from . import checksum, crc, hamming, matrix, parity

SCHEME_LABELS = {
    "parity": "一维奇偶校验",
    "matrix": "二维奇偶校验",
    "crc": "CRC-16/CCITT",
    "inet": "Internet 校验和",
    "hamming": "汉明码（7,4）",
}
SCHEME_KEYS = tuple(SCHEME_LABELS)
CRC_PRESET = "CRC-16/CCITT"
MAX_RUNS = 2000
MAX_FLIPS = 8


def _step(title: str, detail: str) -> dict:
    return {"title": title, "detail": detail}


def bits_to_bytes(data: str) -> bytes:
    padding = (-len(data)) % 8
    padded = data + "0" * padding
    return bytes(
        int(padded[index:index + 8], 2)
        for index in range(0, len(padded), 8)
    )


def build_frames(data: str) -> dict:
    """构造五种发送帧，供单次仿真与批量实验共用。"""
    side = math.ceil(math.sqrt(len(data)))
    matrix_response = matrix.matrix_encode(
        data + "0" * (side * side - len(data)), side, side,
    )
    inet_response = checksum.checksum_frame(bits_to_bytes(data).ljust(2, b"\x00"))
    return {
        "parity": {
            "frame": parity.parity_encode(data, parity.MODE_EVEN)["result"]["frame"],
        },
        "matrix": {
            "frame": matrix_response["result"]["frame"],
            "rows": side,
            "cols": side,
        },
        "crc": {
            "frame": crc.crc_encode(data, preset=CRC_PRESET)["result"]["frame"],
        },
        "inet": {
            "frame": inet_response["result"]["frame_bits"],
        },
        "hamming": {
            "frame": hamming.hamming_encode(data)["result"]["frame"],
        },
    }


def _evaluate(key: str, record: dict, received: str) -> dict:
    if key == "parity":
        response = parity.parity_check(received, parity.MODE_EVEN)
        detected = response["ok"] and bool(response["detected"])
        corrected = False
    elif key == "matrix":
        cols = record["cols"] + 1
        rows = record["rows"] + 1
        grid = [list(received[row * cols:(row + 1) * cols]) for row in range(rows)]
        response = matrix.matrix_check(grid, matrix.MODE_EVEN)
        detected = response["ok"] and bool(response["detected"])
        corrected = bool(response.get("corrected"))
    elif key == "crc":
        response = crc.crc_check(received, preset=CRC_PRESET)
        detected = response["ok"] and bool(response["detected"])
        corrected = False
    elif key == "inet":
        response = checksum.inet_verify(bits_to_bytes(received))
        detected = response["ok"] and bool(response["detected"])
        corrected = False
    else:
        response = hamming.hamming_decode(received)
        detected = response["ok"] and bool(response["detected"])
        corrected = detected
    return {"detected": detected, "corrected": corrected}


def _simulate(records: dict, runs: int, flips: int, seed: int) -> dict:
    rng = random.Random(seed)
    stats = {
        key: {
            "frame_length": len(records[key]["frame"]),
            "detected": 0,
            "corrected": 0,
            "missed": 0,
        }
        for key in SCHEME_KEYS
    }
    for _ in range(runs):
        for key in SCHEME_KEYS:
            frame = records[key]["frame"]
            count = min(flips, len(frame))
            positions = rng.sample(range(len(frame)), count)
            bits = list(frame)
            for position in positions:
                bits[position] = "1" if bits[position] == "0" else "0"
            outcome = _evaluate(key, records[key], "".join(bits))
            if outcome["detected"]:
                stats[key]["detected"] += 1
                if outcome["corrected"]:
                    stats[key]["corrected"] += 1
            else:
                stats[key]["missed"] += 1
    return stats


def batch_experiment(data: str, runs: int = 200, flips: int = 1,
                     seed: int = 2026) -> dict:
    """用同一随机种子跑两遍相同的批量实验，校验结果是否完全一致。"""
    try:
        bits = normalize_bits(data)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [],
                "message": str(exc)}
    if not bits:
        return {"ok": False, "result": None, "steps": [],
                "message": "请先输入要参与实验的二进制数据。"}
    if not 1 <= runs <= MAX_RUNS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"实验次数请填 1～{MAX_RUNS}。"}
    if not 0 <= flips <= MAX_FLIPS:
        return {"ok": False, "result": None, "steps": [],
                "message": f"每次翻转位数请填 0～{MAX_FLIPS}。"}

    records = build_frames(bits)
    first = _simulate(records, runs, flips, seed)
    second = _simulate(records, runs, flips, seed)
    reproducible = first == second
    fingerprint = "|".join(
        f"{key}:{first[key]['detected']}/{first[key]['corrected']}/{first[key]['missed']}"
        for key in SCHEME_KEYS
    )
    steps = [
        _step("固定随机种子", f"seed = {seed}，每次翻 {flips} 位，共跑 {runs} 次"),
        _step("第一次运行", "记录各方案的检出、纠正与漏检次数"),
        _step("第二次运行", "使用完全相同的种子与参数再跑一遍"),
        _step("结果比对",
              "两次统计完全一致，实验可复现" if reproducible
              else "两次统计不一致，实验不可复现"),
    ]
    return {
        "ok": True,
        "result": {
            "stats": first,
            "runs": runs,
            "flips": flips,
            "seed": seed,
            "reproducible": reproducible,
            "fingerprint": fingerprint,
        },
        "steps": steps,
        "message": (
            f"seed={seed} 跑 {runs} 次（每次 {flips} 位错误）："
            + ("两次结果完全一致" if reproducible else "两次结果不一致")
        ),
    }
