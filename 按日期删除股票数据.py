import duckdb
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
from datetime import datetime


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
        self.root.title("日线数据删除工具")
        self.root.geometry("500x250")
        self.root.resizable(False, False)

        # 数据库路径
        self.db_path = os.path.join(get_base_path(), "stock_data", "stock_data.duckdb")
        self.conn = None

        # 创建界面
        self.create_widgets()

    def create_widgets(self):
        # 数据库选择区域
        db_frame = tk.LabelFrame(self.root, text="数据库设置", padx=10, pady=10)
        db_frame.pack(fill="x", padx=10, pady=5)

        self.db_path_var = tk.StringVar(value=self.db_path)

        tk.Entry(db_frame, textvariable=self.db_path_var, width=40).pack(side="left", padx=(0, 5))
        tk.Button(db_frame, text="打开", command=self.select_db).pack(side="left")

        # 日期选择区域
        date_frame = tk.LabelFrame(self.root, text="删除条件", padx=10, pady=10)
        date_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(date_frame, text="日期:").pack(side="left")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(date_frame, textvariable=self.date_var, width=15).pack(side="left", padx=10)

        # 删除按钮
        self.delete_btn = tk.Button(self.root, text="删除数据", command=self.delete_data, bg="#ff6b6b", fg="white",
                                    font=("Arial", 12))
        self.delete_btn.pack(pady=20)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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

    def connect_db(self):
        """连接数据库"""
        try:
            if self.conn:
                self.conn.close()
            db_path = self.db_path_var.get()
            self.conn = duckdb.connect(db_path)
            return True
        except Exception as e:
            messagebox.showerror("数据库连接错误", f"无法连接数据库:\n{str(e)}")
            self.status_var.set("数据库连接失败")
            return False

    def delete_data(self):
        """执行删除操作"""
        date = self.date_var.get().strip()
        if not date:
            messagebox.showwarning("输入错误", "请填写日期")
            return

        # 验证日期格式
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("格式错误", "日期格式应为 YYYY-MM-DD")
            return

        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除 {date} 的所有日线数据吗？\n\n此操作不可撤销！"):
            self.status_var.set("删除已取消")
            return

        # 连接数据库
        if not self.connect_db():
            return

        try:
            # 执行删除
            result = self.conn.execute(f"DELETE FROM dayly_stock_data WHERE date = '{date}'")
            affected_rows = result.fetchall()[0][0] if result else 0

            self.conn.execute("CHECKPOINT")

            if affected_rows > 0:
                self.status_var.set(f"✅ 删除成功！共删除 {affected_rows} 条记录")
                messagebox.showinfo("删除成功", f"已删除 {date} 的 {affected_rows} 条数据")
            else:
                self.status_var.set(f"⚠️ 未找到 {date} 的数据")
                messagebox.showinfo("无数据", f"未找到 {date} 的数据")

        except Exception as e:
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