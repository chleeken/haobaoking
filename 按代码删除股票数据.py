import duckdb
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import tkinter.scrolledtext as scrolledtext
import re


def get_base_path():
    """获取程序所在目录（兼容打包后的exe）"""
    if getattr(sys, 'frozen', False):
        # 打包后的exe运行
        return os.path.dirname(sys.executable)
    else:
        # 普通Python脚本运行
        return os.path.dirname(os.path.abspath(__file__))


class StockDataDeleter:
    def __init__(self, root):
        self.root = root
        self.root.title("股票数据删除工具 - 按代码删除")
        self.root.geometry("700x700")
        self.root.resizable(True, True)

        # 数据库路径
        self.db_path = os.path.join(get_base_path(), "stock_data", "stock_data.duckdb")
        self.conn = None
        self.table_info = {}  # 存储表结构信息

        # 创建界面
        self.create_widgets()

    def create_widgets(self):
        # 数据库选择区域
        db_frame = tk.LabelFrame(self.root, text="数据库设置", padx=10, pady=10)
        db_frame.pack(fill="x", padx=10, pady=5)

        self.db_path_var = tk.StringVar(value=self.db_path)
        
        db_entry = tk.Entry(db_frame, textvariable=self.db_path_var, width=50)
        db_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
        
        tk.Button(db_frame, text="打开", command=self.select_db).pack(side="left", padx=2)
        tk.Button(db_frame, text="诊断", command=self.diagnose_db).pack(side="left", padx=2)

        # 股票代码输入区域
        code_frame = tk.LabelFrame(self.root, text="股票代码设置", padx=10, pady=10)
        code_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 代码输入框（支持多行）
        tk.Label(code_frame, text="请输入股票代码（每行一个，支持多个代码同时删除）:").pack(anchor="w")
        
        self.code_text = scrolledtext.ScrolledText(code_frame, height=8, width=50)
        self.code_text.pack(fill="both", expand=True, pady=5)
        
        # 按钮区域
        button_frame = tk.Frame(code_frame)
        button_frame.pack(fill="x", pady=5)
        
        tk.Button(button_frame, text="粘贴", command=self.paste_code, bg="#4ecdc4", fg="white", width=10).pack(side="left", padx=5)
        tk.Button(button_frame, text="清空", command=self.clear_code, bg="#95a5a6", fg="white", width=10).pack(side="left", padx=5)
        
        # 提示标签
        tk.Label(code_frame, text="提示：支持格式：600004、600004.SH、SH600004、600004.SS 等", fg="gray", font=("Arial", 9)).pack(anchor="w")

        # 删除选项区域
        options_frame = tk.LabelFrame(self.root, text="删除选项", padx=10, pady=10)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        self.match_mode = tk.StringVar(value="smart")
        tk.Radiobutton(options_frame, text="智能匹配（推荐）", variable=self.match_mode, value="smart").pack(anchor="w")
        tk.Radiobutton(options_frame, text="精确匹配", variable=self.match_mode, value="exact").pack(anchor="w")
        tk.Radiobutton(options_frame, text="模糊匹配（包含）", variable=self.match_mode, value="fuzzy").pack(anchor="w")

        # 删除按钮
        self.delete_btn = tk.Button(self.root, text="删除数据", command=self.delete_data, bg="#ff6b6b", fg="white",
                                    font=("Arial", 12), height=2)
        self.delete_btn.pack(pady=10, padx=10, fill="x")

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 显示统计信息的文本框
        info_frame = tk.LabelFrame(self.root, text="操作信息", padx=10, pady=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, width=50, state=tk.DISABLED)
        self.info_text.pack(fill="both", expand=True)

    def select_db(self):
        """选择数据库文件"""
        initial_dir = os.path.dirname(self.db_path)
        if not os.path.exists(initial_dir):
            initial_dir = get_base_path()

        file_path = filedialog.askopenfilename(
            title="选择 DuckDB 数据库文件",
            initialdir=initial_dir,
            filetypes=[("DuckDB 文件", "*.duckdb"), ("所有文件", "*.*")]
        )
        if file_path:
            self.db_path_var.set(file_path)
            self.status_var.set(f"已选择数据库: {os.path.basename(file_path)}")

    def diagnose_db(self):
        """诊断数据库结构"""
        if not self.connect_db():
            return
        
        self.add_info_message("\n" + "="*50)
        self.add_info_message("🔍 开始数据库诊断...")
        
        try:
            # 查找所有表
            tables = self.conn.execute("SHOW TABLES").fetchall()
            self.add_info_message(f"\n📋 数据库中的表：")
            for table in tables:
                self.add_info_message(f"  - {table[0]}")
            
            # 检查 dayly_stock_data 表（可能是拼写错误）
            possible_tables = ['dayly_stock_data', 'daily_stock_data', 'stock_data', 'daily_data']
            found_table = None
            
            for table in tables:
                table_name = table[0].lower()
                for possible in possible_tables:
                    if possible in table_name:
                        found_table = table[0]
                        break
                if found_table:
                    break
            
            if found_table:
                self.add_info_message(f"\n✅ 找到数据表: {found_table}")
                
                # 查看表结构
                columns = self.conn.execute(f"PRAGMA table_info('{found_table}')").fetchall()
                self.add_info_message(f"\n📊 表结构：")
                for col in columns:
                    self.add_info_message(f"  - {col[1]}: {col[2]}")
                
                # 查找可能的股票代码字段
                code_columns = []
                for col in columns:
                    col_name = col[1].lower()
                    if 'code' in col_name or 'symbol' in col_name or 'stock' in col_name:
                        code_columns.append(col[1])
                
                if code_columns:
                    self.add_info_message(f"\n🎯 可能的股票代码字段: {', '.join(code_columns)}")
                    
                    # 显示一些示例数据
                    for code_col in code_columns[:1]:  # 只显示第一个
                        sample = self.conn.execute(f"SELECT {code_col} FROM {found_table} LIMIT 5").fetchall()
                        self.add_info_message(f"\n📝 {code_col} 字段示例数据:")
                        for row in sample:
                            self.add_info_message(f"  - {row[0]}")
                
                # 统计总记录数
                total_count = self.conn.execute(f"SELECT COUNT(*) FROM {found_table}").fetchone()[0]
                self.add_info_message(f"\n📈 总记录数: {total_count}")
                
                # 检查是否有600004的数据
                for code_col in code_columns[:1]:
                    check_query = f"SELECT COUNT(*) FROM {found_table} WHERE {code_col} LIKE '%600004%'"
                    count_600004 = self.conn.execute(check_query).fetchone()[0]
                    self.add_info_message(f"\n🔍 包含'600004'的记录数: {count_600004}")
                    
                    if count_600004 > 0:
                        # 显示具体的代码格式
                        samples = self.conn.execute(f"SELECT DISTINCT {code_col} FROM {found_table} WHERE {code_col} LIKE '%600004%' LIMIT 5").fetchall()
                        self.add_info_message(f"📝 实际存储的代码格式:")
                        for sample in samples:
                            self.add_info_message(f"  - {sample[0]}")
                
                self.table_info['table_name'] = found_table
                self.table_info['code_columns'] = code_columns
                
            else:
                self.add_info_message("\n⚠️ 未找到日线数据表")
                self.add_info_message("请确认表名是否为: dayly_stock_data 或 daily_stock_data")
                
        except Exception as e:
            self.add_info_message(f"❌ 诊断失败: {str(e)}", True)
        finally:
            if self.conn:
                self.conn.close()
        
        self.add_info_message("="*50 + "\n")

    def paste_code(self):
        """粘贴剪切板中的代码"""
        try:
            clipboard_text = self.root.clipboard_get()
            current_text = self.code_text.get("1.0", tk.END).strip()
            
            if current_text:
                self.code_text.insert(tk.END, "\n" + clipboard_text)
            else:
                self.code_text.insert("1.0", clipboard_text)
            
            self.status_var.set("已粘贴剪切板内容")
        except tk.TclError:
            messagebox.showwarning("粘贴失败", "剪切板为空或无法访问")
        except Exception as e:
            messagebox.showerror("粘贴错误", f"粘贴失败: {str(e)}")

    def clear_code(self):
        """清空代码输入框"""
        self.code_text.delete("1.0", tk.END)
        self.status_var.set("已清空代码列表")

    def add_info_message(self, message, is_error=False):
        """添加信息到信息框"""
        self.info_text.config(state=tk.NORMAL)
        
        if is_error:
            tag = "error"
            self.info_text.tag_config("error", foreground="red")
        else:
            tag = "info"
            self.info_text.tag_config("info", foreground="green")
        
        self.info_text.insert(tk.END, message + "\n", tag)
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)

    def connect_db(self):
        """连接数据库"""
        try:
            if self.conn:
                self.conn.close()
            db_path = self.db_path_var.get()
            
            if not os.path.exists(db_path):
                self.add_info_message(f"数据库文件不存在: {db_path}", True)
                return False
            
            self.conn = duckdb.connect(db_path)
            return True
        except Exception as e:
            self.add_info_message(f"数据库连接错误: {str(e)}", True)
            self.status_var.set("数据库连接失败")
            return False

    def find_stock_data_table(self):
        """查找日线数据表"""
        try:
            tables = self.conn.execute("SHOW TABLES").fetchall()
            possible_tables = ['dayly_stock_data', 'daily_stock_data', 'stock_data', 'daily_data']
            
            for table in tables:
                table_name = table[0].lower()
                for possible in possible_tables:
                    if possible in table_name:
                        return table[0]
            return None
        except:
            return None

    def find_code_column(self, table_name):
        """查找股票代码字段"""
        try:
            columns = self.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            for col in columns:
                col_name = col[1].lower()
                if 'code' in col_name or 'symbol' in col_name or 'stock' in col_name:
                    return col[1]
            return None
        except:
            return None

    def build_search_condition(self, code, code_column, match_mode):
        """构建搜索条件"""
        code = code.strip()
        
        if match_mode == "exact":
            # 精确匹配
            return f"{code_column} = '{code}'"
        
        elif match_mode == "fuzzy":
            # 模糊匹配
            return f"{code_column} LIKE '%{code}%'"
        
        else:  # smart mode
            # 智能匹配：尝试多种常见格式
            conditions = []
            
            # 原始代码
            conditions.append(f"{code_column} = '{code}'")
            
            # 带后缀的格式
            conditions.append(f"{code_column} = '{code}.SH'")
            conditions.append(f"{code_column} = '{code}.SZ'")
            conditions.append(f"{code_column} = '{code}.SS'")
            
            # 前缀格式
            conditions.append(f"{code_column} = 'SH{code}'")
            conditions.append(f"{code_column} = 'SZ{code}'")
            
            # 包含匹配
            conditions.append(f"{code_column} LIKE '%{code}%'")
            
            return "(" + " OR ".join(conditions) + ")"

    def delete_data(self):
        """执行删除操作"""
        # 获取输入的代码
        code_text = self.code_text.get("1.0", tk.END).strip()
        if not code_text:
            messagebox.showwarning("输入错误", "请至少输入一个股票代码")
            return
        
        # 解析代码列表
        code_list = [line.strip() for line in code_text.split('\n') if line.strip()]
        
        if not code_list:
            messagebox.showwarning("格式错误", "没有有效的股票代码")
            return
        
        # 连接数据库
        if not self.connect_db():
            return
        
        # 查找数据表
        table_name = self.find_stock_data_table()
        if not table_name:
            messagebox.showerror("表不存在", "未找到日线数据表，请先点击「诊断」按钮查看数据库结构")
            self.add_info_message("❌ 未找到日线数据表", True)
            return
        
        # 查找代码字段
        code_column = self.find_code_column(table_name)
        if not code_column:
            messagebox.showerror("字段不存在", "未找到股票代码字段")
            self.add_info_message("❌ 未找到股票代码字段", True)
            return
        
        # 显示确认信息
        code_display = '\n'.join(code_list[:10])
        if len(code_list) > 10:
            code_display += f"\n... 等共 {len(code_list)} 个代码"
            
        if not messagebox.askyesno("确认删除", 
                                   f"将要删除的表: {table_name}\n代码字段: {code_column}\n匹配模式: {self.match_mode.get()}\n\n"
                                   f"确定要删除以下 {len(code_list)} 个股票代码的所有数据吗？\n\n{code_display}\n\n此操作不可撤销！"):
            self.status_var.set("删除已取消")
            return
        
        # 清空信息框
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.config(state=tk.DISABLED)
        
        self.add_info_message(f"📊 数据库表: {table_name}")
        self.add_info_message(f"🎯 代码字段: {code_column}")
        self.add_info_message(f"⚙️ 匹配模式: {self.match_mode.get()}")
        self.add_info_message("="*50)
        
        total_deleted = 0
        success_list = []
        fail_list = []
        
        try:
            for code in code_list:
                try:
                    # 构建查询条件
                    condition = self.build_search_condition(code, code_column, self.match_mode.get())
                    query = f"DELETE FROM {table_name} WHERE {condition}"
                    
                    self.add_info_message(f"\n🔍 处理代码: {code}")
                    self.add_info_message(f"   SQL: {query}")
                    
                    result = self.conn.execute(query)
                    affected_rows = result.fetchall()[0][0] if result else 0
                    
                    if affected_rows > 0:
                        total_deleted += affected_rows
                        success_list.append((code, affected_rows))
                        self.add_info_message(f"   ✅ 删除 {affected_rows} 条记录")
                    else:
                        fail_list.append(code)
                        self.add_info_message(f"   ⚠️ 未找到数据", True)
                        
                except Exception as e:
                    fail_list.append(code)
                    self.add_info_message(f"   ❌ 删除失败: {str(e)}", True)
            
            # 执行检查点优化
            self.conn.execute("CHECKPOINT")
            
            # 显示汇总信息
            self.add_info_message("\n" + "="*50)
            self.add_info_message(f"📊 删除操作完成:")
            self.add_info_message(f"✅ 成功: {len(success_list)} 个股票代码，共删除 {total_deleted} 条记录")
            self.add_info_message(f"❌ 失败: {len(fail_list)} 个股票代码")
            
            if success_list and len(success_list) <= 20:
                self.add_info_message(f"\n📝 成功列表:")
                for code, count in success_list:
                    self.add_info_message(f"   {code}: {count} 条")
            
            if fail_list and len(fail_list) <= 20:
                self.add_info_message(f"\n⚠️ 失败列表:")
                for code in fail_list:
                    self.add_info_message(f"   {code}")
            
            if total_deleted > 0:
                self.status_var.set(f"✅ 删除完成！共删除 {total_deleted} 条记录")
                messagebox.showinfo("删除完成", f"成功删除 {len(success_list)} 个股票代码的数据，共 {total_deleted} 条记录\n失败: {len(fail_list)} 个")
            else:
                self.status_var.set("⚠️ 未找到任何匹配的数据")
                messagebox.showinfo("无数据", "未找到任何匹配的股票数据\n\n请点击「诊断」按钮查看数据库结构")
                
        except Exception as e:
            self.add_info_message(f"❌ 删除过程出错: {str(e)}", True)
            messagebox.showerror("删除错误", f"删除失败:\n{str(e)}")
            self.status_var.set("删除失败")
        finally:
            if self.conn:
                self.conn.close()

    def on_closing(self):
        """关闭窗口时清理连接"""
        if self.conn:
            self.conn.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = StockDataDeleter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()