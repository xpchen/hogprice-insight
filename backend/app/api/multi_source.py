"""
E2. 多渠道汇总 API
包含3个表格：
1. 淘汰母猪屠宰环比、能繁母猪存栏环比、能繁母猪饲料环比
2. 新生仔猪存栏环比、仔猪饲料环比
3. 生猪存栏环比、育肥猪饲料环比

数据来源：
- 【生猪产业数据】.xlsx：NYB、02.协会猪料、4.2涌益底稿、涌益样本 等
- 1、价格：钢联自动更新模板.xlsx → 月度数据：能繁母猪 M-O、仔猪 K、生猪存栏 H-J
- 涌益周度：月度-能繁/小猪/大猪存栏、月度-猪料销量、月度-淘汰母猪屠宰厂宰杀量 等
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import json
import math
from collections import defaultdict

from app.core.database import get_db
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/multi-source", tags=["multi-source"])


class MultiSourceDataPoint(BaseModel):
    """多渠道数据点"""
    month: str  # 月份 YYYY-MM
    cull_slaughter_yongyi: Optional[float] = None  # 淘汰母猪屠宰环比-涌益
    cull_slaughter_ganglian: Optional[float] = None  # 淘汰母猪屠宰环比-钢联
    breeding_inventory_yongyi: Optional[float] = None  # 能繁母猪存栏环比-涌益
    breeding_inventory_ganglian_nation: Optional[float] = None  # 能繁母猪存栏环比-钢联-全国
    breeding_inventory_ganglian_scale: Optional[float] = None  # 能繁母猪存栏环比-钢联-规模场
    breeding_inventory_ganglian_small: Optional[float] = None  # 能繁母猪存栏环比-钢联-中小散户
    breeding_inventory_nyb: Optional[float] = None  # 能繁母猪存栏环比-NYB
    breeding_feed_yongyi: Optional[float] = None  # 能繁母猪饲料环比-涌益
    breeding_feed_ganglian: Optional[float] = None  # 能繁母猪饲料环比-钢联
    breeding_feed_association: Optional[float] = None  # 能繁母猪饲料环比-协会
    piglet_inventory_yongyi: Optional[float] = None  # 新生仔猪存栏环比-涌益
    piglet_inventory_ganglian_nation: Optional[float] = None  # 新生仔猪存栏环比-钢联-全国
    piglet_inventory_ganglian_scale: Optional[float] = None  # 新生仔猪存栏环比-钢联-规模场
    piglet_inventory_ganglian_small: Optional[float] = None  # 新生仔猪存栏环比-钢联-中小散户
    piglet_inventory_nyb: Optional[float] = None  # 新生仔猪存栏环比-NYB
    piglet_feed_yongyi: Optional[float] = None  # 仔猪饲料环比-涌益
    piglet_feed_ganglian: Optional[float] = None  # 仔猪饲料环比-钢联
    piglet_feed_association: Optional[float] = None  # 仔猪饲料环比-协会
    hog_inventory_yongyi: Optional[float] = None  # 生猪存栏环比-涌益
    hog_inventory_ganglian_nation: Optional[float] = None  # 生猪存栏环比-钢联-全国
    hog_inventory_ganglian_scale: Optional[float] = None  # 生猪存栏环比-钢联-规模场
    hog_inventory_ganglian_small: Optional[float] = None  # 生猪存栏环比-钢联-中小散户
    hog_inventory_nyb: Optional[float] = None  # 生猪存栏环比-NYB
    hog_inventory_nyb_5month: Optional[float] = None  # 生猪存栏环比-NYB-5月龄
    hog_feed_yongyi: Optional[float] = None  # 育肥猪饲料环比-涌益
    hog_feed_ganglian: Optional[float] = None  # 育肥猪饲料环比-钢联
    hog_feed_association: Optional[float] = None  # 育肥猪饲料环比-协会


class MultiSourceResponse(BaseModel):
    """多渠道汇总响应"""
    data: List[MultiSourceDataPoint]
    latest_month: Optional[str] = None


def _parse_excel_date(excel_date: any) -> Optional[date]:
    """解析Excel日期（序列号或字符串）"""
    if isinstance(excel_date, (int, float)):
        # Excel日期序列号（从1900-01-01开始）
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=int(excel_date))).date()
        except:
            pass
    elif isinstance(excel_date, str):
        try:
            if 'T' in excel_date:
                dt = datetime.fromisoformat(excel_date.replace('Z', '+00:00'))
                return dt.date()
            s = excel_date.strip()
            if len(s) == 7 and s[4] == '-':  # YYYY-MM
                return datetime.strptime(s, '%Y-%m').date()
            return datetime.strptime(s, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(excel_date, date):
        return excel_date
    elif isinstance(excel_date, datetime):
        return excel_date.date()
    return None


def _get_raw_table_data(db: Session, sheet_name: str, filename: str = None) -> Optional[List[List]]:
    """获取raw_table数据。filename 为 None 时仅按 sheet 名查找，且取最新导入的文件（id 最大）。"""
    query = db.query(RawSheet).join(RawFile)
    
    if filename:
        # 支持无扩展名或带 .xlsx 的匹配
        query = query.filter(
            (RawFile.filename == filename) | (RawFile.filename == filename.replace(".xlsx", ""))
        )
    
    query = query.filter(RawSheet.sheet_name == sheet_name)
    # 未指定文件名时取最新导入的 sheet（同一 sheet 名可能来自多次导入）
    if filename is None:
        query = query.order_by(RawFile.id.desc())
    sheet = query.first()
    
    if not sheet:
        return None
    
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == sheet.id
    ).first()
    
    if not raw_table:
        return None
    
    table_data = raw_table.table_json
    if isinstance(table_data, str):
        table_data = json.loads(table_data)
    
    return table_data


def _get_raw_table_data_prefer_filenames(
    db: Session, sheet_name: str, preferred_filenames: List[str]
) -> Optional[List[List]]:
    """按 sheet 名取数，优先使用给定的文件名（按顺序尝试），都无则按最新导入取。"""
    for fname in preferred_filenames:
        data = _get_raw_table_data(db, sheet_name, fname)
        if data:
            return data
    return _get_raw_table_data(db, sheet_name, None)


def _safe_float(value: any) -> Optional[float]:
    """安全转换为float"""
    if value is None or value == "":
        return None
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except:
        return None


def _extract_nyb_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取NYB数据
    Sheet结构：
    - 第2行是表头：B列是"月度"，C列是"全国"（能繁环比），G列是"全国"（新生仔猪环比），Q列是"全国"（存栏环比），K列是"全国环比"（5月龄及以上大猪环比）
    - 数据从第3行开始（索引2）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "NYB", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 3:
        return data
    
    # 数据从第3行开始（索引2），B列是日期（索引1），C列是能繁环比-全国（索引2），G列是新生仔猪环比-全国（索引6），Q列是存栏环比（索引16），K列是5月龄及以上大猪环比（索引10）
    for row in table_data[2:]:  # 跳过表头
        if len(row) < 17:
            continue
        
        date_val = _parse_excel_date(row[1])  # B列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # C列：能繁环比-全国（索引2）
        breeding_val = _safe_float(row[2])
        if breeding_val is not None:
            data[month_key]['breeding_inventory_nyb'] = breeding_val
        
        # G列：新生仔猪环比-全国（索引6）
        piglet_val = _safe_float(row[6])
        if piglet_val is not None:
            data[month_key]['piglet_inventory_nyb'] = piglet_val
        
        # Q列：存栏环比（索引16）
        hog_val = _safe_float(row[16])
        if hog_val is not None:
            data[month_key]['hog_inventory_nyb'] = hog_val
        
        # J列：5月龄及以上大猪环比（索引9；分析文档为 J 列）
        if len(row) > 9:
            hog_5month_val = _safe_float(row[9])
            if hog_5month_val is not None:
                data[month_key]['hog_inventory_nyb_5month'] = hog_5month_val
    
    return data


def _extract_association_feed_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取协会猪料数据
    Sheet结构：
    - 第1行是表头：B列是"日期"，H列是"母猪料"，M列是"仔猪料"，R列是"育肥料"
    - 第2行是子表头：I列是"环比"（母猪料），N列是"环比"（仔猪料），S列是"环比"（育肥料）
    - 数据从第3行开始（索引2）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "02.协会猪料", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 3:
        return data
    
    # 数据从第3行开始（索引2），B列是日期（索引1），I列是母猪料环比（索引8），N列是仔猪料环比（索引13），S列是育肥料环比（索引18）
    for row in table_data[2:]:  # 跳过表头
        if len(row) < 19:
            continue
        
        date_val = _parse_excel_date(row[1])  # B列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # I列：母猪料环比（索引8）
        breeding_feed_val = _safe_float(row[8])
        if breeding_feed_val is not None:
            data[month_key]['breeding_feed_association'] = breeding_feed_val
        
        # N列：仔猪料环比（索引13）
        piglet_feed_val = _safe_float(row[13])
        if piglet_feed_val is not None:
            data[month_key]['piglet_feed_association'] = piglet_feed_val
        
        # S列：育肥料环比（索引18）
        hog_feed_val = _safe_float(row[18])
        if hog_feed_val is not None:
            data[month_key]['hog_feed_association'] = hog_feed_val
    
    return data


def _extract_yongyi_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取涌益数据（从4.2涌益底稿sheet）
    Sheet结构：
    - 第1行是表头：G列是"能繁母猪-2020年2月*"（全国），B列是"大猪存栏-2020年5月*"（全国），P列是"饲料销量环比"（猪料销量）
    - 第2行是子表头：G列是"全国"（能繁母猪），B列是"全国"（大猪存栏），P列是"猪料销量"
    - 数据从第3行开始（索引2）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "4.2涌益底稿", "2、【生猪产业数据】.xlsx")
    
    if not table_data or len(table_data) < 3:
        return data
    
    # 数据从第3行开始（索引2）。A=日期(0)，B=大猪存栏-全国(1)，G=能繁母猪-全国(6)，P=猪料销量(15)，Q=后备母猪料(16) 作能繁母猪饲料环比
    for row in table_data[2:]:  # 跳过表头
        if len(row) < 17:
            continue
        
        date_val = _parse_excel_date(row[0])  # A列
        if not date_val:
            continue
        
        month_key = date_val.strftime("%Y-%m")
        
        # G列：能繁母猪环比-全国（索引6）
        breeding_val = _safe_float(row[6])
        if breeding_val is not None:
            data[month_key]['breeding_inventory_yongyi'] = breeding_val
        
        # B列：大猪存栏环比-全国（索引1）
        hog_val = _safe_float(row[1])
        if hog_val is not None:
            data[month_key]['hog_inventory_yongyi'] = hog_val
        
        # P列：猪料销量环比（索引15）→ 育肥猪饲料环比
        feed_val = _safe_float(row[15])
        if feed_val is not None:
            data[month_key]['hog_feed_yongyi'] = feed_val
        
        # Q列：后备母猪料（索引16）→ 能繁母猪饲料环比-涌益
        breeding_feed_val = _safe_float(row[16])
        if breeding_feed_val is not None:
            data[month_key]['breeding_feed_yongyi'] = breeding_feed_val
        # S列：教保料（索引18）→ 仔猪饲料环比-涌益
        if len(row) > 18:
            piglet_feed_val = _safe_float(row[18])
            if piglet_feed_val is not None:
                if 0 < abs(piglet_feed_val) <= 1.5:
                    piglet_feed_val = piglet_feed_val * 100
                data[month_key]['piglet_feed_yongyi'] = round(piglet_feed_val, 2)
    
    return data


def _extract_yongyi_weekly_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """从涌益咨询周度数据中提取：月度-能繁/小猪/大猪存栏、月度-猪料销量，补全表格2/3 涌益列。
    表结构：能繁/小猪/大猪 为 日期(0)、全国(1)、环比(2)，数据从第4或5行起；猪料销量 为 月份(0)、教保料(4)，数据从第2行起。
    """
    data = defaultdict(dict)
    preferred = [
        "2026.1.16-2026.1.22涌益咨询 周度数据.xlsx",
        "涌益咨询 周度数据.xlsx",
    ]

    def _parse_monthly_sheet(sheet_name: str, data_key: str, header_row: int = 3) -> None:
        """header_row 为表头行索引，数据从 header_row+1 行开始。"""
        table = _get_raw_table_data_prefer_filenames(db, sheet_name, preferred)
        start = header_row + 1
        if not table or len(table) <= start:
            return
        for row in table[start:]:
            if len(row) < 3:
                continue
            date_val = _parse_excel_date(row[0])
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            val = _safe_float(row[2])  # 环比
            if val is not None:
                if 0 < abs(val) <= 1.5:
                    val = val * 100
                data[month_key][data_key] = round(val, 2)

    # 月度-能繁母猪存栏（2020年2月新增）→ breeding_inventory_yongyi（表头在第4行）
    _parse_monthly_sheet("月度-能繁母猪存栏（2020年2月新增）", "breeding_inventory_yongyi", header_row=4)
    # 月度-小猪存栏（2020年5月新增）→ 新生仔猪存栏环比（表头在第3行）
    _parse_monthly_sheet("月度-小猪存栏（2020年5月新增）", "piglet_inventory_yongyi", header_row=3)
    # 月度-大猪存栏（2020年5月新增）→ hog_inventory_yongyi（表头在第3行）
    _parse_monthly_sheet("月度-大猪存栏（2020年5月新增）", "hog_inventory_yongyi", header_row=3)

    # 月度-猪料销量：月份(0)、教保料(4)→ 仔猪饲料环比
    table = _get_raw_table_data_prefer_filenames(db, "月度-猪料销量", preferred)
    if table and len(table) >= 2:
        for row in table[2:]:
            if len(row) < 5:
                continue
            date_val = _parse_excel_date(row[0])
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            val = _safe_float(row[4])
            if val is not None:
                if 0 < abs(val) <= 1.5:
                    val = val * 100
                data[month_key]['piglet_feed_yongyi'] = round(val, 2)

    return data


def _find_col_by_header(header_row: List, *keywords: str) -> Optional[int]:
    """在表头行中查找包含全部 keywords 的列索引（0-based），未找到返回 None。"""
    if not header_row:
        return None
    for col_idx, cell in enumerate(header_row):
        s = (cell if cell is not None else "")
        if isinstance(s, (int, float)) and not isinstance(s, bool):
            s = str(s)
        elif not isinstance(s, str):
            s = str(s) if s else ""
        s = s.strip()
        if s and all(k in s for k in keywords):
            return col_idx
    return None


def _extract_ganglian_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取钢联数据（仅来自钢联自动更新模板，不使用 4.1.钢联数据）
    数据来源：1、价格：钢联自动更新模板.xlsx → sheet「月度数据」
    - 第2行是指标名称，数据从第5行开始（索引4）
    - 固定列：A=日期，H-J=生猪存栏，K=仔猪(全国)，M-O=能繁
    - 按表头匹配：新生仔猪-全国「仔猪：出生数环比：中国」、规模场「规模化养殖场：存栏数：中国」、中小散户「中小散：存栏数：中国」；仔猪饲料「仔猪饲料：销量环比：中国」；育肥猪饲料「育肥猪饲料：销量环比：中国」；母猪饲料「母猪饲料：销量环比：中国」
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "月度数据", "1、价格：钢联自动更新模板.xlsx")
    if not table_data:
        table_data = _get_raw_table_data(db, "月度数据", "钢联自动更新模板.xlsx")
    if not table_data or len(table_data) < 5:
        return data

    header_row = table_data[1] if len(table_data) > 1 else []  # 第2行表头
    # 新生仔猪存栏环比：全国/规模场/中小散户；仔猪/育肥猪/母猪饲料环比
    col_piglet_nation = _find_col_by_header(header_row, "仔猪", "出生数环比", "中国")
    col_piglet_scale = _find_col_by_header(header_row, "规模化养殖场", "存栏数", "中国")
    col_piglet_small = _find_col_by_header(header_row, "中小散", "存栏数", "中国")
    col_piglet_feed = _find_col_by_header(header_row, "仔猪饲料", "销量环比", "中国")
    col_hog_feed = _find_col_by_header(header_row, "育肥猪饲料", "销量环比", "中国")
    col_breeding_feed = _find_col_by_header(header_row, "母猪饲料", "销量环比", "中国")

    for row in table_data[4:]:
        if len(row) < 15:
            continue
        date_val = _parse_excel_date(row[0])
        if not date_val:
            continue
        month_key = date_val.strftime("%Y-%m")

        # 生猪存栏：H(7)=全国，I(8)=规模场，J(9)=中小散户
        hog_nation_val = _safe_float(row[7])
        if hog_nation_val is not None:
            data[month_key]['hog_inventory_ganglian_nation'] = hog_nation_val
        hog_scale_val = _safe_float(row[8]) if len(row) > 8 else None
        if hog_scale_val is not None:
            data[month_key]['hog_inventory_ganglian_scale'] = hog_scale_val
        hog_small_val = _safe_float(row[9]) if len(row) > 9 else None
        if hog_small_val is not None:
            data[month_key]['hog_inventory_ganglian_small'] = hog_small_val

        # 新生仔猪存栏环比：优先按表头匹配列，否则退回到 K(10) 仅全国
        if col_piglet_nation is not None and len(row) > col_piglet_nation:
            piglet_val = _safe_float(row[col_piglet_nation])
            if piglet_val is not None:
                data[month_key]['piglet_inventory_ganglian_nation'] = piglet_val
        else:
            piglet_val = _safe_float(row[10])
            if piglet_val is not None:
                data[month_key]['piglet_inventory_ganglian_nation'] = piglet_val
        if col_piglet_scale is not None and len(row) > col_piglet_scale:
            v = _safe_float(row[col_piglet_scale])
            if v is not None:
                data[month_key]['piglet_inventory_ganglian_scale'] = v
        if col_piglet_small is not None and len(row) > col_piglet_small:
            v = _safe_float(row[col_piglet_small])
            if v is not None:
                data[month_key]['piglet_inventory_ganglian_small'] = v

        # 仔猪饲料环比
        if col_piglet_feed is not None and len(row) > col_piglet_feed:
            v = _safe_float(row[col_piglet_feed])
            if v is not None:
                data[month_key]['piglet_feed_ganglian'] = v

        # 育肥猪饲料环比（表格3）
        if col_hog_feed is not None and len(row) > col_hog_feed:
            v = _safe_float(row[col_hog_feed])
            if v is not None:
                data[month_key]['hog_feed_ganglian'] = v

        # 能繁母猪：M(12)=全国，N(13)=规模场，O(14)=中小散户
        breeding_val = _safe_float(row[12]) if len(row) > 12 else None
        if breeding_val is not None:
            data[month_key]['breeding_inventory_ganglian_nation'] = breeding_val
        breeding_scale_val = _safe_float(row[13]) if len(row) > 13 else None
        if breeding_scale_val is not None:
            data[month_key]['breeding_inventory_ganglian_scale'] = breeding_scale_val
        breeding_small_val = _safe_float(row[14]) if len(row) > 14 else None
        if breeding_small_val is not None:
            data[month_key]['breeding_inventory_ganglian_small'] = breeding_small_val

        # 能繁母猪饲料环比（表格1）
        if col_breeding_feed is not None and len(row) > col_breeding_feed:
            v = _safe_float(row[col_breeding_feed])
            if v is not None:
                data[month_key]['breeding_feed_ganglian'] = v

    return data


def _extract_cull_slaughter_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取淘汰母猪屠宰数据
    - 涌益：优先 2、【生猪产业数据】.xlsx → 涌益样本 sheet V列；否则 涌益周度 → 月度-淘汰母猪屠宰厂宰杀量（日期、总宰杀量、总环比）
    - 钢联：sheet「淘汰母猪屠宰」（如来自钢联自动更新模板），第4行起 col0=日期、col1=屠宰量，按月度计算环比
    """
    data = defaultdict(dict)

    def _compute_mom_from_by_month(by_month: Dict[str, float], key_yongyi: bool = True) -> None:
        sorted_months = sorted(by_month.keys())
        key_name = 'cull_slaughter_yongyi' if key_yongyi else 'cull_slaughter_ganglian'
        for i in range(1, len(sorted_months)):
            prev_month = sorted_months[i - 1]
            curr_month = sorted_months[i]
            prev_val = by_month[prev_month]
            curr_val = by_month[curr_month]
            if prev_val is not None and curr_val is not None and prev_val != 0 and not math.isnan(prev_val) and not math.isnan(curr_val):
                mom = (curr_val - prev_val) / prev_val * 100
                if not math.isnan(mom) and not math.isinf(mom):
                    data[curr_month][key_name] = round(mom, 2)

    # 来源1：涌益样本（生猪产业数据）
    table_data = _get_raw_table_data(db, "涌益样本", "2、【生猪产业数据】.xlsx")
    if table_data and len(table_data) >= 3:
        rows_start = 2
        by_month = {}
        for row in table_data[rows_start:]:
            if len(row) < 22:
                continue
            date_val = _parse_excel_date(row[0]) or (_parse_excel_date(row[1]) if len(row) > 1 else None)
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            raw_val = _safe_float(row[21])
            if raw_val is not None:
                by_month[month_key] = raw_val
        if by_month:
            _compute_mom_from_by_month(by_month)
        # 不在此 return，继续用 来源2、钢联 补全/覆盖

    # 来源2：涌益周度 - 月度-淘汰母猪屠宰厂宰杀量（优先 2026.1.16-2026.1.22涌益咨询 周度数据.xlsx）
    YONGYI_CULL_SHEET_PREFERRED_FILES = [
        "2026.1.16-2026.1.22涌益咨询 周度数据.xlsx",
        "涌益咨询 周度数据.xlsx",
    ]
    table_data = _get_raw_table_data_prefer_filenames(
        db, "月度-淘汰母猪屠宰厂宰杀量", YONGYI_CULL_SHEET_PREFERRED_FILES
    )
    if table_data and len(table_data) >= 3:
        # 表结构：第0、1行为表头（行0 有「合计」「环比」），数据从第2行起
        # col0=日期，col12=合计（总宰杀量），col13=环比（小数如 0.0594 表示 5.94%）— 即用「合计」「环比」列
        by_month = {}
        for row in table_data[2:]:
            if len(row) < 14:
                continue
            date_val = _parse_excel_date(row[0])
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            mom_val = _safe_float(row[13])  # 环比（合计列的环比）
            if mom_val is not None:
                # 表中环比多为小数 0.11=11%、0.0594=5.94%，转为百分比数值（≤1.5 视为比例）
                if 0 < abs(mom_val) <= 1.5:
                    mom_val = mom_val * 100
                data[month_key]['cull_slaughter_yongyi'] = round(mom_val, 2)
            else:
                raw_val = _safe_float(row[12])  # 合计（总宰杀量），用于后续自算环比
                if raw_val is not None:
                    by_month[month_key] = raw_val
        if not data and by_month:
            _compute_mom_from_by_month(by_month)

    # 钢联：sheet「淘汰母猪屠宰」（如 1、价格：钢联自动更新模板.xlsx），第4行起 col0=日期、col1=屠宰量
    table_data_gl = _get_raw_table_data(db, "淘汰母猪屠宰", None)
    if table_data_gl and len(table_data_gl) >= 5:
        by_month_gl = {}
        for row in table_data_gl[4:]:
            if len(row) < 2:
                continue
            date_val = _parse_excel_date(row[0])
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            raw_val = _safe_float(row[1])
            if raw_val is not None:
                by_month_gl[month_key] = raw_val
        if by_month_gl:
            _compute_mom_from_by_month(by_month_gl, key_yongyi=False)
    return data


