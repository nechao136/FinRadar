import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime


class RiskScanner:
    def __init__(self, collector, industry_mgr):
        # 依赖注入：需要你之前写的采集器和行业管家
        self.collector = collector
        self.ind_mgr = industry_mgr

        # 路径锚定
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.rule_file = self.BASE_DIR / "config" / "industry_rules.yaml"

        # 加载排雷红线
        with open(self.rule_file, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)

    def scan_stock(self, stock_code):
        """
        对单只股票执行 5 年深度体检
        """
        # 1. 获取行业背景和红线
        logic = self.ind_mgr.get_stock_logic(stock_code)
        nature_id = logic['nature_id']
        rule = logic['config']

        if rule.get('is_special_sector'):
            return {"status": "SKIP", "reason": "金融类需人工核查"}

        # 2. 收集 5 年数据 (从 2020 到 2024, 假设 2025 年报还未全)
        years = ["20201231", "20211231", "20221231", "20231231", "20241231"]
        warnings = []

        for date in years:
            df_year = self.collector.get_stock_metrics(stock_code, date)
            if df_year.empty:
                continue

            # 提取数据行（只有一行）
            data = df_year.iloc[0]
            year_label = date[:4]

            # --- 精准取值 ---
            # 偿债能力 (资产负债表字段)
            debt_ratio = data.get('资产负债率', 0)
            # 盈利质量 (利润表 vs 现金流量表字段)
            net_profit = data.get('净利润', 0)
            op_cash_flow = data.get('经营性现金流-现金流量净额', 0)
            # 资产风险(资产负债表字段)
            # 注意：你提供的表头中没有明确写“商誉”，通常在总资产详情中，
            # 如果暂无商誉字段，我们可以先监控“应收账款”占比
            ar_amount = data.get('资产-应收账款', 0)
            total_assets = data.get('资产-总资产', 1)  # 避开除以0值

            # --- 开始排雷逻辑 ---

            # 1. 负债率检查 (百分比数值)
            debt_limit = rule.get('debt_ratio_limit', 0.6) * 100
            if debt_ratio > debt_limit:
                warnings.append(f"{year_label}负债率过高({round(debt_ratio, 1)}%)")

            # 2. 净现比检查 (盈利质量)
            net_cash_ratio_min = rule.get('net_cash_ratio_min', 0.7)
            if net_profit > 0:
                actual_ratio = op_cash_flow / net_profit
                if actual_ratio < net_cash_ratio_min:
                    warnings.append(f"{year_label}净现比过低({round(actual_ratio, 2)})")
            elif net_profit < 0 and op_cash_flow < 0:
                warnings.append(f"{year_label}经营性亏损(利润与现金流双负)")

            # 3. 应收账款占比检查 (替代商誉检查，防止虚增营收)
            ar_limit = rule.get('ar_to_revenue_limit', 0.4)
            if ar_amount / total_assets > ar_limit:
                warnings.append(f"{year_label}应收账款占比过高({round((ar_amount / total_assets) * 100, 1)}%)")

        return {
            "status": "DANGER" if warnings else "PASS",
            "warnings": warnings,
            "industry": logic['industry'],
            "nature_id": nature_id
        }


if __name__ == "__main__":
    from src.collector.financial_raw import FinancialCollector
    from src.collector.industry import IndustryManager
    from src.collector.stock_list import StockList

    # 1. 初始化组件
    col = FinancialCollector()
    mgr = IndustryManager()
    sl = StockList()
    scanner = RiskScanner(col, mgr)

    # 2. 获取全市场股票清单
    stocks = sl.get_local_list()
    total_count = len(stocks)

    danger_list = []  # 存风险公司
    gold_list = []  # 存优质公司 (无风险点)

    print(f"[{datetime.now()}] 🚀 引擎启动，开始扫描全市场 {total_count} 只股票...")

    # 3. 开始循环扫描
    for index, row in stocks.iterrows():
        code = row['stock_code']
        name = row['stock_name']

        # 进度提示：每扫 100 只打印一次进度
        if index % 100 == 0:
            print(f"正在扫描: {index}/{total_count} ({round(index / total_count * 100, 2)}%)")

        try:
            report = scanner.scan_stock(code)

            # 记录数据结构
            base_info = {
                "代码": code,
                "名称": name,
                "行业": report.get('industry', '未知'),
                "性质ID": report.get('nature_id', '-')
            }

            if report['status'] == "DANGER":
                # 加入黑名单
                base_info["风险详情"] = " | ".join(report['warnings'])
                base_info["风险点数量"] = len(report['warnings'])
                danger_list.append(base_info)

            elif report['status'] == "PASS":
                # 加入优质白名单
                gold_list.append(base_info)

        except Exception as e:
            # 容错处理：防止单只股票数据格式问题导致整个扫描中断
            print(f"跳过股票 {code} {name}: 数据异常或缺失 -> {e}")
            continue

    # 4. 结果持久化
    print(f"\n--- 扫描完成 [{datetime.now()}] ---")

    # 保存黑名单
    if danger_list:
        pd.DataFrame(danger_list).to_csv("排雷结果_黑名单.csv", index=False, encoding='utf-8-sig')
        print(f"🚩 风险公司: {len(danger_list)} 家，已保存至 '排雷结果_黑名单.csv'")

    # 保存优质白名单
    if gold_list:
        pd.DataFrame(gold_list).to_csv("排雷结果_白名单.csv", index=False, encoding='utf-8-sig')
        print(f"✨ 优质公司: {len(gold_list)} 家，已保存至 '排雷结果_白名单.csv'")

    print("💡 建议优先关注 '白名单' 中连续 5 年数据完整的公司。")