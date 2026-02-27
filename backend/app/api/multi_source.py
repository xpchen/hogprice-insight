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
    breeding_inventory_nyb: Optional[float] = None  # 能繁母猪存栏环比-NYB（全国，兼容旧字段）
    breeding_inventory_nyb_nation: Optional[float] = None  # 能繁-NYB-全国
    breeding_inventory_nyb_scale: Optional[float] = None  # 能繁-NYB-规模场
    breeding_inventory_nyb_small: Optional[float] = None  # 能繁-NYB-散户
    breeding_feed_yongyi: Optional[float] = None  # 能繁母猪饲料环比-涌益
    breeding_feed_ganglian: Optional[float] = None  # 能繁母猪饲料环比-钢联
    breeding_feed_association: Optional[float] = None  # 能繁母猪饲料环比-协会
    piglet_inventory_yongyi: Optional[float] = None  # 新生仔猪存栏环比-涌益
    piglet_inventory_ganglian_nation: Optional[float] = None  # 新生仔猪存栏环比-钢联-全国
    piglet_inventory_ganglian_scale: Optional[float] = None  # 新生仔猪存栏环比-钢联-规模场
    piglet_inventory_ganglian_small: Optional[float] = None  # 新生仔猪存栏环比-钢联-中小散户
    piglet_inventory_nyb: Optional[float] = None  # 新生仔猪存栏环比-NYB（全国，兼容）
    piglet_inventory_nyb_nation: Optional[float] = None  # 新生仔猪-NYB-全国
    piglet_inventory_nyb_scale: Optional[float] = None  # 新生仔猪-NYB-规模场
    piglet_inventory_nyb_small: Optional[float] = None  # 新生仔猪-NYB-散户
    piglet_feed_yongyi: Optional[float] = None  # 仔猪饲料环比-涌益
    piglet_feed_ganglian: Optional[float] = None  # 仔猪饲料环比-钢联
    piglet_feed_association: Optional[float] = None  # 仔猪饲料环比-协会
    hog_inventory_yongyi: Optional[float] = None  # 生猪存栏环比-涌益
    hog_inventory_ganglian_nation: Optional[float] = None  # 生猪存栏环比-钢联-全国
    hog_inventory_ganglian_scale: Optional[float] = None  # 生猪存栏环比-钢联-规模场
    hog_inventory_ganglian_small: Optional[float] = None  # 生猪存栏环比-钢联-中小散户
    hog_inventory_nyb: Optional[float] = None  # 生猪存栏环比-NYB（全国，兼容）
    hog_inventory_nyb_nation: Optional[float] = None  # 生猪存栏-NYB-全国
    hog_inventory_nyb_scale: Optional[float] = None  # 生猪存栏-NYB-规模场
    hog_inventory_nyb_small: Optional[float] = None  # 生猪存栏-NYB-散户
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


def _compute_mom_from_raw(by_month: Dict[str, float]) -> Dict[str, float]:
    """从底稿原始值计算环比：(当月-上月)/上月*100"""
    result = {}
    sorted_months = sorted(by_month.keys())
    for i in range(1, len(sorted_months)):
        prev_month = sorted_months[i - 1]
        curr_month = sorted_months[i]
        prev_val = by_month[prev_month]
        curr_val = by_month[curr_month]
        if prev_val is not None and curr_val is not None and prev_val != 0:
            if not math.isnan(prev_val) and not math.isnan(curr_val) and not math.isinf(prev_val) and not math.isinf(curr_val):
                mom = (curr_val - prev_val) / prev_val * 100
                if not math.isnan(mom) and not math.isinf(mom):
                    result[curr_month] = round(mom, 2)
    return result