@router.get("/data", response_model=MultiSourceResponse)
async def get_multi_source_data(
    months: int = Query(999, description="显示最近N个月的数据，999表示全部"),
    db: Session = Depends(get_db)
):
    """
    获取多渠道汇总数据
    数据来源：【生猪产业数据】.xlsx
    """
    # 提取各数据源的数据
    nyb_data = _extract_nyb_data(db)
    association_data = _extract_association_feed_data(db)
    yongyi_data = _extract_yongyi_data(db)
    # 涌益周度：月度-能繁/小猪/大猪存栏、月度-猪料销量，补全新生仔猪存栏环比、仔猪饲料环比等
    yongyi_weekly = _extract_yongyi_weekly_data(db)
    for month, kv in yongyi_weekly.items():
        for k, v in kv.items():
            if v is not None:
                yongyi_data[month][k] = v
    ganglian_data = _extract_ganglian_data(db)
    cull_slaughter_data = _extract_cull_slaughter_data(db)
    
    # 合并所有月份
    all_months = set()
    all_months.update(nyb_data.keys())
    all_months.update(association_data.keys())
    all_months.update(yongyi_data.keys())
    all_months.update(ganglian_data.keys())
    all_months.update(cull_slaughter_data.keys())
    
    # 按月份排序
    sorted_months = sorted(all_months)
    
    # 如果指定了月份数，只取最近的N个月
    if months < 999:
        sorted_months = sorted_months[-months:]
    
    # 构建数据点
    data_points = []
    for month in sorted_months:
        point = MultiSourceDataPoint(month=month)
        
        # 合并各数据源
        if month in nyb_data:
            point.breeding_inventory_nyb = nyb_data[month].get('breeding_inventory_nyb')
            point.piglet_inventory_nyb = nyb_data[month].get('piglet_inventory_nyb')
            point.hog_inventory_nyb = nyb_data[month].get('hog_inventory_nyb')
            point.hog_inventory_nyb_5month = nyb_data[month].get('hog_inventory_nyb_5month')
        
        if month in association_data:
            point.breeding_feed_association = association_data[month].get('breeding_feed_association')
            point.piglet_feed_association = association_data[month].get('piglet_feed_association')
            point.hog_feed_association = association_data[month].get('hog_feed_association')
        
        if month in yongyi_data:
            point.breeding_inventory_yongyi = yongyi_data[month].get('breeding_inventory_yongyi')
            point.breeding_feed_yongyi = yongyi_data[month].get('breeding_feed_yongyi')
            point.piglet_inventory_yongyi = yongyi_data[month].get('piglet_inventory_yongyi')
            point.piglet_feed_yongyi = yongyi_data[month].get('piglet_feed_yongyi')
            point.hog_inventory_yongyi = yongyi_data[month].get('hog_inventory_yongyi')
            point.hog_feed_yongyi = yongyi_data[month].get('hog_feed_yongyi')
        
        if month in ganglian_data:
            point.breeding_inventory_ganglian_nation = ganglian_data[month].get('breeding_inventory_ganglian_nation')
            point.breeding_inventory_ganglian_scale = ganglian_data[month].get('breeding_inventory_ganglian_scale')
            point.breeding_inventory_ganglian_small = ganglian_data[month].get('breeding_inventory_ganglian_small')
            point.piglet_inventory_ganglian_nation = ganglian_data[month].get('piglet_inventory_ganglian_nation')
            point.piglet_inventory_ganglian_scale = ganglian_data[month].get('piglet_inventory_ganglian_scale')
            point.piglet_inventory_ganglian_small = ganglian_data[month].get('piglet_inventory_ganglian_small')
            point.hog_inventory_ganglian_nation = ganglian_data[month].get('hog_inventory_ganglian_nation')
            point.hog_inventory_ganglian_scale = ganglian_data[month].get('hog_inventory_ganglian_scale')
            point.hog_inventory_ganglian_small = ganglian_data[month].get('hog_inventory_ganglian_small')
            point.breeding_feed_ganglian = ganglian_data[month].get('breeding_feed_ganglian')
            point.piglet_feed_ganglian = ganglian_data[month].get('piglet_feed_ganglian')
            point.hog_feed_ganglian = ganglian_data[month].get('hog_feed_ganglian')
        
        if month in cull_slaughter_data:
            point.cull_slaughter_yongyi = cull_slaughter_data[month].get('cull_slaughter_yongyi')
            point.cull_slaughter_ganglian = cull_slaughter_data[month].get('cull_slaughter_ganglian')
        
        data_points.append(point)
    
    latest_month = sorted_months[-1] if sorted_months else None
    
    return MultiSourceResponse(
        data=data_points,
        latest_month=latest_month
    )
