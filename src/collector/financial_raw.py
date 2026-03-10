import akshare as ak
import pandas as pd
from pathlib import Path


class FinancialCollector:
    def __init__(self, data_dir="data/raw_financials"):
        # BASE_DIR 指向项目的顶层根目录
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.data_dir = self.BASE_DIR / data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_individual_finance(self, report_date="20241231", force_update=False):
        """
        下载全市场指定日期的三张表，并保存
        :param report_date: 报告期 (如 20241231)
        :param force_update: 是否忽略本地缓存，强制重新下载
        """
        # 定义本地文件路径
        files = {
            "balance": self.data_dir / f"all_balance_{report_date}.csv",
            "profit": self.data_dir / f"all_profit_{report_date}.csv",
            "cash": self.data_dir / f"all_cash_{report_date}.csv"
        }

        # 检查是否所有文件都存在
        all_exist = all(f.exists() for f in files.values())

        if all_exist and not force_update:
            print(f"[{report_date}] 发现本地缓存，正在加载...")
            df_balance = pd.read_csv(files["balance"], dtype={'股票代码': str})
            df_profit = pd.read_csv(files["profit"], dtype={'股票代码': str})
            df_cash = pd.read_csv(files["cash"], dtype={'股票代码': str})
            return df_balance, df_profit, df_cash

        # 否则，从接口抓取
        try:
            print(f"[{report_date}] 正在从网络抓取全市场财报 (强制更新={force_update})...")
            
            # 1. 资产负债表 (Balance Sheet)
            df_balance = ak.stock_zcfz_em(date=report_date)
            # 2. 利润表 (Income Statement)
            df_profit = ak.stock_lrb_em(date=report_date)
            # 3. 现金流量表 (Cash Flow)
            df_cash = ak.stock_xjll_em(date=report_date)
            
            # 保存大表，方便后续多次读取
            df_balance.to_csv(f"{self.data_dir}/all_balance_{report_date}.csv", index=False, encoding='utf-8-sig')
            df_profit.to_csv(f"{self.data_dir}/all_profit_{report_date}.csv", index=False, encoding='utf-8-sig')
            df_cash.to_csv(f"{self.data_dir}/all_cash_{report_date}.csv", index=False, encoding='utf-8-sig')

            print(f"[{report_date}] 抓取并保存成功。")
            return df_balance, df_profit, df_cash
        except Exception as e:
            print(f"抓取失败: {e}")
            return None, None, None

    def get_stock_metrics(self, stock_code, report_date="20241231"):
        """
        从大表中提取特定个股的数据
        """
        stock_code = str(stock_code).zfill(6)
        df_b, df_p, df_c = self.fetch_individual_finance(report_date)

        if df_b is None or df_p is None or df_c is None:
            return pd.DataFrame()

        # 1. 提取个股各表数据
        # 备注：东方财富接口返回的字段名可能包含‘股票代码’
        b_stock = df_b[df_b['股票代码'] == stock_code]
        p_stock = df_p[df_p['股票代码'] == stock_code]
        c_stock = df_c[df_c['股票代码'] == stock_code]

        if b_stock.empty or p_stock.empty or c_stock.empty:
            return pd.DataFrame()

        # 2. 横向合并 (使用 pandas.concat 或 merge)
        # 为了避免重复的列名（如股票名称），我们只保留一张表的索引信息
        combined = pd.merge(b_stock, p_stock, on=['股票代码', '股票简称'], suffixes=('', '_profit'))
        combined = pd.merge(combined, c_stock, on=['股票代码', '股票简称'], suffixes=('', '_cash'))

        return combined
    

if __name__ == "__main__":
    collector = FinancialCollector()
    collector.fetch_individual_finance("20251231")