def _extract_nyb_data(db: Session) -> Dict[str, Dict[str, Optional[float]]]:
    """提取NYB数据（《生猪产业数据》-【NYB】）
    底稿为原始值，需计算环比。C/D/F列=全国/规模场/散户（能繁、新生仔猪、生猪存栏各自对应块）
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "NYB", "2、【生猪产业数据】.xlsx")

    if not table_data or len(table_data) < 3:
        return data

    # 收集底稿原始值，再计算环比
    breeding_raw = defaultdict(dict)  # month -> {nation, scale, small}
    piglet_raw = defaultdict(dict)
    hog_raw = defaultdict(dict)
    hog_5month_raw = {}

    for row in table_data[2:]:
        if len(row) < 17:
            continue
        date_val = _parse_excel_date(row[1])
        if not date_val:
            continue
        month_key = date_val.strftime("%Y-%m")

        # 能繁：C(2)=全国，D(3)=规模场，F(5)=散户
        for col_idx, key in [(2, 'nation'), (3, 'scale'), (5, 'small')]:
            if len(row) > col_idx:
                v = _safe_float(row[col_idx])
                if v is not None:
                    breeding_raw[month_key][key] = v

        # 新生仔猪：G(6)=全国，H(7)=规模场，J(9)=散户（沿用类似结构）
        for col_idx, key in [(6, 'nation'), (7, 'scale'), (9, 'small')]:
            if len(row) > col_idx:
                v = _safe_float(row[col_idx])
                if v is not None:
                    piglet_raw[month_key][key] = v

        # 生猪存栏：Q(16)=全国，R(17)=规模场，T(19)=散户
        for col_idx, key in [(16, 'nation'), (17, 'scale'), (19, 'small')]:
            if len(row) > col_idx:
                v = _safe_float(row[col_idx])
                if v is not None:
                    hog_raw[month_key][key] = v

        if len(row) > 10:
            v = _safe_float(row[10])  # K列 5月龄
            if v is not None:
                hog_5month_raw[month_key] = v

    def _apply_mom(raw_dict: Dict, key: str, out_key: str) -> None:
        by_month = {m: d[key] for m, d in raw_dict.items() if key in d}
        moms = _compute_mom_from_raw(by_month)
        for m, val in moms.items():
            data[m][out_key] = val

    _apply_mom(breeding_raw, 'nation', 'breeding_inventory_nyb')
    _apply_mom(breeding_raw, 'nation', 'breeding_inventory_nyb_nation')
    _apply_mom(breeding_raw, 'scale', 'breeding_inventory_nyb_scale')
    _apply_mom(breeding_raw, 'small', 'breeding_inventory_nyb_small')
    _apply_mom(piglet_raw, 'nation', 'piglet_inventory_nyb')
    _apply_mom(piglet_raw, 'nation', 'piglet_inventory_nyb_nation')
    _apply_mom(piglet_raw, 'scale', 'piglet_inventory_nyb_scale')
    _apply_mom(piglet_raw, 'small', 'piglet_inventory_nyb_small')
    _apply_mom(hog_raw, 'nation', 'hog_inventory_nyb')
    _apply_mom(hog_raw, 'nation', 'hog_inventory_nyb_nation')
    _apply_mom(hog_raw, 'scale', 'hog_inventory_nyb_scale')
    _apply_mom(hog_raw, 'small', 'hog_inventory_nyb_small')

    hog_5month_moms = _compute_mom_from_raw(hog_5month_raw)
    for m, val in hog_5month_moms.items():
        data[m]['hog_inventory_nyb_5month'] = val

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
    """提取涌益数据（4.2涌益底稿）
    G列能繁、B列大猪存栏为底稿原始值，需计算环比；P/Q/S 饲料列为环比，直接使用。
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "4.2涌益底稿", "2、【生猪产业数据】.xlsx")

    if not table_data or len(table_data) < 3:
        return data

    breeding_raw, hog_raw = {}, {}
    for row in table_data[2:]:
        if len(row) < 17:
            continue
        date_val = _parse_excel_date(row[0])
        if not date_val:
            continue
        month_key = date_val.strftime("%Y-%m")
        v = _safe_float(row[6])
        if v is not None:
            breeding_raw[month_key] = v
        v = _safe_float(row[1])
        if v is not None:
            hog_raw[month_key] = v

        # 饲料环比（已是环比）
        feed_val = _safe_float(row[15])
        if feed_val is not None:
            data[month_key]['hog_feed_yongyi'] = feed_val
        breeding_feed_val = _safe_float(row[16])
        if breeding_feed_val is not None:
            data[month_key]['breeding_feed_yongyi'] = breeding_feed_val
        if len(row) > 18:
            piglet_feed_val = _safe_float(row[18])
            if piglet_feed_val is not None:
                if 0 < abs(piglet_feed_val) <= 1.5:
                    piglet_feed_val = piglet_feed_val * 100
                data[month_key]['piglet_feed_yongyi'] = round(piglet_feed_val, 2)

    for m, val in _compute_mom_from_raw(breeding_raw).items():
        data[m]['breeding_inventory_yongyi'] = val
    for m, val in _compute_mom_from_raw(hog_raw).items():
        data[m]['hog_inventory_yongyi'] = val

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

    # 月度-猪料销量：仔猪饲料环比改为F列(5)（用户要求B列→F列）
    table = _get_raw_table_data_prefer_filenames(db, "月度-猪料销量", preferred)
    if table and len(table) >= 2:
        for row in table[2:]:
            if len(row) < 6:
                continue
            date_val = _parse_excel_date(row[0])
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            val = _safe_float(row[5])  # F列（用户要求从B改为F）
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
    """提取钢联数据（钢联自动更新模板 → 月度数据）
    能繁、新生仔猪、生猪存栏的 H-J,K,M-O 列为底稿原始值，需计算环比；饲料环比列已是环比，直接使用。
    """
    data = defaultdict(dict)
    table_data = _get_raw_table_data(db, "月度数据", "1、价格：钢联自动更新模板.xlsx")
    if not table_data:
        table_data = _get_raw_table_data(db, "月度数据", "钢联自动更新模板.xlsx")
    if not table_data or len(table_data) < 5:
        return data

    header_row = table_data[1] if len(table_data) > 1 else []
    col_piglet_nation = _find_col_by_header(header_row, "仔猪", "出生数环比", "中国")
    col_piglet_scale = _find_col_by_header(header_row, "规模化养殖场", "存栏数", "中国")
    col_piglet_small = _find_col_by_header(header_row, "中小散", "存栏数", "中国")
    col_piglet_feed = _find_col_by_header(header_row, "仔猪饲料", "销量环比", "中国")
    col_hog_feed = _find_col_by_header(header_row, "育肥猪饲料", "销量环比", "中国")
    col_breeding_feed = _find_col_by_header(header_row, "母猪饲料", "销量环比", "中国")

    # 收集底稿原始值（能繁 M-O、新生仔猪 K/表头列、生猪存栏 H-J）
    hog_raw = defaultdict(dict)
    piglet_raw = defaultdict(dict)
    breeding_raw = defaultdict(dict)

    for row in table_data[4:]:
        if len(row) < 15:
            continue
        date_val = _parse_excel_date(row[0])
        if not date_val:
            continue
        month_key = date_val.strftime("%Y-%m")

        # 生猪存栏：H(7)=全国，I(8)=规模场，J(9)=中小散户（底稿原始值）
        for i, k in [(7, 'nation'), (8, 'scale'), (9, 'small')]:
            if len(row) > i:
                v = _safe_float(row[i])
                if v is not None:
                    hog_raw[month_key][k] = v

        # 新生仔猪：表头匹配或 K(10)
        piglet_nation_col = col_piglet_nation if col_piglet_nation is not None else 10
        if len(row) > piglet_nation_col:
            v = _safe_float(row[piglet_nation_col])
            if v is not None:
                piglet_raw[month_key]['nation'] = v
        for col_var, k in [(col_piglet_scale, 'scale'), (col_piglet_small, 'small')]:
            if col_var is not None and len(row) > col_var:
                v = _safe_float(row[col_var])
                if v is not None:
                    piglet_raw[month_key][k] = v

        # 能繁：M(12)=全国，N(13)=规模场，O(14)=中小散户（底稿原始值）
        for i, k in [(12, 'nation'), (13, 'scale'), (14, 'small')]:
            if len(row) > i:
                v = _safe_float(row[i])
                if v is not None:
                    breeding_raw[month_key][k] = v

        # 饲料环比（已是环比，直接写入）
        if col_piglet_feed is not None and len(row) > col_piglet_feed:
            v = _safe_float(row[col_piglet_feed])
            if v is not None:
                data[month_key]['piglet_feed_ganglian'] = v
        if col_hog_feed is not None and len(row) > col_hog_feed:
            v = _safe_float(row[col_hog_feed])
            if v is not None:
                data[month_key]['hog_feed_ganglian'] = v
        if col_breeding_feed is not None and len(row) > col_breeding_feed:
            v = _safe_float(row[col_breeding_feed])
            if v is not None:
                data[month_key]['breeding_feed_ganglian'] = v

    # 从底稿计算环比
    for raw_d, prefixes in [
        (breeding_raw, ['breeding_inventory_ganglian_nation', 'breeding_inventory_ganglian_scale', 'breeding_inventory_ganglian_small']),
        (piglet_raw, ['piglet_inventory_ganglian_nation', 'piglet_inventory_ganglian_scale', 'piglet_inventory_ganglian_small']),
        (hog_raw, ['hog_inventory_ganglian_nation', 'hog_inventory_ganglian_scale', 'hog_inventory_ganglian_small']),
    ]:
        for key, prefix in [('nation', prefixes[0]), ('scale', prefixes[1]), ('small', prefixes[2])]:
            by_month = {m: d[key] for m, d in raw_d.items() if key in d}
            moms = _compute_mom_from_raw(by_month)
            for m, val in moms.items():
                data[m][prefix] = val

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
            point.breeding_inventory_nyb = nyb_data[month].get('breeding_inventory_nyb') or nyb_data[month].get('breeding_inventory_nyb_nation')
            point.breeding_inventory_nyb_nation = nyb_data[month].get('breeding_inventory_nyb_nation')
            point.breeding_inventory_nyb_scale = nyb_data[month].get('breeding_inventory_nyb_scale')
            point.breeding_inventory_nyb_small = nyb_data[month].get('breeding_inventory_nyb_small')
            point.piglet_inventory_nyb = nyb_data[month].get('piglet_inventory_nyb') or nyb_data[month].get('piglet_inventory_nyb_nation')
            point.piglet_inventory_nyb_nation = nyb_data[month].get('piglet_inventory_nyb_nation')
            point.piglet_inventory_nyb_scale = nyb_data[month].get('piglet_inventory_nyb_scale')
            point.piglet_inventory_nyb_small = nyb_data[month].get('piglet_inventory_nyb_small')
            point.hog_inventory_nyb = nyb_data[month].get('hog_inventory_nyb') or nyb_data[month].get('hog_inventory_nyb_nation')
            point.hog_inventory_nyb_nation = nyb_data[month].get('hog_inventory_nyb_nation')
            point.hog_inventory_nyb_scale = nyb_data[month].get('hog_inventory_nyb_scale')
            point.hog_inventory_nyb_small = nyb_data[month].get('hog_inventory_nyb_small')
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
