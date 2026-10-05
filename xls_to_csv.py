import os

def convert_xls_to_csv():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xls_path = os.path.join(script_dir, 'Table.xls')
    csv_path = os.path.join(script_dir, 'table.csv')
    
    if not os.path.exists(xls_path):
        return
    
    try:
        # 读取文件（自动检测编码）
        for encoding in ['gbk', 'utf-8', 'gb2312']:
            try:
                with open(xls_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except:
                continue
        else:
            return
        
        # 替换制表符为逗号
        content = content.replace('\t', ',')
        
        # 保存为 CSV
        with open(csv_path, 'w', encoding='utf-8-sig') as f:
            f.write(content)
            
    except Exception as e:
        pass

if __name__ == "__main__":
    convert_xls_to_csv()