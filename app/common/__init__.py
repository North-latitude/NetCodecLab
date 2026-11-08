"""公共层：位串工具与全局常量。

这一层只放“多个模块都要用、但不属于任何一种校验算法”的东西，
任何页面或算法都可以 import，且不依赖 Tkinter。
"""

from . import bits  # noqa: F401
from . import config  # noqa: F401

__all__ = ["bits", "config"]
