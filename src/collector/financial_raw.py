import akshare as ak
import pandas as pd
import os


class FinancialCollector:
    def __init__(self, data_dir="data/raw_financials"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def fetch_individual_finance(self, report_date="20241231"):
        """
        下载全市场指定日期的三张表，并保存
        """
        try:
            print(f"正在下载 {report_date} 报告期的全市场财报...")
            
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
            
            return df_balance, df_profit, df_cash
        except Exception as e:
            print(f"抓取失败: {e}")
            return None, None, None

    def get_stock_metrics(self, stock_code, report_date="20241231"):
        """
        从大表中提取特定个股的数据
        """
        # 读取本地保存的大表
        df_profit = pd.read_csv(f"{self.data_dir}/all_profit_{report_date}.csv", dtype={'股票代码': str})
        
        # 筛选个股数据
        stock_data = df_profit[df_profit['股票代码'] == stock_code]
        return stock_data
    

if __name__ == "__main__":
    collector = FinancialCollector()
    collector.fetch_individual_finance("20250930")
