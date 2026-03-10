import pandas as pd

class DupontAnalyser:
    def __init__(self, data_dir="data/raw_financials"):
        self.data_dir = data_dir

    def load_market_data(self, report_date):
        """加载全市场大表数据"""
        try:
            # 强制将股票代码读取为字符串，防止丢失前导零
            self.df_balance = pd.read_csv(f"{self.data_dir}/all_balance_{report_date}.csv", dtype={'股票代码': str})
            self.df_profit = pd.read_csv(f"{self.data_dir}/all_profit_{report_date}.csv", dtype={'股票代码': str})
            return True
        except FileNotFoundError:
            print(f"找不到 {report_date} 的数据文件，请先运行采集脚本。")
            return False

    def calculate_stock(self, stock_code):
        """计算单只股票的杜邦三要素"""
        try:
            stock_code = str(stock_code).zfill(6)
            # 1. 提取利润数据
            profit_row = self.df_profit[self.df_profit['股票代码'] == stock_code].iloc[0]
            # 东方财富接口列名通常包含：'营业总收入', '净利润'
            net_profit = profit_row['净利润']
            revenue = profit_row['营业总收入']

            # 2. 提取资产数据
            balance_row = self.df_balance[self.df_balance['股票代码'] == stock_code].iloc[0]
            # 对应列名：'资产-总资产', '股东权益合计'
            total_assets = balance_row['资产-总资产']
            total_equity = balance_row['股东权益合计']

            # 3. 杜邦公式计算
            # 销售净利率 (Profit Margin)
            net_margin = net_profit / revenue
            # 资产周转率 (Asset Turnover)
            asset_turnover = revenue / total_assets
            # 权益乘数 (Financial Leverage)
            equity_multiplier = total_assets / total_equity
            
            # 最终 ROE
            roe = net_margin * asset_turnover * equity_multiplier

            return {
                "代码": stock_code,
                "名称": profit_row['股票简称'],
                "ROE": round(roe * 100, 2), # 转为百分比
                "净利率": round(net_margin * 100, 2),
                "周转率": round(asset_turnover, 3),
                "杠杆倍数": round(equity_multiplier, 2)
            }
        except Exception as e:
            print(f"计算股票 {stock_code} 时出错: {e}")
            return None

    def analyze_portfolio(self, stock_list):
        """批量分析组合"""
        results = []
        for code in stock_list:
            res = self.calculate_stock(code)
            if res:
                results.append(res)
        return pd.DataFrame(results)
    

if __name__ == "__main__":
    analyser = DupontAnalyser()
    analyser.load_market_data("20250930")
    print(analyser.calculate_stock("600362"))