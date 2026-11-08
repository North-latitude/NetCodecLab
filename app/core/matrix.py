"""二维奇偶校验：把数据排成方阵，行、列各补 1 位校验。

一维奇偶校验只能报“出错了”，二维奇偶能把错误**定位到行列交叉点**并纠正。
代价是要多发 `rows + cols + 1` 位校验位。

已知局限：**多位错误只能检出、不能纠正**。当两行两列同时报错时，
交叉点有两个或四个，分不清哪一个是真错位，所以只报告“无法纠正”，绝不猜。
"""

from __future__ import annotations

from ..common.bits import count_ones, normalize_bits

MODE_EVEN = "even"
MODE_ODD = "odd"
MODE_NAMES = {MODE_EVEN: "偶校验", MODE_ODD: "奇校验"}


def _step(title: str, detail: str) -> dict:
    """统一步骤结构，界面的步骤表直接吃这个格式。"""
    return {"title": title, "detail": detail}


def _check_mode(mode: str) -> str:
    if mode not in MODE_NAMES:
        raise ValueError(f"mode 只能是 'even' 或 'odd'，收到 {mode!r}")
    return mode


def parity_bit_for(data_bits: str, mode: str = MODE_EVEN) -> str:
    """算出一段位串应该补的校验位（这里被二维方阵复用来算行列校验）。"""
    _check_mode(mode)
    ones = count_ones(data_bits)
    need_odd = mode == MODE_ODD
    return "1" if ((ones % 2 == 1) != need_odd) else "0"


def matrix_encode(data: str, rows: int, cols: int, mode: str = MODE_EVEN) -> dict:
    """把数据按行优先排成 rows×cols 方阵，并补上行列校验位。

    返回的 matrix 是 (rows+1) 行 × (cols+1) 列：最后一行是列校验，
    最后一列是行校验，右下角是前面行列校验位再算一次的“总校验位”。

    {ok, result: {matrix, rows, cols, row_parity, col_parity, frame}, steps, message}
    """
    try:
        bits = normalize_bits(data)
        _check_mode(mode)
    except ValueError as exc:
        return {"ok": False, "result": None, "steps": [], "message": str(exc)}

    if rows <= 0 or cols <= 0:
        return {"ok": False, "result": None, "steps": [],
                "message": "行数和列数都必须是正整数"}
    if rows * cols != len(bits):
        return {"ok": False, "result": None, "steps": [],
                "message": f"{len(bits)} 位数据排不满 {rows}×{cols} 的方阵"
                           f"（需要 {rows * cols} 位），请调整行列或数据长度"}

    grid = [[bits[r * cols + c] for c in range(cols)] for r in range(rows)]
    row_parity = []
    col_parity = []
    for r in range(rows):
        row_parity.append(parity_bit_for("".join(grid[r]), mode))
    for c in range(cols):
        col_parity.append(parity_bit_for("".join(grid[r][c] for r in range(rows)), mode))
    # 右下角：对行校验位再算一次列方向的校验位（等价于对列校验位算行方向）
    corner = parity_bit_for("".join(row_parity), mode)

    matrix = [row[:] + [row_parity[r]] for r, row in enumerate(grid)]
    matrix.append(col_parity + [corner])
    frame = "".join("".join(r) for r in matrix)

    steps = [
        _step("排成方阵", f"把 {len(bits)} 位数据按行优先排成 {rows} 行 × {cols} 列"),
        _step("补行校验", f"每行末尾补 1 位，{MODE_NAMES[mode]}：{' '.join(row_parity)}"),
        _step("补列校验", f"每列末尾补 1 位，{' '.join(col_parity)}"),
        _step("补总校验位", f"右下角 = 对行校验位再算一次 = {corner}"),
        _step("组帧", f"得到 {rows + 1}×{cols + 1} 方阵，共 {len(frame)} 位"),
    ]
    return {
        "ok": True,
        "result": {
            "matrix": matrix,
            "rows": rows,
            "cols": cols,
            "row_parity": row_parity,
            "col_parity": col_parity,
            "frame": frame,
        },
        "steps": steps,
        "message": f"二维奇偶：{rows}×{cols} 数据 + 行列校验，整帧 {len(frame)} 位",
    }


