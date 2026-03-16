# --*-- Coding: UTF-8 --*--
#! filename: __main__.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 主入口， 默认启动CLI程序
# 如需运行gui输入： python chat/gui.py Or pythonw chat\gui.py
import sys
import ctypes
from error_handling import _DEBUG_MODE


def hide_console():
    """
    在Windows下隐藏控制台
    """
    if sys.platform == "win32":
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window != 0:
            ctypes.windll.user32.ShowWindow(console_window, 0)  # SW_HIDE


if (not _DEBUG_MODE) and "gui" in sys.argv:
    hide_console()

if __name__ == "__main__":
    if sys.platform == "win32":
        from cli import app

        app()
    else:
        print("目前应用程序只能在Windows平台上正常运行， 其他平台敬请期待……")
