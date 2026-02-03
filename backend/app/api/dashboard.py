"""默认首页聚合接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.services.indicator_query_service import query_indicator_ts, query_indicator_metrics

router = APIRouter(prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])


class CardData(BaseModel):
    card_id: str
    title: str
    chart_type: str
    data: dict
    update_time: str
    config: dict = {}


class DashboardResponse(BaseModel):
    cards: List[CardData]
    global_filters: dict


@router.get("/default", response_model=DashboardResponse)
async def get_default_dashboard(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """返回首页7个卡片数据"""
    
    # 默认时间范围：近6个月
    end_date = date.today()
    start_date = end_date - timedelta(days=180)
    
    cards = []
    
    # 卡片1：全国出栏均价 + 标肥价差（合并图）
    try:
        price_data = query_indicator_ts(
            db=db,
            indicator_code="hog_price_nation",
            region_code="NATION",
            freq="D",
            from_date=start_date,
            to_date=end_date
        )
        
        spread_data = query_indicator_ts(
            db=db,
            indicator_code="spread_std_fat",
            region_code="NATION",
            freq="D",
            from_date=start_date,
            to_date=end_date
        )
        
        cards.append(CardData(
            card_id="card_1_price_spread",
            title="全国出栏均价 + 标肥价差",
            chart_type="dual_axis",
            data={
                "series1": {
                    "name": "全国出栏均价",
                    "data": price_data.get("series", []),
                    "unit": price_data.get("unit")
                },
                "series2": {
                    "name": "标肥价差",
                    "data": spread_data.get("series", []),
                    "unit": spread_data.get("unit")
                }
            },
            update_time=price_data.get("update_time", ""),
            config={
                "axis1": "left",
                "axis2": "right"
            }
        ))
    except Exception as e:
        cards.append(CardData(
            card_id="card_1_price_spread",
            title="全国出栏均价 + 标肥价差",
            chart_type="dual_axis",
            data={"error": str(e)},
            update_time="",
            config={}
        ))
    
    # 卡片2：日度屠宰量季节性（农历对齐）
    try:
        slaughter_data = query_indicator_ts(
            db=db,
            indicator_code="slaughter_daily",
            region_code="NATION",
            freq="D",
            from_date=start_date - timedelta(days=365),  # 需要更多历史数据用于季节性
            to_date=end_date
        )
        
        # 这里需要调用农历对齐服务处理数据
        # 简化处理：直接返回时序数据
        cards.append(CardData(
            card_id="card_2_slaughter_seasonality",
            title="日度屠宰量季节性",
            chart_type="seasonality",
            data={
                "series": slaughter_data.get("series", []),
                "unit": slaughter_data.get("unit")
            },
            update_time=slaughter_data.get("update_time", ""),
            config={
                "lunar_alignment": True,
                "years": [end_date.year - 1, end_date.year]
            }
        ))
    except Exception as e:
        cards.append(CardData(
            card_id="card_2_slaughter_seasonality",
            title="日度屠宰量季节性",
            chart_type="seasonality",
            data={"error": str(e)},
            update_time="",
            config={}
        ))
    
    # 卡片3：价格&屠宰走势（年度筛选）
    try:
        price_trend = query_indicator_ts(
            db=db,
            indicator_code="hog_price_nation",
            region_code="NATION",
            freq="D",
            from_date=start_date,
            to_date=end_date
        )
        
        slaughter_trend = query_indicator_ts(
            db=db,
            indicator_code="slaughter_daily",
            region_code="NATION",
            freq="D",
            from_date=start_date,
            to_date=end_date
        )
        
        cards.append(CardData(
            card_id="card_3_price_slaughter_trend",
            title="价格&屠宰走势",
            chart_type="line",
            data={
                "series": [
                    {
                        "name": "价格",
                        "data": price_trend.get("series", []),
                        "unit": price_trend.get("unit")
                    },
                    {
                        "name": "屠宰量",
                        "data": slaughter_trend.get("series", []),
                        "unit": slaughter_trend.get("unit")
                    }
                ]
            },
            update_time=price_trend.get("update_time", ""),
            config={
                "year_filter": True
            }
        ))
    except Exception as e:
        cards.append(CardData(
            card_id="card_3_price_slaughter_trend",
            title="价格&屠宰走势",
            chart_type="line",
            data={"error": str(e)},
            update_time="",
            config={}
        ))
    
    # 卡片4：均重专区入口（6图）
    cards.append(CardData(
        card_id="card_4_weight_entrance",
        title="均重专区",
        chart_type="entrance",
        data={
            "indicators": [
                {"code": "hog_weight_pre_slaughter", "name": "宰前均重"},
                {"code": "hog_weight_out_week", "name": "出栏均重"},
                {"code": "hog_weight_scale", "name": "规模场出栏均重"},
                {"code": "hog_weight_retail", "name": "散户出栏均重"},
                {"code": "hog_weight_90kg", "name": "90kg出栏占比"},
                {"code": "hog_weight_150kg", "name": "150kg出栏占比"}
            ]
        },
        update_time="",
        config={}
    ))
    
    # 卡片5：价差专区入口
    cards.append(CardData(
        card_id="card_5_spread_entrance",
        title="价差专区",
        chart_type="entrance",
        data={
            "indicators": [
                {"code": "spread_std_fat", "name": "标肥价差"},
                {"code": "spread_region", "name": "区域价差"},
                {"code": "spread_hog_carcass", "name": "毛白价差"}
            ]
        },
        update_time="",
        config={}
    ))
    
    # 卡片6：冻品库容率（分省区季节性）
    try:
        frozen_data = query_indicator_ts(
            db=db,
            indicator_code="frozen_capacity_rate",
            freq="W",
            from_date=start_date - timedelta(days=365),
            to_date=end_date
        )
        
        cards.append(CardData(
            card_id="card_6_frozen_capacity",
            title="冻品库容率",
            chart_type="seasonality",
            data={
                "series": frozen_data.get("series", []),
                "unit": frozen_data.get("unit")
            },
            update_time=frozen_data.get("update_time", ""),
            config={
                "region_filter": True,
                "by_province": True
            }
        ))
    except Exception as e:
        cards.append(CardData(
            card_id="card_6_frozen_capacity",
            title="冻品库容率",
            chart_type="seasonality",
            data={"error": str(e)},
            update_time="",
            config={}
        ))
    
    # 卡片7：产业链周度汇总
    try:
        profit_data = query_indicator_ts(
            db=db,
            indicator_code="profit_breeding",
            region_code="NATION",
            freq="W",
            from_date=start_date,
            to_date=end_date
        )
        
        feed_data = query_indicator_ts(
            db=db,
            indicator_code="feed_price_full",
            region_code="NATION",
            freq="W",
            from_date=start_date,
            to_date=end_date
        )
        
        cards.append(CardData(
            card_id="card_7_industry_chain",
            title="产业链周度汇总",
            chart_type="line",
            data={
                "series": [
                    {
                        "name": "养殖利润",
                        "data": profit_data.get("series", []),
                        "unit": profit_data.get("unit")
                    },
                    {
                        "name": "全价料价格",
                        "data": feed_data.get("series", []),
                        "unit": feed_data.get("unit")
                    }
                ]
            },
            update_time=profit_data.get("update_time", ""),
            config={}
        ))
    except Exception as e:
        cards.append(CardData(
            card_id="card_7_industry_chain",
            title="产业链周度汇总",
            chart_type="line",
            data={"error": str(e)},
            update_time="",
            config={}
        ))
    
    return DashboardResponse(
        cards=cards,
        global_filters={
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "regions": ["NATION"],
            "years": [end_date.year - 1, end_date.year]
        }
    )
