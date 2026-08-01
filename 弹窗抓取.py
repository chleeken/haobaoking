# -*- coding: utf-8 -*-
import tkinter as tk
import ctypes
import ctypes.wintypes
import pyperclip
import threading
import time
import logging
from typing import Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("popup_monitor.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 只抓【弹窗类窗口】的类名
TARGET_CLASSES = {
    "#32770",    # 系统弹窗、MessageBox
    "TForm",     # Delphi/C++Builder 弹窗
    "TMessageForm",
    "MessageBoxW"
}

last_popup_text = ""
last_hwnd: Optional[int] = None
is_running = True

# 定义Windows API函数的参数和返回值类型
user32 = ctypes.windll.user32
user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
user32.GetClassNameW.argtypes = (ctypes.wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int)
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = (ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT))
user32.GetWindowRect.restype = ctypes.c_bool
user32.GetWindowTextW.argtypes = (ctypes.wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int)
user32.GetWindowTextW.restype = ctypes.c_int

# 定义EnumChildWindows的回调函数类型
EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

def get_popup_text(hwnd: int) -> str:
    """获取弹窗内的文本内容"""
    try:
        if not hwnd:
            return ""

        text_parts = []

        def enum_child_callback(hwnd_child: int, lParam: int) -> bool:
            try:
                # 获取控件类名
                cls_buf = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd_child, cls_buf, 64)
                cls_name = cls_buf.value.strip()

                # 只抓取文本显示类控件
                if cls_name in ("Static", "Edit", "TEdit", "TLabel"):
                    txt_buf = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(hwnd_child, txt_buf, 512)
                    txt = txt_buf.value.strip()
                    if txt and len(txt) > 1:
                        text_parts.append(txt)
            except Exception as e:
                logger.debug(f"枚举子控件失败: {e}")
            return True

        # 转换回调函数并调用
        callback = EnumChildProc(enum_child_callback)
        user32.EnumChildWindows(hwnd, callback, 0)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"获取弹窗文本失败: {e}")
        return ""

def is_valid_popup(hwnd: int) -> Tuple[bool, str]:
    """判断窗口是否为有效弹窗"""
    try:
        if not hwnd:
            return False, ""

        # 获取窗口类名
        cls_buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls_buf, 64)
        cls_name = cls_buf.value.strip()

        if cls_name not in TARGET_CLASSES:
            return False, cls_name

        # 检查窗口大小，过滤过小的控件
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width < 100 or height < 50:
            return False, "窗口过小"

        return True, cls_name
    except Exception as e:
        logger.error(f"检查弹窗有效性失败: {e}")
        return False, str(e)

def monitor_popup():
    """主监控循环"""
    global last_popup_text, last_hwnd

    while is_running:
        try:
            # 获取前台窗口
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                time.sleep(0.5)
                continue

            # 检查是否为有效弹窗
            is_popup, cls_name = is_valid_popup(hwnd)
            if not is_popup:
                time.sleep(0.5)
                continue

            # 获取弹窗文本
            popup_text = get_popup_text(hwnd)
            if not popup_text:
                time.sleep(0.5)
                continue

            # 去重：避免重复复制同一个弹窗
            if hwnd == last_hwnd and popup_text == last_popup_text:
                time.sleep(0.5)
                continue

            # 复制到剪贴板
            try:
                pyperclip.copy(popup_text)
                last_hwnd = hwnd
                last_popup_text = popup_text
                logger.info(f"已复制弹窗文本: {popup_text[:50]}...")
                root.after(0, lambda: show_status(f"已复制: {popup_text[:20]}..."))
            except Exception as e:
                logger.error(f"复制到剪贴板失败: {e}")

        except Exception as e:
            logger.error(f"监控循环异常: {e}")
            time.sleep(1)  # 异常后延长等待时间，避免CPU占用过高

        time.sleep(0.3)

def show_status(msg: str):
    """更新状态栏提示"""
    status_label.config(text=msg)
    root.after(1000, lambda: status_label.config(text=""))

def on_closing():
    """窗口关闭时的清理操作"""
    global is_running
    is_running = False
    logger.info("程序正在退出...")
    root.destroy()

# ==================== GUI ====================
root = tk.Tk()
root.title("弹窗自动抓取工具 v2.1")
root.geometry("400x120")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_closing)

frame = tk.Frame(root, padx=15, pady=15)
frame.pack(expand=True, fill=tk.BOTH)

title_label = tk.Label(
    frame,
    text="✅ 已启动：自动抓取弹窗文字",
    font=("宋体", 14, "bold")
)
title_label.pack()

status_label = tk.Label(
    frame,
    text="",
    fg="green",
    font=("宋体", 12)
)
status_label.pack(pady=8)

# 启动监控线程
monitor_thread = threading.Thread(target=monitor_popup, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.critical(f"程序异常退出: {e}")
