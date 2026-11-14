"""项目公共 Tkinter 控件。"""

import tkinter as tk

from app.common.theme import (
    COLOR_BACKGROUND,
    COLOR_PRIMARY,
    FONT_BOLD,
    FONT_FAMILY,
    FONT_NORMAL,
)


class BitStrip(tk.Frame):
    """位串条：从左到右显示二进制位，索引从 0 开始。"""

    def __init__(self, master, bits="", highlights=None, **kwargs):
        kwargs.setdefault("bg", COLOR_BACKGROUND)
        super().__init__(master, **kwargs)

        self._bits = ""
        self._labels = []
        self._strip = tk.Frame(self, bg=self.cget("bg"))
        self._strip.pack(anchor="w")
        self.set_bits(bits, highlights)

    def set_bits(self, bits, highlights=None):
        """替换位串，并可同时指定需要高亮的位索引。"""
        bits = str(bits)
        if any(bit not in "01" for bit in bits):
            raise ValueError("位串只能包含字符 0 和 1")

        self._bits = bits
        for label in self._labels:
            label.destroy()
        self._labels.clear()

        for index, bit in enumerate(bits):
            label = tk.Label(
                self._strip,
                text=bit,
                width=2,
                height=1,
                bg="#FFFFFF",
                fg="#1E293B",
                font=(FONT_FAMILY, 12, "bold"),
                relief="solid",
                bd=1,
            )
            label.grid(row=0, column=index, padx=(0, 4))
            self._labels.append(label)

        self.highlight([] if highlights is None else highlights)

    def highlight(self, indices):
        """高亮指定索引的位，传入空列表可清除全部高亮。"""
        if isinstance(indices, int):
            indices = [indices]

        indices = set(indices)
        if any(index < 0 or index >= len(self._bits) for index in indices):
            raise IndexError("高亮位索引超出位串范围")

        for index, label in enumerate(self._labels):
            selected = index in indices
            label.configure(
                bg=COLOR_PRIMARY if selected else "#FFFFFF",
                fg="#FFFFFF" if selected else "#1E293B",
            )

    def clear_highlights(self):
        self.highlight([])


class StepTable(tk.Frame):
    """两列步骤表，每一步由标题和说明组成。"""

    def __init__(self, master, steps=None, **kwargs):
        kwargs.setdefault("bg", "#CBD5E1")
        kwargs.setdefault("highlightbackground", "#CBD5E1")
        kwargs.setdefault("highlightthickness", 1)
        super().__init__(master, **kwargs)

        self._row_widgets = []
        self.columnconfigure(0, weight=1, uniform="step_columns")
        self.columnconfigure(1, weight=2, uniform="step_columns")

        self._create_header()
        self.bind("<Configure>", self._update_wrap_lengths)
        if steps:
            self.set_steps(steps)

    def _create_header(self):
        for column, text in enumerate(("标题", "说明")):
            label = tk.Label(
                self,
                text=text,
                bg=COLOR_PRIMARY,
                fg="#FFFFFF",
                font=FONT_BOLD,
                anchor="w",
                padx=14,
                pady=10,
            )
            label.grid(row=0, column=column, sticky="nsew", pady=(0, 1))

    def set_steps(self, steps):
        """替换全部步骤，steps 为（标题，说明）二元组的可迭代对象。"""
        self.clear()
        for title, description in steps:
            self.add_step(title, description)

    def add_step(self, title, description):
        """在表格末尾添加一步。"""
        row = len(self._row_widgets) + 1
        background = "#FFFFFF" if row % 2 else "#F8FAFC"
        title_label = tk.Label(
            self,
            text=str(title),
            bg=background,
            fg="#1E293B",
            font=FONT_BOLD,
            anchor="w",
            justify="left",
            padx=14,
            pady=10,
        )
        description_label = tk.Label(
            self,
            text=str(description),
            bg=background,
            fg="#475569",
            font=FONT_NORMAL,
            anchor="w",
            justify="left",
            padx=14,
            pady=10,
        )
        title_label.grid(row=row, column=0, sticky="nsew", pady=(0, 1))
        description_label.grid(row=row, column=1, sticky="nsew", pady=(0, 1))
        self._row_widgets.append((title_label, description_label))
        self._update_wrap_lengths()

    def clear(self):
        """清空全部步骤，保留表头。"""
        for row_widgets in self._row_widgets:
            for widget in row_widgets:
                widget.destroy()
        self._row_widgets.clear()

    def _update_wrap_lengths(self, event=None):
        width = max(self.winfo_width(), 240)
        title_width = max(int(width / 3) - 30, 80)
        description_width = max(int(width * 2 / 3) - 30, 120)
        for title_label, description_label in self._row_widgets:
            title_label.configure(wraplength=title_width)
            description_label.configure(wraplength=description_width)


__all__ = ["BitStrip", "StepTable"]
