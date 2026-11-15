"""编码工坊页面。"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# 允许直接运行 app/views/encoding_view.py 进行页面预览。
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

from app.core import decimal_to_binary, encode_text, text_to_bitstream
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


def _rounded_rectangle(canvas, x1, y1, x2, y2, radius=16, **kwargs):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)


class EncodingView(tk.Frame):
    """字符编码查询与可视化换算页面。"""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg", COLOR_BACKGROUND)
        super().__init__(master, **kwargs)

        self._records = []
        self.input_var = tk.StringVar(value="你好A")
        self.charset_var = tk.StringVar(value="UTF-8")
        self.step_description_labels = {}

        self._build_hero()
        self._build_input_area()
        self._build_result_area()
        self._build_steps_area()
        self.parse_input()

    def _build_hero(self):
        self.hero = tk.Canvas(
            self,
            height=142,
            bg="#4F46E5",
            highlightthickness=0,
            bd=0,
        )
        self.hero.pack(fill="x", padx=24, pady=(20, 14))
        self.hero.bind("<Configure>", self._draw_hero)

    def _build_input_area(self):
        card = tk.Frame(
            self,
            bg="#FFFFFF",
            highlightbackground="#D5DDE9",
            highlightthickness=1,
        )
        card.pack(fill="x", padx=24, pady=(0, 14))
        tk.Frame(card, bg=COLOR_PRIMARY, height=3).pack(fill="x")

        row = tk.Frame(card, bg="#FFFFFF")
        row.pack(fill="x", padx=18, pady=(13, 6))

        tk.Label(
            row,
            text="原始字符",
            bg="#FFFFFF",
            fg="#1E293B",
            font=FONT_BOLD,
        ).pack(side="left")

        self.input_entry = tk.Entry(
            row,
            textvariable=self.input_var,
            bg="#F5F7FB",
            fg="#1E293B",
            insertbackground=COLOR_PRIMARY,
            font=(FONT_FAMILY, 12),
            relief="solid",
            bd=1,
        )
        self.input_entry.pack(
            side="left", fill="x", expand=True, padx=(12, 16), ipady=5,
        )
        self.input_entry.bind("<Return>", lambda event: self.parse_input())

        tk.Label(
            row,
            text="位流编码",
            bg="#FFFFFF",
            fg="#64748B",
            font=FONT_NORMAL,
        ).pack(side="left")

        self.charset_box = ttk.Combobox(
            row,
            textvariable=self.charset_var,
            values=("UTF-8", "GBK"),
            state="readonly",
            width=8,
            font=FONT_NORMAL,
        )
        self.charset_box.pack(side="left", padx=(8, 12), ipady=3)
        self.charset_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.parse_input(),
        )

        self.parse_button = tk.Button(
            row,
            text="解析",
            command=self.parse_input,
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            font=FONT_BOLD,
            relief="flat",
            bd=0,
            padx=24,
            pady=7,
            cursor="hand2",
        )
        self.parse_button.pack(side="left")
        self.convert_button = tk.Button(
            row,
            text="进制换算",
            command=self._open_base_convert_dialog,
            bg="#EEF2FF",
            fg="#4338CA",
            activebackground="#E0E7FF",
            activeforeground="#3730A3",
            font=FONT_BOLD,
            relief="flat",
            bd=0,
            padx=16,
            pady=7,
            cursor="hand2",
        )
        self.convert_button.pack(side="left", padx=(8, 0))

        self.status_label = tk.Label(
            card,
            text="输入字符后点击解析",
            bg="#FFFFFF",
            fg="#64748B",
            font=(FONT_FAMILY, 10),
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=18, pady=(0, 10))

    def _build_result_area(self):
        section = tk.Frame(self, bg=COLOR_BACKGROUND)
        section.pack(fill="both", expand=True, padx=24)

        header = tk.Frame(section, bg=COLOR_BACKGROUND)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(
            header,
            text="字符编码探索",
            bg=COLOR_BACKGROUND,
            fg="#172033",
            font=(FONT_FAMILY, 13, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="点击字符卡片，观察编码细节",
            bg=COLOR_BACKGROUND,
            fg="#7B8BA1",
            font=(FONT_FAMILY, 10),
        ).pack(side="right")

        body = tk.Frame(
            section,
            bg="#FFFFFF",
            highlightbackground="#D5DDE9",
            highlightthickness=1,
        )
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        cards_panel = tk.Frame(body, bg="#F8FAFD")
        cards_panel.grid(row=0, column=0, sticky="nsew")
        cards_panel.rowconfigure(0, weight=1)
        cards_panel.columnconfigure(0, weight=1)

        self.character_cards = []
        self.selected_index = None
        self.cards_canvas = tk.Canvas(
            cards_panel,
            bg="#F8FAFD",
            highlightthickness=0,
            bd=0,
        )
        self.cards_frame = tk.Frame(self.cards_canvas, bg="#F8FAFD")
        self.cards_window = self.cards_canvas.create_window(
            (0, 0), window=self.cards_frame, anchor="nw",
        )
        horizontal_bar = ttk.Scrollbar(
            cards_panel, orient="horizontal", command=self.cards_canvas.xview,
        )
        self.cards_canvas.configure(xscrollcommand=horizontal_bar.set)
        self.cards_canvas.grid(row=0, column=0, sticky="nsew")
        horizontal_bar.grid(row=1, column=0, sticky="ew")
        self.cards_frame.bind(
            "<Configure>",
            lambda event: self.cards_canvas.configure(
                scrollregion=self.cards_canvas.bbox("all"),
            ),
        )
        self.cards_canvas.bind(
            "<Configure>",
            lambda event: self.cards_canvas.itemconfigure(
                self.cards_window, height=event.height,
            ),
        )
        self.cards_canvas.bind(
            "<MouseWheel>",
            lambda event: self.cards_canvas.xview_scroll(
                int(-event.delta / 120), "units",
            ),
        )

        self._build_detail_panel(body)

    def _clear_character_cards(self):
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.character_cards.clear()
        self.selected_index = None
        self.cards_canvas.xview_moveto(0)

    def _create_decimal_card(self, response):
        """在字符卡片前插入十进制转二进制的竖式卡片。"""
        card = tk.Frame(
            self.cards_frame,
            width=196,
            height=190,
            bg="#FFFFFF",
            highlightbackground=COLOR_PRIMARY,
            highlightthickness=2,
        )
        card.pack(side="left", fill="y", padx=(8, 4), pady=8)
        card.pack_propagate(False)
        tk.Frame(card, bg=COLOR_PRIMARY, height=3).pack(fill="x")

        header = tk.Frame(card, bg="#FFFFFF")
        header.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(
            header, text="DEC → BIN", bg="#FFFFFF", fg=COLOR_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="除 2 取余", bg="#FFFFFF", fg="#94A3B8",
            font=(FONT_FAMILY, 8),
        ).pack(side="right")

        if not response["ok"]:
            tk.Label(
                card, text=response["message"], bg="#FFFFFF", fg=COLOR_ERROR,
                font=(FONT_FAMILY, 9), justify="left", anchor="nw",
                wraplength=170,
            ).pack(fill="both", expand=True, padx=10, pady=8)
            return

        result = response["result"]
        tk.Label(
            card, text=f"十进制 {result['value']}", bg="#FFFFFF", fg="#172033",
            font=(FONT_FAMILY, 11, "bold"),
        ).pack(anchor="w", padx=10, pady=(3, 0))

        body = "\n".join(
            f"{item['dividend']:>4} ÷ 2 = {item['quotient']:>4} 余 {item['remainder']}"
            for item in result["rows"]
        )
        tk.Label(
            card, text=body, bg="#FFFFFF", fg="#475569",
            font=("Consolas", 9), justify="left", anchor="w",
        ).pack(fill="x", padx=10, pady=(3, 2))

        tk.Label(
            card, text=f"从下往上 → {result['binary']}", bg="#FFFFFF",
            fg=COLOR_PRIMARY, font=("Consolas", 11, "bold"),
        ).pack(anchor="w", padx=10)

    def _create_character_card(self, index, record):
        card = tk.Frame(
            self.cards_frame,
            width=168,
            height=190,
            bg="#FFFFFF",
            highlightbackground="#D5DDE9",
            highlightthickness=1,
        )
        card.pack(side="left", fill="y", padx=(8 if index == 0 else 4, 4), pady=8)
        card.pack_propagate(False)

        strip = tk.Frame(card, bg="#CBD5E1", height=3)
        strip.pack(fill="x")
        surface = tk.Frame(card, bg="#FFFFFF")
        surface.pack(fill="both", expand=True)

        header = tk.Frame(surface, bg="#FFFFFF")
        header.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(
            header,
            text=f"CHAR {index + 1:02d}",
            bg="#FFFFFF",
            fg="#94A3B8",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="Unicode",
            bg="#FFFFFF",
            fg="#94A3B8",
            font=(FONT_FAMILY, 9),
        ).pack(side="right")

        char_label = tk.Label(
            surface,
            text=self._display_char(record["char"]),
            bg="#FFFFFF",
            fg="#263248",
            font=(FONT_FAMILY, 26, "bold"),
        )
        char_label.pack(pady=(2, 0))
        tk.Label(
            surface,
            text=f"U+{record['codepoint']:04X}",
            bg="#FFFFFF",
            fg=COLOR_PRIMARY,
            font=("Consolas", 11, "bold"),
        ).pack()
        tk.Frame(surface, bg="#E2E8F0", height=1).pack(
            fill="x", padx=13, pady=7,
        )

        for title, key in (("UTF-8", "utf8"), ("GBK", "gbk")):
            row = tk.Frame(surface, bg="#FFFFFF")
            row.pack(fill="x", padx=12, pady=1)
            tk.Label(
                row,
                text=title,
                bg="#FFFFFF",
                fg="#8491A5",
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left")
            tk.Label(
                row,
                text=self._hex_bytes(record[key]),
                bg="#FFFFFF",
                fg="#334155",
                font=("Consolas", 10, "bold"),
            ).pack(side="right")

        selected_bytes = record[self._selected_encoding_key()]
        bit_count = len(selected_bytes) * 8 if selected_bytes is not None else 0
        tk.Label(
            surface,
            text=f"位流  ·  {bit_count} BIT" if selected_bytes is not None else "位流不可用",
            bg="#FFFFFF",
            fg="#8491A5",
            font=(FONT_FAMILY, 9),
        ).pack(anchor="w", padx=12, pady=(7, 2))

        bits_canvas = tk.Canvas(
            surface,
            width=140,
            height=20,
            bg="#FFFFFF",
            highlightthickness=0,
            bd=0,
        )
        bits_canvas.pack(padx=12, pady=(0, 7))
        if selected_bytes is not None:
            bits = "".join(f"{byte:08b}" for byte in selected_bytes)
            cell_width = min(12, 136 / len(bits))
            total_width = cell_width * len(bits)
            start_x = (140 - total_width) / 2
            for bit_index, bit in enumerate(bits):
                x1 = start_x + bit_index * cell_width
                bits_canvas.create_rectangle(
                    x1,
                    3,
                    x1 + max(cell_width - 1, 2),
                    17,
                    fill=COLOR_PRIMARY if bit == "1" else "#CBD5E1",
                    outline="",
                )
        else:
            bits_canvas.create_text(
                70, 10, text="NOT SUPPORTED", fill=COLOR_ERROR,
                font=("Segoe UI", 9, "bold"),
            )

        self.character_cards.append({
            "card": card,
            "surface": surface,
            "strip": strip,
            "char_label": char_label,
        })
        self._bind_character_click(card, index)

    def _bind_character_click(self, widget, index):
        widget.configure(cursor="hand2")
        widget.bind("<Button-1>", lambda event: self._select_character(index))
        for child in widget.winfo_children():
            self._bind_character_click(child, index)

    def _select_character(self, index):
        self._show_conversion_steps(index)

    def _update_card_selection(self, index):
        self.selected_index = index
        for card_index, widgets in enumerate(self.character_cards):
            selected = card_index == index
            background = "#EEF2FF" if selected else "#FFFFFF"
            widgets["card"].configure(
                highlightbackground=COLOR_PRIMARY if selected else "#D5DDE9",
                highlightthickness=2 if selected else 1,
            )
            widgets["strip"].configure(
                bg=COLOR_PRIMARY if selected else "#CBD5E1",
            )
            widgets["char_label"].configure(
                fg=COLOR_PRIMARY if selected else "#263248",
            )
            self._set_card_background(widgets["surface"], background)

    def _set_card_background(self, widget, background):
        widget.configure(bg=background)
        for child in widget.winfo_children():
            self._set_card_background(child, background)

    def _build_detail_panel(self, parent):
        detail = tk.Frame(parent, bg="#F3F5FC")
        detail.grid(row=0, column=1, sticky="nsew")

        tk.Label(
            detail,
            text="当前字符 · 字节视图",
            bg="#F3F5FC",
            fg="#64748B",
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(pady=(10, 5))

        self.detail_char_canvas = tk.Canvas(
            detail,
            width=62,
            height=62,
            bg="#F3F5FC",
            highlightthickness=0,
            bd=0,
        )
        self.detail_char_canvas.pack()

        self.detail_codepoint = tk.Label(
            detail,
            text="等待选择",
            bg="#F3F5FC",
            fg="#334155",
            font=("Consolas", 11, "bold"),
        )
        self.detail_codepoint.pack(pady=(5, 5))

        self.detail_encoding = tk.Label(
            detail,
            text="UTF-8 字节",
            bg="#F3F5FC",
            fg="#64748B",
            font=(FONT_FAMILY, 10),
        )
        self.detail_encoding.pack()

        self.byte_frame = tk.Frame(detail, bg="#F3F5FC")
        self.byte_frame.pack(pady=(6, 3))

        self.detail_bit_count = tk.Label(
            detail,
            text="",
            bg="#F3F5FC",
            fg="#8491A5",
            font=(FONT_FAMILY, 9),
        )
        self.detail_bit_count.pack(pady=(0, 8))

    def _build_steps_area(self):
        section = tk.Frame(self, bg=COLOR_BACKGROUND)
        section.pack(fill="x", padx=24, pady=(14, 20))

        header = tk.Frame(section, bg=COLOR_BACKGROUND)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(
            header,
            text="换算过程",
            bg=COLOR_BACKGROUND,
            fg="#172033",
            font=(FONT_FAMILY, 13, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="CONVERSION STEPS",
            bg=COLOR_BACKGROUND,
            fg="#94A3B8",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        cards = tk.Frame(section, bg=COLOR_BACKGROUND)
        cards.pack(fill="x")
        step_data = (
            ("unicode", "Unicode 码点", "#6366F1"),
            ("utf8", "UTF-8 编码", COLOR_PRIMARY),
            ("gbk", "GBK 映射", "#0891B2"),
        )
        for index, (key, title, color) in enumerate(step_data):
            cards.columnconfigure(index, weight=1, uniform="encoding_steps")
            card = tk.Frame(
                cards,
                bg="#FFFFFF",
                height=116,
                highlightbackground="#D5DDE9",
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0, 12) if index < 2 else (0, 0),
            )
            card.grid_propagate(False)
            tk.Frame(card, bg=color, height=3).pack(fill="x")

            card_header = tk.Frame(card, bg="#FFFFFF")
            card_header.pack(fill="x", padx=13, pady=(9, 3))
            number = tk.Canvas(
                card_header,
                width=25,
                height=25,
                bg="#FFFFFF",
                highlightthickness=0,
                bd=0,
            )
            number.pack(side="left")
            number.create_oval(1, 1, 24, 24, fill=color, outline="")
            number.create_text(
                12.5,
                12.5,
                text=f"{index + 1:02d}",
                fill="#FFFFFF",
                font=("Segoe UI", 8, "bold"),
            )
            tk.Label(
                card_header,
                text=title,
                bg="#FFFFFF",
                fg="#263248",
                font=(FONT_FAMILY, 11, "bold"),
            ).pack(side="left", padx=(9, 0))

            description = tk.Label(
                card,
                text="选择结果行后显示换算信息。",
                bg="#FFFFFF",
                fg="#718096",
                font=(FONT_FAMILY, 10),
                justify="left",
                anchor="nw",
                wraplength=180,
            )
            description.pack(fill="both", expand=True, padx=14, pady=(2, 9))
            card.bind(
                "<Configure>",
                lambda event, label=description: label.configure(
                    wraplength=max(event.width - 28, 100),
                ),
            )
            self.step_description_labels[key] = description

    def _draw_hero(self, event=None):
        canvas = self.hero
        canvas.delete("all")
        width = max(canvas.winfo_width(), 640)
        height = max(canvas.winfo_height(), 142)

        for y in range(height):
            color = _mix_colors("#312E81", "#6366F1", y / height)
            canvas.create_line(0, y, width, y, fill=color)

        line_color = "#A5B4FC"
        canvas.create_oval(
            width - 270, -85, width + 55, 240,
            outline=line_color, width=1,
        )
        canvas.create_oval(
            width - 215, 10, width - 45, 180,
            outline=line_color, width=1,
        )
        points = [
            (width - 215, 50), (width - 130, 32), (width - 72, 91),
            (width - 178, 112), (width - 108, 126),
        ]
        for start, end in ((0, 1), (1, 2), (0, 3), (3, 4), (4, 2), (1, 4)):
            canvas.create_line(*points[start], *points[end], fill=line_color, width=2)
        for index, (x, y) in enumerate(points):
            radius = 6 if index == 2 else 4
            canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill="#FFFFFF", outline="",
            )

        canvas.create_text(
            28,
            25,
            anchor="w",
            text="01  /  ENCODING WORKSHOP",
            fill="#C7D2FE",
            font=("Segoe UI", 10, "bold"),
        )
        canvas.create_line(28, 44, 66, 44, fill="#FFFFFF", width=3)
        canvas.create_text(
            27,
            72,
            anchor="w",
            text="编码工坊",
            fill="#FFFFFF",
            font=(FONT_FAMILY, 24, "bold"),
        )
        canvas.create_text(
            29,
            111,
            anchor="w",
            text="从字符到字节，让每一个编码步骤都清晰可见。",
            fill="#E0E7FF",
            font=(FONT_FAMILY, 11),
        )

    def parse_input(self):
        """调用算法层解析文本，并刷新原有字符编码卡片。"""
        text = self.input_var.get()
        self._clear_character_cards()
        self._records.clear()

        charset = self.charset_var.get()
        primary = "utf-8" if charset == "UTF-8" else "gbk"
        response = encode_text(text, primary)
        if not response["ok"]:
            self.status_label.configure(text=response["message"], fg=COLOR_ERROR)
            self._clear_details()
            return

        bitstream = text_to_bitstream(text, primary)
        decimal_text = text.strip()
        decimal_response = None
        if decimal_text.isdigit():
            # 纯数字输入时，额外在最左侧插入十进制转二进制的竖式卡片（T-03）。
            decimal_response = decimal_to_binary(decimal_text)
            self._create_decimal_card(decimal_response)
        for index, item in enumerate(response["result"]["chars"]):
            record = {
                "char": item["char"],
                "codepoint": item["code_point"],
                "utf8": item["utf8"]["bytes"],
                "gbk": item["gbk"]["bytes"],
            }
            self._records.append(record)
            self._create_character_card(index, record)

        if bitstream["ok"]:
            status = (
                f"解析完成 · {len(text)} 个字符 · 当前位流采用 {charset} · "
                f"{bitstream['message']}"
            )
            color = COLOR_PASS
        else:
            status = (
                f"解析完成 · {len(text)} 个字符 · 当前位流采用 {charset}，"
                "部分内容无法编码"
            )
            color = COLOR_ERROR
        if decimal_response is not None:
            if decimal_response["ok"]:
                status += (
                    f" · 十进制 {decimal_response['result']['value']} → "
                    f"{decimal_response['result']['binary']}"
                )
            else:
                status += f" · {decimal_response['message']}"
        self.status_label.configure(text=status, fg=color)
        self._select_character(0)

    def _open_base_convert_dialog(self):
        """打开十进制转二进制的竖式换算窗口（对应验收项 T-03）。"""
        existing = getattr(self, "_convert_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return

        dialog = tk.Toplevel(self)
        self._convert_dialog = dialog
        dialog.title("十进制 → 二进制")
        dialog.configure(bg=COLOR_BACKGROUND)
        dialog.geometry("580x480")
        dialog.transient(self.winfo_toplevel())

        card = tk.Frame(
            dialog, bg="#FFFFFF", highlightbackground="#D5DDE9",
            highlightthickness=1,
        )
        card.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Frame(card, bg=COLOR_PRIMARY, height=3).pack(fill="x")

        tk.Label(
            card, text="十进制转二进制 · 除 2 取余竖式", bg="#FFFFFF",
            fg="#172033", font=(FONT_FAMILY, 13, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row = tk.Frame(card, bg="#FFFFFF")
        row.pack(fill="x", padx=16)
        tk.Label(
            row, text="十进制整数", bg="#FFFFFF", fg="#334155", font=FONT_BOLD,
        ).pack(side="left")
        value_var = tk.StringVar(value="78")
        entry = tk.Entry(
            row, textvariable=value_var, width=10, bg="#F5F7FB", fg="#1E293B",
            insertbackground=COLOR_PRIMARY, font=("Consolas", 13),
            relief="solid", bd=1,
        )
        entry.pack(side="left", padx=(12, 12), ipady=4)

        result_label = tk.Label(
            card, text="", bg="#FFFFFF", fg=COLOR_PRIMARY,
            font=("Consolas", 13, "bold"), anchor="w",
        )
        result_label.pack(fill="x", padx=16, pady=(10, 4))

        ladder = tk.Text(
            card, height=9, bg="#F8FAFD", fg="#1E293B",
            font=("Consolas", 12), relief="flat", bd=0, padx=12, pady=8,
        )
        ladder.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        hint = tk.Label(
            card, text="", bg="#FFFFFF", fg="#718096",
            font=(FONT_FAMILY, 10), anchor="w", justify="left", wraplength=520,
        )
        hint.pack(fill="x", padx=16, pady=(0, 10))

        def convert():
            response = decimal_to_binary(value_var.get())
            ladder.configure(state="normal")
            ladder.delete("1.0", "end")
            if not response["ok"]:
                result_label.configure(text="无法换算", fg=COLOR_ERROR)
                ladder.insert("1.0", response["message"])
                hint.configure(text="")
            else:
                lines = [
                    f"{item['dividend']:>5} ÷ 2 = {item['quotient']:>5}   …   余 {item['remainder']}"
                    for item in response["result"]["rows"]
                ]
                lines.append("")
                lines.append(
                    f"从下往上读余数  →  {response['result']['binary']}"
                )
                ladder.insert("1.0", "\n".join(lines))
                result_label.configure(
                    text=f"二进制结果  {response['result']['binary']}",
                    fg=COLOR_PRIMARY,
                )
                hint.configure(
                    text=f"共 {response['result']['width']} 位 · {response['message']}",
                )
            ladder.configure(state="disabled")

        tk.Button(
            row, text="换算", command=convert, bg=COLOR_PRIMARY, fg="#FFFFFF",
            activebackground="#1D4ED8", activeforeground="#FFFFFF",
            font=FONT_BOLD, relief="flat", bd=0, padx=18, pady=6,
            cursor="hand2",
        ).pack(side="left")
        entry.bind("<Return>", lambda event: convert())
        convert()
        dialog.update_idletasks()
        x = self.winfo_toplevel().winfo_rootx() + 90
        y = self.winfo_toplevel().winfo_rooty() + 70
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _selected_encoding_key(self):
        return "utf8" if self.charset_var.get() == "UTF-8" else "gbk"

    def _show_conversion_steps(self, index):
        self._update_card_selection(index)
        record = self._records[index]
        char = self._display_char(record["char"])
        codepoint = record["codepoint"]
        charset = self.charset_var.get()
        selected_bytes = record[self._selected_encoding_key()]

        self.detail_char_canvas.delete("all")
        _rounded_rectangle(
            self.detail_char_canvas,
            2,
            2,
            60,
            60,
            16,
            fill="#4F46E5",
            outline="",
        )
        self.detail_char_canvas.create_text(
            31,
            31,
            text=char,
            fill="#FFFFFF",
            font=(FONT_FAMILY, 21 if len(char) > 1 else 29, "bold"),
        )
        self.detail_codepoint.configure(
            text=f"U+{codepoint:04X}  ·  DEC {codepoint}",
        )
        self.detail_encoding.configure(text=f"{charset} 字节视图")
        self._update_byte_chips(selected_bytes)

        self.step_description_labels["unicode"].configure(
            text=f"字符「{char}」对应 U+{codepoint:04X}，十进制码点为 {codepoint}。",
        )

        if record["utf8"] is not None:
            utf8_text = (
                f"{self._utf8_rule(codepoint)}；"
                f"编码结果为 {self._hex_bytes(record['utf8'])}。"
            )
        else:
            utf8_text = "当前字符无法进行 UTF-8 编码。"
        self.step_description_labels["utf8"].configure(text=utf8_text)

        if record["gbk"] is not None:
            gbk_text = (
                f"通过 GBK 字符映射表转换，得到 "
                f"{self._hex_bytes(record['gbk'])}。"
            )
        else:
            gbk_text = "当前字符不在 GBK 字符集中，无法生成对应字节。"
        self.step_description_labels["gbk"].configure(text=gbk_text)

    def _update_byte_chips(self, data):
        for child in self.byte_frame.winfo_children():
            child.destroy()

        if data is None:
            tk.Label(
                self.byte_frame,
                text="当前字符集不支持",
                bg="#F3F5FC",
                fg=COLOR_ERROR,
                font=FONT_BOLD,
            ).pack(pady=12)
            self.detail_bit_count.configure(text="没有可显示的位流")
            return

        for byte in data:
            chip = tk.Frame(
                self.byte_frame,
                bg="#FFFFFF",
                highlightbackground="#D6DDF0",
                highlightthickness=1,
            )
            chip.pack(side="left", padx=3)
            tk.Label(
                chip,
                text=f"{byte:02X}",
                bg="#FFFFFF",
                fg=COLOR_PRIMARY,
                font=("Consolas", 12, "bold"),
            ).pack(padx=8, pady=(5, 0))
            tk.Label(
                chip,
                text=f"{byte:08b}",
                bg="#FFFFFF",
                fg="#64748B",
                font=("Consolas", 9),
            ).pack(padx=5, pady=(1, 5))

        self.detail_bit_count.configure(
            text=f"{len(data)} 字节  ·  {len(data) * 8} 位",
        )

    def _clear_details(self):
        self.detail_char_canvas.delete("all")
        _rounded_rectangle(
            self.detail_char_canvas,
            2,
            2,
            60,
            60,
            16,
            fill="#CBD5E1",
            outline="",
        )
        self.detail_char_canvas.create_text(
            31, 31, text="—", fill="#FFFFFF", font=(FONT_FAMILY, 25, "bold"),
        )
        self.detail_codepoint.configure(text="等待输入")
        self.detail_encoding.configure(text="字节视图")
        self.detail_bit_count.configure(text="")
        for child in self.byte_frame.winfo_children():
            child.destroy()
        for label in self.step_description_labels.values():
            label.configure(text="输入并解析字符后显示换算信息。")

    @staticmethod
    def _display_char(char):
        return {" ": "空格", "\t": "Tab", "\n": "换行", "\r": "回车"}.get(char, char)

    @staticmethod
    def _hex_bytes(data):
        return bytes(data).hex(" ").upper() if data is not None else "不支持"

    @staticmethod
    def _utf8_rule(codepoint):
        if codepoint <= 0x7F:
            return "码点位于单字节范围，直接表示"
        if codepoint <= 0x7FF:
            return "按双字节 UTF-8 模板拆分"
        if codepoint <= 0xFFFF:
            return "按三字节 UTF-8 模板拆分"
        return "按四字节 UTF-8 模板拆分"


__all__ = ["EncodingView"]


if __name__ == "__main__":
    root = tk.Tk()
    root.title("编码工坊")
    window_width, window_height = 1100, 740
    x = max((root.winfo_screenwidth() - window_width) // 2, 0)
    y = max((root.winfo_screenheight() - window_height) // 2, 0)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.minsize(1000, 680)
    EncodingView(root).pack(fill="both", expand=True)

    # 独立预览时将窗口置前，避免被编辑器遮挡。
    root.update_idletasks()
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    root.after(800, lambda: root.attributes("-topmost", False))
    root.mainloop()
