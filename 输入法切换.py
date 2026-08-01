import tkinter as tk
import ctypes
from ctypes import wintypes
import sys
import threading

# 托盘依赖
try:
    import pystray
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "pillow"])
    import pystray
    from PIL import Image

# 输入法控制
user32 = ctypes.WinDLL('user32', use_last_error=True)
HKL = wintypes.HKL
user32.ActivateKeyboardLayout.restype = HKL
user32.ActivateKeyboardLayout.argtypes = [HKL, wintypes.UINT]
ENGLISH_LAYOUT = 0x04090409

def set_chinese():
    user32.ActivateKeyboardLayout(0, 0)

def set_english():
    user32.ActivateKeyboardLayout(ENGLISH_LAYOUT, 0)

# ================== 主窗口 ==================
root = tk.Tk()
root.title("输入法强制锁定（带停止）")
root.geometry("310x190")
root.resizable(False, False)

# 单选变量：zh=中文 en=英文 stop=停止
mode_var = tk.StringVar(value="zh")

def on_mode_change():
    mode = mode_var.get()
    if mode == "zh":
        set_chinese()
    elif mode == "en":
        set_english()
    # stop：什么都不做，不再切换

# 界面
frame = tk.Frame(root, padx=25, pady=25)
frame.pack(expand=True, fill=tk.BOTH)

tk.Radiobutton(
    frame, text="中文（默认）", variable=mode_var, value="zh",
    command=on_mode_change, font=("微软雅黑", 12)
).pack(anchor=tk.W, pady=4)

tk.Radiobutton(
    frame, text="英文", variable=mode_var, value="en",
    command=on_mode_change, font=("微软雅黑", 12)
).pack(anchor=tk.W, pady=4)

tk.Radiobutton(
    frame, text="停止（不切换）", variable=mode_var, value="stop",
    command=on_mode_change, font=("微软雅黑", 12)
).pack(anchor=tk.W, pady=4)

# 启动默认中文
set_chinese()

# ================== 托盘 ==================
icon = None

def create_icon():
    global icon
    img = Image.new('RGB', (64, 64), color='#2D8CF0')
    icon = pystray.Icon(
        "input_switcher",
        img,
        "输入法锁定",
        menu=(
            pystray.MenuItem("显示窗口", lambda: (root.deiconify(), root.focus_force())),
            pystray.MenuItem("退出", lambda: (icon.stop(), root.destroy(), sys.exit()))
        )
    )

def to_tray():
    root.withdraw()

root.protocol("WM_DELETE_WINDOW", to_tray)

if __name__ == "__main__":
    create_icon()
    threading.Thread(target=icon.run, daemon=True).start()
    root.mainloop()
