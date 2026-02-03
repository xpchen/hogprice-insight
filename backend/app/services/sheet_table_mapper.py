"""Sheet表映射服务 - 将sheet映射到对应的独立表"""
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import re


class SheetTableMapper:
    """Sheet到表的映射器"""
    
    # Sheet名称到表名的映射规则（手动映射）
    SHEET_TO_TABLE_MAP = {
        # 涌益日度（8个）
        "价格+宰量": "yongyi_daily_price_slaughter",
        "各省份均价": "yongyi_daily_province_avg",
        "屠宰企业日度屠宰量": "yongyi_daily_slaughter_vol",
        "出栏价": "yongyi_daily_out_price",
        "散户标肥价差": "yongyi_daily_scatter_fat_spread",
        "市场主流标猪肥猪价格": "yongyi_daily_market_std_fat_price",
        "市场主流标猪肥猪均价方便作图": "yongyi_daily_market_avg_convenient",
        "交割地市出栏价": "yongyi_daily_delivery_city_price",
        
        # 涌益周度（主要sheet，13个）
        "周度-商品猪出栏价": "yongyi_weekly_out_price",
        "周度-体重": "yongyi_weekly_weight",
        "周度-屠宰厂宰前活猪重": "yongyi_weekly_slaughter_prelive_weight",
        "周度-各体重段价差": "yongyi_weekly_weight_spread",
        "周度-养殖利润最新": "yongyi_weekly_farm_profit_latest",
        "周度-冻品库存": "yongyi_weekly_frozen_inventory",
        "周度-冻品库存多样本": "yongyi_weekly_frozen_inventory_multi",
        "周度-毛白价差": "yongyi_weekly_live_white_spread",
        "周度-猪肉价（前三等级白条均价）": "yongyi_weekly_pork_price",
        "周度-屠宰企业日度屠宰量": "yongyi_weekly_slaughter_daily",
        "周度-50公斤二元母猪价格": "yongyi_weekly_sow_50kg_price",
        "周度-规模场15公斤仔猪出栏价": "yongyi_weekly_piglet_15kg_price",
        "周度-淘汰母猪价格": "yongyi_weekly_cull_sow_price",
        "周度-宰后结算价": "yongyi_weekly_post_slaughter_settle_price",
        
        # 钢联日度（7个）
        "分省区猪价": "ganglian_daily_province_price",
        "集团企业出栏价": "ganglian_daily_group_enterprise_price",
        "交割库出栏价": "ganglian_daily_delivery_warehouse_price",
        "区域价差": "ganglian_daily_region_spread",
        "肥标价差": "ganglian_daily_fat_std_spread",
        "毛白价差": "ganglian_daily_live_white_spread",
        "养殖利润（周度）": "ganglian_weekly_farm_profit",
    }
    
    @staticmethod
    def sheet_name_to_table_name(sheet_name: str, source_code: str, dataset_type: str) -> str:
        """
        将sheet名称转换为表名
        
        Args:
            sheet_name: Sheet名称
            source_code: 数据源代码（YONGYI/GANGLIAN/DCE）
            dataset_type: 数据集类型（DAILY/WEEKLY）
        
        Returns:
            表名
        """
        # 先查映射表
        if sheet_name in SheetTableMapper.SHEET_TO_TABLE_MAP:
            return SheetTableMapper.SHEET_TO_TABLE_MAP[sheet_name]
        
        # 否则自动生成
        # 1. 转换为snake_case
        snake_name = SheetTableMapper._to_snake_case(sheet_name)
        
        # 2. 组合表名
        table_name = f"{source_code.lower()}_{dataset_type.lower()}_{snake_name}"
        
        # 3. 限制长度（MySQL表名最长64字符）
        if len(table_name) > 64:
            table_name = table_name[:64]
        
        return table_name
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """将中文/英文名称转换为snake_case"""
        # 移除特殊字符
        name = re.sub(r'[^\w\s-]', '', name)
        # 替换空格和连字符为下划线
        name = re.sub(r'[\s-]+', '_', name)
        # 转小写
        name = name.lower()
        # 移除连续下划线
        name = re.sub(r'_+', '_', name)
        # 移除首尾下划线
        name = name.strip('_')
        return name
    
    @staticmethod
    def table_exists(db: Session, table_name: str) -> bool:
        """检查表是否存在"""
        inspector = inspect(db.bind)
        return table_name in inspector.get_table_names()
    
    @staticmethod
    def get_table_schema(db: Session, table_name: str) -> Optional[Dict]:
        """获取表结构信息"""
        if not SheetTableMapper.table_exists(db, table_name):
            return None
        
        inspector = inspect(db.bind)
        columns = inspector.get_columns(table_name)
        
        return {
            "table_name": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": col.get("default")
                }
                for col in columns
            ]
        }


def get_table_name_for_sheet(
    sheet_name: str,
    source_code: str,
    dataset_type: str
) -> str:
    """获取sheet对应的表名（便捷函数）"""
    return SheetTableMapper.sheet_name_to_table_name(sheet_name, source_code, dataset_type)
