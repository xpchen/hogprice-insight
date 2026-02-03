"""
单独运行区域价差数据入库脚本
数据来源：钢联"区域价差"sheet

标题格式：（区域价差：XX-YY）
注释：5日涨跌，10日涨跌
"""
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path
import pandas as pd
import hashlib
from datetime import datetime, date
from typing import Dict, List, Optional
import json
import io
import re

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import (
    FactObservation, FactObservationTag, DimMetric, DimGeo, 
    ImportBatch, DimSource
)
from app.utils.value_cleaner import clean_numeric_value
from app.utils.region_normalizer import normalize_province_name
from app.services.region_mapping_service import get_or_create_region


class RegionSpreadExtractor:
    """区域价差数据提取器"""
    
    def __init__(self, db: Session, file_path: Path):
        self.db = db
        self.file_path = file_path
        self.extraction_log = []
        
    def extract_and_insert(self) -> Dict:
        """提取并插入数据"""
        print(f"开始提取区域价差数据: {self.file_path}")
        
        # 创建导入批次
        batch = self._create_batch()
        
        # 提取数据
        results = {
            "batch_id": batch.id,
            "region_spread": self._extract_region_spread(batch.id)
        }
        
        # 提交事务
        try:
            self.db.commit()
            print("数据提交成功")
        except Exception as e:
            self.db.rollback()
            print(f"数据提交失败: {e}")
            raise
        
        # 保存提取日志
        self._save_extraction_log(results)
        
        return results
    
    def _create_batch(self) -> ImportBatch:
        """创建导入批次"""
        batch = ImportBatch(
            filename=self.file_path.name,
            source_code="GANGLIAN",
            status="completed",
            total_rows=0,
            inserted_count=0,
            failed_rows=0
        )
        self.db.add(batch)
        self.db.flush()
        return batch
    
    def _extract_region_spread(self, batch_id: int) -> Dict:
        """提取区域价差数据（从区域价差sheet，提取所有区域对）"""
        print("提取区域价差数据...")
        
        sheet_name = "区域价差"
        excel_file = pd.ExcelFile(self.file_path, engine='openpyxl')
        
        # 检查sheet是否存在
        if sheet_name not in excel_file.sheet_names:
            return {"error": f"Sheet '{sheet_name}' 不存在", "inserted": 0}
        
        # 读取指标名称行（第2行）
        indicator_names_df = pd.read_excel(
            excel_file, sheet_name=sheet_name,
            header=None, nrows=1, skiprows=1
        )
        indicator_names = indicator_names_df.iloc[0].tolist()
        
        # 读取单位行（第3行）
        units_df = pd.read_excel(
            excel_file, sheet_name=sheet_name,
            header=None, nrows=1, skiprows=2
        )
        units = units_df.iloc[0].tolist()
        
        # 读取数据（从第5行开始）
        df = pd.read_excel(
            excel_file, sheet_name=sheet_name,
            header=None, skiprows=4
        )
        
        # 提取所有区域对列
        # 注意：第1列（index 0）是"指标名称"列，在数据行中是日期列
        # 第2列开始（index 1+）是各区域对的价差数据列
        total_inserted = 0
        region_pair_results = {}
        
        # 从第2列开始处理（第1列是日期列）
        for col_idx in range(1, len(indicator_names)):
            if col_idx >= len(indicator_names):
                break
                
            raw_header = indicator_names[col_idx]
            if pd.isna(raw_header) or not raw_header:
                continue
            
            raw_header_str = str(raw_header)
            
            # 解析区域对，格式："商品猪：出栏均价：XX（日） - 商品猪：出栏均价：YY（日）"
            # 提取XX和YY
            # 匹配模式：商品猪：出栏均价：XX（日） - 商品猪：出栏均价：YY（日）
            match = re.search(r'商品猪：出栏均价：([^：（）]+)（日）\s*-\s*商品猪：出栏均价：([^：（）]+)（日）', raw_header_str)
            if not match:
                # 尝试更宽松的匹配
                match = re.search(r'：([^：（）]+)（日）\s*-\s*[^：]*：([^：（）]+)（日）', raw_header_str)
                if not match:
                    print(f"跳过列 {col_idx}: 无法解析区域对 - {raw_header_str}")
                    continue
            
            region1 = match.group(1).strip()
            region2 = match.group(2).strip()
            region_pair = f"{region1}-{region2}"
            
            print(f"处理区域对: {region_pair} (列 {col_idx})")
            
            # 获取或创建指标（每个区域对一个指标）
            # 指标名称格式：区域价差：XX-YY
            metric_key = f"GL_D_REGION_SPREAD_{region1}_{region2}"
            metric_name = f"区域价差：{region1}-{region2}"
            metric = self._get_or_create_metric(
                metric_key=metric_key,
                metric_name=metric_name,
                source_code="GANGLIAN",
                sheet_name=sheet_name,
                unit=units[col_idx] if col_idx < len(units) else "元/公斤",
                raw_header=raw_header_str
            )
            
            # 提取该区域对的数据
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            for row_idx, row in df.iterrows():
                try:
                    # 第1列（index 0）是日期列
                    date_val = row.iloc[0]
                    if pd.isna(date_val):
                        skipped_count += 1
                        continue
                    
                    # 转换为日期对象
                    if isinstance(date_val, str):
                        trade_date = pd.to_datetime(date_val).date()
                    elif hasattr(date_val, 'date'):
                        trade_date = date_val.date()
                    else:
                        trade_date = pd.to_datetime(date_val).date()
                    
                    # 获取该区域对的价差值
                    spread_val = row.iloc[col_idx]
                    if pd.isna(spread_val):
                        skipped_count += 1
                        continue
                    
                    value = clean_numeric_value(spread_val)
                    if value is None:
                        skipped_count += 1
                        continue
                    
                    # 构建dedup_key
                    tags = {
                        "region_pair": region_pair,
                        "region1": region1,
                        "region2": region2,
                        "source": "GANGLIAN"
                    }
                    
                    dedup_key = self._generate_dedup_key(
                        source_code="GANGLIAN",
                        sheet_name=sheet_name,
                        metric_key=metric_key,
                        geo_code=region_pair,
                        obs_date=trade_date,
                        tags=tags
                    )
                    
                    # 检查是否已存在
                    existing = self.db.query(FactObservation).filter(
                        FactObservation.dedup_key == dedup_key
                    ).first()
                    
                    if existing:
                        existing.value = value
                        existing.batch_id = batch_id
                        updated_count += 1
                    else:
                        # 创建新记录
                        obs = FactObservation(
                            batch_id=batch_id,
                            metric_id=metric.id,
                            obs_date=trade_date,
                            period_type="day",
                            value=value,
                            geo_id=None,  # 暂时不关联geo_id
                            tags_json=tags,
                            dedup_key=dedup_key
                        )
                        self.db.add(obs)
                        self.db.flush()
                        
                        # 添加标签
                        tag1 = FactObservationTag(
                            observation_id=obs.id,
                            tag_key="region_pair",
                            tag_value=region_pair
                        )
                        tag2 = FactObservationTag(
                            observation_id=obs.id,
                            tag_key="region1",
                            tag_value=region1
                        )
                        tag3 = FactObservationTag(
                            observation_id=obs.id,
                            tag_key="region2",
                            tag_value=region2
                        )
                        self.db.add(tag1)
                        self.db.add(tag2)
                        self.db.add(tag3)
                        inserted_count += 1
                        
                except Exception as e:
                    print(f"处理{region_pair}第{row_idx}行数据失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            self.db.flush()
            total_inserted += inserted_count
            region_pair_results[region_pair] = inserted_count
            print(f"  {region_pair}: 插入 {inserted_count} 条，更新 {updated_count} 条，跳过 {skipped_count} 条")
        
        log_entry = {
            "sheet": sheet_name,
            "metric": "区域价差",
            "metric_key": "GL_D_REGION_SPREAD",
            "inserted": total_inserted,
            "region_pairs": region_pair_results,
            "date_range": {
                "start": str(df.iloc[0, 0]) if len(df) > 0 else None,
                "end": str(df.iloc[-1, 0]) if len(df) > 0 else None
            }
        }
        self.extraction_log.append(log_entry)
        
        return {"inserted": total_inserted, "region_pairs": region_pair_results, "log": log_entry}
    
    def _get_or_create_metric(
        self, 
        metric_key: str,
        metric_name: str,
        source_code: str,
        sheet_name: str,
        unit: str,
        raw_header: str
    ) -> DimMetric:
        """获取或创建指标"""
        metric = self.db.query(DimMetric).filter(
            DimMetric.raw_header == raw_header,
            DimMetric.sheet_name == sheet_name
        ).first()
        
        if not metric:
            metric = DimMetric(
                metric_group="spread",
                metric_name=metric_name,
                unit=unit,
                freq="D",
                raw_header=raw_header,
                sheet_name=sheet_name,
                source_updated_at=None,
                parse_json={},
                value_type="spread",
                preferred_agg="mean",
                suggested_axis="left",
                display_precision="2",
                seasonality_supported="true"
            )
            self.db.add(metric)
            self.db.flush()
        
        return metric
    
    def _generate_dedup_key(
        self,
        source_code: str,
        sheet_name: str,
        metric_key: str,
        geo_code: Optional[str],
        obs_date: date,
        tags: Dict
    ) -> str:
        """生成去重键"""
        canonical_tags = "|".join([f"{k}={v}" for k, v in sorted(tags.items())])
        key_str = f"{source_code}|{sheet_name}|{metric_key}|{geo_code or 'NATION'}|{obs_date}|{canonical_tags}"
        return hashlib.sha1(key_str.encode()).hexdigest()[:16]
    
    def _save_extraction_log(self, results: Dict):
        """保存提取日志"""
        # 日志文件保存到项目根目录的docs文件夹
        workspace_root = Path(self.file_path).parent.parent
        log_file = workspace_root / "docs" / "region_spread_extraction_log.json"
        
        log_data = {
            "extraction_date": datetime.now().isoformat(),
            "source_file": str(self.file_path),
            "batch_id": results["batch_id"],
            "results": {
                "region_spread": results["region_spread"].get("log", {})
            },
            "total_inserted": results["region_spread"].get("inserted", 0)
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"提取日志已保存到: {log_file}")


def main():
    """主函数"""
    # 文件路径 - 从项目根目录查找
    # project_root 是 backend 目录，需要回到上一级
    workspace_root = project_root.parent
    ganglian_file = workspace_root / "docs" / "1、价格：钢联自动更新模板.xlsx"
    
    if not ganglian_file.exists():
        print(f"错误: 文件不存在: {ganglian_file}")
        print(f"尝试查找文件...")
        # 尝试直接使用绝对路径
        import os
        possible_paths = [
            workspace_root / "docs" / "1、价格：钢联自动更新模板.xlsx",
            Path("docs") / "1、价格：钢联自动更新模板.xlsx",
            Path("../docs") / "1、价格：钢联自动更新模板.xlsx",
        ]
        for p in possible_paths:
            if p.exists():
                ganglian_file = p
                print(f"找到文件: {ganglian_file}")
                break
        else:
            print("未找到文件，请检查文件路径")
            return
    
    # 连接数据库
    db = next(get_db())
    
    try:
        # 提取数据
        extractor = RegionSpreadExtractor(db, ganglian_file)
        results = extractor.extract_and_insert()
        
        print("\n提取结果:")
        print(f"批次ID: {results['batch_id']}")
        
        # 区域价差统计
        region_spread_result = results['region_spread']
        print(f"\n区域价差: 总计插入 {region_spread_result.get('inserted', 0)} 条")
        if 'region_pairs' in region_spread_result:
            print("  各区域对详情:")
            for pair, count in region_spread_result['region_pairs'].items():
                print(f"    {pair}: {count} 条")
        
        print(f"\n总计: {region_spread_result.get('inserted', 0)} 条")
        
    except Exception as e:
        print(f"提取失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    # 设置UTF-8编码输出
    import sys
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    main()
