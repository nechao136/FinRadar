import pandas as pd
import numpy as np

class ValuationAnalyser:
    def __init__(self, data_dir="data/raw_financials"):
        self.data_dir = data_dir
        # 默认折现率 (r)，通常设为 8%-10%
        self.r = 0.09 

    def load_data(self, report_date, stock_code):
        """加载单只股票的所有报表数据"""
        try:
            stock_code = str(stock_code).zfill(6)
            # 加载全市场大表并筛选
            df_b = pd.read_csv(f"{self.data_dir}/all_balance_{report_date}.csv", dtype={'股票代码': str})
            df_p = pd.read_csv(f"{self.data_dir}/all_profit_{report_date}.csv", dtype={'股票代码': str})
            # 假设你已经采集了现金流量表
            df_c = pd.read_csv(f"{self.data_dir}/all_cash_{report_date}.csv", dtype={'股票代码': str})

            self.b_row = df_b[df_b['股票代码'] == stock_code].iloc[0]
            self.p_row = df_p[df_p['股票代码'] == stock_code].iloc[0]
            self.c_row = df_c[df_c['股票代码'] == stock_code].iloc[0]
            return True
        except Exception as e:
            print(f"加载数据失败: {e}")
            return False

    def calc_ddm(self, g=0.03):
        """
        1. 股利折现模型 (DDM - 戈登增长模型)
        公式: V = D1 / (r - g)
        """
        # 假设分红总额 = 净利润 * 分红率 (通常取 30%-50%)
        # 也可以直接从财报获取上一年度现金分红
        net_profit = self.p_row['净利润']
        payout_ratio = 0.4  # 假设分红率为40%
        d0 = (net_profit * payout_ratio) / self.b_row['资产-总资产'] # 简化为每资产分红
        # 注意：这里为了演示简化了股数逻辑，实战中应用：每股分红 / (r - g)
        v_ddm = (net_profit * payout_ratio * (1 + g)) / (self.r - g)
        return v_ddm

    def calc_dcf(self, g_growth=0.10, g_terminal=0.02, years=5):
        """
        2. 自由现金流折现模型 (DCF - 两阶段模型)
        """
        # FCF 简化计算：经营活动现金流 - 资本开支(假设为总资产的5%)
        fcf0 = self.c_row['经营活动产生的现金流量净额'] - (self.b_row['资产-总资产'] * 0.05)
        
        # 第一阶段：高速增长期
        pv_stage1 = 0
        for t in range(1, years + 1):
            fcf_t = fcf0 * (1 + g_growth)**t
            pv_stage1 += fcf_t / (1 + self.r)**t
            
        # 第二阶段：永续增长期 (终值)
        fcf_final = fcf0 * (1 + g_growth)**years * (1 + g_terminal)
        tv = fcf_final / (self.r - g_terminal)
        pv_tv = tv / (1 + self.r)**years
        
        return pv_stage1 + pv_tv

    def calc_rim(self):
        """
        3. 剩余收益模型 (RIM)
        价值 = 当前净资产 + 未来剩余收益的折现
        """
        equity = self.b_row['股东权益合计']
        net_profit = self.p_row['净利润']
        # 剩余收益 = 净利润 - (期初净资产 * 资本成本)
        residual_income = net_profit - (equity * self.r)
        
        # 简化为永续剩余收益模型
        v_rim = equity + (residual_income / self.r)
        return v_rim

    def integrated_valuation(self, stock_code, current_market_cap):
        """
        综合分析：根据公司类型分配权重
        """
        v_ddm = self.calc_ddm()
        v_dcf = self.calc_dcf()
        v_rim = self.calc_rim()
        
        # 逻辑：如果净利率高且增长快，DCF权重高；如果分红高，DDM权重高
        # 这里演示统一取平均值，实战可根据你 5+5 的分类调整
        fair_value_total = (v_ddm * 0.33) + (v_dcf * 0.33) + (v_rim * 0.34)
        
        margin_of_safety = (fair_value_total - current_market_cap) / fair_value_total
        
        return {
            "代码": stock_code,
            "DDM估值": round(v_ddm / 1e8, 2), # 以亿为单位
            "DCF估值": round(v_dcf / 1e8, 2),
            "RIM估值": round(v_rim / 1e8, 2),
            "综合内在价值(亿)": round(fair_value_total / 1e8, 2),
            "当前市值(亿)": round(current_market_cap / 1e8, 2),
            "安全边际": f"{margin_of_safety:.1%}",
            "结论": "高估" if margin_of_safety < 0 else ("极具价值" if margin_of_safety > 0.3 else "合理")
        }

if __name__ == "__main__":
    v = ValuationAnalyser()
    # 示例：分析江西铜业，假设当前市值 800 亿
    if v.load_data("20241231", "600362"):
        report = v.integrated_valuation("600362", 800 * 1e8)
        print(report)