def matrix_check(matrix: list[list[str]], mode: str = MODE_EVEN) -> dict:
    """接收端：用行、列校验位定位 1 位错误并纠正。

    返回 {ok, detected, error_pos, corrected, result, steps, message}
    error_pos 为 (行, 列) 下标元组（原始数据区坐标），无法定位时为 None。
    """
    try:
        _check_mode(mode)
    except ValueError as exc:
        return {"ok": False, "detected": False, "error_pos": None,
                "corrected": None, "steps": [], "message": str(exc)}

    try:
        grid = [list(str(cell) for cell in row) for row in matrix]
    except TypeError:
        return {"ok": False, "detected": False, "error_pos": None, "corrected": None,
                "steps": [], "message": "matrix 必须是二维列表"}

    height = len(grid)
    width = len(grid[0]) if height else 0
    if height < 2 or width < 2:
        return {"ok": False, "detected": False, "error_pos": None, "corrected": None,
                "steps": [], "message": "方阵至少要有 1 行 1 列数据 + 校验位"}
    if any(len(row) != width for row in grid):
        return {"ok": False, "detected": False, "error_pos": None, "corrected": None,
                "steps": [], "message": "方阵每一行的长度必须相同"}
    for row in grid:
        for cell in row:
            if cell not in ("0", "1"):
                return {"ok": False, "detected": False, "error_pos": None,
                        "corrected": None, "steps": [],
                        "message": f"方阵里只能有 0/1，发现 {cell!r}"}

    want_odd = mode == MODE_ODD
    bad_rows = []
    bad_cols = []
    for r in range(height):
        ones = grid[r].count("1")
        if (ones % 2 == 1) != want_odd:
            bad_rows.append(r)
    for c in range(width):
        ones = sum(1 for r in range(height) if grid[r][c] == "1")
        if (ones % 2 == 1) != want_odd:
            bad_cols.append(c)

    steps = [_step("逐行复核", f"1 的个数不符合{MODE_NAMES[mode]}的行：{bad_rows or '无'}"),
             _step("逐列复核", f"1 的个数不符合{MODE_NAMES[mode]}的列：{bad_cols or '无'}")]

    detected = bool(bad_rows or bad_cols)
    error_pos = None
    corrected = None
    result_matrix = [row[:] for row in grid]

    if not detected:
        steps.append(_step("判定", "行、列校验全部通过，判定数据未损坏"))
        return {"ok": True, "detected": False, "error_pos": None,
                "corrected": None, "result": {"matrix": result_matrix},
                "steps": steps, "message": "校验通过：未检出错误"}

    if len(bad_rows) == 1 and len(bad_cols) == 1:
        r, c = bad_rows[0], bad_cols[0]
        # 交叉点落在校验位区域时，说明错的是校验位本身，数据位没错
        if r == height - 1 or c == width - 1:
            steps.append(_step("定位", f"交叉点在第 {r + 1} 行第 {c + 1} 列，位于校验位区域，"
                                       "判定为校验位本身出错（数据位无误）"))
            result_matrix[r][c] = "1" if result_matrix[r][c] == "0" else "0"
            return {"ok": True, "detected": True, "error_pos": (r, c),
                    "corrected": result_matrix,
                    "result": {"matrix": result_matrix, "error_in_parity": True},
                    "steps": steps,
                    "message": f"检出错误：第 {r + 1} 行第 {c + 1} 列（校验位区），已纠正"}
        result_matrix[r][c] = "1" if result_matrix[r][c] == "0" else "0"
        error_pos = (r, c)
        steps.append(_step("定位", f"只有第 {r + 1} 行和第 {c + 1} 列同时报错，"
                                   f"交叉点 ({r + 1}, {c + 1}) 就是出错位"))
        steps.append(_step("纠正", f"把第 {r + 1} 行第 {c + 1} 列的 {grid[r][c]} 取反为 "
                                   f"{result_matrix[r][c]}，数据恢复"))
        return {"ok": True, "detected": True, "error_pos": error_pos,
                "corrected": result_matrix,
                "result": {"matrix": result_matrix, "error_in_parity": False},
                "steps": steps,
                "message": f"检出并纠正 1 位错误：第 {r + 1} 行第 {c + 1} 列"}

    steps.append(_step("判定", f"{len(bad_rows)} 行、{len(bad_cols)} 列同时报错，"
                               "存在多个错误交叉点，无法唯一确定出错位"))
    steps.append(_step("处理", "按 2 位及以上错误处理：只报告“无法纠正”，不擅自修改数据"))
    return {"ok": True, "detected": True, "error_pos": None,
            "corrected": None,
            "result": {"matrix": grid, "bad_rows": bad_rows, "bad_cols": bad_cols},
            "steps": steps,
            "message": "检出错误，但错误位不唯一（疑似多位错误），无法纠正"}


def matrix_frame_to_text(frame: str, rows: int, cols: int) -> str:
    """把一维位串按 (rows+1)×(cols+1) 还原成多行文本，方便界面展示方阵。"""
    width = cols + 1
    lines = [frame[i:i + width] for i in range(0, len(frame), width)]
    return "\n".join(lines)

