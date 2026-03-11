import pandas as pd
import akshare as ak
from pathlib import Path
from tqdm import tqdm


class AbsoluteValuator:
    def __init__(self, data_dir="data/raw_financials", r=0.08):
        self.market_cap_map = None
        self.df_spot = None
        self.df_c = None
        self.df_p = None
        self.df_b = None
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.data_dir = self.BASE_DIR / data_dir
        self.r = r  # 基准折现率 (8%)

    def load_all_financials(self, report_date):
        """一次性加载全市场数据到内存，避免循环读取"""
        print(f"正在预加载 {report_date} 财报数据...")
        self.df_b = pd.read_csv(self.data_dir / f"all_balance_{report_date}.csv", dtype={'股票代码': str})
        self.df_p = pd.read_csv(self.data_dir / f"all_profit_{report_date}.csv", dtype={'股票代码': str})
        self.df_c = pd.read_csv(self.data_dir / f"all_cash_{report_date}.csv", dtype={'股票代码': str})

        # 获取最新实时市值 (使用 akshare)
        print("获取全市场实时行情...")
        self.df_spot = ak.stock_zh_a_spot_em()
        # 提取代码和总市值 (单位：元)
        self.market_cap_map = self.df_spot.set_index('代码')['总市值'].to_dict()

    def get_params_by_nature(self, nature_id):
        """根据性质ID动态调整估值参数"""
        # 默认参数
        params = {"g": 0.03, "weights": (0.33, 0.33, 0.34)}  # (DDM, DCF, RIM)

        if nature_id == 'E':  # 金融类：偏重分红和剩余收益
            # 银行股永续增长率g绝不能超过r，通常设为 2% 左右锚定长期通胀
            # 权重彻底剔除 DCF (0.0)，由 DDM 和 RIM 均分
            params = {"g": 0.02, "weights": (0.50, 0.0, 0.50)}
        elif nature_id == 'B' or nature_id == 'D':  # 科技/成长：偏重现金流
            params = {"g": 0.05, "weights": (0.10, 0.70, 0.20)}
        elif nature_id == 'C':  # 消费：平衡型
            params = {"g": 0.04, "weights": (0.30, 0.40, 0.30)}

        # 修正3：安全锁，确保 g 永远小于 r 至少 2%
        if params["g"] >= self.r - 0.02:
            params["g"] = self.r - 0.02

        return params

    def calc_intrinsic_value(self, code, nature_id):
        """核心计算逻辑"""
        try:
            # 提取单行数据
            b = self.df_b[self.df_b['股票代码'] == code].iloc[0]
            p = self.df_p[self.df_p['股票代码'] == code].iloc[0]
            c = self.df_c[self.df_c['股票代码'] == code].iloc[0]

            p_id = self.get_params_by_nature(nature_id)
            g = p_id['g']

            # --- 1. DDM (股利折现) ---
            net_profit = p.get('净利润', 0)
            payout_ratio = 0.30 if nature_id == 'E' else 0.35
            v_ddm = (net_profit * payout_ratio * (1 + g)) / (self.r - g)

            # --- 2. DCF (自由现金流折现 - 简化两阶段) ---
            # FCF = 经营现金流 - 资本开支(估算)
            fcf0 = c.get('经营性现金流-现金流量净额', 0) * 0.8  # 假设20%用于维护性开支
            v_dcf = (fcf0 * (1 + g)) / (self.r - g)

            # --- 3. RIM (剩余收益) ---
            equity = b.get('股东权益合计', 1)
            v_rim = equity + (net_profit - equity * self.r) / (self.r - g + 0.01) # 增加微小偏移防止分母为0

            # 综合估值
            w = p_id['weights']
            fair_value = v_ddm * w[0] + v_dcf * w[1] + v_rim * w[2]

            return fair_value, equity
        except:
            return None, None

    def run_valuation(self, whitelist_path):
        """执行白名单批量估值"""
        white_df = pd.read_csv(whitelist_path, dtype={'代码': str})
        results = []

        for _, row in tqdm(white_df.iterrows(), total=len(white_df), desc="估值进度"):
            code = row['代码']
            name = row['名称']
            nature = row['性质ID']

            intrinsic_v, equity = self.calc_intrinsic_value(code, nature)
            current_cap = self.market_cap_map.get(code, 0)

            if intrinsic_v and current_cap > 0:
                # 计算PB (市净率) 辅助判断
                pb = current_cap / equity if equity > 0 else 0

                # 计算安全边际
                margin = (intrinsic_v - current_cap) / intrinsic_v
                results.append({
                    "代码": code,
                    "名称": name,
                    "性质": nature,
                    "PB": round(pb, 2),
                    "内在价值(亿)": round(intrinsic_v / 1e8, 2),
                    "当前市值(亿)": round(current_cap / 1e8, 2),
                    "安全边际": f"{margin:.1%}",
                    "估值状态": "低估" if margin > 0.2 else ("合理" if margin > -0.1 else "高估")
                })

        final_df = pd.DataFrame(results).sort_values(by="安全边际", ascending=False)
        final_df.to_csv("白名单内在价值分析报告.csv", index=False, encoding='utf-8-sig')
        print("估值完成，报告已生成。")


if __name__ == "__main__":
    valuator = AbsoluteValuator()
    valuator.load_all_financials("20250930")
    valuator.run_valuation("排雷结果_白名单.csv")