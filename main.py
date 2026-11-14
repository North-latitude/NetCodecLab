"""NetCodecLab 主入口：运行本文件即可演示整套可视化实验。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    from app.views.main_window import MainWindow

    app = MainWindow()

    app.update_idletasks()
    width, height = app.winfo_width(), app.winfo_height()
    x = max((app.winfo_screenwidth() - width) // 2, 0)
    y = max((app.winfo_screenheight() - height) // 2, 0)
    app.geometry(f"+{x}+{y}")

    app.mainloop()


if __name__ == "__main__":
    main()
