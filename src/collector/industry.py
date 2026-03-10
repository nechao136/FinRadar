import akshare as ak
import pandas as pd
import os
import yaml
from pathlib import Path


class IndustryManager:
    def __init__(self):
        # BASE_DIR 指向项目的顶层根目录
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        # 基础路径设置
        self.data_dir = self.BASE_DIR / "data" / "meta"
        self.config_dir = self.BASE_DIR / "config"
        self.industry_file = os.path.join(self.data_dir, "industry_map.csv")
        self.map_file = os.path.join(self.config_dir, "industry_nature_map.csv")
        self.rule_file = os.path.join(self.config_dir, "industry_rules.yaml")

        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)

        self.industry_map = {}  # {代码: 行业}
        self.nature_map = {}  # {具体行业: 性质ID}
        self.rules = {}  # {性质ID: 规则详情}

        # 初始化数据
        self._load_all_configs()

    def _load_all_configs(self):
        """一次性加载所有配置"""
        # 1. 加载股票-行业对应关系 (若没有则抓取)
        if os.path.exists(self.industry_file):
            df_map = pd.read_csv(self.industry_file, dtype={'代码': str})
            self.industry_map = dict(zip(df_map['代码'], df_map['行业']))
        else:
            self.fetch_all_industries()
            self.save_cache()

        # 2. 加载行业性质映射
        if os.path.exists(self.map_file):
            df_nature = pd.read_csv(self.map_file)
            self.nature_map = dict(zip(df_nature['具体行业'], df_nature['性质ID']))

        # 3. 加载专业规则库 (YAML)
        if os.path.exists(self.rule_file):
            with open(self.rule_file, 'r', encoding='utf-8') as f:
                self.rules = yaml.safe_load(f)

    def fetch_all_industries(self):
        """
        获取全市场行业板块及成分股
        """
        try:
            # 1. 获取所有行业板块列表
            df_ind_list = ak.stock_board_industry_name_em()

            for index, row in df_ind_list.iterrows():
                board_name = row['板块名称']
                print(f"正在同步行业: {board_name}...")

                # 2. 获取该行业下的所有个股
                try:
                    df_cons = ak.stock_board_industry_cons_em(symbol=board_name)
                    for code in df_cons['代码']:
                        self.industry_map[code] = board_name
                except Exception:
                    continue  # 容错处理

        except Exception as e:
            print(f"同步行业数据失败: {e}")

    def save_cache(self):
        """将行业映射保存到 CSV，下次启动无需等待"""
        df = pd.DataFrame(list(self.industry_map.items()), columns=['代码', '行业'])
        df.to_csv(self.industry_file, index=False, encoding='utf-8-sig')

    def get_stock_logic(self, stock_code):
        """
        终极核心方法：通过股票代码，直接拿走整套排雷标准
        """
        stock_code = str(stock_code).zfill(6)
        # 获取行业名
        ind_name = self.industry_map.get(stock_code, "未知行业")
        # 获取性质ID (A/B/C/D/E/F)
        nature_id = self.nature_map.get(ind_name, "DEFAULT")
        # 获取对应的规则配置
        rule_config = self.rules.get(nature_id, self.rules.get("DEFAULT"))

        return {
            "industry": ind_name,
            "nature_id": nature_id,
            "config": rule_config
        }


if __name__ == "__main__":
    # 使用示例
    manager = IndustryManager()

    # 模拟扫描江西铜业 (600362)
    logic = manager.get_stock_logic("600362")
    print(f"代码: 600362 | 行业: {logic['industry']} | 性质: {logic['nature_id']}")
    print(f"适用红线标准: {logic['config']}")