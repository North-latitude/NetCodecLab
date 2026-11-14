"""信道模拟页面：比特翻转、接收判定与五种校验方案对比。"""

import math
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# 允许直接运行 app/views/channel_view.py 进行页面预览。
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

from app.common.bits import normalize_bits
from app.common.theme import (
    COLOR_BACKGROUND,
    COLOR_ERROR,
    COLOR_PASS,
    COLOR_PRIMARY,
    FONT_BOLD,
    FONT_FAMILY,
    FONT_NORMAL,
)
from app.core import checksum, crc, hamming, matrix, parity


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


class ChannelView(tk.Frame):
    """以同一组输入数据对比五种校验方案的检错与纠错表现。"""

    SCHEMES = (
        ("parity", "一维奇偶校验"),
        ("matrix", "二维奇偶校验"),
        ("crc", "CRC-16/CCITT"),
        ("inet", "Internet 校验和"),
        ("hamming", "汉明码（7,4）"),
    )
    LABELS = dict(SCHEMES)
    KEYS = tuple(key for key, _ in SCHEMES)
    CRC_PRESET = "CRC-16/CCITT"

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg", COLOR_BACKGROUND)
        super().__init__(master, **kwargs)

        self.data_var = tk.StringVar(value="10110101")
        self.scheme_var = tk.StringVar(value=self.LABELS["hamming"])
        self.current_key = "hamming"
        self.data = ""
        self.frames = {}
        self.flipped = {key: set() for key in self.KEYS}
        self.outcomes = {}
        self._bit_layout = (30, 6, 1)
        self._updating_table = False
        self.step_titles = []
        self.step_values = []
        self.step_descriptions = []

        self._build_hero()
        self._build_input_area()
        self._build_body()
        self.generate_frames()

    def _build_hero(self):
        self.hero = tk.Canvas(
            self, height=116, bg="#059669", highlightthickness=0, bd=0,
        )
        self.hero.pack(fill="x", padx=24, pady=(20, 14))
        self.hero.bind("<Configure>", self._draw_hero)

    def _build_input_area(self):
        card = tk.Frame(
            self, bg="#FFFFFF", highlightbackground="#D5DDE9", highlightthickness=1,
        )
        card.pack(fill="x", padx=24)
        tk.Frame(card, bg="#10B981", height=3).pack(fill="x")

        row = tk.Frame(card, bg="#FFFFFF")
        row.pack(fill="x", padx=18, pady=(12, 6))
        tk.Label(
            row, text="原始二进制数据", bg="#FFFFFF", fg="#334155", font=FONT_BOLD,
        ).pack(side="left")
        self.data_entry = tk.Entry(
            row,
            textvariable=self.data_var,
            bg="#F5F7FB",
            fg="#1E293B",
            insertbackground="#059669",
            font=("Consolas", 11),
            relief="solid",
            bd=1,
        )
        self.data_entry.pack(
            side="left", fill="x", expand=True, padx=(12, 12), ipady=5,
        )
        self.data_entry.bind("<Return>", lambda event: self.generate_frames())
        tk.Button(
            row,
            text="载入五种方案",
            command=self.generate_frames,
            bg="#059669",
            fg="#FFFFFF",
            activebackground="#047857",
            activeforeground="#FFFFFF",
            font=FONT_BOLD,
            relief="flat",
            bd=0,
            padx=18,
            pady=7,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            row,
            text="清除翻转",
            command=self.clear_flips,
            bg="#E8EEF5",
            fg="#475569",
            activebackground="#D8E1EC",
            activeforeground="#1E293B",
            font=FONT_NORMAL,
            relief="flat",
            bd=0,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        self.status_label = tk.Label(
            card,
            text="输入 1～16 位二进制数据，将同时生成五种发送帧",
            bg="#FFFFFF",
            fg="#64748B",
            font=(FONT_FAMILY, 9),
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=18, pady=(0, 10))

    def _build_body(self):
        body = tk.Frame(self, bg=COLOR_BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=(14, 20))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        left = tk.Frame(body, bg=COLOR_BACKGROUND)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self._build_channel_card(left)
        self._build_process_cards(left)

        right = tk.Frame(body, bg=COLOR_BACKGROUND)
        right.grid(row=0, column=1, sticky="nsew")
        self._build_verdict_card(right)
        self._build_comparison_table(right)

    def _build_channel_card(self, parent):
        card = tk.Frame(
            parent, bg="#FFFFFF", highlightbackground="#D5DDE9", highlightthickness=1,
        )
        card.pack(fill="x")
        tk.Frame(card, bg=COLOR_PRIMARY, height=3).pack(fill="x")

        header = tk.Frame(card, bg="#FFFFFF")
        header.pack(fill="x", padx=16, pady=(11, 6))
        tk.Label(
            header, text="信道位串", bg="#FFFFFF", fg="#172033",
            font=(FONT_FAMILY, 11, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="点击任意 bit 翻转", bg="#FFFFFF", fg="#94A3B8",
            font=(FONT_FAMILY, 8),
        ).pack(side="left", padx=(10, 0))
        self.scheme_box = ttk.Combobox(
            header,
            textvariable=self.scheme_var,
            values=[label for _, label in self.SCHEMES],
            state="readonly",
            width=16,
            font=FONT_NORMAL,
        )
        self.scheme_box.pack(side="right")
        self.scheme_box.bind("<<ComboboxSelected>>", self._on_scheme_selected)

        sent = tk.Frame(card, bg="#FFFFFF")
        sent.pack(fill="x", padx=16)
        tk.Label(
            sent, text="发送帧", bg="#FFFFFF", fg="#8491A5",
            font=(FONT_FAMILY, 8, "bold"),
        ).pack(side="left")
        self.sent_label = tk.Label(
            sent, text="—", bg="#FFFFFF", fg="#475569",
            font=("Consolas", 9), anchor="w",
        )
        self.sent_label.pack(side="left", padx=(12, 0))

        self.bit_canvas = tk.Canvas(
            card, height=106, bg="#F8FAFC", highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self.bit_canvas.pack(fill="x", padx=14, pady=(7, 5))
        self.bit_canvas.bind("<Configure>", lambda event: self._draw_bits())
        self.bit_canvas.bind("<Button-1>", self._on_bit_click)

        footer = tk.Frame(card, bg="#FFFFFF")
        footer.pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(
            footer, text="■", fg=COLOR_ERROR, bg="#FFFFFF", font=(FONT_FAMILY, 8),
        ).pack(side="left")
        tk.Label(
            footer, text="已翻转", fg="#718096", bg="#FFFFFF", font=(FONT_FAMILY, 8),
        ).pack(side="left", padx=(3, 12))
        tk.Label(
            footer, text="□", fg=COLOR_PRIMARY, bg="#FFFFFF", font=(FONT_FAMILY, 8),
        ).pack(side="left")
        tk.Label(
            footer, text="蓝框为校验位 · 下方数字为 bit 序号",
            fg="#718096", bg="#FFFFFF", font=(FONT_FAMILY, 8),
        ).pack(side="left", padx=(3, 0))

    def _build_process_cards(self, parent):
        section = tk.Frame(parent, bg=COLOR_BACKGROUND)
        section.pack(fill="both", expand=True, pady=(14, 0))
        colors = ("#10B981", COLOR_PRIMARY, "#0891B2")
        titles = ("发送端编码", "信道错误注入", "接收端处理")
        for index in range(3):
            section.columnconfigure(index, weight=1, uniform="channel_steps")
            card = tk.Frame(
                section, bg="#FFFFFF", highlightbackground="#D5DDE9",
                highlightthickness=1,
            )
            card.grid(
                row=0, column=index, sticky="nsew",
                padx=(0, 10) if index < 2 else (0, 0),
            )
            tk.Frame(card, bg=colors[index], height=3).pack(fill="x")
            header = tk.Frame(card, bg="#FFFFFF")
            header.pack(fill="x", padx=10, pady=(8, 5))
            badge = tk.Canvas(
                header, width=24, height=24, bg="#FFFFFF", highlightthickness=0,
            )
            badge.pack(side="left")
            badge.create_oval(1, 1, 23, 23, fill=colors[index], outline="")
            badge.create_text(
                12, 12, text=f"{index + 1:02d}", fill="#FFFFFF",
                font=("Segoe UI", 7, "bold"),
            )
            title = tk.Label(
                header, text=titles[index], bg="#FFFFFF", fg="#263248",
                font=(FONT_FAMILY, 9, "bold"),
            )
            title.pack(side="left", padx=(6, 0))
            value = tk.Label(
                card, text="—", bg="#F8FAFC", fg=colors[index],
                font=("Consolas", 10, "bold"), anchor="w", padx=7, pady=3,
            )
            value.pack(fill="x", padx=10, pady=(0, 5))
            description = tk.Label(
                card, text="等待数据", bg="#FFFFFF", fg="#718096",
                font=(FONT_FAMILY, 8), justify="left", anchor="nw", wraplength=150,
            )
            description.pack(fill="both", expand=True, padx=10, pady=(0, 9))
            card.bind(
                "<Configure>",
                lambda event, label=description: label.configure(
                    wraplength=max(event.width - 20, 90),
                ),
            )
            self.step_titles.append(title)
            self.step_values.append(value)
            self.step_descriptions.append(description)

    def _build_verdict_card(self, parent):
        card = tk.Frame(
            parent, bg="#FFFFFF", highlightbackground="#D5DDE9", highlightthickness=1,
        )
        card.pack(fill="x")
        self.verdict_strip = tk.Frame(card, bg=COLOR_PASS, height=4)
        self.verdict_strip.pack(fill="x")
        header = tk.Frame(card, bg="#FFFFFF")
        header.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(
            header, text="接收端判定", bg="#FFFFFF", fg="#64748B",
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="RECEIVER VERDICT", bg="#FFFFFF", fg="#A0AEC0",
            font=("Segoe UI", 7, "bold"),
        ).pack(side="right")

        status_row = tk.Frame(card, bg="#FFFFFF")
        status_row.pack(fill="x", padx=16)
        self.verdict_icon = tk.Canvas(
            status_row, width=46, height=46, bg="#FFFFFF", highlightthickness=0,
        )
        self.verdict_icon.pack(side="left")
        self.verdict_status = tk.Label(
            status_row, text="等待发送帧", bg="#FFFFFF", fg="#64748B",
            font=(FONT_FAMILY, 14, "bold"),
        )
        self.verdict_status.pack(side="left", padx=(10, 0))
        self.verdict_detail = tk.Label(
            card, text="生成五种发送帧后显示判定。", bg="#FFFFFF", fg="#64748B",
            font=(FONT_FAMILY, 8), justify="left", anchor="nw", wraplength=280,
        )
        self.verdict_detail.pack(fill="x", padx=16, pady=(6, 6))
        card.bind(
            "<Configure>",
            lambda event: self.verdict_detail.configure(
                wraplength=max(event.width - 32, 160),
            ),
        )

        metrics = tk.Frame(card, bg="#FFFFFF")
        metrics.pack(fill="x", padx=16, pady=(0, 6))
        self.metric_values = []
        for column, title in enumerate(("当前帧长", "翻转位数")):
            metric = tk.Frame(
                metrics, bg="#F8FAFC", highlightbackground="#E2E8F0",
                highlightthickness=1,
            )
            metric.pack(
                side="left", fill="x", expand=True,
                padx=(0, 8) if column == 0 else (0, 0),
            )
            tk.Label(
                metric, text=title, bg="#F8FAFC", fg="#8491A5",
                font=(FONT_FAMILY, 7, "bold"),
            ).pack(pady=(4, 0))
            value = tk.Label(
                metric, text="—", bg="#F8FAFC", fg="#334155",
                font=("Consolas", 11, "bold"),
            )
            value.pack(pady=(0, 4))
            self.metric_values.append(value)
        self.recovered_label = tk.Label(
            card, text="", bg="#FFFFFF", fg="#334155",
            font=("Consolas", 8, "bold"), justify="left", anchor="nw",
            wraplength=280,
        )
        self.recovered_label.pack(fill="x", padx=16, pady=(0, 10))

    def _build_comparison_table(self, parent):
        card = tk.Frame(
            parent, bg="#FFFFFF", highlightbackground="#D5DDE9", highlightthickness=1,
        )
        card.pack(fill="both", expand=True, pady=(14, 0))
        tk.Frame(card, bg="#6366F1", height=3).pack(fill="x")
        header = tk.Frame(card, bg="#FFFFFF")
        header.pack(fill="x", padx=14, pady=(10, 7))
        tk.Label(
            header, text="五种方案对比", bg="#FFFFFF", fg="#172033",
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="点击行切换位串", bg="#FFFFFF", fg="#94A3B8",
            font=(FONT_FAMILY, 8),
        ).pack(side="right")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Channel.Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#334155",
            rowheight=29,
            borderwidth=0,
            font=(FONT_FAMILY, 8),
        )
        style.configure(
            "Channel.Treeview.Heading",
            background="#EEF2F7",
            foreground="#64748B",
            relief="flat",
            font=(FONT_FAMILY, 8, "bold"),
        )
        style.map(
            "Channel.Treeview",
            background=[("selected", "#DBEAFE")],
            foreground=[("selected", "#1E3A8A")],
        )
        columns = ("frame", "verdict", "correction")
        self.table = ttk.Treeview(
            card, columns=columns, show="tree headings", height=5,
            style="Channel.Treeview", selectmode="browse",
        )
        self.table.column("#0", width=125, minwidth=105, anchor="w", stretch=True)
        self.table.heading("#0", text="校验方案")
        for key, title, width in (
            ("frame", "帧长", 48),
            ("verdict", "判定", 66),
            ("correction", "纠错", 66),
        ):
            self.table.column(key, width=width, minwidth=42, anchor="center", stretch=False)
            self.table.heading(key, text=title)
        self.table.pack(fill="both", expand=True, padx=12)
        self.table.tag_configure("pass", foreground="#15803D")
        self.table.tag_configure("error", foreground=COLOR_ERROR)
        self.table.tag_configure("corrected", foreground="#0284C7")
        self.table.tag_configure("odd", background="#F8FAFC")
        for key, label in self.SCHEMES:
            self.table.insert("", "end", iid=key, text=label, values=("—", "—", "—"))
        self.table.bind("<<TreeviewSelect>>", self._on_table_selected)

        tk.Label(
            card,
            text="各方案按相同相对位置注入错误；帧结构不同，帧长也不同。",
            bg="#FFFFFF", fg="#94A3B8", font=(FONT_FAMILY, 7),
            anchor="w", justify="left", wraplength=300,
        ).pack(fill="x", padx=14, pady=(6, 9))

    def generate_frames(self):
        """使用真实算法同时构造五种发送帧。"""
        try:
            data = normalize_bits(self.data_var.get())
        except ValueError as exc:
            self._show_input_error(str(exc))
            return
        if len(data) > 16:
            self._show_input_error("为了清楚展示，请输入不超过 16 位的数据。")
            return

        frames = {}
        responses = [
            self._encode_parity(data),
            self._encode_matrix(data),
            self._encode_crc(data),
            self._encode_inet(data),
            self._encode_hamming(data),
        ]
        for key, response in zip(self.KEYS, responses):
            if not response["ok"]:
                self._show_input_error(response["message"])
                return
            frames[key] = response

        self.data = data
        self.frames = frames
        self.flipped = {key: set() for key in self.KEYS}
        self.frames["parity"]["check_indices"] = {len(data)}
        self.frames["crc"]["check_indices"] = set(range(len(data), len(data) + 16))
        self.frames["inet"]["check_indices"] = set(
            range(max(len(self.frames["inet"]["result"]["frame"]) - 16, 0),
                  len(self.frames["inet"]["result"]["frame"]))
        )
        hamming_frame = self.frames["hamming"]["result"]["frame"]
        self.frames["hamming"]["check_indices"] = {
            base + offset
            for base in range(0, len(hamming_frame), 7)
            for offset in (0, 1, 3)
        }
        self.status_label.configure(
            text=f"已生成 5 种发送帧 · 原始数据 {len(data)} 位 · 点击位块开始注入错误",
            fg=COLOR_PASS,
        )
        self._refresh_all()

    def _encode_parity(self, data):
        return parity.parity_encode(data, mode=parity.MODE_EVEN)

    def _encode_matrix(self, data):
        side = math.ceil(math.sqrt(len(data)))
        padding = side * side - len(data)
        response = matrix.matrix_encode(
            data + "0" * padding, rows=side, cols=side, mode=matrix.MODE_EVEN,
        )
        response["padding"] = padding
        response["check_indices"] = {
            row * (side + 1) + side for row in range(side + 1)
        } | {
            side * (side + 1) + column for column in range(side + 1)
        }
        return response

    def _encode_crc(self, data):
        return crc.crc_encode(data, preset=self.CRC_PRESET)

    def _encode_inet(self, data):
        data_bytes = self._bits_to_bytes(data)
        data_bytes = data_bytes.ljust(2, b"\x00")
        response = checksum.checksum_frame(data_bytes)
        if response["ok"]:
            response["result"]["frame"] = response["result"]["frame_bits"]
        return response

    def _encode_hamming(self, data):
        return hamming.hamming_encode(data)

    def _evaluate(self, key):
        record = self.frames[key]
        received = self._received_bits(key)
        if key == "parity":
            response = parity.parity_check(received, mode=parity.MODE_EVEN)
            detected = response["ok"] and bool(response["detected"])
            corrected = False
        elif key == "matrix":
            rows = record["result"]["rows"] + 1
            cols = record["result"]["cols"] + 1
            received_matrix = [
                list(received[row * cols:(row + 1) * cols]) for row in range(rows)
            ]
            response = matrix.matrix_check(received_matrix, mode=matrix.MODE_EVEN)
            detected = response["ok"] and bool(response["detected"])
            corrected = bool(response.get("corrected"))
        elif key == "crc":
            response = crc.crc_check(received, preset=self.CRC_PRESET)
            detected = response["ok"] and bool(response["detected"])
            corrected = False
        elif key == "inet":
            response = checksum.inet_verify(self._bits_to_bytes(received))
            detected = response["ok"] and bool(response["detected"])
            corrected = False
        else:
            response = hamming.hamming_decode(received)
            detected = response["ok"] and bool(response["detected"])
            corrected = detected

        valid = response["ok"] and not detected
        if valid:
            title = "校验通过"
            tag = "pass"
            color = COLOR_PASS
        elif corrected:
            title = "检出并已纠正"
            tag = "corrected"
            color = "#0284C7"
        else:
            title = "检出错误"
            tag = "error"
            color = COLOR_ERROR
        return {
            "response": response,
            "valid": valid,
            "detected": detected,
            "corrected": corrected,
            "title": title,
            "tag": tag,
            "color": color,
            "message": response["message"],
        }

    def _received_bits(self, key):
        bits = list(self.frames[key]["result"]["frame"])
        for position in self.flipped[key]:
            bits[position] = "1" if bits[position] == "0" else "0"
        return "".join(bits)

    def _on_bit_click(self, event):
        if self.current_key not in self.frames:
            return
        size, gap, per_row = self._bit_layout
        row = (event.y - 8) // 48
        column = (event.x - 8) // (size + gap)
        if row < 0 or column < 0:
            return
        x_in_cell = (event.x - 8) % (size + gap)
        y_in_cell = (event.y - 8) % 48
        if x_in_cell >= size or y_in_cell >= size:
            return
        position = row * per_row + column
        frame_length = len(self.frames[self.current_key]["result"]["frame"])
        if position >= frame_length:
            return
        positions = self.flipped[self.current_key]
        if position in positions:
            positions.remove(position)
        else:
            positions.add(position)
        self._map_flips_to_other_schemes()
        self._refresh_all()

    def _map_flips_to_other_schemes(self):
        reference_key = self.current_key
        reference_length = len(self.frames[reference_key]["result"]["frame"])
        source = set(self.flipped[reference_key])
        for key in self.KEYS:
            if key == reference_key:
                continue
            target_length = len(self.frames[key]["result"]["frame"])
            self.flipped[key] = {
                round(position * (target_length - 1) / max(reference_length - 1, 1))
                for position in source
            }

    def _refresh_all(self):
        if not self.frames:
            return
        self.outcomes = {key: self._evaluate(key) for key in self.KEYS}
        self._refresh_channel()
        self._refresh_verdict()
        self._refresh_steps()
        self._refresh_table()

    def _refresh_channel(self):
        frame = self.frames[self.current_key]["result"]["frame"]
        self.sent_label.configure(text=frame)
        self._draw_bits()

    def _refresh_verdict(self):
        outcome = self.outcomes[self.current_key]
        color = outcome["color"]
        self.verdict_strip.configure(bg=color)
        self.verdict_status.configure(text=outcome["title"], fg=color)
        self.verdict_detail.configure(text=outcome["message"])
        self._draw_verdict_icon(color, "✓" if outcome["valid"] else "!")
        for label, value in zip(
            self.metric_values,
            (f"{len(self.frames[self.current_key]['result']['frame'])} bit",
             f"{len(self.flipped[self.current_key])} bit"),
        ):
            label.configure(text=value, fg=color)
        if outcome["corrected"]:
            decoded = self.data
            if self.current_key == "hamming":
                decoded = outcome["response"]["result"]["data"][:len(self.data)]
            suffix = "已恢复" if decoded == self.data else "多位错误，结果可能不可靠"
            recovered = f"译码输出：{decoded}（{suffix}）"
        elif outcome["valid"]:
            recovered = f"接收数据：{self.data}"
        else:
            recovered = "译码输出：未执行纠错"
        self.recovered_label.configure(text=recovered, fg=color)

    def _refresh_steps(self):
        record = self.frames[self.current_key]
        outcome = self.outcomes[self.current_key]
        positions = sorted(self.flipped[self.current_key])
        frame_length = len(record["result"]["frame"])
        values = (
            f"{len(self.data)} → {frame_length} bit",
            f"{len(positions)} bit",
            "PASS" if outcome["valid"] else "FIXED" if outcome["corrected"] else "ERROR",
        )
        descriptions = (
            record["message"],
            "位串保持原样，未注入错误。" if not positions else
            "翻转位置：" + "、".join(map(str, positions)) + "；红色位块为信道错误。",
            outcome["message"],
        )
        for index in range(3):
            self.step_values[index].configure(text=values[index])
            self.step_descriptions[index].configure(text=descriptions[index])
        self.step_values[2].configure(fg=outcome["color"])

    def _refresh_table(self):
        self._updating_table = True
        try:
            for index, key in enumerate(self.KEYS):
                outcome = self.outcomes[key]
                verdict = "通过" if outcome["valid"] else "已纠正" if outcome["corrected"] else "检出"
                correction = "已纠正" if outcome["corrected"] else "—" if outcome["valid"] else "不能"
                tags = [outcome["tag"]]
                if index % 2:
                    tags.append("odd")
                self.table.item(
                    key,
                    text=self.LABELS[key],
                    values=(len(self.frames[key]["result"]["frame"]), verdict, correction),
                    tags=tags,
                )
            self.table.selection_set(self.current_key)
            self.table.focus(self.current_key)
        finally:
            self._updating_table = False

    def _draw_bits(self):
        canvas = self.bit_canvas
        canvas.delete("all")
        if self.current_key not in self.frames:
            return
        frame = self.frames[self.current_key]["result"]["frame"]
        received = self._received_bits(self.current_key)
        width = max(canvas.winfo_width(), 240)
        size, gap = 30, 6
        per_row = max(1, (width - 16 + gap) // (size + gap))
        self._bit_layout = (size, gap, per_row)
        rows = math.ceil(len(frame) / per_row)
        canvas.configure(height=max(54, rows * 48 + 10))
        check_indices = self.frames[self.current_key]["check_indices"]

        for position, bit in enumerate(received):
            row, column = divmod(position, per_row)
            x1 = 8 + column * (size + gap)
            y1 = 8 + row * 48
            flipped = position in self.flipped[self.current_key]
            fill = COLOR_ERROR if flipped else "#EFF6FF" if position in check_indices else "#FFFFFF"
            outline = COLOR_ERROR if flipped else COLOR_PRIMARY if position in check_indices else "#CBD5E1"
            foreground = "#FFFFFF" if flipped else "#1E293B"
            _rounded_rectangle(
                canvas, x1, y1, x1 + size, y1 + size,
                radius=5, fill=fill, outline=outline, width=2,
            )
            canvas.create_text(
                x1 + size / 2, y1 + size / 2 + 1, text=bit,
                fill=foreground, font=("Consolas", 11, "bold"),
            )
            canvas.create_text(
                x1 + size / 2, y1 + size + 10, text=str(position),
                fill=COLOR_ERROR if flipped else "#94A3B8",
                font=("Consolas", 7),
            )

    def _draw_hero(self, event):
        canvas = self.hero
        canvas.delete("all")
        width = max(event.width, 600)
        height = max(event.height, 116)
        bands = 90
        for index in range(bands):
            ratio = index / (bands - 1)
            color = _mix_colors("#10B981", "#134E4A", ratio)
            x1 = round(index * width / bands)
            x2 = round((index + 1) * width / bands)
            canvas.create_rectangle(x1, 0, x2, height, fill=color, outline="")
        canvas.create_oval(width - 290, -105, width - 50, 135, fill="#167A6C", outline="")
        canvas.create_oval(width - 190, 34, width - 40, 184, fill="#116457", outline="")
        canvas.create_text(
            32, 29, text="信道模拟", fill="#FFFFFF", anchor="w",
            font=(FONT_FAMILY, 21, "bold"),
        )
        canvas.create_text(
            34, 60, text="CHANNEL SIMULATOR  /  BIT ERROR INJECTION",
            fill="#D1FAE5", anchor="w", font=("Segoe UI", 9, "bold"),
        )
        canvas.create_text(
            34, 89,
            text="点击比特注入错误，观察五种校验方案的检错与纠错差异。",
            fill="#ECFDF5", anchor="w", font=FONT_NORMAL,
        )
        canvas.create_text(
            width - 38, 49, text="01 → 0", fill="#D1FAE5", anchor="e",
            font=("Consolas", 17, "bold"),
        )
        canvas.create_text(
            width - 38, 80, text="SEND  /  FLIP  /  VERIFY",
            fill="#A7F3D0", anchor="e", font=("Segoe UI", 8, "bold"),
        )

    def _draw_verdict_icon(self, color, symbol):
        self.verdict_icon.delete("all")
        self.verdict_icon.create_oval(2, 2, 44, 44, fill=color, outline="")
        self.verdict_icon.create_text(
            23, 22, text=symbol, fill="#FFFFFF",
            font=("Segoe UI Symbol", 18, "bold"),
        )

    def _on_scheme_selected(self, event):
        self.current_key = next(
            key for key, label in self.SCHEMES if label == self.scheme_var.get()
        )
        self._refresh_all()

    def _on_table_selected(self, event):
        if self._updating_table:
            return
        selection = self.table.selection()
        if not selection or selection[0] not in self.KEYS:
            return
        if selection[0] == self.current_key:
            return
        self.current_key = selection[0]
        self.scheme_var.set(self.LABELS[self.current_key])
        self._refresh_all()

    def clear_flips(self):
        if not self.frames:
            return
        self.flipped = {key: set() for key in self.KEYS}
        self._refresh_all()

    def _show_input_error(self, message):
        self.status_label.configure(text=message, fg=COLOR_ERROR)

    @staticmethod
    def _bits_to_bytes(data):
        padding = (-len(data)) % 8
        padded = data + "0" * padding
        return bytes(
            int(padded[index:index + 8], 2)
            for index in range(0, len(padded), 8)
        )


if __name__ == "__main__":
    root = tk.Tk()
    root.title("NetCodecLab · 信道模拟")
    root.geometry("1180x800")
    root.minsize(1000, 760)
    root.configure(bg=COLOR_BACKGROUND)
    view = ChannelView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
