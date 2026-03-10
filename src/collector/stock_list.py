import akshare as ak
import pandas as pd
import os
from datetime import datetime
from pathlib import Path

class StockList:
    def __init__(self, data_dir="data"):
        # BASE_DIR 指向项目的顶层根目录
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.data_dir = self.BASE_DIR / data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "stock_list.csv"

    def fetch_all_stocks(self):
        """
        从 AkShare 获取实时 A 股编号和名称列表
        """
        try:
            print(f"[{datetime.now()}] 正在从 AkShare 获取全量 A 股列表...")
            # 使用 stock_info_a_code_name 接口获取代码和简称
            # 这个接口数据量小，速度快，适合做基础索引
            df = ak.stock_info_a_code_name()
            
            # 统一字段名，方便后续使用
            df = df.rename(columns={'code': 'stock_code', 'name': 'stock_name'})
            
            # 格式化代码（确保 6 位数字，防止 000001 变成 1）
            df['stock_code'] = df['stock_code'].apply(lambda x: str(x).zfill(6))
            
            # 保存到本地 CSV，作为缓存
            df.to_csv(self.file_path, index=False, encoding='utf-8-sig')
            print(f"成功获取 {len(df)} 只股票，数据已保存至: {self.file_path}")
            return df
        
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            # 如果接口失效且有旧数据，则返回旧数据
            if os.path.exists(self.file_path):
                print("加载本地缓存数据...")
                return pd.read_csv(self.file_path)
            return None
        
    def get_local_list(self):
        """
        快速读取本地已有的列表
        """
        if os.path.exists(self.file_path):
            return pd.read_csv(self.file_path, dtype={'stock_code': str})
        return self.fetch_all_stocks()


if __name__ == "__main__":
    collector = StockList()
    collector.fetch_all_stocks()
