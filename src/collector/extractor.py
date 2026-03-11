import pandas as pd
import akshare as ak
from pathlib import Path
from tqdm import tqdm


class FullFinancialExtractor:
    def __init__(self, data_dir="data/raw_financials"):
        # BASE_DIR 指向项目的顶层根目录
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.data_dir = self.BASE_DIR / data_dir
        # 生成时间轴
        years = [str(y) for y in range(2014, 2026)]  # 包含2026年
        months = ['0331', '0630', '0930', '1231']
        self.report_dates = [y + m for y in years for m in months]
        # 定义三张表的命名前缀（请确保你的文件名符合此规则）
        self.table_types = {
            'balance': 'all_balance_',
            'profit': 'all_profit_',
            'cash': 'all_cash_'
        }

    def extract_full_history(self, stock_code, output_file="full_history_data.csv"):
        """横向合并三表数据"""
        all_period_data = []

        print(f"开始深度提取代码 {stock_code} 的三表数据...")
        for date in tqdm(self.report_dates):
            period_dfs = []

            # 依次读取三张表
            for t_name, prefix in self.table_types.items():
                file_path = self.data_dir / f"{prefix}{date}.csv"
                if file_path.exists():
                    try:
                        df = pd.read_csv(file_path, dtype={'股票代码': str})
                        target_row = df[df['股票代码'] == stock_code].copy()
                        if not target_row.empty:
                            # 为防止列名冲突，除了股票代码和名称，其余列加上表名前缀
                            # 但为了方便你后续分析，我们保留原始列名，仅在合并时去重
                            period_dfs.append(target_row.set_index('股票代码'))
                    except Exception:
                        pass  # 忽略读取错误

            # 如果该报告期至少有一张表的数据，则进行横向合并
            if period_dfs:
                # 使用 concat 横向合并（axis=1），会自动处理重复的列
                merged_period = pd.concat(period_dfs, axis=1)
                # 移除重复列（如股票名称、行业等）
                merged_period = merged_period.loc[:, ~merged_period.columns.duplicated()]
                merged_period['报告期'] = date
                all_period_data.append(merged_period)

        if all_period_data:
            final_df = pd.concat(all_period_data, ignore_index=True)
            final_df = final_df.sort_values('报告期')
            # 调整列顺序，把报告期放到最前面
            cols = ['报告期'] + [c for c in final_df.columns if c != '报告期']
            final_df[cols].to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n三表合一历史数据提取完成！\n保存路径: {output_file}")
        else:
            print("未找到该公司的任何报表数据。")

    def get_realtime_data(self, stock_code, output_file="realtime_summary.csv"):
        """获取实时行情、市值及估值指标"""
        print(f"正在抓取 {stock_code} 的最新市场数据...")
        try:
            df_spot = ak.stock_zh_a_spot_em()
            target = df_spot[df_spot['代码'] == stock_code].copy()
            if not target.empty:
                # 选取你分析最需要的字段
                useful_cols = [
                    "序号",
                    "代码",
                    "名称",
                    "最新价",
                    "涨跌幅",
                    "涨跌额",
                    "成交量",
                    "成交额",
                    "振幅",
                    "最高",
                    "最低",
                    "今开",
                    "昨收",
                    "量比",
                    "换手率",
                    "市盈率-动态",
                    "市净率",
                    "总市值",
                    "流通市值",
                    "涨速",
                    "5分钟涨跌",
                    "60日涨跌幅",
                    "年初至今涨跌幅",
                ]
                target[useful_cols].to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"实时数据已保存: {output_file}")
        except Exception as e:
            print(f"实时行情获取失败: {e}")


if __name__ == "__main__":
    extractor = FullFinancialExtractor()
    # 以你关注的“招商银行”为例
    code = "603899"

    extractor.extract_full_history(code, f"{code}_history_full.csv")
    extractor.get_realtime_data(code, f"{code}_realtime.csv")