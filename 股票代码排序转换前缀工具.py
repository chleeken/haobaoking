# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
from datetime import datetime

FONT = ("宋体", 18)
ENCODING = "utf-8"
BACKUP_SUFFIX = "_pak"  # 修改为原文件名+_pak
PROG_DIR = os.path.dirname(os.path.abspath(__file__))

class StockSortTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("股票代码排序工具")
        self.geometry("1200x650")
        self.current_file = None
        self.stock_items = []  # 列表元素：(原始字符串, 纯数字)
        self.sorted_items = []

        self._init_ui()

    def _init_ui(self):
        # 工具栏
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        self.btn_open = tk.Button(toolbar, text="打开", font=FONT, command=self.open_file)
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.btn_sort = tk.Button(toolbar, text="排序", font=FONT, command=self.do_sort)
        self.btn_sort.pack(side=tk.LEFT, padx=5)

        self.btn_convert = tk.Button(toolbar, text="转化", font=FONT, command=self.convert_and_save, bg="lightblue")
        self.btn_convert.pack(side=tk.LEFT, padx=5)

        self.btn_add_prefix = tk.Button(toolbar, text="一键加前缀(sh/sz)", font=FONT, command=self.add_prefix)
        self.btn_add_prefix.pack(side=tk.LEFT, padx=5)

        self.btn_del_prefix = tk.Button(toolbar, text="一键去前缀", font=FONT, command=self.del_prefix)
        self.btn_del_prefix.pack(side=tk.LEFT, padx=5)

        self.btn_save = tk.Button(toolbar, text="保存结果", font=FONT, command=self.save_result)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        # 左右显示区域 - 使用grid确保对称
        display_frame = tk.Frame(self)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置grid列权重，使左右等宽
        display_frame.grid_columnconfigure(0, weight=1)
        display_frame.grid_columnconfigure(1, weight=1)
        display_frame.grid_rowconfigure(0, weight=1)

        # 左边：原始
        left_frame = tk.Frame(display_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        
        tk.Label(left_frame, text="原始股票代码", font=FONT).pack()
        
        # 为左边添加滚动条
        left_text_frame = tk.Frame(left_frame)
        left_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.txt_original = tk.Text(left_text_frame, font=FONT, wrap=tk.NONE)
        self._add_scroll(self.txt_original, left_text_frame)

        # 右边：排序后
        right_frame = tk.Frame(display_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        
        tk.Label(right_frame, text="排序后股票代码", font=FONT).pack()
        
        # 为右边添加滚动条
        right_text_frame = tk.Frame(right_frame)
        right_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.txt_sorted = tk.Text(right_text_frame, font=FONT, wrap=tk.NONE)
        self._add_scroll(self.txt_sorted, right_text_frame)

    def _add_scroll(self, text_widget, frame):
        """为文本组件添加滚动条"""
        # 垂直滚动条
        y_scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 水平滚动条
        x_scrollbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 配置文本组件的滚动
        text_widget.config(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _parse_line(self, line):
        """解析一行，提取股票代码的数字部分"""
        s = line.strip()
        if not s:
            return None
        
        lower = s.lower()
        # 去除前缀
        if lower.startswith("sh") or lower.startswith("sz"):
            num_str = s[2:]
        else:
            num_str = s
        
        # 提取数字部分（可能包含其他字符，如空格）
        num_str = ''.join(filter(str.isdigit, num_str))
        
        try:
            # 如果长度不足6位，在前面补0
            if len(num_str) < 6:
                num_str = num_str.zfill(6)
            num = int(num_str)
        except:
            # 如果转换失败，返回一个很大的数，确保排到最后
            num = 999999999
        
        return (s, num)

    def _backup(self, src_path):
        """备份文件 - 备份文件名为原文件名+_pak.后缀"""
        try:
            dirname = os.path.dirname(src_path)
            fname = os.path.basename(src_path)
            base, ext = os.path.splitext(fname)
            
            # 备份文件名：原文件名_pak.后缀
            bak = f"{base}{BACKUP_SUFFIX}{ext}"
            bak_path = os.path.join(dirname, bak)
            
            # 如果备份文件已存在，添加数字后缀
            counter = 1
            while os.path.exists(bak_path):
                bak = f"{base}{BACKUP_SUFFIX}_{counter}{ext}"
                bak_path = os.path.join(dirname, bak)
                counter += 1
            
            shutil.copy2(src_path, bak_path)
            return bak_path
        except Exception as e:
            messagebox.showerror("备份失败", str(e))
            return None

    def open_file(self):
        path = filedialog.askopenfilename(
            initialdir=PROG_DIR,
            title="选择股票代码文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not path:
            return

        # 备份文件
        bak_path = self._backup(path)
        
        try:
            with open(path, "r", encoding=ENCODING) as f:
                lines = [line.rstrip('\n') for line in f if line.strip()]

            # 解析每一行
            self.stock_items = []
            for line in lines:
                parsed = self._parse_line(line)
                if parsed:
                    self.stock_items.append(parsed)
            
            self.current_file = path

            # 显示原始内容
            self.txt_original.delete(1.0, tk.END)
            self.txt_original.insert(tk.END, "\n".join([item[0] for item in self.stock_items]))
            
            # 清空排序显示
            self.txt_sorted.delete(1.0, tk.END)
            self.sorted_items = []
            
            # 显示成功消息
            msg = f"文件打开成功"
            if bak_path:
                msg += f"，已备份为：{os.path.basename(bak_path)}"
            self._auto_msg(msg)
            
        except Exception as e:
            messagebox.showerror("错误", f"打开失败：{str(e)}")

    def do_sort(self):
        """排序功能：按照 000001 → 300001 → 600001 的顺序"""
        if not self.stock_items:
            messagebox.showwarning("提示", "请先打开文件")
            return
        
        # 排序：按数字从小到大
        self.sorted_items = sorted(self.stock_items, key=lambda x: (x[1], x[0]))
        
        # 显示排序结果
        show_text = "\n".join([item[0] for item in self.sorted_items])
        self.txt_sorted.delete(1.0, tk.END)
        self.txt_sorted.insert(tk.END, show_text)
        
        self._auto_msg("排序完成")
        
    def convert_and_save(self):
        """转化并保存到原文件"""
        if not self.stock_items:
            messagebox.showwarning("提示", "请先打开文件")
            return
        
        if not self.current_file:
            messagebox.showwarning("提示", "没有打开的文件")
            return
        
        # 先排序
        self.do_sort()
        
        if not self.sorted_items:
            return
        
        # 备份原文件
        bak_path = self._backup(self.current_file)
        
        try:
            # 保存排序结果到原文件
            with open(self.current_file, "w", encoding=ENCODING) as f:
                for item in self.sorted_items:
                    f.write(item[0] + "\n")
            
            # 更新原始显示区域为排序后的内容（保持同步）
            self.stock_items = self.sorted_items.copy()
            self.txt_original.delete(1.0, tk.END)
            self.txt_original.insert(tk.END, "\n".join([item[0] for item in self.stock_items]))
            
            msg = f"转化成功，已保存到原文件"
            if bak_path:
                msg += f"，备份文件：{os.path.basename(bak_path)}"
            self._auto_msg(msg)
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{str(e)}")

    def _add_prefix_one(self, code):
        """为单个代码添加前缀"""
        c = code.strip()
        lower_c = c.lower()
        
        # 如果已经有前缀，保持不变
        if lower_c.startswith("sh") or lower_c.startswith("sz"):
            return c
        
        # 提取数字部分
        num_part = ''.join(filter(str.isdigit, c))
        if len(num_part) != 6:
            return c  # 不是6位数字，保持不变
        
        # 根据首位判断前缀
        if num_part.startswith(('0', '3')):
            return f"sz{num_part}"
        elif num_part.startswith('6'):
            return f"sh{num_part}"
        else:
            return c

    def add_prefix(self):
        """一键添加前缀"""
        if not self.stock_items:
            messagebox.showwarning("提示", "请先打开文件")
            return
        
        new_items = []
        for raw, num in self.stock_items:
            new_raw = self._add_prefix_one(raw)
            # 重新解析，更新数字部分
            new_parsed = self._parse_line(new_raw)
            if new_parsed:
                new_items.append(new_parsed)
        
        if new_items:
            self.stock_items = new_items
            self.txt_original.delete(1.0, tk.END)
            self.txt_original.insert(tk.END, "\n".join([item[0] for item in self.stock_items]))
            
            # 清空排序结果
            self.txt_sorted.delete(1.0, tk.END)
            self.sorted_items = []
            
            self._auto_msg("已自动添加前缀")

    def _del_prefix_one(self, s):
        """为单个代码去除前缀"""
        lower = s.lower()
        if lower.startswith("sh"):
            return s[2:]
        elif lower.startswith("sz"):
            return s[2:]
        else:
            return s

    def del_prefix(self):
        """一键去除前缀"""
        if not self.stock_items:
            messagebox.showwarning("提示", "请先打开文件")
            return
        
        new_items = []
        for raw, num in self.stock_items:
            new_raw = self._del_prefix_one(raw)
            # 重新解析，更新数字部分
            new_parsed = self._parse_line(new_raw)
            if new_parsed:
                new_items.append(new_parsed)
        
        if new_items:
            self.stock_items = new_items
            self.txt_original.delete(1.0, tk.END)
            self.txt_original.insert(tk.END, "\n".join([item[0] for item in self.stock_items]))
            
            # 清空排序结果
            self.txt_sorted.delete(1.0, tk.END)
            self.sorted_items = []
            
            self._auto_msg("已去除所有前缀")

    def save_result(self):
        """保存排序结果"""
        if not self.sorted_items:
            messagebox.showwarning("提示", "请先完成排序")
            return
        
        path = filedialog.asksaveasfilename(
            initialdir=PROG_DIR,
            title="保存排序后文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            defaultextension=".txt"
        )
        if not path:
            return
        
        try:
            with open(path, "w", encoding=ENCODING) as f:
                for item in self.sorted_items:
                    f.write(item[0] + "\n")
            self._auto_msg("保存成功")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{str(e)}")

    def _auto_msg(self, msg):
        """显示自动消失的提示消息"""
        win = tk.Toplevel(self)
        win.title("提示")
        win.geometry("400x120")
        win.resizable(False, False)
        
        # 让窗口居中
        win.update_idletasks()
        x = (win.winfo_screenwidth() - win.winfo_width()) // 2
        y = (win.winfo_screenheight() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")
        
        tk.Label(win, text=msg, font=FONT, wraplength=380).pack(expand=True)
        self.after(2000, win.destroy)

if __name__ == "__main__":
    app = StockSortTool()
    app.mainloop()