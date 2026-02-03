"""
从钢联Excel文件提取价格数据并插入MySQL
用于价格展示功能的初始数据导入

数据来源：
1. 全国猪价（季节性）- 钢联"分省区猪价"sheet的"中国"列
2. 标肥价差（季节性）- 钢联"肥标价差"sheet
3. 猪价&标肥价差（可年度筛选）- 同上
4. 日度屠宰量（农历）- 涌益日度"价格+宰量"sheet
5. 区域价差 - 钢联"区域价差"sheet

记录提取过程，供将来导入数据使用
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


class GanglianPriceExtractor:
    """钢联价格数据提取器"""
    
    def __init__(self, db: Session, file_path: Path):
        self.db = db
        self.file_path = file_path
        self.extraction_log = []
        
    def extract_and_insert(self) -> Dict:
        """提取并插入数据"""
        print(f"开始提取钢联价格数据: {self.file_path}")
        
        # 创建导入批次
        batch = self._create_batch()
        
        # 提取数据
        results = {
            "batch_id": batch.id,
            "national_price": self._extract_national_price(batch.id),
            "fat_std_spread": self._extract_fat_std_spread(batch.id),
            "slaughter_data": self._extract_slaughter_data(batch.id),
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
    
    def _extract_national_price(self, batch_id: int) -> Dict:
        """提取全国猪价数据（从分省区猪价sheet的"中国"列）"""
        print("提取全国猪价数据...")
        
        sheet_name = "分省区猪价"
        excel_file = pd.ExcelFile(self.file_path, engine='openpyxl')
        
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
        
        # 读取更新时间行（第4行）
        update_times_df = pd.read_excel(
            excel_file, sheet_name=sheet_name,
            header=None, nrows=1, skiprows=3
        )
        update_times = update_times_df.iloc[0].tolist()
        
        # 读取数据（从第5行开始）
        df = pd.read_excel(
            excel_file, sheet_name=sheet_name,
            header=None, skiprows=4
        )
        
        # 找到"中国"列
        china_col_idx = None
        for idx, name in enumerate(indicator_names):
            if name and ("中国" in str(name) or "全国" in str(name)):
                china_col_idx = idx
                break
        
        if china_col_idx is None:
            return {"error": "未找到全国/中国列", "inserted": 0}
        
        # 获取或创建指标
        metric = self._get_or_create_metric(
            metric_key="GL_D_PRICE_NATION",
            metric_name="全国出栏均价",
            source_code="GANGLIAN",
            sheet_name=sheet_name,
            unit=units[china_col_idx] if china_col_idx < len(units) else "元/公斤",
            raw_header=indicator_names[china_col_idx]
        )
        
        # 提取数据
        inserted_count = 0
        for row_idx, row in df.iterrows():
            try:
                # 第一列是日期
                date_val = row.iloc[0]
                if pd.isna(date_val):
                    continue
                
                # 转换为日期
                if isinstance(date_val, str):
                    trade_date = pd.to_datetime(date_val).date()
                else:
                    trade_date = date_val.date() if hasattr(date_val, 'date') else pd.to_datetime(date_val).date()
                
                # 获取价格值
                price_val = row.iloc[china_col_idx]
                if pd.isna(price_val):
                    continue
                
                value = clean_numeric_value(price_val)
                if value is None:
                    continue
                
                # 构建dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code="GANGLIAN",
                    sheet_name=sheet_name,
                    metric_key="GL_D_PRICE_NATION",
                    geo_code="NATION",
                    obs_date=trade_date,
                    tags={}
                )
                
                # 检查是否已存在
                existing = self.db.query(FactObservation).filter(
                    FactObservation.dedup_key == dedup_key
                ).first()
                
                if existing:
                    existing.value = value
                    existing.batch_id = batch_id
                    updated_count = 1
                else:
                    # 创建新记录
                    obs = FactObservation(
                        batch_id=batch_id,
                        metric_id=metric.id,
                        obs_date=trade_date,
                        period_type="day",
                        value=value,
                        geo_id=None,  # 全国数据，不需要geo_id
                        tags_json={"scope": "nation", "source": "GANGLIAN"},
                        dedup_key=dedup_key
                    )
                    self.db.add(obs)
                    self.db.flush()
                    
                    # 添加标签
                    tag = FactObservationTag(
                        observation_id=obs.id,
                        tag_key="scope",
                        tag_value="nation"
                    )
                    self.db.add(tag)
                    inserted_count += 1
                    
            except Exception as e:
                print(f"处理第{row_idx}行数据失败: {e}")
                continue
        
        self.db.flush()
        
        log_entry = {
            "sheet": sheet_name,
            "metric": "全国出栏均价",
            "metric_key": "GL_D_PRICE_NATION",
            "inserted": inserted_count,
            "date_range": {
                "start": str(df.iloc[0, 0]) if len(df) > 0 else None,
                "end": str(df.iloc[-1, 0]) if len(df) > 0 else None
            }
        }
        self.extraction_log.append(log_entry)
        
        return {"inserted": inserted_count, "log": log_entry}
    
    def _extract_fat_std_spread(self, batch_id: int) -> Dict:
        """提取标肥价差数据（从肥标价差sheet，提取所有省区）"""
        print("提取标肥价差数据（所有省区）...")
        
        sheet_name = "肥标价差"
        excel_file = pd.ExcelFile(self.file_path, engine='openpyxl')
        
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
        
        # 提取所有省区列
        # 注意：第1列（index 0）是"指标名称"列，在数据行中是日期列
        # 第2列开始（index 1+）是各省区的价差数据列
        total_inserted = 0
        province_results = {}
        
        import re
        # 省份列表
        provinces_list = ["四川", "贵州", "重庆", "湖南", "江西", "湖北", "河北", "河南", 
                         "山东", "山西", "辽宁", "吉林", "黑龙江", "中国"]
        
        # 从第2列开始处理（第1列是日期列）
        for col_idx in range(1, len(indicator_names)):
            if col_idx >= len(indicator_names):
                break
                
            raw_header = indicator_names[col_idx]
            if pd.isna(raw_header) or not raw_header:
                continue
            
            raw_header_str = str(raw_header)
            
            # 提取省区名称
            province_name = None
            # 尝试从raw_header中提取省区名称，例如："生猪标肥：价差：四川（日）" -> "四川"
            match = re.search(r'：([^：（）]+)（', raw_header_str)
            if match:
                province_name = match.group(1).strip()
            else:
                # 如果没有匹配到，尝试查找省份列表
                for p in provinces_list:
                    if p in raw_header_str:
                        province_name = p
                        break
            
            if not province_name:
                print(f"跳过列 {col_idx}: 无法识别省区名称 - {raw_header_str}")
                continue
            
            print(f"处理省区: {province_name} (列 {col_idx})")
            
            # 获取或创建指标（每个省区一个指标）
            metric_key = f"GL_D_FAT_STD_SPREAD_{province_name}"
            metric = self._get_or_create_metric(
                metric_key=metric_key,
                metric_name="标肥价差",
                source_code="GANGLIAN",
                sheet_name=sheet_name,
                unit=units[col_idx] if col_idx < len(units) else "元/公斤",
                raw_header=raw_header_str
            )
            
            # 提取该省区的数据
            inserted_count = 0
            for row_idx, row in df.iterrows():
                try:
                    # 第1列（index 0）是日期列（列头显示为"指标名称"，但数据行中是日期）
                    date_val = row.iloc[0]
                    if pd.isna(date_val):
                        continue
                    
                    # 转换为日期对象
                    if isinstance(date_val, str):
                        trade_date = pd.to_datetime(date_val).date()
                    elif hasattr(date_val, 'date'):
                        trade_date = date_val.date()
                    else:
                        trade_date = pd.to_datetime(date_val).date()
                    
                    # 获取该省区的价差值（col_idx对应的是省区列）
                    spread_val = row.iloc[col_idx]
                    if pd.isna(spread_val):
                        continue
                    
                    value = clean_numeric_value(spread_val)
                    if value is None:
                        continue
                    
                    # 构建dedup_key
                    geo_code = "NATION" if province_name == "中国" else province_name
                    tags = {"scope": "nation", "source": "GANGLIAN"} if province_name == "中国" else {"province": province_name, "source": "GANGLIAN"}
                    
                    dedup_key = self._generate_dedup_key(
                        source_code="GANGLIAN",
                        sheet_name=sheet_name,
                        metric_key=metric_key,
                        geo_code=geo_code,
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
                        if province_name == "中国":
                            tag = FactObservationTag(
                                observation_id=obs.id,
                                tag_key="scope",
                                tag_value="nation"
                            )
                        else:
                            tag = FactObservationTag(
                                observation_id=obs.id,
                                tag_key="province",
                                tag_value=province_name
                            )
                        self.db.add(tag)
                        inserted_count += 1
                        
                except Exception as e:
                    print(f"处理{province_name}第{row_idx}行数据失败: {e}")
                    continue
            
            self.db.flush()
            total_inserted += inserted_count
            province_results[province_name] = inserted_count
            print(f"  {province_name}: 插入 {inserted_count} 条数据")
        
        log_entry = {
            "sheet": sheet_name,
            "metric": "标肥价差（分省区）",
            "metric_key": "GL_D_FAT_STD_SPREAD",
            "inserted": total_inserted,
            "provinces": province_results,
            "date_range": {
                "start": str(df.iloc[0, 0]) if len(df) > 0 else None,
                "end": str(df.iloc[-1, 0]) if len(df) > 0 else None
            }
        }
        self.extraction_log.append(log_entry)
        
        return {"inserted": total_inserted, "provinces": province_results, "log": log_entry}
    
    def _extract_slaughter_data(self, batch_id: int) -> Dict:
        """提取日度屠宰量数据（从涌益日度文件）"""
        print("提取日度屠宰量数据...")
        
        # 涌益日度文件路径 - 从项目根目录查找
        workspace_root = Path(self.file_path).parent.parent
        yongyi_file = workspace_root / "docs" / "2026年2月2日涌益咨询日度数据.xlsx"
        if not yongyi_file.exists():
            return {"error": f"涌益日度文件不存在: {yongyi_file}", "inserted": 0}
        
        sheet_name = "价格+宰量"
        excel_file = pd.ExcelFile(yongyi_file, engine='openpyxl')
        
        # 读取数据
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # 找到"日期"列和"日屠宰量合计1"或"日度屠宰量合计2"列
        date_col = None
        slaughter_col = None
        
        for col in df.columns:
            if "日期" in str(col):
                date_col = col
            if "屠宰量" in str(col) or "宰量" in str(col):
                slaughter_col = col
        
        if date_col is None or slaughter_col is None:
            return {"error": "未找到日期列或屠宰量列", "inserted": 0}
        
        # 获取或创建指标
        metric = self._get_or_create_metric(
            metric_key="YY_D_SLAUGHTER_TOTAL",
            metric_name="日度屠宰量",
            source_code="YONGYI",
            sheet_name=sheet_name,
            unit="头",
            raw_header=slaughter_col
        )
        
        inserted_count = 0
        for idx, row in df.iterrows():
            try:
                trade_date = pd.to_datetime(row[date_col]).date()
                slaughter_val = row[slaughter_col]
                
                if pd.isna(slaughter_val):
                    continue
                
                value = clean_numeric_value(slaughter_val)
                if value is None:
                    continue
                
                # 构建dedup_key
                dedup_key = self._generate_dedup_key(
                    source_code="YONGYI",
                    sheet_name=sheet_name,
                    metric_key="YY_D_SLAUGHTER_TOTAL",
                    geo_code="NATION",
                    obs_date=trade_date,
                    tags={"scope": "nation"}
                )
                
                # 检查是否已存在
                existing = self.db.query(FactObservation).filter(
                    FactObservation.dedup_key == dedup_key
                ).first()
                
                if existing:
                    existing.value = value
                    existing.batch_id = batch_id
                else:
                    # 创建新记录
                    obs = FactObservation(
                        batch_id=batch_id,
                        metric_id=metric.id,
                        obs_date=trade_date,
                        period_type="day",
                        value=value,
                        geo_id=None,
                        tags_json={"scope": "nation", "source": "YONGYI"},
                        dedup_key=dedup_key
                    )
                    self.db.add(obs)
                    self.db.flush()
                    
                    # 添加标签
                    tag = FactObservationTag(
                        observation_id=obs.id,
                        tag_key="scope",
                        tag_value="nation"
                    )
                    self.db.add(tag)
                    inserted_count += 1
                    
            except Exception as e:
                print(f"处理第{idx}行数据失败: {e}")
                continue
        
        self.db.flush()
        
        log_entry = {
            "sheet": sheet_name,
            "metric": "日度屠宰量",
            "metric_key": "YY_D_SLAUGHTER_TOTAL",
            "inserted": inserted_count,
            "source_file": str(yongyi_file)
        }
        self.extraction_log.append(log_entry)
        
        return {"inserted": inserted_count, "log": log_entry}
    
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
        
        import re
        
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
            for row_idx, row in df.iterrows():
                try:
                    # 第1列（index 0）是日期列
                    date_val = row.iloc[0]
                    if pd.isna(date_val):
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
                        continue
                    
                    value = clean_numeric_value(spread_val)
                    if value is None:
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
                    continue
            
            self.db.flush()
            total_inserted += inserted_count
            region_pair_results[region_pair] = inserted_count
            print(f"  {region_pair}: 插入 {inserted_count} 条数据")
        
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
                metric_group="price" if "价格" in metric_name else "spread" if "价差" in metric_name else "slaughter",
                metric_name=metric_name,
                unit=unit,
                freq="D",
                raw_header=raw_header,
                sheet_name=sheet_name,
                source_updated_at=None,
                parse_json={},
                value_type="price" if "价格" in metric_name else "spread" if "价差" in metric_name else "volume",
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
        log_file = workspace_root / "docs" / "ganglian_price_extraction_log.json"
        
        log_data = {
            "extraction_date": datetime.now().isoformat(),
            "source_file": str(self.file_path),
            "batch_id": results["batch_id"],
            "results": {
                "national_price": results["national_price"].get("log", {}),
                "fat_std_spread": results["fat_std_spread"].get("log", {}),
                "slaughter_data": results["slaughter_data"].get("log", {}),
                "region_spread": results["region_spread"].get("log", {})
            },
            "total_inserted": (
                results["national_price"].get("inserted", 0) +
                results["fat_std_spread"].get("inserted", 0) +
                results["slaughter_data"].get("inserted", 0) +
                results["region_spread"].get("inserted", 0)
            )
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
        extractor = GanglianPriceExtractor(db, ganglian_file)
        results = extractor.extract_and_insert()
        
        print("\n提取结果:")
        print(f"批次ID: {results['batch_id']}")
        print(f"全国猪价: 插入 {results['national_price'].get('inserted', 0)} 条")
        
        # 标肥价差分省区统计
        spread_result = results['fat_std_spread']
        print(f"\n标肥价差（分省区）: 总计插入 {spread_result.get('inserted', 0)} 条")
        if 'provinces' in spread_result:
            print("  各省区详情:")
            for province, count in spread_result['provinces'].items():
                print(f"    {province}: {count} 条")
        
        print(f"日度屠宰量: 插入 {results['slaughter_data'].get('inserted', 0)} 条")
        
        # 区域价差统计
        region_spread_result = results['region_spread']
        print(f"\n区域价差: 总计插入 {region_spread_result.get('inserted', 0)} 条")
        if 'region_pairs' in region_spread_result:
            print("  各区域对详情:")
            for pair, count in region_spread_result['region_pairs'].items():
                print(f"    {pair}: {count} 条")
        
        print(f"\n总计: {results['national_price'].get('inserted', 0) + spread_result.get('inserted', 0) + results['slaughter_data'].get('inserted', 0) + region_spread_result.get('inserted', 0)} 条")
        
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
