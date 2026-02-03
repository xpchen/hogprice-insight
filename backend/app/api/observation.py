"""Observation查询API - 支持按tags、geo、time筛选"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys_user import SysUser
from app.models.fact_observation import FactObservation
from app.models.fact_observation_tag import FactObservationTag
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/observation", tags=["observation"])


class ObservationResponse(BaseModel):
    """Observation响应模型"""
    id: int
    metric_name: str
    obs_date: Optional[date]
    period_type: Optional[str]
    period_start: Optional[date]
    period_end: Optional[date]
    value: Optional[float]
    raw_value: Optional[str]
    geo_code: Optional[str]
    tags: Dict[str, Any]
    unit: Optional[str]
    
    class Config:
        from_attributes = True


class TagInfo(BaseModel):
    """Tag信息模型"""
    tag_key: str
    tag_value: str
    count: int


@router.get("/query", response_model=List[ObservationResponse])
async def query_observations(
    source_code: Optional[str] = Query(None, description="数据源代码"),
    metric_key: Optional[str] = Query(None, description="指标键（支持通配符）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    period_type: Optional[str] = Query(None, description="周期类型（day/week/month）"),
    geo_code: Optional[str] = Query(None, description="地理位置代码"),
    tag_key: Optional[str] = Query(None, description="Tag键"),
    tag_value: Optional[str] = Query(None, description="Tag值"),
    indicator: Optional[str] = Query(None, description="指标名称（用于周度-体重等表的行维度筛选）"),
    nation_col: Optional[str] = Query(None, description="全国列名（用于筛选特定全国列，如'全国1'、'全国2'）"),
    limit: int = Query(1000, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    查询observation数据（支持tags筛选）
    
    支持按数据源、指标、时间范围、周期类型、地理位置、tags筛选
    支持通过indicator参数筛选行维度指标（如"全国2"、"90Kg出栏占比"等）
    """
    # 构建查询，join metric以便后续使用
    from app.models.dim_metric import DimMetric
    from app.models.import_batch import ImportBatch
    from app.models.raw_file import RawFile
    query = db.query(FactObservation).join(DimMetric, FactObservation.metric_id == DimMetric.id)
    
    # 数据源代码筛选（通过metric_key前缀判断：YY=涌益, GL=钢联, DCE=大商所）
    if source_code:
        # 构建source_code到metric_key前缀的映射
        source_prefix_map = {
            "YONGYI": "YY",
            "GANGLIAN": "GL",
            "DCE": "DCE"
        }
        prefix = source_prefix_map.get(source_code, source_code[:2])
        
        # 通过parse_json中的metric_key前缀筛选
        query = query.filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ).like(f"{prefix}_%")
        )
    
    # 指标键筛选
    if metric_key:
        # 通过raw_header、metric_name或parse_json中的metric_key匹配
        query = query.filter(
            or_(
                DimMetric.raw_header == metric_key,
                DimMetric.metric_name.like(f"%{metric_key}%"),
                DimMetric.raw_header.like(f"%{metric_key}%"),
                # 检查parse_json中是否包含metric_key
                func.json_unquote(
                    func.json_extract(DimMetric.parse_json, '$.metric_key')
                ) == metric_key
            )
        )
    
    # 时间范围筛选
    if start_date:
        query = query.filter(FactObservation.obs_date >= start_date)
    if end_date:
        query = query.filter(FactObservation.obs_date <= end_date)
    
    # 周期类型筛选
    if period_type:
        query = query.filter(FactObservation.period_type == period_type)
    
    # 地理位置筛选
    if geo_code:
        if geo_code == "NATION":
            # NATION表示全国数据，geo_id应该为NULL
            query = query.filter(FactObservation.geo_id.is_(None))
        else:
            # 其他省份，需要join geo表
            from app.models.dim_geo import DimGeo
            query = query.join(DimGeo, FactObservation.geo_id == DimGeo.id).filter(
                DimGeo.province == geo_code
            )
    
    # Tags筛选
    if tag_key and tag_value:
        query = query.join(FactObservationTag).filter(
            and_(
                FactObservationTag.tag_key == tag_key,
                FactObservationTag.tag_value == tag_value
            )
        )
    elif tag_key:
        query = query.join(FactObservationTag).filter(
            FactObservationTag.tag_key == tag_key
        )
    
    # Indicator筛选（通过tags_json中的indicator字段）
    if indicator:
        query = query.filter(
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.indicator')
            ) == indicator
        )
    
    # Nation_col筛选（通过tags_json中的nation_col字段）
    if nation_col:
        query = query.filter(
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.nation_col')
            ) == nation_col
        )
    
    # 排序和分页
    query = query.order_by(FactObservation.obs_date.desc())
    query = query.offset(offset).limit(limit)
    
    observations = query.all()
    
    # 转换为响应模型
    results = []
    for obs in observations:
        # 获取tags
        tags = obs.tags_json or {}
        
        # 获取geo_code
        geo_code_val = obs.geo.province if obs.geo else None
        
        # 获取metric信息
        metric_name = obs.metric.metric_name if obs.metric else ""
        unit = obs.metric.unit if obs.metric else None
        
        results.append(ObservationResponse(
            id=obs.id,
            metric_name=metric_name,
            obs_date=obs.obs_date,
            period_type=obs.period_type,
            period_start=obs.period_start,
            period_end=obs.period_end,
            value=float(obs.value) if obs.value else None,
            raw_value=obs.raw_value,
            geo_code=geo_code_val,
            tags=tags,
            unit=unit
        ))
    
    return results


