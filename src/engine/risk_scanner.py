import pandas as pd

class RiskScanner:
    def __init__(self, data_dir="data/raw_financials"):
        self.data_dir = data_dir

    def load_data(self, report_date):
        self.df_balance = pd.read_csv(f"{self.data_dir}/all_balance_{report_date}.csv", dtype={'股票代码': str})
        # 如果需要现金流排雷，也可以加载现金流量表
        # self.df_cash = pd.read_csv(f"{self.data_dir}/all_cash_{report_date}.csv", dtype={'股票代码': str})

    def scan_stock(self, stock_code):
        try:
            stock_code = str(stock_code).zfill(6)
            b_row = self.df_balance[self.df_balance['股票代码'] == stock_code].iloc[0]
            
            # 获取核心指标
            total_assets = b_row['资产-总资产']
            cash = b_row['资产-货币资金']
            ar = b_row['资产-应收账款']
            inventory = b_row['资产-存货']
            debt_ratio = b_row['资产负债率']
            name = b_row['股票简称']

            # --- 风险扫描逻辑 ---
            warnings = []

            # 1. 现金含量排雷：账面看起来有钱，但实际现金占比极低
            cash_ratio = cash / total_assets
            if cash_ratio < 0.05:
                warnings.append(f"🔴 现金占比过低 ({cash_ratio:.1%})，流动性风险高")

            # 2. 应收账款排雷：钱都在别人兜里，可能是虚假繁荣
            ar_ratio = ar / total_assets
            if ar_ratio > 0.3:
                warnings.append(f"🟡 应收账款占比偏高 ({ar_ratio:.1%})，警惕回款风险")

            # 3. 存货挤压排雷：货卖不动，可能面临减值
            inv_ratio = inventory / total_assets
            if inv_ratio > 0.4:
                warnings.append(f"🟠 存货占比偏高 ({inv_ratio:.1%})，警惕库存积压")

            # 4. 杠杆风险：资不抵债
            if debt_ratio > 70:
                warnings.append(f"🔴 负债率过高 ({debt_ratio}%)，财务压力巨大")

            # 5. “存贷双高”初级检测：如果账上有钱但还在大量借钱（需结合负债明细，这里做简化提示）
            if cash_ratio > 0.2 and debt_ratio > 50:
                warnings.append(f"⚠️ 疑似存贷双高：账面资金充裕但负债率不低，需核实资金真实性")

            return {
                "代码": stock_code,
                "名称": name,
                "风险等级": "高危" if len(warnings) >= 2 else ("关注" if len(warnings) == 1 else "安全"),
                "预警信息": " | ".join(warnings) if warnings else "财务指标表现健康"
            }
        except Exception as e:
            return {"代码": stock_code, "风险等级": "分析失败", "预警信息": str(e)}

    def scan_portfolio(self, stock_list):
        results = [self.scan_stock(code) for code in stock_list]
        return pd.DataFrame(results)
    

if __name__ == "__main__":
    scanner = RiskScanner()
    scanner.load_data("20250930")
    print(scanner.scan_stock("600362"))