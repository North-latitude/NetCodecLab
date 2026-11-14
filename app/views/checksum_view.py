"""校验实验室页面。"""

import math
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# 允许直接运行 app/views/checksum_view.py 进行页面预览。
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

from app.core import checksum, crc, hamming, matrix, parity
from app.common.theme import (
    COLOR_BACKGROUND,
    COLOR_ERROR,
    COLOR_PASS,
    COLOR_PRIMARY,
    FONT_FAMILY,
)

# 演示字号比公共主题大 1 磅，便于课堂投影查看。
FONT_NORMAL = (FONT_FAMILY, 11)
FONT_BOLD = (FONT_FAMILY, 11, "bold")


def _mix_colors(start, end, ratio):
    start = start.lstrip("#")
    end = end.lstrip("#")
    channels = []
    for index in (0, 2, 4):
        start_value = int(start[index:index + 2], 16)
        end_value = int(end[index:index + 2], 16)
        value = round(start_value + (end_value - start_value) * ratio)
        channels.append(f"{value:02X}")
    return "#" + "".join(channels)


def _rounded_rectangle(canvas, x1, y1, x2, y2, radius=6, **kwargs):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class ChecksumView(tk.Frame):
    """五种校验方案的发送、错误注入与接收判定可视化。"""

    SCHEMES = (
        "一维奇偶校验（偶）", "一维奇偶校验（奇）",
        "二维奇偶校验（偶）", "二维奇偶校验（奇）",
        "CRC-16/CCITT", "Internet 校验和", "汉明码（7,4）",
    )
    SCHEME_KEYS = {
        "一维奇偶校验（偶）": "parity",
        "一维奇偶校验（奇）": "parity",
        "二维奇偶校验（偶）": "matrix",
        "二维奇偶校验（奇）": "matrix",
        "CRC-16/CCITT": "crc",
        "Internet 校验和": "inet",
        "汉明码（7,4）": "hamming",
    }
    SCHEME_MODES = {
        "一维奇偶校验（偶）": "even",
        "一维奇偶校验（奇）": "odd",
        "二维奇偶校验（偶）": "even",
        "二维奇偶校验（奇）": "odd",
    }
    CRC_PRESET = "CRC-16/CCITT"

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg", COLOR_BACKGROUND)
        super().__init__(master, **kwargs)

        self.scheme_var = tk.StringVar(value="汉明码（7,4）")
        self.data_var = tk.StringVar(value="10110101")
        self.current = None
        self.received_bits = ""
        self.flipped_positions = set()
        self.receiver_data_bits = ""
        self.receiver_data_color = COLOR_PRIMARY
        self.step_title_labels = []
        self.step_value_labels = []
        self.step_description_labels = []

        self._build_hero()
        self._build_input_area()
        self._build_frame_area()
        self._build_analysis_area()
        self.generate_frame()

    def _build_hero(self):
        self.hero = tk.Canvas(
            self, height=132, bg="#0891B2", highlightthickness=0, bd=0,
        )
        self.hero.pack(fill="x", padx=24, pady=(20, 14))
        self.hero.bind("<Configure>", self._draw_hero)

    def _build_input_area(self):
        card = tk.Frame(
            self, bg="#FFFFFF", highlightbackground="#D5DDE9", highlightthickness=1,
        )
        card.pack(fill="x", padx=24, pady=(0, 14))
        tk.Frame(card, bg="#0891B2", height=3).pack(fill="x")

        row = tk.Frame(card, bg="#FFFFFF")
        row.pack(fill="x", padx=18, pady=(13, 6))
        tk.Label(
            row, text="校验方案", bg="#FFFFFF", fg="#334155", font=FONT_BOLD,
        ).pack(side="left")

        ttk.Style(self).theme_use("clam")
        self.scheme_box = ttk.Combobox(
            row,
            textvariable=self.scheme_var,
            values=self.SCHEMES,
            state="readonly",
            width=19,
            font=FONT_NORMAL,
        )
        self.scheme_box.pack(side="left", padx=(10, 16), ipady=3)
        self.scheme_box.bind(
            "<<ComboboxSelected>>", lambda event: self.generate_frame(),
        )

        tk.Label(
            row, text="数据输入", bg="#FFFFFF", fg="#334155", font=FONT_BOLD,
        ).pack(side="left")
        self.data_entry = tk.Entry(
            row,
            textvariable=self.data_var,
            bg="#F5F7FB",
            fg="#1E293B",
            insertbackground=COLOR_PRIMARY,
            font=("Consolas", 12),
            relief="solid",
            bd=1,
        )
        self.data_entry.pack(
            side="left", fill="x", expand=True, padx=(10, 12), ipady=5,
        )
        self.data_entry.bind("<Return>", lambda event: self.generate_frame())

        self.generate_button = tk.Button(
            row,
            text="生成发送帧",
            command=self.generate_frame,
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            font=FONT_BOLD,
            relief="flat",
            bd=0,
            padx=18,
            pady=7,
            cursor="hand2",
        )
        self.generate_button.pack(side="left")

        self.status_label = tk.Label(
            card,
            text="二进制位串；CRC 方案可输入 1～9 个 ASCII 字符（如 123456789）",
            bg="#FFFFFF",
            fg="#64748B",
            font=(FONT_FAMILY, 10),
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=18, pady=(0, 10))

    def _build_frame_area(self):
        card = tk.Frame(
            self, bg="#FFFFFF", highlightbackground="#D5DDE9", highlightthickness=1,
        )
        card.pack(fill="x", padx=24)

        header = tk.Frame(card, bg="#FFFFFF")
        header.pack(fill="x", padx=16, pady=(11, 4))
        tk.Label(
            header, text="帧传输可视化", bg="#FFFFFF", fg="#172033",
            font=(FONT_FAMILY, 12, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="蓝框为校验位 · 点击接收帧反转 · 红框为错误位",
            bg="#FFFFFF",
            fg="#8491A5",
            font=(FONT_FAMILY, 9),
        ).pack(side="right")

        sent_row = tk.Frame(card, bg="#FFFFFF")
        sent_row.pack(fill="x", padx=14)
        tk.Label(
            sent_row, text="发送帧", width=8, bg="#FFFFFF", fg="#475569",
            font=FONT_BOLD,
        ).pack(side="left")
        self.sent_canvas = tk.Canvas(
            sent_row, height=47, bg="#FFFFFF", highlightthickness=0, bd=0,
        )
        self.sent_canvas.pack(side="left", fill="x", expand=True)
        self.sent_canvas.bind("<Configure>", lambda event: self._draw_frames())

        received_row = tk.Frame(card, bg="#FFFFFF")
        received_row.pack(fill="x", padx=14, pady=(0, 9))
        tk.Label(
            received_row, text="接收帧", width=8, bg="#FFFFFF", fg="#475569",
            font=FONT_BOLD,
        ).pack(side="left")
        self.received_canvas = tk.Canvas(
            received_row, height=47, bg="#FFFFFF", highlightthickness=0, bd=0,
        )
        self.received_canvas.pack(side="left", fill="x", expand=True)
        self.received_canvas.bind("<Configure>", lambda event: self._draw_frames())

    def _build_analysis_area(self):
        section = tk.Frame(self, bg=COLOR_BACKGROUND)
        section.pack(fill="both", expand=True, padx=24, pady=(14, 20))
        section.rowconfigure(0, weight=1)
        section.columnconfigure(0, weight=3)
        section.columnconfigure(1, weight=2)

        process = tk.Frame(section, bg=COLOR_BACKGROUND)
        process.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        header = tk.Frame(process, bg=COLOR_BACKGROUND)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(
            header, text="计算步骤", bg=COLOR_BACKGROUND, fg="#172033",
            font=(FONT_FAMILY, 12, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="CALCULATION STEPS", bg=COLOR_BACKGROUND, fg="#94A3B8",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        cards = tk.Frame(process, bg=COLOR_BACKGROUND)
        cards.pack(fill="both", expand=True)
        colors = ("#6366F1", COLOR_PRIMARY, "#0891B2", COLOR_PASS)
        for index in range(4):
            row, column = divmod(index, 2)
            cards.rowconfigure(row, weight=1, uniform="process_rows")
            cards.columnconfigure(column, weight=1, uniform="process_columns")
            card = tk.Frame(
                cards, bg="#FFFFFF", highlightbackground="#D5DDE9",
                highlightthickness=1,
            )
            card.grid(
                row=row, column=column, sticky="nsew",
                padx=(0, 10) if column == 0 else (0, 0),
                pady=(0, 10) if row == 0 else (0, 0),
            )
            tk.Frame(card, bg=colors[index], height=3).pack(fill="x")

            card_header = tk.Frame(card, bg="#FFFFFF")
            card_header.pack(fill="x", padx=12, pady=(8, 5))
            number = tk.Canvas(
                card_header, width=25, height=25, bg="#FFFFFF",
                highlightthickness=0, bd=0,
            )
            number.pack(side="left")
            number.create_oval(1, 1, 24, 24, fill=colors[index], outline="")
            number.create_text(
                12.5, 12.5, text=f"{index + 1:02d}", fill="#FFFFFF",
                font=("Segoe UI", 8, "bold"),
            )
            title = tk.Label(
                card_header, text="等待计算", bg="#FFFFFF", fg="#263248",
                font=(FONT_FAMILY, 11, "bold"), anchor="w",
            )
            title.pack(side="left", padx=(8, 0))

            value = tk.Label(
                card, text="—", bg="#F8FAFC", fg=colors[index],
                font=("Consolas", 11, "bold"), anchor="w", padx=8, pady=3,
            )
            value.pack(fill="x", padx=12, pady=(0, 5))
            description = tk.Label(
                card,
                text="生成发送帧后显示当前步骤。",
                bg="#FFFFFF",
                fg="#718096",
                font=(FONT_FAMILY, 9),
                justify="left",
                anchor="nw",
                width=1,
                wraplength=190,
            )
            description.pack(fill="both", expand=True, padx=12, pady=(0, 8))
            card.bind(
                "<Configure>",
                lambda event, label=description: label.configure(
                    wraplength=max(event.width - 24, 100),
                ),
            )
            self.step_title_labels.append(title)
            self.step_value_labels.append(value)
            self.step_description_labels.append(description)

        receiver = tk.Frame(
            section, bg="#FFFFFF", highlightbackground="#D5DDE9",
            highlightthickness=1,
        )
        receiver.grid(row=0, column=1, sticky="nsew")
        self.receiver_strip = tk.Frame(receiver, bg=COLOR_PASS, height=4)
        self.receiver_strip.pack(fill="x")
        receiver_header = tk.Frame(receiver, bg="#FFFFFF")
        receiver_header.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(
            receiver_header, text="接收端判定", bg="#FFFFFF", fg="#64748B",
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(side="left")
        tk.Label(
            receiver_header, text="RECEIVER", bg="#FFFFFF", fg="#A0AEC0",
            font=("Segoe UI", 8, "bold"),
        ).pack(side="right")

        status_row = tk.Frame(receiver, bg="#FFFFFF")
        status_row.pack(fill="x", padx=16)
        self.receiver_icon = tk.Canvas(
            status_row, width=48, height=48, bg="#FFFFFF",
            highlightthickness=0, bd=0,
        )
        self.receiver_icon.pack(side="left")
        status_text = tk.Frame(status_row, bg="#FFFFFF")
        status_text.pack(side="left", padx=(10, 0))
        self.receiver_status = tk.Label(
            status_text, text="等待发送帧", bg="#FFFFFF", fg="#64748B",
            font=(FONT_FAMILY, 15, "bold"),
        )
        self.receiver_status.pack(anchor="w")
        self.receiver_state = tk.Label(
            status_text, text="WAITING FOR FRAME", bg="#FFFFFF", fg="#94A3B8",
            font=("Segoe UI", 8, "bold"),
        )
        self.receiver_state.pack(anchor="w", pady=(2, 0))
        self._draw_receiver_icon("#94A3B8", "…")

        self.receiver_detail = tk.Label(
            receiver,
            text="选择校验方案并生成发送帧。",
            bg="#FFFFFF",
            fg="#64748B",
            font=(FONT_FAMILY, 9),
            justify="left",
            anchor="nw",
            wraplength=260,
        )
        self.receiver_detail.pack(fill="x", padx=16, pady=(6, 5))

        metrics = tk.Frame(receiver, bg="#FFFFFF")
        metrics.pack(fill="x", padx=16, pady=(0, 6))
        self.receiver_metric_values = []
        for column, title_text in enumerate(("接收帧长", "反转位数")):
            metric = tk.Frame(
                metrics, bg="#F8FAFC", highlightbackground="#E2E8F0",
                highlightthickness=1,
            )
            metric.pack(
                side="left", fill="x", expand=True,
                padx=(0, 8) if column == 0 else (0, 0),
            )
            tk.Label(
                metric, text=title_text, bg="#F8FAFC", fg="#8491A5",
                font=(FONT_FAMILY, 8, "bold"),
            ).pack(pady=(4, 0))
            metric_value = tk.Label(
                metric, text="—", bg="#F8FAFC", fg="#334155",
                font=("Consolas", 12, "bold"),
            )
            metric_value.pack(pady=(0, 4))
            self.receiver_metric_values.append(metric_value)

        self.receiver_extra = tk.Label(
            receiver,
            text="",
            bg="#FFFFFF",
            fg="#334155",
            font=(FONT_FAMILY, 9, "bold"),
            justify="left",
            anchor="nw",
            wraplength=260,
        )
        self.receiver_extra.pack(fill="x", padx=16, pady=(1, 4))
        self.receiver_data_title = tk.Label(
            receiver, text="接收数据", bg="#FFFFFF", fg="#8491A5",
            font=(FONT_FAMILY, 9, "bold"),
        )
        self.receiver_data_title.pack(anchor="w", padx=16)
        self.receiver_data_canvas = tk.Canvas(
            receiver, height=34, bg="#FFFFFF", highlightthickness=0, bd=0,
        )
        self.receiver_data_canvas.pack(fill="x", padx=14, pady=(3, 5))
        self.receiver_data_canvas.bind(
            "<Configure>", lambda event: self._draw_receiver_data(),
        )
        self.receiver_hint = tk.Label(
            receiver,
            text="汉明码演示每次反转 1 位",
            bg="#FFFFFF",
            fg="#94A3B8",
            font=(FONT_FAMILY, 9),
        )
        self.receiver_hint.pack(anchor="w", padx=16, pady=(0, 9))

    def _draw_receiver_icon(self, color, symbol):
        self.receiver_icon.delete("all")
        self.receiver_icon.create_oval(2, 2, 46, 46, fill=color, outline="")
        self.receiver_icon.create_text(
            24, 23, text=symbol, fill="#FFFFFF",
            font=("Segoe UI Symbol", 20, "bold"),
        )

    def _draw_hero(self, event=None):
        canvas = self.hero
        canvas.delete("all")
        width = max(canvas.winfo_width(), 640)
        height = max(canvas.winfo_height(), 132)
        for y in range(height):
            color = _mix_colors("#164E63", "#0891B2", y / height)
            canvas.create_line(0, y, width, y, fill=color)

        line_color = "#67E8F9"
        canvas.create_oval(width - 260, -80, width + 50, 230, outline=line_color)
        canvas.create_oval(width - 205, 5, width - 45, 165, outline=line_color, width=2)
        points = [
            (width - 205, 45), (width - 125, 30), (width - 70, 82),
            (width - 170, 105), (width - 105, 118),
        ]
        for start, end in ((0, 1), (1, 2), (0, 3), (3, 4), (4, 2), (1, 4)):
            canvas.create_line(*points[start], *points[end], fill=line_color, width=2)
        for x, y in points:
            canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#FFFFFF", outline="")

        canvas.create_text(
            28, 24, anchor="w", text="02  /  CHECKSUM LABORATORY",
            fill="#A5F3FC", font=("Segoe UI", 10, "bold"),
        )
        canvas.create_line(28, 42, 66, 42, fill="#FFFFFF", width=3)
        canvas.create_text(
            27, 68, anchor="w", text="校验实验室", fill="#FFFFFF",
            font=(FONT_FAMILY, 24, "bold"),
        )
        canvas.create_text(
            29, 104, anchor="w", text="从发送帧到接收判定，观察校验与纠错的完整过程。",
            fill="#CFFAFE", font=(FONT_FAMILY, 11),
        )

    def generate_frame(self):
        """根据当前方案生成发送帧；CRC 额外支持 ASCII 标准测试文本。"""
        scheme = self.SCHEME_KEYS[self.scheme_var.get()]
        raw_text = self.data_var.get()
        stripped = raw_text.strip()
        compact = "".join(stripped.split())
        text = None

        if scheme == "crc" and compact and any(char not in "01" for char in compact):
            text = stripped
            if len(text) > 9:
                self.status_label.configure(
                    text="CRC 文本模式请输入 1～9 个 ASCII 字符。", fg=COLOR_ERROR,
                )
                self._clear_results()
                return
            try:
                raw = text.encode("ascii")
            except UnicodeEncodeError:
                self.status_label.configure(
                    text="CRC 文本模式仅支持 ASCII 字符。", fg=COLOR_ERROR,
                )
                self._clear_results()
                return
            data = "".join(f"{byte:08b}" for byte in raw)
        else:
            data = compact

        if not data or any(bit not in "01" for bit in data) or (text is None and len(data) > 16):
            self.status_label.configure(
                text="请输入 1～16 位二进制数据；CRC 也可输入 ASCII 文本。", fg=COLOR_ERROR,
            )
            self._clear_results()
            return

        try:
            if scheme == "parity":
                self.current = self._parity_result(data)
            elif scheme == "matrix":
                self.current = self._matrix_result(data)
            elif scheme == "inet":
                self.current = self._internet_checksum_result(data)
            elif scheme == "crc":
                self.current = self._crc_result(data, text=text)
            else:
                self.current = self._hamming_result(data)
        except (ValueError, IndexError) as error:
            self.status_label.configure(text=str(error), fg=COLOR_ERROR)
            self._clear_results()
            return

        self.received_bits = self.current["frame"]
        self.flipped_positions.clear()
        if text is not None:
            status = (
                f"ASCII {len(text)} 字符 · 数据 {len(data)} 位 · "
                f"CRC-16 = {self.current['steps'][-1][1]} · 点击接收帧注入错误"
            )
        else:
            status = (
                f"发送帧已生成 · 数据 {len(data)} 位 · 帧长 "
                f"{len(self.current['frame'])} 位 · 点击接收帧注入错误"
            )
        self.status_label.configure(text=status, fg=COLOR_PASS)
        self._draw_frames()
        self._evaluate_receiver()

    def _parity_result(self, data):
        mode = self.SCHEME_MODES[self.scheme_var.get()]
        encoded = parity.parity_encode(data, mode)
        frame = encoded["result"]["frame"]
        return {
            "key": "parity",
            "mode": mode,
            "data": data,
            "frame": frame,
            "check_indices": {len(data)},
            "steps": self._algorithm_steps(
                encoded, f"{len(data)} BIT",
                f"P = {encoded['result']['parity']}", frame,
            ),
        }

    def _matrix_result(self, data):
        side = max(1, math.ceil(math.sqrt(len(data))))
        padding = (-len(data)) % (side * side)
        padded = data + "0" * padding
        mode = self.SCHEME_MODES[self.scheme_var.get()]
        encoded = matrix.matrix_encode(padded, side, side, mode)
        frame = encoded["result"]["frame"]
        width = side + 1
        check_indices = {
            row * width + side for row in range(side)
        } | set(range(side * width, len(frame)))
        return {
            "key": "matrix",
            "mode": mode,
            "data": data,
            "frame": frame,
            "side": side,
            "padding": padding,
            "check_indices": check_indices,
            "steps": self._algorithm_steps(
                encoded, f"{side} × {side}",
                "ROW " + "".join(encoded["result"]["row_parity"]), frame,
            ),
        }

    def _internet_checksum_result(self, data):
        # 与算法调度层一致：不足 16 位时先在尾部补 0。
        padded = data.ljust(max(len(data), 16), "0")
        data_bytes = checksum.frame_bits_to_bytes(padded)
        encoded = checksum.checksum_frame(data_bytes)
        frame = encoded["result"]["frame_bits"]
        return {
            "key": "inet",
            "data": data,
            "frame": frame,
            "check_indices": set(range(max(len(frame) - 16, 0), len(frame))),
            "steps": self._algorithm_steps(
                encoded, f"{len(data_bytes)} BYTE", "RFC 1071",
                f"0x{encoded['result']['checksum']:04X}",
            ),
        }

    def _crc_result(self, data, text=None):
        encoded = crc.crc_encode(data, preset=self.CRC_PRESET)
        frame = encoded["result"]["frame"]
        steps = self._algorithm_steps(
            encoded, "16 BIT · 0x1021",
            f"INIT 0x{encoded['result']['init']:04X}",
            encoded["result"]["crc_hex"],
        )
        if len(steps) > 1:
            title, value, _ = steps[1]
            source = (
                f"ASCII 文本 {text} 转换为 {len(data)} 位数据"
                if text is not None else f"输入 {len(data)} 位二进制数据"
            )
            steps[1] = (
                title, value,
                f"{source}；寄存器初值 0x{encoded['result']['init']:04X}。",
            )
        return {
            "key": "crc",
            "data": data,
            "text": text,
            "frame": frame,
            "check_indices": set(range(len(data), len(frame))),
            "steps": steps,
        }

    def _hamming_result(self, data):
        encoded = hamming.hamming_encode(data)
        frame = encoded["result"]["frame"]
        steps = self._algorithm_steps(
            encoded, f"{len(encoded['result']['blocks'])} GROUP",
            encoded["result"]["blocks"][0]["codeword"], frame,
        )
        if len(steps) > 1:
            title, value, _ = steps[1]
            steps[1] = (
                title, value,
                f"按 p1、p2、p4 的覆盖范围进行偶校验，得到码字 {value}。",
            )
        check_indices = {
            block_start + parity_index
            for block_start in range(0, len(frame), 7)
            for parity_index in (0, 1, 3)
        }
        return {
            "key": "hamming",
            "data": data,
            "frame": frame,
            "check_indices": check_indices,
            "steps": steps,
        }

    @staticmethod
    def _algorithm_steps(response, first, second, final):
        """直接展示算法层步骤，并提取关键结果作为卡片视觉焦点。"""
        source = response.get("steps", [])
        steps = []
        for index, step in enumerate(source):
            value = first if index == 0 else second if index == 1 else "···"
            if index == len(source) - 1:
                value = final
            steps.append((step["title"], value, step["detail"]))
        return steps

    def _flip_bit(self, index):
        if not self.received_bits:
            return

        # 汉明码演示限制为单个错误，避免超出其纠错能力。
        if self.current["key"] == "hamming" and index not in self.flipped_positions:
            for old_index in list(self.flipped_positions):
                self.received_bits = self._toggle_bit(self.received_bits, old_index)
            self.flipped_positions.clear()

        self.received_bits = self._toggle_bit(self.received_bits, index)
        if index in self.flipped_positions:
            self.flipped_positions.remove(index)
        else:
            self.flipped_positions.add(index)
        self._draw_frames()
        self._evaluate_receiver()

    def _evaluate_receiver(self):
        if self.current is None:
            return

        scheme = self.current["key"]
        if scheme == "parity":
            outcome = self._check_parity()
        elif scheme == "matrix":
            outcome = self._check_matrix()
        elif scheme == "inet":
            outcome = self._check_internet_checksum()
        elif scheme == "crc":
            outcome = self._check_crc()
        else:
            outcome = self._check_hamming()

        color = outcome["color"]
        self.receiver_strip.configure(bg=color)
        self.receiver_status.configure(text=outcome["title"], fg=color)
        passed = color == COLOR_PASS
        self._draw_receiver_icon(color, "✓" if passed else "!")
        self.receiver_state.configure(
            text="FRAME ACCEPTED" if passed else "ERROR DETECTED", fg=color,
        )
        for metric, value in zip(
            self.receiver_metric_values,
            (f"{len(self.received_bits)} bit", f"{len(self.flipped_positions)} bit"),
        ):
            metric.configure(text=value, fg=color)
        self.receiver_detail.configure(text=outcome["detail"])
        self.receiver_extra.configure(text=outcome["extra"])
        if scheme == "hamming" or outcome.get("corrected", False):
            data_title = "纠错后恢复的数据"
        elif outcome.get("retransmitted", False):
            data_title = "重传后恢复的数据"
        else:
            data_title = "接收端提取的数据"
        self.receiver_data_title.configure(text=data_title)
        hints = {
            "parity": "一维校验只能检错；候选位不唯一时通过重传恢复数据",
            "matrix": "二维奇偶校验可纠正单个错误，多位错误仅检错",
            "inet": "Internet 校验和用于检错，点击接收位注入错误",
            "crc": "CRC 用于检错，点击接收位观察余数变化",
            "hamming": "汉明码演示每次反转 1 位",
        }
        self.receiver_hint.configure(text=hints[scheme])
        self.receiver_data_bits = outcome["data"]
        self.receiver_data_color = color
        self._draw_receiver_data()

        encode_steps = self.current["steps"]
        if len(encode_steps) > 3:
            final_step = encode_steps[-1]
            summary = final_step[2]
            if scheme == "crc":
                summary = (
                    f"{len(self.current['data'])} 位数据 + 16 位 CRC → "
                    f"{len(self.current['frame'])} 位发送帧。"
                )
            encode_steps = encode_steps[:2] + [(
                "后续编码步骤", final_step[1], summary,
            )]
        self._render_steps(encode_steps + [outcome["step"]])
        self.step_value_labels[3].configure(fg=color)

    def _check_parity(self):
        mode = self.current["mode"]
        mode_name = parity.MODE_NAMES[mode]
        verdict = parity.parity_check(self.received_bits, mode)
        valid = verdict.get("ok", True) and not verdict.get("detected", False)
        message = verdict.get("message", "")
        if valid:
            return {
                "title": "校验通过",
                "color": COLOR_PASS,
                "detail": message,
                "extra": f"{mode_name}只能检错，无法定位或纠正错误位。",
                "data": self.received_bits[:-1],
                "step": ("接收端奇偶判定", "PASS", message),
            }

        # 一维校验只有 1 位校验信息：先枚举候选错误位，说明定位是否唯一；
        # 无法唯一时按真实协议的做法请求重传，用重传帧恢复数据。
        located = parity.parity_locate(self.received_bits, mode)
        candidates = located.get("candidates", [])
        total = len(self.received_bits)
        if candidates:
            shown = "、".join(str(index + 1) for index in candidates[:8])
            if len(candidates) > 8:
                shown += " …"
            locate_text = f"候选错误位：第 {shown} 位，共 {len(candidates)} 个"
            step_value = f"{len(candidates)} 候选"
        else:
            locate_text = "候选错误位：无（疑似多位错误，单比特翻转均无法通过校验）"
            step_value = "无法定位"
        extra = (
            f"{locate_text}\n"
            f"候选不唯一 → 请求重传，恢复数据：{self.current['data']}"
        )
        return {
            "title": "检出错误，已请求重传",
            "color": COLOR_ERROR,
            "detail": f"{message}；{total} 个位置都可能出错，无法唯一定位。",
            "extra": extra,
            "data": self.current["data"],
            "retransmitted": True,
            "step": ("候选定位与重传", step_value, extra),
        }

    def _check_matrix(self):
        side = self.current["side"]
        width = side + 1
        grid = [
            list(self.received_bits[index:index + width])
            for index in range(0, len(self.received_bits), width)
        ]
        verdict = matrix.matrix_check(grid, self.current["mode"])
        detected = verdict.get("detected", False)
        corrected_matrix = verdict.get("corrected")
        corrected = detected and corrected_matrix is not None
        output_grid = corrected_matrix if corrected else grid
        message = verdict.get("message", "")
        data = "".join(
            output_grid[row][column]
            for row in range(side)
            for column in range(side)
        )[:len(self.current["data"])]
        corrected_frame = "".join("".join(row) for row in output_grid)

        if not detected:
            title = "校验通过"
            color = COLOR_PASS
            extra = "行、列校验全部通过，无需纠错。"
            step_value = "PASS"
        elif corrected:
            title = "错误已定位并纠正"
            color = COLOR_PASS
            row, column = verdict["error_pos"]
            before = grid[row][column]
            after = output_grid[row][column]
            extra = (
                f"纠错位置：第 {row + 1} 行第 {column + 1} 列"
                f"（{before} → {after}）\n纠错后帧：{corrected_frame}"
            )
            step_value = f"R{row + 1} · C{column + 1}"
        else:
            title = "检测到无法纠正的错误"
            color = COLOR_ERROR
            extra = "多位错误导致交叉点不唯一，只能检错，不能擅自纠正。"
            step_value = "UNCERTAIN"

        return {
            "title": title,
            "color": color,
            "detail": message,
            "extra": extra,
            "data": data,
            "corrected": corrected,
            "corrected_frame": corrected_frame if corrected else None,
            "step": ("接收端定位与纠错", step_value, message),
        }

    def _check_internet_checksum(self):
        received = checksum.frame_bits_to_bytes(self.received_bits)
        verdict = checksum.inet_verify(received)
        valid = verdict.get("ok", True) and not verdict.get("detected", False)
        message = verdict.get("message", "")
        sum_hex = verdict.get("result", {}).get("sum_hex")
        detail = message
        if sum_hex is not None:
            detail += f" 接收反码和为 {sum_hex}，有效帧应为 0xFFFF。"
        return {
            "title": "校验通过" if valid else "检测到传输错误",
            "color": COLOR_PASS if valid else COLOR_ERROR,
            "detail": detail,
            "extra": "仅用于检错，不能定位或纠正错误位。",
            "data": self.received_bits[:len(self.current["data"])],
            "step": ("接收端反码求和", sum_hex or "—", detail),
        }

    def _check_crc(self):
        verdict = crc.crc_check(
            self.received_bits,
            preset=self.CRC_PRESET,
            data_len=len(self.current["data"]),
        )
        valid = verdict.get("ok", True) and not verdict.get("detected", False)
        message = verdict.get("message", "")
        remainder_hex = verdict.get("result", {}).get("remainder_hex")
        detail = message
        if remainder_hex is not None:
            detail += f" 接收余数为 {remainder_hex}。"
        return {
            "title": "余数为零，通过" if valid else "余数非零，帧损坏",
            "color": COLOR_PASS if valid else COLOR_ERROR,
            "detail": detail,
            "extra": "CRC 能检测常见传输错误，但本页面不执行纠错。",
            "data": self.received_bits[:len(self.current["data"])],
            "step": ("接收端计算余数", remainder_hex or "—", detail),
        }

    def _check_hamming(self):
        verdict = hamming.hamming_decode(self.received_bits)
        ok = verdict.get("ok", True)
        corrected_frame = verdict.get("corrected_frame", self.received_bits)
        corrected = ok and corrected_frame != self.received_bits
        error_pos = verdict.get("error_pos")
        syndrome = verdict.get("syndrome")
        message = verdict.get("message", "")

        restored_data = "".join(
            corrected_frame[block_start + offset]
            for block_start in range(0, len(corrected_frame), 7)
            for offset in (2, 4, 5, 6)
        )[:len(self.current["data"])]
        if not ok:
            title = "检测到无法纠正的错误"
            detail = message
            extra = "请每次只反转一个接收位，再观察汉明码纠错。"
        elif corrected:
            title = "错误已定位并纠正"
            position = f" 错误位置：{error_pos}。" if error_pos is not None else ""
            detail = f"{message}{position}已使用算法返回的纠错帧恢复数据。"
            extra = f"纠错后帧：{corrected_frame}"
        else:
            title = "校验通过，无需纠错"
            detail = message
            extra = "点击上方接收帧的任意位，可观察定位与纠错结果。"

        step_text = f"hamming_decode 返回综合症 {syndrome}；{message}"
        return {
            "title": title,
            "color": COLOR_PASS if ok else COLOR_ERROR,
            "detail": detail,
            "extra": extra,
            "data": restored_data,
            "corrected_frame": corrected_frame,
            "step": (
                "综合症与纠错",
                "".join(map(str, syndrome)) if syndrome is not None else "—",
                step_text,
            ),
        }

    def _draw_frames(self):
        frame = self.current["frame"] if self.current else ""
        check_indices = self.current["check_indices"] if self.current else set()
        self._draw_bits(
            self.sent_canvas, frame, check_indices=check_indices,
        )
        self._draw_bits(
            self.received_canvas,
            self.received_bits,
            check_indices=check_indices,
            flipped=self.flipped_positions,
            interactive=True,
        )

    def _draw_receiver_data(self):
        if self.current and self.current.get("text") is not None:
            self.receiver_data_canvas.delete("all")
            self.receiver_data_canvas.create_text(
                max(self.receiver_data_canvas.winfo_width(), 220) / 2, 22,
                text=self.current["text"], fill=self.receiver_data_color,
                font=("Consolas", 13, "bold"),
            )
            return
        self._draw_bits(
            self.receiver_data_canvas,
            self.receiver_data_bits,
            check_indices=set(range(len(self.receiver_data_bits))),
            accent=self.receiver_data_color,
            show_positions=False,
        )

    def _draw_bits(
        self, canvas, bits, check_indices=None, flipped=None,
        interactive=False, accent=COLOR_PRIMARY, show_positions=True,
    ):
        canvas.delete("all")
        if not bits:
            canvas.create_text(
                8, 20, anchor="w", text="等待生成发送帧",
                fill="#94A3B8", font=(FONT_FAMILY, 10),
            )
            return

        check_indices = check_indices or set()
        flipped = flipped or set()
        width = max(canvas.winfo_width(), 220)
        count = len(bits)
        gap = 3 if count <= 32 else 1
        cell_width = min(26, (width - 12 - gap * (count - 1)) / count)
        cell_width = max(cell_width, 6)
        bit_font_size = 10 if cell_width >= 12 else 8
        total_width = cell_width * count + gap * (count - 1)
        start_x = max((width - total_width) / 2, 4)
        box_height = 25 if show_positions else 24

        for index, bit in enumerate(bits):
            x1 = start_x + index * (cell_width + gap)
            x2 = x1 + cell_width
            selected = index in flipped
            check = index in check_indices
            background = COLOR_ERROR if selected else ("#E0E7FF" if check else "#FFFFFF")
            border = COLOR_ERROR if selected else (accent if check else "#CBD5E1")
            foreground = "#FFFFFF" if selected else (accent if check else "#334155")
            tag = f"bit_{index}"
            _rounded_rectangle(
                canvas, x1, 2, x2, 2 + box_height, 4,
                fill=background, outline=border, width=1, tags=(tag,),
            )
            canvas.create_text(
                (x1 + x2) / 2, 2 + box_height / 2, text=bit,
                fill=foreground, font=("Consolas", bit_font_size, "bold"), tags=(tag,),
            )
            if show_positions:
                canvas.create_text(
                    (x1 + x2) / 2, 38, text=str(index + 1),
                    fill="#A0AEC0", font=("Segoe UI", 7), tags=(tag,),
                )
            if interactive:
                canvas.tag_bind(
                    tag, "<Button-1>", lambda event, i=index: self._flip_bit(i),
                )

    @staticmethod
    def _shorten_bit_runs(text, limit=22):
        """卡片内压缩超长位串，避免 ASCII 文本的数据位撑破步骤卡。"""

        def replace(match):
            bits = match.group(0)
            if len(bits) <= limit:
                return bits
            half = limit // 2
            return f"{bits[:half]}…{bits[-half:]}（共 {len(bits)} 位）"

        return re.sub(r"[01]{17,}", replace, text)

    def _render_steps(self, steps):
        for index in range(4):
            if index < len(steps):
                title, value, description = steps[index]
                self.step_title_labels[index].configure(text=title)
                self.step_value_labels[index].configure(
                    text=self._shorten_bit_runs(value, 22),
                )
                self.step_description_labels[index].configure(
                    text=self._shorten_bit_runs(description),
                )
            else:
                self.step_title_labels[index].configure(text="等待计算")
                self.step_value_labels[index].configure(text="—")
                self.step_description_labels[index].configure(text="")

    def _clear_results(self):
        self.current = None
        self.received_bits = ""
        self.flipped_positions.clear()
        self.receiver_data_bits = ""
        self._draw_frames()
        self._draw_receiver_data()
        self.receiver_strip.configure(bg="#CBD5E1")
        self.receiver_status.configure(text="等待有效输入", fg="#64748B")
        self.receiver_state.configure(text="WAITING FOR FRAME", fg="#94A3B8")
        self._draw_receiver_icon("#94A3B8", "…")
        for metric in self.receiver_metric_values:
            metric.configure(text="—", fg="#334155")
        self.receiver_detail.configure(text="请输入有效数据。")
        self.receiver_extra.configure(text="")
        self._render_steps([])

    @staticmethod
    def _toggle_bit(bits, index):
        return bits[:index] + str(1 - int(bits[index])) + bits[index + 1:]


__all__ = ["ChecksumView"]


if __name__ == "__main__":
    root = tk.Tk()
    root.title("校验实验室")
    window_width, window_height = 1100, 800
    x = max((root.winfo_screenwidth() - window_width) // 2, 0)
    y = max((root.winfo_screenheight() - window_height) // 2, 0)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.minsize(1000, 760)
    ChecksumView(root).pack(fill="both", expand=True)
    root.update_idletasks()
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    root.mainloop()