@router.get("/tags", response_model=List[TagInfo])
async def get_available_tags(
    tag_key: Optional[str] = Query(None, description="Tag键（如果提供，返回该键的所有值）"),
    source_code: Optional[str] = Query(None, description="数据源代码"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取可用的tag键值对（支持动态筛选器）
    
    如果提供tag_key，返回该键的所有值及其计数
    如果不提供，返回所有tag键及其计数
    """
    if tag_key:
        # 返回指定tag_key的所有值
        results = db.query(
            FactObservationTag.tag_value,
            func.count(FactObservationTag.observation_id).label('count')
        ).filter(
            FactObservationTag.tag_key == tag_key
        ).group_by(FactObservationTag.tag_value).all()
        
        return [
            TagInfo(tag_key=tag_key, tag_value=row[0], count=row[1])
            for row in results
        ]
    else:
        # 返回所有tag_key及其计数
        results = db.query(
            FactObservationTag.tag_key,
            func.count(func.distinct(FactObservationTag.tag_value)).label('count')
        ).group_by(FactObservationTag.tag_key).all()
        
        return [
            TagInfo(tag_key=row[0], tag_value="", count=row[1])
            for row in results
        ]


@router.get("/raw/sheets")
async def get_raw_sheets(
    batch_id: Optional[int] = Query(None, description="批次ID"),
    raw_file_id: Optional[int] = Query(None, description="Raw文件ID"),
    parse_status: Optional[str] = Query(None, description="解析状态"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取raw_sheet列表
    """
    query = db.query(RawSheet)
    
    if batch_id:
        query = query.join(RawFile).filter(RawFile.batch_id == batch_id)
    
    if raw_file_id:
        query = query.filter(RawSheet.raw_file_id == raw_file_id)
    
    if parse_status:
        query = query.filter(RawSheet.parse_status == parse_status)
    
    sheets = query.all()
    
    return [
        {
            "id": sheet.id,
            "raw_file_id": sheet.raw_file_id,
            "sheet_name": sheet.sheet_name,
            "row_count": sheet.row_count,
            "col_count": sheet.col_count,
            "parse_status": sheet.parse_status,
            "parser_type": sheet.parser_type,
            "error_count": sheet.error_count,
            "observation_count": sheet.observation_count
        }
        for sheet in sheets
    ]


@router.get("/raw/table")
async def get_raw_table(
    raw_sheet_id: int = Query(..., description="Raw sheet ID"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取raw_table JSON数据
    """
    raw_table = db.query(RawTable).filter(RawTable.raw_sheet_id == raw_sheet_id).first()
    
    if not raw_table:
        raise HTTPException(status_code=404, detail="Raw table not found")
    
    return {
        "raw_sheet_id": raw_table.raw_sheet_id,
        "table_json": raw_table.table_json,
        "merged_cells_json": raw_table.merged_cells_json,
        "created_at": raw_table.created_at
    }
