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


class StepPlayer(tk.Frame):
    """逐步演示控制条：上一步、下一步、自动播放与重置。"""

    def __init__(self, master, on_step=None, interval=900, **kwargs):
        kwargs.setdefault("bg", "#FFFFFF")
        kwargs.setdefault("highlightbackground", "#D5DDE9")
        kwargs.setdefault("highlightthickness", 1)
        super().__init__(master, **kwargs)

        self._on_step = on_step
        self._interval = interval
        self._titles = []
        self._index = -1
        self._job = None

        self.columnconfigure(1, weight=1)

        tk.Label(
            self, text="逐步演示", bg=COLOR_PRIMARY, fg="#FFFFFF",
            font=(FONT_FAMILY, 9, "bold"), padx=10, pady=4,
        ).grid(row=0, column=0, padx=(10, 10), pady=8)

        self._title = tk.Label(
            self, text="生成结果后可逐步查看完整过程", bg="#FFFFFF",
            fg="#64748B", font=(FONT_FAMILY, 10), anchor="w",
        )
        self._title.grid(row=0, column=1, sticky="we", padx=(0, 10))

        self._counter = tk.Label(
            self, text="0 / 0", bg="#FFFFFF", fg="#94A3B8",
            font=(FONT_FAMILY, 10, "bold"),
        )
        self._counter.grid(row=0, column=2, padx=(0, 10))

        self._prev_button = self._make_button(
            "上一步", self.prev, "#F1F5F9", "#334155",
        )
        self._prev_button.grid(row=0, column=3, padx=(0, 6))
        self._next_button = self._make_button(
            "下一步", self.next, COLOR_PRIMARY, "#FFFFFF",
        )
        self._next_button.grid(row=0, column=4, padx=(0, 6))
        self._auto_button = self._make_button(
            "自动播放", self.toggle_auto, "#ECFDF5", "#047857",
        )
        self._auto_button.grid(row=0, column=5, padx=(0, 6))
        self._reset_button = self._make_button(
            "重置", self.reset, "#FEF2F2", "#B91C1C",
        )
        self._reset_button.grid(row=0, column=6, padx=(0, 10))

        self.bind("<Destroy>", self._on_destroy)

    @property
    def index(self):
        return self._index

    def _make_button(self, text, command, background, foreground):
        return tk.Button(
            self, text=text, command=command, bg=background, fg=foreground,
            activebackground=background, activeforeground=foreground,
            font=(FONT_FAMILY, 9, "bold"), relief="flat", bd=0,
            padx=12, pady=5, cursor="hand2",
        )

    def load(self, titles, on_step=None):
        """装载一组步骤标题，可选替换步进回调。"""
        self._stop_auto()
        if on_step is not None:
            self._on_step = on_step
        self._titles = list(titles)
        self._index = -1
        self._notify()

    def next(self):
        if self._index + 1 >= len(self._titles):
            self._stop_auto()
            return
        self._index += 1
        self._notify()

    def prev(self):
        if self._index <= 0:
            return
        self._index -= 1
        self._notify()

    def reset(self):
        self._stop_auto()
        self._index = -1
        self._notify()

    def toggle_auto(self):
        if self._job is not None:
            self._stop_auto()
            return
        if not self._titles:
            return
        if self._index + 1 >= len(self._titles):
            self._index = -1
            self._notify()
        self._auto_button.configure(text="暂停")
        self._job = self.after(260, self._auto_step)

    def _auto_step(self):
        self._job = None
        if self._index + 1 >= len(self._titles):
            self._stop_auto()
            return
        self._index += 1
        self._notify()
        if self._index + 1 >= len(self._titles):
            self._stop_auto()
        else:
            self._job = self.after(self._interval, self._auto_step)

    def _stop_auto(self):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        try:
            self._auto_button.configure(text="自动播放")
        except tk.TclError:
            pass

    def _notify(self):
        total = len(self._titles)
        if self._index < 0:
            self._counter.configure(text=f"0 / {total}")
            hint = "点击“下一步”或“自动播放”查看逐步过程"
            self._title.configure(
                text=hint if total else "暂无可演示的步骤",
            )
        else:
            self._counter.configure(text=f"{self._index + 1} / {total}")
            self._title.configure(text=self._titles[self._index])
        self._prev_button.configure(
            state="normal" if self._index > 0 else "disabled",
        )
        self._next_button.configure(
            state="normal" if self._index + 1 < total else "disabled",
        )
        if self._on_step is not None:
            self._on_step(self._index)

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None


__all__ = ["BitStrip", "StepTable", "StepPlayer"]
