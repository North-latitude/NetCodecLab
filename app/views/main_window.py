"""主窗口：把编码、校验、信道三个实验页面组合为一个应用。"""

import tkinter as tk
import tkinter.font as tkfont

from app.common.theme import COLOR_BACKGROUND, FONT_FAMILY
from app.views.channel_view import ChannelView
from app.views.checksum_view import ChecksumView
from app.views.encoding_view import EncodingView


def _rounded_rectangle(canvas, x1, y1, x2, y2, radius=13, **kwargs):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)


def _enlarge_default_fonts(delta=1):
    """放大下拉菜单等使用 Tk 默认字体的控件。"""
    for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont"):
        try:
            font = tkfont.nametofont(name)
            size = font.cget("size")
            font.configure(size=size + delta if size > 0 else size - delta)
        except tk.TclError:
            pass


class MainWindow(tk.Tk):
    """左侧导航 + 右侧页面，三个实验页面堆叠后按需置顶。"""

    PAGES = (
        ("encoding", "编码工坊", "01", "ENCODING WORKSHOP", "#6366F1", EncodingView),
        ("checksum", "校验实验室", "02", "CHECKSUM LABORATORY", "#0891B2", ChecksumView),
        ("channel", "信道模拟", "03", "CHANNEL SIMULATOR", "#10B981", ChannelView),
    )

    def __init__(self):
        super().__init__()
        _enlarge_default_fonts()

        self.title("NetCodecLab · 网络编码可视化实验室")
        self.geometry("1360x880")
        self.minsize(1200, 800)
        self.configure(bg=COLOR_BACKGROUND)

        self.nav_buttons = {}
        self.pages = {}

        self._build_sidebar()
        self._build_pages()
        self.show_page("encoding")

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg="#111827", width=236)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg="#111827")
        brand.pack(fill="x", padx=22, pady=(30, 38))

        logo = tk.Canvas(
            brand, width=48, height=48, bg="#111827",
            highlightthickness=0, bd=0,
        )
        logo.pack(side="left")
        _rounded_rectangle(logo, 2, 2, 46, 46, fill="#6366F1", outline="")
        logo.create_text(
            24, 24, text="N", fill="#FFFFFF", font=("Segoe UI", 21, "bold"),
        )

        brand_text = tk.Frame(brand, bg="#111827")
        brand_text.pack(side="left", padx=(12, 0), pady=3)
        tk.Label(
            brand_text, text="NetCodecLab", bg="#111827", fg="#FFFFFF",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand_text, text="NETWORK CODEC LAB", bg="#111827", fg="#64748B",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(3, 0))

        tk.Label(
            sidebar, text="实验模块", bg="#111827", fg="#64748B",
            font=(FONT_FAMILY, 11), anchor="w",
        ).pack(fill="x", padx=28, pady=(0, 10))

        for key, title, index, _, color, _ in self.PAGES:
            button = tk.Button(
                sidebar,
                text=f"{index}    {title}",
                command=lambda name=key: self.show_page(name),
                bg="#111827",
                fg="#94A3B8",
                activebackground="#25304A",
                activeforeground="#FFFFFF",
                relief="flat",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
                font=(FONT_FAMILY, 13, "bold"),
                anchor="w",
                padx=22,
                pady=16,
            )
            button.pack(fill="x", padx=16, pady=4)
            self.nav_buttons[key] = button

        status = tk.Frame(sidebar, bg="#192236")
        status.pack(side="bottom", fill="x", padx=18, pady=24)

        dot = tk.Canvas(
            status, width=12, height=12, bg="#192236",
            highlightthickness=0, bd=0,
        )
        dot.pack(side="left", padx=(16, 8), pady=16)
        dot.create_oval(2, 2, 10, 10, fill="#34D399", outline="")
        tk.Label(
            status, text="系统已就绪", bg="#192236", fg="#CBD5E1",
            font=(FONT_FAMILY, 11),
        ).pack(side="left")

    def _build_pages(self):
        content = tk.Frame(self, bg=COLOR_BACKGROUND)
        content.pack(side="right", fill="both", expand=True)
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        for key, _, _, _, _, view_class in self.PAGES:
            page = view_class(content)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = page

    def show_page(self, key):
        """切换到指定实验页面，并同步侧边栏选中状态。"""
        self.pages[key].tkraise()

        for name, button in self.nav_buttons.items():
            selected = name == key
            accent = next(color for page, _, _, _, color, _ in self.PAGES if page == name)
            button.configure(
                bg=accent if selected else "#111827",
                fg="#FFFFFF" if selected else "#94A3B8",
                activebackground=accent if selected else "#25304A",
            )


if __name__ == "__main__":
    MainWindow().mainloop()
