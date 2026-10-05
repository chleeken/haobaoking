import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

class LineRemoverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("按开头代码删除文件行工具")
        self.geometry("800x600")
        self.option_add("*Font", "SimSun 10")
        
        # 选中的文件列表
        self.file_paths = []
        
        self.build_ui()
    
    def build_ui(self):
        # 1. 顶部配置区
        frame_config = ttk.Frame(self)
        frame_config.pack(fill="x", padx=10, pady=10)
        
        # 代码输入框
        ttk.Label(frame_config, text="输入开头代码（如 sh.600）：").grid(row=0, column=0, sticky="w", padx=5)
        self.code_entry = ttk.Entry(frame_config, width=30)
        self.code_entry.grid(row=0, column=1, padx=5, pady=3)
        self.code_entry.focus()
        
        # 匹配模式选择
        ttk.Label(frame_config, text="匹配模式：").grid(row=0, column=2, sticky="w", padx=5)
        self.match_var = tk.BooleanVar(value=True)
        ttk.Radiobutton(frame_config, text="开头匹配", variable=self.match_var, value=True).grid(row=0, column=3, padx=2)
        ttk.Radiobutton(frame_config, text="包含匹配", variable=self.match_var, value=False).grid(row=0, column=4, padx=2)
        
        # 2. 文件选择区
        frame_file = ttk.Frame(self)
        frame_file.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(frame_file, text="添加文件", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(frame_file, text="清空列表", command=self.clear_files).pack(side="left", padx=5)
        
        # 文件列表显示
        self.file_list = tk.Listbox(frame_file, width=80, height=3)
        self.file_list.pack(side="left", padx=5)
        scrollbar = ttk.Scrollbar(frame_file, orient="vertical", command=self.file_list.yview)
        scrollbar.pack(side="left", fill="y")
        self.file_list.config(yscrollcommand=scrollbar.set)
        
        # 3. 预览和操作区
        frame_operate = ttk.Frame(self)
        frame_operate.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 预览文本框
        ttk.Label(frame_operate, text="处理预览（仅显示前100行）：").pack(anchor="w", padx=5)
        self.preview_text = scrolledtext.ScrolledText(frame_operate, width=90, height=20, font=("Consolas", 9))
        self.preview_text.pack(fill="both", expand=True, padx=5, pady=3)
        
        # 功能按钮
        frame_btn = ttk.Frame(self)
        frame_btn.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(frame_btn, text="生成预览", command=self.generate_preview).pack(side="left", padx=5)
        ttk.Button(frame_btn, text="执行删除", command=self.execute_delete).pack(side="left", padx=5)
        ttk.Button(frame_btn, text="退出", command=self.quit).pack(side="left", padx=5)
    
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[("文本文件", "*.txt;*.prg;*.csv"), ("所有文件", "*.*")]
        )
        if paths:
            self.file_paths.extend(paths)
            self.file_list.delete(0, tk.END)
            for path in self.file_paths:
                self.file_list.insert(tk.END, os.path.basename(path))
    
    def clear_files(self):
        self.file_paths.clear()
        self.file_list.delete(0, tk.END)
        self.preview_text.delete(1.0, tk.END)
    
    def _read_lines(self, path):
        for enc in ("utf-8", "gbk", "gb18030"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.readlines()
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise UnicodeDecodeError("utf-8", b"", 0, 1, f"无法解码文件: {path}")
    
    def generate_preview(self):
        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入要匹配的开头代码！")
            return
        if not self.file_paths:
            messagebox.showwarning("提示", "请先添加文件！")
            return
        
        self.preview_text.delete(1.0, tk.END)
        preview_content = f"=== 预览开始（匹配代码：{code}，模式：{'开头匹配' if self.match_var.get() else '包含匹配'}）===\n\n"
        
        for path in self.file_paths:
            preview_content += f"【文件：{os.path.basename(path)}】\n"
            try:
                lines = self._read_lines(path)[:100]
                deleted_count = 0
                for i, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    if self.match_var.get():
                        match = line_stripped.startswith(code)
                    else:
                        match = code in line_stripped
                    
                    if match:
                        preview_content += f"❌ 第{i}行（已删除）：{line_stripped}\n"
                        deleted_count += 1
                    else:
                        preview_content += f"✅ 第{i}行（保留）：{line_stripped}\n"
                preview_content += f"该文件预览部分共删除 {deleted_count} 行\n\n"
            except Exception as e:
                preview_content += f"⚠️ 读取文件失败：{str(e)}\n\n"
        
        self.preview_text.insert(1.0, preview_content)
    
    def execute_delete(self):
        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入要匹配的开头代码！")
            return
        if not self.file_paths:
            messagebox.showwarning("提示", "请先添加文件！")
            return
        
        confirm = messagebox.askyesno("确认", f"是否要对选中的 {len(self.file_paths)} 个文件执行删除操作？\n匹配代码：{code}\n模式：{'开头匹配' if self.match_var.get() else '包含匹配'}")
        if not confirm:
            return
        
        total_deleted = 0
        for path in self.file_paths:
            try:
                lines = self._read_lines(path)
                new_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    if self.match_var.get():
                        match = line_stripped.startswith(code)
                    else:
                        match = code in line_stripped
                    if not match:
                        new_lines.append(line)
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.writelines(new_lines)
                deleted = len(lines) - len(new_lines)
                total_deleted += deleted
            except Exception as e:
                messagebox.showerror("错误", f"处理文件 {os.path.basename(path)} 失败：{str(e)}")
        
        messagebox.showinfo("完成", f"所有文件处理完毕！\n总计删除 {total_deleted} 行数据")
        self.generate_preview()

if __name__ == "__main__":
    app = LineRemoverApp()
    app.mainloop()
