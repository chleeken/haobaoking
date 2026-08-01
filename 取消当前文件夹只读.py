import os
import sys
def remove_readonly_from_files(folder_path):
    # 校验文件夹路径是否有效
    if not os.path.isdir(folder_path):
        sys.exit(1)
    
    # 遍历文件夹内一级文件(不包含子文件夹)
    for file_name in os.listdir(folder_path):
        file_full_path = os.path.join(folder_path, file_name)
        # 仅处理文件,跳过子文件夹
        if os.path.isfile(file_full_path):
            # 取消只读属性(Windows/Linux/Mac 通用)
            try:
                # 清除文件只读标识
                os.chmod(file_full_path, 0o644)  # 普通文件权限,可读写
            except:
                # 静默忽略单个文件处理失败(如权限不足),不中断整体执行
                continue

if __name__ == "__main__":
    # 获取脚本所在的当前文件夹路径
    TARGET_FOLDER = os.path.dirname(os.path.abspath(sys.argv[0]))
    # 执行取消只读操作
    remove_readonly_from_files(TARGET_FOLDER)
