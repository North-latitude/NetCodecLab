"""全项目共享的常量。

这些值会被算法层和界面层同时引用，集中在这里避免两边写死不同的数字
（本项目真的吃过这个亏：界面按 8 位显示、算法按 7 位算，结果对不上）。
"""

from __future__ import annotations

# 每个字节固定 8 位
BITS_PER_BYTE = 8

# 默认字符集：编码工坊与纠错演示都以 UTF-8 为准，GBK 作为对比项
DEFAULT_ENCODING = "utf-8"  # 统一 UTF-8，GBK 编不了 emoji

# 一次最多处理的字符数，防止把界面卡死
MAX_INPUT_CHARS = 200

# 信道模拟器允许的最大帧长（位）
MAX_FRAME_BITS = 512

# 批量实验允许的最大次数
MAX_BATCH_RUNS = 20000

# 批量实验的默认参数（同一 seed 可复现）
DEFAULT_BATCH_RUNS = 1000
DEFAULT_ERROR_RATE = 0.01
DEFAULT_BATCH_SEED = 2026
