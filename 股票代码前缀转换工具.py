import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog

def main():
    root = tk.Tk()
    root.title("股票代码前缀转换工具")
    root.geometry("900x600")

    current_file = None
    mode = tk.IntVar(value=1)

    # -------------------- 自动关闭弹窗通用函数 --------------------
    def auto_close_msg(title, msg, msg_type="info", timeout=1000):
        top = tk.Toplevel(root)
        top.title(title)
        top.geometry("300x120")
        top.resizable(False, False)
        top.transient(root)
        top.grab_set()

        # 居中
        x = (root.winfo_screenwidth() - top.winfo_reqwidth()) // 2
        y = (root.winfo_screenheight() - top.winfo_reqheight()) // 2
        top.geometry(f"+{x}+{y}")

        # 图标
        if msg_type == "info":
            icon = "ℹ️"
            color = "#0078D7"
        elif msg_type == "warning":
            icon = "⚠️"
            color = "#FF8C00"
        else:
            icon = "❌"
            color = "#E63946"

        tk.Label(top, text=icon, font=("Arial", 24), fg=color).pack(pady=(10, 0))
        tk.Label(top, text=msg, wraplength=250, justify="center").pack(pady=5)

        btn = ttk.Button(top, text="确定", command=top.destroy)
        btn.pack(pady=5)

        top.after(timeout, top.destroy)

    # -------------------- 打开文件 --------------------
    def open_file():
        nonlocal current_file
        filepath = filedialog.askopenfilename(
            title="选择文本文件",
            initialdir=os.getcwd(),
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        current_file = filepath
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            text_original.delete(1.0, tk.END)
            text_original.insert(tk.END, content)
        except Exception as e:
            auto_close_msg("错误", f"打开失败：{str(e)}", msg_type="error")

    # -------------------- 转换并保存 --------------------
    def convert_and_save():
        if not current_file or not os.path.isfile(current_file):
            auto_close_msg("提示", "请先打开文件", msg_type="warning")
            return

        backup_path = current_file + ".pak"
        try:
            shutil.copy(current_file, backup_path)
        except Exception as e:
            auto_close_msg("错误", f"备份失败：{str(e)}", msg_type="error")
            return

        lines = text_original.get(1.0, tk.END).splitlines()
        converted = []

        for line in lines:
            s = line.strip()
            if not s:
                converted.append("")
                continue

            if mode.get() == 1:
                first = s[0]
                if first == "6":
                    converted.append(f"sh.{s}")
                elif first in ("0", "3"):
                    converted.append(f"sz.{s}")
                else:
                    converted.append(s)
            else:
                if s.startswith("sh."):
                    converted.append(s[3:])
                elif s.startswith("sz."):
                    converted.append(s[3:])
                else:
                    converted.append(s)

        result_text = "\n".join(converted)
        text_converted.delete(1.0, tk.END)
        text_converted.insert(tk.END, result_text)

        try:
            with open(current_file, "w", encoding="utf-8") as f:
                f.write(result_text)
        except Exception as e:
            auto_close_msg("错误", f"保存失败：{str(e)}", msg_type="error")
            return

        auto_close_msg("完成", f"转换成功！\n备份：{os.path.basename(backup_path)}", msg_type="info")

    # ==================== 界面布局 ====================
    frame_top = ttk.Frame(root)
    frame_top.pack(side=tk.TOP, fill=tk.X, pady=15, padx=10)

    ttk.Button(frame_top, text="打开", command=open_file).pack(side=tk.LEFT, padx=10)
    ttk.Button(frame_top, text="转换并保存", command=convert_and_save).pack(side=tk.LEFT, padx=10)

    ttk.Radiobutton(frame_top, text="加 sh./sz.", variable=mode, value=1).pack(side=tk.LEFT, padx=10)
    ttk.Radiobutton(frame_top, text="删 sh./sz.", variable=mode, value=2).pack(side=tk.LEFT, padx=10)

    frame_middle = ttk.Frame(root)
    frame_middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=15, pady=5)
    frame_middle.grid_columnconfigure(0, weight=1)
    frame_middle.grid_columnconfigure(1, weight=1)
    frame_middle.grid_rowconfigure(0, weight=1)

    # ========== 左边：原内容 + 滚动条 ==========
    frame_left = ttk.LabelFrame(frame_middle, text="原内容")
    frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

    text_original = tk.Text(frame_left, font=("宋体", 12), wrap=tk.WORD)
    scroll_original = ttk.Scrollbar(frame_left, command=text_original.yview)
    text_original.config(yscrollcommand=scroll_original.set)

    text_original.grid(row=0, column=0, sticky="nsew")
    scroll_original.grid(row=0, column=1, sticky="ns")
    frame_left.grid_rowconfigure(0, weight=1)
    frame_left.grid_columnconfigure(0, weight=1)

    # ========== 右边：转换后内容 + 滚动条 ==========
    frame_right = ttk.LabelFrame(frame_middle, text="转换后内容")
    frame_right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    text_converted = tk.Text(frame_right, font=("宋体", 12), wrap=tk.WORD)
    scroll_converted = ttk.Scrollbar(frame_right, command=text_converted.yview)
    text_converted.config(yscrollcommand=scroll_converted.set)

    text_converted.grid(row=0, column=0, sticky="nsew")
    scroll_converted.grid(row=0, column=1, sticky="ns")
    frame_right.grid_rowconfigure(0, weight=1)
    frame_right.grid_columnconfigure(0, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()
