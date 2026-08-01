#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奕豪Editor - 多功能记事本软件
版本: v-3.14.1025
作者: uulov@qq.com
版权: 2026.1.19 19:03:22
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, colorchooser
import datetime
import json
import subprocess
import re
import random
import string
from pathlib import Path
import ctypes
import platform

# 设置DPI感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class AutoScrollbar(ttk.Scrollbar):
    """自动隐藏的滚动条"""
    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.pack_forget()
        else:
            self.pack(side=tk.RIGHT, fill=tk.Y)
        super().set(low, high)

class TextLineNumbers(tk.Canvas):
    """行号显示组件"""
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.text_widget = None
        self.highlight_line = None
        
    def attach(self, text_widget):
        self.text_widget = text_widget
        
    def redraw(self, *args):
        """重绘行号"""
        self.delete("all")
        
        if not self.text_widget:
            return
            
        # 获取可见行
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
                
            y = dline[1]
            linenum = str(i).split(".")[0]
            
            # 检查该行是否有内容
            line_text = self.text_widget.get(f"{linenum}.0", f"{linenum}.end")
            if line_text.strip():  # 只有有内容时才显示行号
                # 高亮当前行
                if self.highlight_line == int(linenum):
                    self.create_rectangle(0, y, self.winfo_width(), y + dline[3],
                                         fill="#FFD700", outline="#FFD700")
                
                self.create_text(2, y, anchor="nw", text=linenum,
                                font=("宋体", 14), fill="#333333")
            i = self.text_widget.index(f"{i}+1line")

class CustomText(tk.Text):
    """自定义文本组件，支持行高亮"""
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)
        self.highlight_tag = "highlight"
        self.tag_configure(self.highlight_tag, background="#FFD700")
        
    def toggle_highlight_line(self, line_number):
        """切换行高亮"""
        tags = self.tag_names(f"{line_number}.0")
        if self.highlight_tag in tags:
            self.tag_remove(self.highlight_tag, f"{line_number}.0", f"{line_number}.end")
            return False
        else:
            # 移除其他高亮
            self.tag_remove(self.highlight_tag, "1.0", "end")
            self.tag_add(self.highlight_tag, f"{line_number}.0", f"{line_number}.end")
            return True

class Tab:
    """标签页类"""
    def __init__(self, notebook, path=None):
        self.notebook = notebook
        self.path = path
        self.original_content = ""
        self.is_modified = False
        self.created = datetime.datetime.now()
        
        # 创建文本框架
        self.frame = ttk.Frame(notebook)
        
        # 创建行号（放在左边）
        self.line_numbers = TextLineNumbers(self.frame, width=20, bg="#F0F0F0")
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # 创建文本组件
        self.text = CustomText(self.frame, wrap="word", font=("宋体", 18),
                              bg="#E6E6FA", undo=True, maxundo=-1)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建垂直滚动条
        self.v_scrollbar = AutoScrollbar(self.frame, orient=tk.VERTICAL,
                                        command=self.text.yview)
        self.text.config(yscrollcommand=self.v_scrollbar.set)
        
        # 连接行号和文本组件
        self.line_numbers.attach(self.text)
        
        # 绑定事件
        self.text.bind("<KeyRelease>", self.on_text_change)
        self.text.bind("<MouseWheel>", self.on_mouse_wheel)
        self.text.bind("<Button-4>", self.on_mouse_wheel)
        self.text.bind("<Button-5>", self.on_mouse_wheel)
        self.text.bind("<Configure>", self.on_configure)
        
        # 行号点击事件
        self.line_numbers.bind("<Button-1>", self.on_line_number_click)
        
        # 初始内容
        if path and os.path.exists(path):
            self.load_file()
        else:
            self.set_title("未命名")
            self.ensure_empty_lines()
            
    def on_text_change(self, event=None):
        """文本变化事件"""
        current_content = self.text.get("1.0", "end-1c")
        self.is_modified = (current_content != self.original_content)
        
        # 更新标签显示
        self.update_title()
        
        # 确保有10行空行
        self.ensure_empty_lines()
        
        # 重绘行号
        self.line_numbers.redraw()
        
    def on_mouse_wheel(self, event):
        """鼠标滚轮事件"""
        if event.delta:
            self.text.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.text.yview_scroll(-1, "units")
        elif event.num == 5:
            self.text.yview_scroll(1, "units")
        self.line_numbers.redraw()
        return "break"
        
    def on_configure(self, event=None):
        """配置变化事件"""
        self.line_numbers.redraw()
        
    def on_line_number_click(self, event):
        """行号点击事件"""
        # 计算点击的行号
        line_number = int(event.y / 20) + 1
        max_lines = int(self.text.index('end-1c').split('.')[0])
        
        if line_number <= max_lines:
            is_highlighted = self.text.toggle_highlight_line(line_number)
            self.line_numbers.highlight_line = line_number if is_highlighted else None
            self.line_numbers.redraw()
        
    def load_file(self):
        """加载文件"""
        if not self.path or not os.path.exists(self.path):
            return
            
        try:
            # 获取文件大小
            file_size = os.path.getsize(self.path)
            
            # 对于大文件（>10MB），使用分块读取
            if file_size > 10 * 1024 * 1024:  # 10MB
                content = self.load_large_file()
            else:
                # 尝试多种编码
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-16', 'ascii']
                content = None
                
                for encoding in encodings:
                    try:
                        with open(self.path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                        
                if content is None:
                    # 如果所有编码都失败，使用二进制读取
                    content = self.load_large_file()
                    
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content)
            self.original_content = content
            self.is_modified = False
            self.set_title(os.path.basename(self.path))
            
            # 确保有10行空行
            self.ensure_empty_lines()
            
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")
            
    def load_large_file(self, chunk_size=8192):
        """加载大文件"""
        content = ""
        try:
            with open(self.path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        content += chunk.decode('utf-8', errors='ignore')
                    except:
                        try:
                            content += chunk.decode('gbk', errors='ignore')
                        except:
                            content += chunk.decode('ascii', errors='ignore')
        except Exception as e:
            raise e
        return content
        
    def save_file(self, path=None):
        """保存文件"""
        if path:
            self.path = path
            
        if not self.path:
            return False
            
        try:
            content = self.text.get("1.0", "end-1c")
            # 移除自动添加的空行
            lines = content.split('\n')
            while lines and not lines[-1].strip():
                lines.pop()
                
            content = '\n'.join(lines)
            
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.original_content = content
            self.is_modified = False
            self.set_title(os.path.basename(self.path))
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"无法保存文件: {str(e)}")
            return False
            
    def ensure_empty_lines(self):
        """确保有10行空行"""
        content = self.text.get("1.0", "end-1c")
        lines = content.split('\n')
        
        # 计算末尾空行数
        empty_count = 0
        for line in reversed(lines):
            if line.strip():
                break
            empty_count += 1
            
        # 如果少于10行，添加空行
        if empty_count < 10:
            for _ in range(10 - empty_count):
                self.text.insert("end", "\n")
                
    def set_title(self, title):
        """设置标签标题"""
        if not hasattr(self, 'frame'):
            return
            
        try:
            index = self.notebook.index(self.frame)
            if index >= 0:
                if self.is_modified:
                    self.notebook.tab(self.frame, text=f"*{title}")
                else:
                    self.notebook.tab(self.frame, text=title)
        except:
            pass
            
    def update_title(self):
        """更新标签标题"""
        if self.path:
            self.set_title(os.path.basename(self.path))
        else:
            self.set_title("未命名")
            
    def get_highlighted_text(self):
        """获取高亮文本"""
        try:
            # 首先尝试获取选择文本
            sel_range = self.text.tag_ranges("sel")
            if sel_range:
                return self.text.get(sel_range[0], sel_range[1])
            
            # 如果没有选择文本，尝试获取高亮行
            if hasattr(self.line_numbers, 'highlight_line') and self.line_numbers.highlight_line:
                line_num = self.line_numbers.highlight_line
                return self.text.get(f"{line_num}.0", f"{line_num}.end")
        except:
            pass
        return None

