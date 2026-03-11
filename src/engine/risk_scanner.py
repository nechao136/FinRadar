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
        industry = logic['industry']

        if rule.get('is_special_sector'):
            return self._scan_financial_sector(stock_code, industry)

        # 2. 收集 5 年数据 (从 2020 到 2024, 假设 2025 年报还未全)
        years = ["20201231", "20211231", "20221231", "20231231", "20241231"]
        warnings = []
        valid_years = 0

        for date in years:
            df_year = self.collector.get_stock_metrics(stock_code, date)
            if df_year.empty:
                continue

            # 提取数据行（只有一行）
            valid_years += 1
            data = df_year.iloc[0]
            year_label = date[:4]

            # --- 核心字段提取 ---
            net_profit = data.get('净利润', 0)
            op_cash_flow = data.get('经营性现金流-现金流量净额', 0)
            equity = data.get('股东权益合计', 1)
            revenue = data.get('营业总收入', 1)
            op_cost = data.get('营业总支出-营业支出', 0)
            inventory = data.get('资产-存货', 0)
            ar_amount = data.get('资产-应收账款', 0)
            total_assets = data.get('资产-总资产', 1)
            debt_ratio = data.get('资产负债率', 0)
            capex = data.get('投资性现金流-现金流量净额', 0)
            # 商誉通常在‘资产-总资产’的明细里，如果你的表头没抓取，可暂设为0或后续补充
            goodwill = data.get('资产-商誉', 0)

            # --- 全维度排雷算法 ---

            # 1. ROE (核心盈利)
            roe = (net_profit / equity) * 100
            if roe < 8: warnings.append(f"{year_label}ROE过低({round(roe, 1)}%)")

            # 2. 净现比 (利润质量)
            if net_profit > 0:
                actual_cash_ratio = op_cash_flow / net_profit
                if actual_cash_ratio < 0.8: warnings.append(f"{year_label}净现比过低({round(actual_cash_ratio, 2)})")
            else:
                warnings.append(f"{year_label}利润亏损")

            # 3. 负债率 (财务杠杆)
            debt_limit = rule.get('debt_ratio_limit', 0.6) * 100
            if debt_ratio > debt_limit: warnings.append(f"{year_label}负债率过高({round(debt_ratio, 1)}%)")

            # 4. 毛利率 (产品竞争力)
            gross_margin = ((revenue - op_cost) / revenue) * 100
            if gross_margin < 15: warnings.append(f"{year_label}毛利过低({round(gross_margin, 1)}%)")

            # 5. 应收账款 (回款风险)
            if ar_amount / total_assets > 0.3: warnings.append(
                f"{year_label}应收占比高({round((ar_amount / total_assets) * 100, 1)}%)")

            # 6. 存货占比 (减值风险)
            if inventory / total_assets > 0.4: warnings.append(
                f"{year_label}存货堆积({round((inventory / total_assets) * 100, 1)}%)")

            # 7. 自由现金流 (FCF - 真实造血)
            fcf = op_cash_flow + capex
            if fcf < 0 < net_profit: warnings.append(f"{year_label}FCF为负(碎钞机)")

            # 8. 商誉风险 (如果存在)
            if goodwill / equity > 0.2: warnings.append(f"{year_label}商誉炸弹({round((goodwill / equity) * 100, 1)}%)")

        # 确保至少有 3 年以上数据，否则视为新股不进白名单
        if valid_years < 3:
            warnings.append("存续数据不足3年")

        return {
            "status": "DANGER" if warnings else "PASS",
            "warnings": warnings,
            "industry": logic['industry'],
            "nature_id": nature_id
        }

    def _scan_financial_sector(self, stock_code, industry):
        """
        金融类深度筛选：5年连续体检
        """
        years = ["20201231", "20211231", "20221231", "20231231", "20241231"]
        warnings = []
        prev_equity = None  # 用于比较净资产增长

        for date in years:
            df_year = self.collector.get_stock_metrics(stock_code, date)
            if df_year.empty: continue

            data = df_year.iloc[0]
            year_label = date[:4]

            # 1. 盈利能力 (ROE)
            equity = data.get('股东权益合计', 1)
            net_profit = data.get('净利润', 0)
            roe = (net_profit / equity) * 100

            if roe < 6:
                warnings.append(f"{year_label}回报过低(ROE:{round(roe, 1)}%)")

            # 2. 净资产成长性 (检查是否在“缩水”)
            if prev_equity is not None:
                if equity < prev_equity * 0.98:  # 允许 2% 的波动，防止由于分红导致的微调
                    warnings.append(f"{year_label}净资产萎缩(较上年减少)")
            prev_equity = equity

            # 3. 现金红利 (可选：如果你的表头有‘分红’字段)
            # data.get('派现', 0) ...

        return {
            "status": "DANGER" if warnings else "PASS",
            "warnings": warnings,
            "industry": industry,
            "nature_id": "E"
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