class YihaoEditor:
    """主编辑器类"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("奕豪Editor-v-3.14.1025 永久免费版 作者: 靳好宝 Email: uulov@qq.com  copyright 2026.1.17 19:03:22")
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(__file__), "yihao_config.json")
        self.recent_files_file = os.path.join(os.path.dirname(__file__), "recent_files.json")
        
        # 加载配置
        self.config = self.load_config()
        
        # 初始化变量
        self.tabs = []
        self.current_tab = None
        self.always_on_top = False
        self.auto_save_id = None
        
        # 设置窗口属性
        self.setup_window()
        
        # 创建界面
        self.create_widgets()
        
        # 创建菜单
        self.create_menu()
        
        # 绑定事件
        self.bind_events()
        
        # 启动自动保存
        self.start_auto_save()
        
        # 创建初始标签页
        self.create_new_tab()
        
    def setup_window(self):
        """设置窗口属性"""
        # 窗口大小和位置
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
        except:
            pass
            
    def load_config(self):
        """加载配置"""
        default_config = {
            "font": {"family": "宋体", "size": 18},
            "colors": {
                "toolbar_bg": "#9400D3",
                "toolbar_border": "#9400D3",
                "editor_bg": "#E6E6FA",
                "button_bg": "#9ACD32",
                "button_fg": "#000000",
                "button_border": "#9370D8"
            },
            "recent_files": [],
            "window_position": None
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置
                    default_config.update(loaded_config)
        except:
            pass
            
        return default_config
        
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def load_recent_files(self):
        """加载最近打开的文件"""
        try:
            if os.path.exists(self.recent_files_file):
                with open(self.recent_files_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
        
    def save_recent_files(self, files):
        """保存最近打开的文件"""
        try:
            with open(self.recent_files_file, 'w', encoding='utf-8') as f:
                json.dump(files, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def add_to_recent_files(self, filepath):
        """添加到最近打开的文件"""
        recent_files = self.load_recent_files()
        
        # 移除已存在的
        if filepath in recent_files:
            recent_files.remove(filepath)
            
        # 添加到开头
        recent_files.insert(0, filepath)
        
        # 只保留最近10个
        recent_files = recent_files[:10]
        
        self.save_recent_files(recent_files)
        
    def create_widgets(self):       
        # 工具栏框架
        toolbar_frame = tk.Frame(self.root, bg=self.config["colors"]["toolbar_bg"],
                                highlightthickness=2,
                                highlightbackground=self.config["colors"]["toolbar_border"])
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        # 第一行工具栏
        self.create_toolbar_row1(toolbar_frame)
        
        # 第二行工具栏
        self.create_toolbar_row2(toolbar_frame)
        
        # 标签页框架
        notebook_frame = tk.Frame(self.root)
        notebook_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标签页控件
        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_bar = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_toolbar_row1(self, parent):
        """创建第一行工具栏"""
        row1_frame = tk.Frame(parent, bg=self.config["colors"]["toolbar_bg"])
        row1_frame.pack(side=tk.TOP, fill=tk.X, pady=(5, 2.5))
        
        # 按钮列表
        buttons_row1 = [
            ("↑", self.toggle_always_on_top, "始终置顶/取消置顶"),
            ("Time", self.insert_time, "插入当前时间"),
            ("Home", self.open_home_file, "打开软件目录文件"),
            ("txt", self.save_as_txt, "保存为TXT文件"),
            ("cmd", self.run_cmd, "在CMD中运行高亮行"),
            ("pws", self.run_powershell, "在PowerShell中运行高亮行"),
            ("Python", self.run_python, "运行Python文件"),
            ("path", self.add_to_path, "添加到系统PATH"),
            ("→", self.insert_spaces, "插入4个空格"),
            ("clear", self.clear_action, "清理/清除注释"),
            ("#", lambda: self.insert_symbol("#"), "插入#"),
            ("%", lambda: self.insert_symbol("%"), "插入%"),
            ("@", lambda: self.insert_symbol("@"), "插入@"),
            ("*", lambda: self.insert_symbol("*"), "插入*"),
            ("_", lambda: self.insert_symbol("_"), "插入_"),
            (",", lambda: self.insert_symbol(","), "插入,"),
            ("'", lambda: self.insert_symbol("'"), "插入'"),
            ('"', lambda: self.insert_symbol('"'), "插入\""),
            (".", lambda: self.insert_symbol("."), "插入."),
            (":", lambda: self.insert_symbol(":"), "插入:"),
            (";", lambda: self.insert_symbol(";"), "插入;"),
            ("...", lambda: self.insert_symbol("..."), "插入..."),
            ("Φ", lambda: self.insert_symbol("Φ"), "插入Φ"),
            ("=", lambda: self.insert_symbol("="), "插入="),
            ("()", lambda: self.insert_brackets("()"), "插入()"),
            ("[]", lambda: self.insert_brackets("[]"), "插入[]"),
            ("{}", lambda: self.insert_brackets("{}"), "插入{}"),
            ("/", lambda: self.insert_symbol("/"), "插入/")
        ]
        
        # 创建按钮
        for text, command, tooltip in buttons_row1:
            btn_color = "#FFFF00" if text == "clear" else self.config["colors"]["button_bg"]
            btn = tk.Button(row1_frame, text=text, command=command,
                           bg=btn_color, fg=self.config["colors"]["button_fg"],
                           relief=tk.RAISED, bd=2,
                           highlightbackground=self.config["colors"]["button_border"],
                           font=("宋体", 10))
            btn.pack(side=tk.LEFT, padx=2)
            
            # 添加工具提示
            self.create_tooltip(btn, tooltip)
            
            # 根据文件类型设置Python按钮颜色
            if text == "Python":
                self.python_button = btn
                
    def create_toolbar_row2(self, parent):
        """创建第二行工具栏"""
        row2_frame = tk.Frame(parent, bg=self.config["colors"]["toolbar_bg"])
        row2_frame.pack(side=tk.TOP, fill=tk.X, pady=(2.5, 5))
        
        # 按钮列表
        buttons_row2 = [
            ("新建", self.create_new_tab, "新建页面"),
            ("打开", self.open_file, "打开文件"),
            ("保存", self.save_file, "保存当前页面"),
            ("全保存", self.save_all, "保存所有页面"),
            ("另存为", self.save_as, "另存为"),
            ("剪切", self.cut_text, "剪切"),
            ("复制", self.copy_text, "复制"),
            ("粘贴", self.paste_text, "粘贴"),
            ("全复制", self.copy_all, "复制全部"),
            ("↶", self.undo_action, "撤销"),
            ("↷", self.redo_action, "重做"),
            ("关闭", self.close_tab, "关闭当前页面"),
            ("清除", self.clear_text, "清除当前页面"),
            ("PD", self.generate_password, "生成随机密码"),
            ("规范行首", self.format_line_start, "规范行首为3空格"),
            ("删行首", self.remove_line_start_spaces, "删除行首空格"),
            ("删行尾", self.remove_line_end_spaces, "删除行尾空格"),
            ("删空行", self.remove_empty_lines, "删除空行"),
            ("删空格", self.remove_spaces, "删除所有空格"),
            ("删重行", self.remove_duplicate_lines, "删除重复行"),
            ("FN", self.copy_filename, "复制文件名"),
            ("Fp", self.copy_filepath, "复制文件路径"),
            ("查找", self.find_text, "查找"),
            ("替换", self.replace_text, "替换"),
            ("。", lambda: self.insert_symbol("。"), "插入中文句号"),
            ("cname", self.rename_file, "重命名文件"),
            ("Tol", self.count_text, "统计字数")
        ]
        
        # 创建按钮
        for text, command, tooltip in buttons_row2:
            btn_color = "#FFFF00" if text in ["关闭", "清除"] else self.config["colors"]["button_bg"]
            btn = tk.Button(row2_frame, text=text, command=command,
                           bg=btn_color, fg=self.config["colors"]["button_fg"],
                           relief=tk.RAISED, bd=2,
                           highlightbackground=self.config["colors"]["button_border"],
                           font=("宋体", 10))
            btn.pack(side=tk.LEFT, padx=2)
            
            # 添加工具提示
            self.create_tooltip(btn, tooltip)
            
            # 保存按钮引用
            if text == "保存":
                self.save_button = btn
            elif text == "全保存":
                self.save_all_button = btn
                
    def create_tooltip(self, widget, text):
        """创建工具提示"""
        def on_enter(event):
            # 创建工具提示窗口
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # 创建顶层窗口
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(tooltip, text=text, background="yellow",
                            relief="solid", borderwidth=1,
                            font=("宋体", 9), padx=2, pady=2)
            label.pack()
            
            widget.tooltip = tooltip
            
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')
                
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        
    def create_menu(self):
        """创建菜单"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建", command=self.create_new_tab)
        file_menu.add_command(label="打开", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="保存", command=self.save_file)
        file_menu.add_command(label="另存为", command=self.save_as)
        file_menu.add_command(label="全部保存", command=self.save_all)
        file_menu.add_separator()
        file_menu.add_command(label="关闭", command=self.close_tab)
        file_menu.add_command(label="退出", command=self.on_closing)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="撤销", command=self.undo_action)
        edit_menu.add_command(label="重做", command=self.redo_action)
        edit_menu.add_separator()
        edit_menu.add_command(label="剪切", command=self.cut_text)
        edit_menu.add_command(label="复制", command=self.copy_text)
        edit_menu.add_command(label="粘贴", command=self.paste_text)
        edit_menu.add_separator()
        edit_menu.add_command(label="全选", command=self.select_all)
        
        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="外观设置", command=self.open_settings)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        
    def bind_events(self):
        """绑定事件"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 更新按钮状态
        self.root.after(100, self.update_button_states)
        
    def create_new_tab(self, path=None):
        """创建新标签页"""
        tab = Tab(self.notebook, path)
        self.tabs.append(tab)
        
        # 添加到笔记本
        title = os.path.basename(path) if path else "未命名"
        self.notebook.add(tab.frame, text=title)
        
        # 切换到新标签页
        self.notebook.select(tab.frame)
        self.current_tab = tab
        
        # 绑定右键菜单
        self.bind_context_menu(tab.text)
        
        # 如果是新文件，确保有空行
        if not path:
            tab.ensure_empty_lines()
            
        # 更新Python按钮状态
        self.update_python_button()
            
        return tab
        
    def bind_context_menu(self, text_widget):
        """绑定右键菜单"""
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label="剪切", command=self.cut_text)
        context_menu.add_command(label="复制", command=self.copy_text)
        context_menu.add_command(label="粘贴", command=self.paste_text)
        context_menu.add_separator()
        context_menu.add_command(label="保存", command=self.save_file)
        context_menu.add_command(label="另存为", command=self.save_as)
        context_menu.add_separator()
        context_menu.add_command(label="新建", command=self.create_new_tab)
        context_menu.add_command(label="打开", command=self.open_file)
        context_menu.add_separator()
        context_menu.add_command(label="设置", command=self.open_settings)
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
                
        text_widget.bind("<Button-3>", show_context_menu)
        
    def on_tab_changed(self, event=None):
        """标签页切换事件"""
        selected = self.notebook.select()
        if selected:
            for tab in self.tabs:
                if tab.frame == self.notebook.nametowidget(selected):
                    self.current_tab = tab
                    
                    # 离开页面时自动保存
                    if tab.is_modified and tab.path:
                        tab.save_file()
                        
                    # 更新Python按钮状态
                    self.update_python_button()
                    break
                    
    def update_python_button(self):
        """更新Python按钮状态"""
        if hasattr(self, 'python_button'):
            if self.current_tab and self.current_tab.path and self.current_tab.path.endswith('.py'):
                self.python_button.config(bg="#00FF00", state=tk.NORMAL)  # 绿色
            else:
                self.python_button.config(bg="#808080", state=tk.DISABLED)  # 灰色
                
    def update_button_states(self):
        """更新按钮状态"""
        # 更新保存按钮颜色
        if hasattr(self, 'save_button'):
            if self.current_tab and self.current_tab.is_modified:
                self.save_button.config(bg="#FF0000")  # 红色
            else:
                self.save_button.config(bg="#00FF00")  # 绿色
                
        # 更新全部保存按钮颜色
        if hasattr(self, 'save_all_button'):
            any_modified = any(tab.is_modified and tab.path for tab in self.tabs)
            if any_modified:
                self.save_all_button.config(bg="#FF0000")  # 红色
            else:
                self.save_all_button.config(bg="#00FF00")  # 绿色
                
        # 定期更新
        self.root.after(1000, self.update_button_states)
        
    def open_file_direct(self, filepath):
        """直接打开文件"""
        # 检查是否已打开
        for tab in self.tabs:
            if tab.path == filepath:
                self.notebook.select(tab.frame)
                return
                
        # 创建新标签页打开
        self.create_new_tab(filepath)
        self.add_to_recent_files(filepath)
        
    def toggle_always_on_top(self):
        """切换窗口置顶"""
        self.always_on_top = not self.always_on_top
        self.root.attributes('-topmost', self.always_on_top)
        
    def insert_time(self):
        """插入当前时间"""
        if self.current_tab:
            current_time = datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            self.current_tab.text.insert(tk.INSERT, current_time)
            
    def open_home_file(self):
        """打开软件目录中的文件"""
        home_dir = os.path.dirname(__file__)
        filepath = filedialog.askopenfilename(initialdir=home_dir,
                                             filetypes=[("所有文件", "*.*")])
        if filepath:
            self.open_file_direct(filepath)
            
    def save_as_txt(self):
        """保存为TXT文件"""
        if not self.current_tab:
            return
            
        # 获取第一行作为文件名
        content = self.current_tab.text.get("1.0", "2.0")
        first_line = content.split('\n')[0].strip()
        
        if not first_line:
            first_line = "未命名"
            
        # 创建txt目录
        txt_dir = os.path.join(os.path.dirname(__file__), "txt")
        os.makedirs(txt_dir, exist_ok=True)
        
        # 保存文件
        filename = f"{first_line}.txt"
        filepath = os.path.join(txt_dir, filename)
        
        if self.current_tab.save_file(filepath):
            self.show_message("保存成功", 1000)
            
    def run_cmd(self):
        """在CMD中运行高亮行"""
        if not self.current_tab:
            return
            
        highlighted = self.current_tab.get_highlighted_text()
        if not highlighted:
            # 如果没有高亮，直接打开CMD
            subprocess.Popen("cmd.exe")
            return
            
        # 处理文本
        lines = highlighted.split('\n')
        if len(lines) != 1:
            subprocess.Popen("cmd.exe")
            return
            
        line = lines[0].strip()
        # 移除#号及后面的内容
        if '#' in line:
            line = line.split('#')[0].strip()
            
        # 复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(line)
        
        # 在CMD中运行
        subprocess.Popen(["cmd.exe", "/k", line])
        
    def run_powershell(self):
        """在PowerShell中运行高亮行"""
        if not self.current_tab:
            return
            
        highlighted = self.current_tab.get_highlighted_text()
        if not highlighted:
            # 如果没有高亮，直接打开PowerShell
            subprocess.Popen("powershell.exe")
            return
            
        # 处理文本
        lines = highlighted.split('\n')
        if len(lines) != 1:
            subprocess.Popen("powershell.exe")
            return
            
        line = lines[0].strip()
        # 移除#号及后面的内容
        if '#' in line:
            line = line.split('#')[0].strip()
            
        # 复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(line)
        
        # 在PowerShell中运行
        subprocess.Popen(["powershell.exe", "-Command", line])
        
    def run_python(self):
        """运行Python文件"""
        if not self.current_tab or not self.current_tab.path:
            return
            
        if self.current_tab.path.endswith('.py'):
            try:
                subprocess.Popen(["python", self.current_tab.path])
            except:
                messagebox.showerror("错误", "无法运行Python文件")
                
    def add_to_path(self):
        """添加到系统PATH"""
        if not self.current_tab:
            return
            
        highlighted = self.current_tab.get_highlighted_text()
        if not highlighted:
            messagebox.showinfo("提示", "请先高亮要添加的路径")
            return
            
        # 处理文本
        lines = highlighted.split('\n')
        if len(lines) != 1:
            messagebox.showinfo("提示", "只能高亮一行")
            return
            
        path = lines[0].strip()
        # 移除#号及后面的内容
        if '#' in path:
            path = path.split('#')[0].strip()
            
        # 检查是否是有效路径
        if not os.path.exists(path):
            messagebox.showinfo("错误", "路径不存在")
            return
            
        # 检查是否已在PATH中
        current_path = os.environ.get('PATH', '')
        if path in current_path.split(';'):
            messagebox.showinfo("提示", "该路径已在系统PATH中")
            return
            
        try:
            # 添加到系统PATH（需要管理员权限）
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                "Environment", 0, winreg.KEY_ALL_ACCESS)
            current_value, _ = winreg.QueryValueEx(key, "Path")
            
            if path not in current_value:
                new_value = f"{current_value};{path}" if current_value else path
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_value)
                winreg.CloseKey(key)
                
                # 通知系统环境变量已更改
                import ctypes
                ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0, 1000, None)
                
                messagebox.showinfo("成功", "路径已添加到系统PATH")
            else:
                messagebox.showinfo("提示", "该路径已在系统PATH中")
                
        except Exception as e:
            messagebox.showerror("错误", f"添加路径失败: {str(e)}")
            
    def insert_spaces(self):
        """插入4个空格"""
        if self.current_tab:
            self.current_tab.text.insert(tk.INSERT, "    ")
            
    def clear_action(self):
        """清理/清除注释"""
        if not self.current_tab:
            return
            
        if self.current_tab.path and self.current_tab.path.endswith('.py'):
            # 清除Python注释
            self.clear_python_comments()
        else:
            # 执行清理操作
            self.execute_clear_txt()
            
    def clear_python_comments(self):
        """清除Python注释"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        
        # 移除单行注释
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 保留字符串中的注释
            in_string = False
            string_char = None
            new_line = ""
            
            for i, char in enumerate(line):
                if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif string_char == char:
                        in_string = False
                        string_char = None
                        
                if not in_string and char == '#':
                    # 找到注释开始，跳出循环
                    break
                    
                new_line += char
                
            cleaned_lines.append(new_line.rstrip())
            
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", '\n'.join(cleaned_lines))
        
    def execute_clear_txt(self):
        """执行clear.txt清理操作"""
        clear_file = os.path.join(os.path.dirname(__file__), "clear.txt")
        
        # 如果文件不存在，创建它
        if not os.path.exists(clear_file):
            with open(clear_file, 'w', encoding='utf-8') as f:
                f.write("# 清理规则文件\n")
                f.write("# 格式: 关键词 替换词\n")
                f.write("# 如果替换词为空，则删除关键词\n")
                f.write("# 如果关键词以*结尾，匹配包含该词的所有词\n")
            return
            
        # 读取清理规则
        try:
            with open(clear_file, 'r', encoding='utf-8') as f:
                rules = f.readlines()
        except:
            self.show_message("无法读取clear.txt", 2000)
            return
            
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        
        for rule in rules:
            rule = rule.strip()
            if not rule or rule.startswith('#'):
                continue
                
            parts = rule.split(' ', 1)
            if len(parts) < 1:
                continue
                
            keyword = parts[0].strip()
            replacement = parts[1].strip() if len(parts) > 1 else ""
            
            if keyword.endswith('*'):
                # 匹配包含关键词的词
                keyword = keyword[:-1]
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                content = pattern.sub(replacement, content)
            else:
                # 精确匹配关键词
                pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                content = pattern.sub(replacement, content)
                
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", content)
        
    def insert_symbol(self, symbol):
        """插入符号"""
        if self.current_tab:
            self.current_tab.text.insert(tk.INSERT, symbol)
            
    def insert_brackets(self, brackets):
        """插入括号"""
        if self.current_tab:
            self.current_tab.text.insert(tk.INSERT, brackets)
            # 将光标移到括号中间
            if len(brackets) == 2:
                self.current_tab.text.mark_set(tk.INSERT, f"insert -1c")
                
    def open_file(self):
        """打开文件"""
        filepath = filedialog.askopenfilename(
            filetypes=[("所有文件", "*.*"),
                      ("文本文件", "*.txt"),
                      ("Python文件", "*.py"),
                      ("HTML文件", "*.html"),
                      ("批处理文件", "*.bat"),
                      ("INI文件", "*.ini"),
                      ("AutoHotkey", "*.ahk")])
        
        if filepath:
            self.open_file_direct(filepath)
            
    def save_file(self):
        """保存当前文件"""
        if not self.current_tab:
            return
            
        if self.current_tab.path:
            if self.current_tab.save_file():
                self.show_message("保存成功", 1000)
        else:
            self.save_as()
            
    def save_all(self):
        """保存所有文件"""
        saved_count = 0
        for tab in self.tabs:
            if tab.path and tab.is_modified:
                if tab.save_file():
                    saved_count += 1
                    
        if saved_count > 0:
            self.show_message(f"成功保存{saved_count}个文件", 1000)
            
    def save_as(self):
        """另存为"""
        if not self.current_tab:
            return
            
        # 获取默认扩展名
        default_ext = ".txt"
        if self.current_tab.path:
            _, ext = os.path.splitext(self.current_tab.path)
            if ext:
                default_ext = ext
                
        filepath = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=[("文本文件", "*.txt"),
                      ("Python文件", "*.py"),
                      ("INI文件", "*.ini"),
                      ("HTML文件", "*.html"),
                      ("AutoHotkey", "*.ahk"),
                      ("批处理文件", "*.bat"),
                      ("宏文件", "*.mcr"),
                      ("所有文件", "*.*")])
        
        if filepath:
            if self.current_tab.save_file(filepath):
                self.add_to_recent_files(filepath)
                self.show_message("保存成功", 1000)
                
    def cut_text(self):
        """剪切文本"""
        if self.current_tab:
            self.current_tab.text.event_generate("<<Cut>>")
            
    def copy_text(self):
        """复制文本"""
        if self.current_tab:
            self.current_tab.text.event_generate("<<Copy>>")
            
    def paste_text(self):
        """粘贴文本"""
        if self.current_tab:
            self.current_tab.text.event_generate("<<Paste>>")
            
    def copy_all(self):
        """复制全部文本"""
        if self.current_tab:
            self.current_tab.text.tag_add(tk.SEL, "1.0", "end-1c")
            self.current_tab.text.event_generate("<<Copy>>")
            self.current_tab.text.tag_remove(tk.SEL, "1.0", "end-1c")
            
    def undo_action(self):
        """撤销"""
        if self.current_tab:
            try:
                self.current_tab.text.edit_undo()
            except:
                pass
                
    def redo_action(self):
        """重做"""
        if self.current_tab:
            try:
                self.current_tab.text.edit_redo()
            except:
                pass
                
    def close_tab(self):
        """关闭当前标签页"""
        if not self.current_tab:
            return
            
        # 如果有未保存的修改
        if self.current_tab.is_modified and self.current_tab.path:
            response = messagebox.askyesnocancel("保存", "文件已修改，是否保存？")
            if response is None:  # 取消
                return
            elif response:  # 是
                if not self.current_tab.save_file():
                    return
                    
        # 移除标签页
        for i, tab in enumerate(self.tabs):
            if tab == self.current_tab:
                self.notebook.forget(tab.frame)
                self.tabs.pop(i)
                break
                
        # 如果所有标签页都关闭了，创建一个新标签页
        if not self.tabs:
            self.create_new_tab()
            
    def clear_text(self):
        """清除文本"""
        if self.current_tab:
            self.current_tab.text.delete("1.0", tk.END)
            
    def generate_password(self):
        """生成随机密码"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        password = ''.join(random.choice(chars) for _ in range(20))
        
        # 插入到光标位置
        if self.current_tab:
            self.current_tab.text.insert(tk.INSERT, password)
            
        # 复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(password)
        
    def format_line_start(self):
        """规范行首为3个空格"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        lines = content.split('\n')
        
        formatted_lines = []
        for line in lines:
            # 计算行首空格数
            space_count = len(line) - len(line.lstrip())
            if space_count < 3:
                line = ' ' * (3 - space_count) + line
            formatted_lines.append(line)
            
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", '\n'.join(formatted_lines))
        
    def remove_line_start_spaces(self):
        """删除行首空格"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        lines = content.split('\n')
        
        cleaned_lines = [line.lstrip() for line in lines]
        
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", '\n'.join(cleaned_lines))
        
    def remove_line_end_spaces(self):
        """删除行尾空格"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        lines = content.split('\n')
        
        cleaned_lines = [line.rstrip() for line in lines]
        
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", '\n'.join(cleaned_lines))
        
    def remove_empty_lines(self):
        """删除空行"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        lines = content.split('\n')
        
        # 保留最后10行空行
        non_empty_lines = []
        empty_count = 0
        
        for line in lines:
            if line.strip():
                non_empty_lines.append(line)
                empty_count = 0
            else:
                empty_count += 1
                # 只保留最多10行空行
                if empty_count <= 10:
                    non_empty_lines.append(line)
                    
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", '\n'.join(non_empty_lines))
        
    def remove_spaces(self):
        """删除所有空格"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        content = content.replace(' ', '').replace('\t', '')
        
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", content)
        
    def remove_duplicate_lines(self):
        """删除重复行"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        lines = content.split('\n')
        
        seen = set()
        unique_lines = []
        
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
                
        # 更新文本
        self.current_tab.text.delete("1.0", tk.END)
        self.current_tab.text.insert("1.0", '\n'.join(unique_lines))
        
    def copy_filename(self):
        """复制文件名"""
        if self.current_tab and self.current_tab.path:
            filename = os.path.basename(self.current_tab.path)
            self.root.clipboard_clear()
            self.root.clipboard_append(filename)
            self.show_message("文件名已复制", 1000)
            
    def copy_filepath(self):
        """复制文件路径"""
        if self.current_tab and self.current_tab.path:
            # 修复剪贴板使用方法
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_tab.path)
            self.show_message("文件路径已复制", 1000)
        elif self.current_tab:
            self.show_message("文件未保存，无法复制路径", 1000)
            
    def find_text(self):
        """查找文本"""
        if not self.current_tab:
            return
            
        # 创建查找对话框
        find_dialog = tk.Toplevel(self.root)
        find_dialog.title("查找")
        find_dialog.geometry("300x150")
        find_dialog.transient(self.root)
        
        # 尝试获取当前高亮文本
        highlighted = self.current_tab.get_highlighted_text()
        default_text = highlighted.strip() if highlighted else ""
        
        tk.Label(find_dialog, text="查找内容:").pack(pady=5)
        find_entry = tk.Entry(find_dialog, width=30)
        find_entry.pack(pady=5)
        
        if default_text:
            find_entry.insert(0, default_text)
            
        def find_next():
            text_to_find = find_entry.get()
            if not text_to_find:
                return
                
            # 从当前位置开始查找
            content = self.current_tab.text.get("1.0", tk.END)
            if text_to_find in content:
                # 移除之前的高亮
                self.current_tab.text.tag_remove("find", "1.0", tk.END)
                
                # 获取当前光标位置
                current_pos = self.current_tab.text.index(tk.INSERT)
                
                # 从当前位置开始查找
                start_pos = current_pos
                found_pos = self.current_tab.text.search(text_to_find, start_pos, tk.END)
                
                # 如果没找到，从头开始找
                if not found_pos:
                    found_pos = self.current_tab.text.search(text_to_find, "1.0", tk.END)
                    
                if found_pos:
                    end_pos = f"{found_pos}+{len(text_to_find)}c"
                    self.current_tab.text.tag_add("find", found_pos, end_pos)
                    self.current_tab.text.tag_config("find", background="yellow")
                    self.current_tab.text.see(found_pos)
                    self.current_tab.text.mark_set(tk.INSERT, end_pos)
                    
        def find_all():
            text_to_find = find_entry.get()
            if not text_to_find:
                return
                
            content = self.current_tab.text.get("1.0", tk.END)
            if text_to_find in content:
                # 移除之前的高亮
                self.current_tab.text.tag_remove("find", "1.0", tk.END)
                
                # 查找并高亮所有匹配项
                start_pos = "1.0"
                count = 0
                while True:
                    start_pos = self.current_tab.text.search(text_to_find, start_pos, tk.END)
                    if not start_pos:
                        break
                    end_pos = f"{start_pos}+{len(text_to_find)}c"
                    self.current_tab.text.tag_add("find", start_pos, end_pos)
                    start_pos = end_pos
                    count += 1
                    
                self.current_tab.text.tag_config("find", background="yellow")
                self.show_message(f"找到 {count} 个匹配项", 2000)
                
        button_frame = tk.Frame(find_dialog)
        button_frame.pack(pady=5)
        
        tk.Button(button_frame, text="查找下一个", command=find_next).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="查找全部", command=find_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="关闭", command=find_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def replace_text(self):
        """替换文本"""
        if not self.current_tab:
            return
            
        # 创建替换对话框
        replace_dialog = tk.Toplevel(self.root)
        replace_dialog.title("替换")
        replace_dialog.geometry("350x200")
        replace_dialog.transient(self.root)
        
        # 尝试获取当前高亮文本
        highlighted = self.current_tab.get_highlighted_text()
        default_find = highlighted.strip() if highlighted else ""
        
        tk.Label(replace_dialog, text="查找内容:").pack(pady=2)
        find_entry = tk.Entry(replace_dialog, width=30)
        find_entry.pack(pady=2)
        
        if default_find:
            find_entry.insert(0, default_find)
            
        tk.Label(replace_dialog, text="替换为:").pack(pady=2)
        replace_entry = tk.Entry(replace_dialog, width=30)
        replace_entry.pack(pady=2)
        
        def replace_next():
            find_text = find_entry.get()
            replace_text = replace_entry.get()
            
            if not find_text:
                return
                
            # 从当前位置开始查找
            current_pos = self.current_tab.text.index(tk.INSERT)
            found_pos = self.current_tab.text.search(find_text, current_pos, tk.END)
            
            # 如果没找到，从头开始找
            if not found_pos:
                found_pos = self.current_tab.text.search(find_text, "1.0", tk.END)
                
            if found_pos:
                end_pos = f"{found_pos}+{len(find_text)}c"
                
                # 替换文本
                self.current_tab.text.delete(found_pos, end_pos)
                self.current_tab.text.insert(found_pos, replace_text)
                
                # 移动光标到替换后的位置
                new_end_pos = f"{found_pos}+{len(replace_text)}c"
                self.current_tab.text.mark_set(tk.INSERT, new_end_pos)
                self.current_tab.text.see(new_end_pos)
                
        def replace_all():
            find_text = find_entry.get()
            replace_text = replace_entry.get()
            
            if not find_text:
                return
                
            # 获取当前文本
            content = self.current_tab.text.get("1.0", tk.END)
            
            # 计算替换次数
            count = content.count(find_text)
            
            if count > 0:
                # 执行全部替换
                new_content = content.replace(find_text, replace_text)
                self.current_tab.text.delete("1.0", tk.END)
                self.current_tab.text.insert("1.0", new_content)
                self.show_message(f"替换了 {count} 处", 2000)
            else:
                self.show_message("未找到匹配项", 1000)
                
        button_frame = tk.Frame(replace_dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="替换下一个", command=replace_next).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="全部替换", command=replace_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="关闭", command=replace_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def rename_file(self):
        """重命名文件"""
        if not self.current_tab or not self.current_tab.path:
            messagebox.showinfo("提示", "当前文件未保存")
            return
            
        old_filename = os.path.basename(self.current_tab.path)
        new_filename = simpledialog.askstring("重命名", "请输入新文件名:", 
                                             initialvalue=old_filename)
        
        if new_filename and new_filename != old_filename:
            new_path = os.path.join(os.path.dirname(self.current_tab.path), new_filename)
            
            try:
                os.rename(self.current_tab.path, new_path)
                self.current_tab.path = new_path
                self.current_tab.update_title()
                self.show_message("重命名成功", 1000)
            except Exception as e:
                messagebox.showerror("错误", f"重命名失败: {str(e)}")
                
    def count_text(self):
        """统计字数"""
        if not self.current_tab:
            return
            
        content = self.current_tab.text.get("1.0", "end-1c")
        
        # 移除标点符号
        import re
        chinese_punctuation = "。，、；：？！""''（）《》【】~～@#￥%……&*（）——+{}|:\"<>?`-=[]\\;',./"
        english_punctuation = string.punctuation
        all_punctuation = chinese_punctuation + english_punctuation
        
        # 移除标点
        for punct in all_punctuation:
            content = content.replace(punct, '')
            
        # 统计字符数
        char_count = len(content.replace('\n', '').replace('\r', '').replace(' ', ''))
        
        messagebox.showinfo("统计结果", f"总字符数: {char_count}")
        
    def open_settings(self):
        """打开设置对话框"""
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("设置")
        settings_dialog.geometry("500x600")
        settings_dialog.transient(self.root)
        
        # 字体设置
        tk.Label(settings_dialog, text="字体设置", font=("宋体", 12, "bold")).pack(pady=10)
        
        font_frame = tk.Frame(settings_dialog)
        font_frame.pack(pady=5)
        
        tk.Label(font_frame, text="字体大小:").pack(side=tk.LEFT, padx=5)
        font_size_var = tk.StringVar(value=str(self.config["font"]["size"]))
        font_size_spinbox = tk.Spinbox(font_frame, from_=8, to=72, textvariable=font_size_var, width=10)
        font_size_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 颜色设置
        tk.Label(settings_dialog, text="颜色设置", font=("宋体", 12, "bold")).pack(pady=10)
        
        colors = [
            ("工具栏背景色", "toolbar_bg", self.config["colors"]["toolbar_bg"]),
            ("编辑器背景色", "editor_bg", self.config["colors"]["editor_bg"]),
            ("按钮背景色", "button_bg", self.config["colors"]["button_bg"]),
            ("按钮文字色", "button_fg", self.config["colors"]["button_fg"]),
            ("按钮边框色", "button_border", self.config["colors"]["button_border"])
        ]
        
        color_vars = {}
        color_entries = {}
        color_previews = {}
        
        # 预设颜色
        preset_colors = {
            "默认紫色": {
                "toolbar_bg": "#9400D3",
                "toolbar_border": "#9400D3",
                "editor_bg": "#E6E6FA",
                "button_bg": "#9ACD32",
                "button_fg": "#000000",
                "button_border": "#9370D8"
            },
            "深色主题": {
                "toolbar_bg": "#2E2E2E",
                "toolbar_border": "#2E2E2E",
                "editor_bg": "#1E1E1E",
                "button_bg": "#3E3E3E",
                "button_fg": "#FFFFFF",
                "button_border": "#4E4E4E"
            },
            "蓝色主题": {
                "toolbar_bg": "#1E3A5F",
                "toolbar_border": "#1E3A5F",
                "editor_bg": "#E6F3FF",
                "button_bg": "#4A90E2",
                "button_fg": "#FFFFFF",
                "button_border": "#357ABD"
            },
            "绿色主题": {
                "toolbar_bg": "#2E7D32",
                "toolbar_border": "#2E7D32",
                "editor_bg": "#F1F8E9",
                "button_bg": "#4CAF50",
                "button_fg": "#FFFFFF",
                "button_border": "#388E3C"
            },
            "橙色主题": {
                "toolbar_bg": "#EF6C00",
                "toolbar_border": "#EF6C00",
                "editor_bg": "#FFF3E0",
                "button_bg": "#FF9800",
                "button_fg": "#FFFFFF",
                "button_border": "#F57C00"
            },
            "红色主题": {
                "toolbar_bg": "#C62828",
                "toolbar_border": "#C62828",
                "editor_bg": "#FFEBEE",
                "button_bg": "#F44336",
                "button_fg": "#FFFFFF",
                "button_border": "#D32F2F"
            }
        }
        
        for label, key, value in colors:
            frame = tk.Frame(settings_dialog)
            frame.pack(pady=3)
            
            tk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
            var = tk.StringVar(value=value)
            color_vars[key] = var
            
            entry = tk.Entry(frame, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            color_entries[key] = entry
            
            # 创建颜色预览框
            preview_frame = tk.Frame(frame, width=20, height=20, bg=value, relief="solid", borderwidth=1)
            preview_frame.pack(side=tk.LEFT, padx=2)
            preview_frame.pack_propagate(False)
            color_previews[key] = preview_frame
            
            # 更新预览框颜色的函数
            def update_preview(var=var, preview=preview_frame):
                color = var.get()
                if color:
                    try:
                        preview.config(bg=color)
                    except:
                        pass
            
            var.trace("w", lambda *args: update_preview())
            
            # 创建颜色选择按钮
            def create_color_picker(entry_widget=entry, var_widget=var, preview_widget=preview_frame):
                def pick_color():
                    color = colorchooser.askcolor(title="选择颜色", initialcolor=var_widget.get())
                    if color and color[1]:
                        var_widget.set(color[1])
                        entry_widget.delete(0, tk.END)
                        entry_widget.insert(0, color[1])
                        preview_widget.config(bg=color[1])
                return pick_color
            
            color_picker = create_color_picker()
            tk.Button(frame, text="选择颜色", command=color_picker, width=10).pack(side=tk.LEFT, padx=5)
        
        # 添加预设颜色按钮
        tk.Label(settings_dialog, text="预设主题", font=("宋体", 12, "bold")).pack(pady=10)
        
        preset_frame = tk.Frame(settings_dialog)
        preset_frame.pack(pady=5)
        
        # 创建两行预设按钮
        row1 = tk.Frame(preset_frame)
        row1.pack()
        row2 = tk.Frame(preset_frame)
        row2.pack()
        
        for i, (theme_name, theme_colors) in enumerate(preset_colors.items()):
            if i < 3:
                row = row1
            else:
                row = row2
                
            def apply_preset(colors_dict=theme_colors):
                # 应用预设颜色到对应的输入框
                for key, color_value in colors_dict.items():
                    if key in color_vars:
                        color_vars[key].set(color_value)
                        if key in color_entries:
                            color_entries[key].delete(0, tk.END)
                            color_entries[key].insert(0, color_value)
                        if key in color_previews:
                            color_previews[key].config(bg=color_value)
            
            btn = tk.Button(row, text=theme_name, command=apply_preset, 
                           width=10, font=("宋体", 9))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        def save_settings():
            # 保存字体设置
            try:
                self.config["font"]["size"] = int(font_size_var.get())
            except:
                pass
                
            # 保存颜色设置
            for key, var in color_vars.items():
                self.config["colors"][key] = var.get()
                
            # 应用设置
            self.apply_settings()
            
            # 保存到配置文件
            self.save_config()
            
            settings_dialog.destroy()
            self.show_message("设置已保存", 1000)
            
        # 添加预览按钮
        preview_frame = tk.Frame(settings_dialog)
        preview_frame.pack(pady=10)
        
        def preview_settings():
            # 临时应用设置以预览
            temp_config = self.config.copy()
            try:
                temp_config["font"]["size"] = int(font_size_var.get())
            except:
                pass
            
            for key, var in color_vars.items():
                temp_config["colors"][key] = var.get()
            
            # 应用临时设置
            font_family = temp_config["font"]["family"]
            font_size = temp_config["font"]["size"]
            
            for tab in self.tabs:
                tab.text.config(font=(font_family, font_size))
                tab.text.config(bg=temp_config["colors"]["editor_bg"])
                
            # 更新工具栏颜色
            for widget in self.root.children.values():
                if isinstance(widget, tk.Frame):
                    try:
                        # 更新工具栏背景色
                        widget.config(bg=temp_config["colors"]["toolbar_bg"],
                                     highlightbackground=temp_config["colors"]["toolbar_border"])
                        
                        # 更新按钮颜色
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Frame):
                                child.config(bg=temp_config["colors"]["toolbar_bg"])
                                for button in child.winfo_children():
                                    if isinstance(button, tk.Button):
                                        # 特殊按钮保持原有颜色
                                        if button.cget("text") in ["clear", "关闭", "清除"]:
                                            continue
                                        button.config(bg=temp_config["colors"]["button_bg"],
                                                     fg=temp_config["colors"]["button_fg"],
                                                     highlightbackground=temp_config["colors"]["button_border"])
                    except:
                        pass
                        
            self.show_message("预览已应用，点击保存设置永久生效", 2000)
        
        tk.Button(preview_frame, text="预览设置", command=preview_settings, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(preview_frame, text="保存设置", command=save_settings, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(preview_frame, text="取消", command=settings_dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)
        
    def apply_settings(self):
        """应用设置"""
        # 更新当前标签页字体
        font_family = self.config["font"]["family"]
        font_size = self.config["font"]["size"]
        
        for tab in self.tabs:
            tab.text.config(font=(font_family, font_size))
            tab.text.config(bg=self.config["colors"]["editor_bg"])
            
        # 更新工具栏颜色
        for widget in self.root.children.values():
            if isinstance(widget, tk.Frame):
                try:
                    # 更新工具栏背景色
                    widget.config(bg=self.config["colors"]["toolbar_bg"],
                                 highlightbackground=self.config["colors"]["toolbar_border"])
                    
                    # 更新按钮颜色
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            child.config(bg=self.config["colors"]["toolbar_bg"])
                            for button in child.winfo_children():
                                if isinstance(button, tk.Button):
                                    # 特殊按钮保持原有颜色
                                    if button.cget("text") in ["clear", "关闭", "清除"]:
                                        continue
                                    button.config(bg=self.config["colors"]["button_bg"],
                                                 fg=self.config["colors"]["button_fg"],
                                                 highlightbackground=self.config["colors"]["button_border"])
                except:
                    pass
                    
    def select_all(self):
        """全选"""
        if self.current_tab:
            self.current_tab.text.tag_add(tk.SEL, "1.0", "end-1c")
            self.current_tab.text.mark_set(tk.INSERT, "1.0")
            self.current_tab.text.see(tk.INSERT)
            
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("关于", 
                          "奕豪Editor v-3.14.1024\n"
                          "作者: uulov@qq.com\n"
                          "版权: 2025.12.31 19:03:22\n"
                          "多功能记事本软件")
                          
    def show_message(self, message, duration):
        """显示临时消息"""
        self.status_bar.config(text=message)
        self.root.after(duration, lambda: self.status_bar.config(text="就绪"))
        
    def start_auto_save(self):
        """启动自动保存"""
        def auto_save():
            for tab in self.tabs:
                if tab.path and tab.is_modified:
                    tab.save_file()
            self.root.after(60000, auto_save)  # 每分钟执行一次
            
        self.auto_save_id = self.root.after(60000, auto_save)
        
    def on_closing(self):
        """窗口关闭事件"""
        # 停止自动保存
        if self.auto_save_id:
            self.root.after_cancel(self.auto_save_id)
            
        # 保存所有已修改的文件
        for tab in self.tabs:
            if tab.path and tab.is_modified:
                tab.save_file()
                
        # 保存窗口位置
        self.config["window_position"] = self.root.geometry()
        self.save_config()
        
        self.root.destroy()
        
    def run(self):
        """运行程序"""
        # 恢复窗口位置
        if self.config.get("window_position"):
            self.root.geometry(self.config["window_position"])
            
        # 打开最近的文件
        recent_files = self.load_recent_files()
        for filepath in recent_files[:3]:  # 只打开前3个
            if os.path.exists(filepath):
                self.open_file_direct(filepath)
                
        self.root.mainloop()

def main():
    """主函数"""
    editor = YihaoEditor()
    editor.run()

if __name__ == "__main__":
    main()