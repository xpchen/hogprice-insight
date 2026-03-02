"""通用工具函数：日期解析、数值清洗、省份映射"""
from datetime import datetime, date, timedelta
from typing import Optional
import math
import re


# ── 省份名 → region_code 映射 ──
PROVINCE_TO_CODE = {
    "全国": "NATION",
    "黑龙江": "HEILONGJIANG", "吉林": "JILIN", "辽宁": "LIAONING",
    "北京": "BEIJING", "天津": "TIANJIN", "河北": "HEBEI",
    "山西": "SHANXI", "内蒙古": "NEIMENGGU", "内蒙": "NEIMENGGU",
    "山东": "SHANDONG", "江苏": "JIANGSU", "浙江": "ZHEJIANG",
    "安徽": "ANHUI", "福建": "FUJIAN", "上海": "SHANGHAI",
    "河南": "HENAN", "湖北": "HUBEI", "湖南": "HUNAN", "江西": "JIANGXI",
    "广东": "GUANGDONG", "广西": "GUANGXI", "海南": "HAINAN",
    "四川": "SICHUAN", "重庆": "CHONGQING", "贵州": "GUIZHOU",
    "云南": "YUNNAN", "西藏": "XIZANG",
    "陕西": "SHAANXI", "甘肃": "GANSU", "青海": "QINGHAI",
    "宁夏": "NINGXIA", "新疆": "XINJIANG",
    # 大区
    "东北": "NORTHEAST", "华北": "NORTH", "华东": "EAST",
    "华中": "CENTRAL", "华南": "SOUTH", "西南": "SOUTHWEST", "西北": "NORTHWEST",
}

# region_code → 省份名
CODE_TO_PROVINCE = {v: k for k, v in PROVINCE_TO_CODE.items() if k != "内蒙"}


def province_to_code(name: str) -> Optional[str]:
    """省份名称 → region_code"""
    if not name:
        return None
    name = name.strip().replace("省", "").replace("市", "").replace("自治区", "").replace("特别行政区", "")
    return PROVINCE_TO_CODE.get(name)


def parse_date(value) -> Optional[date]:
    """解析日期，支持 datetime/str/Excel serial number"""
    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    # pandas Timestamp
    try:
        import pandas as pd
        if isinstance(value, pd.Timestamp):
            return value.date()
        if pd.isna(value):
            return None
    except ImportError:
        pass

    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in ("na", "n/a", "null", "none", ""):
            return None
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        if re.match(r"^\d{4}-\d{1,2}$", value):
            try:
                return datetime.strptime(value, "%Y-%m").date()
            except ValueError:
                pass
        if "T" in value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except Exception:
                pass

    # Excel serial number
    if isinstance(value, (int, float)):
        try:
            v = int(value)
            if 1 < v < 100000:
                return (datetime(1899, 12, 30) + timedelta(days=v)).date()
        except Exception:
            pass

    return None


def parse_month(value) -> Optional[date]:
    """解析月份，返回该月第一天"""
    d = parse_date(value)
    if d:
        return d.replace(day=1)
    return None


def clean_value(value) -> Optional[float]:
    """清洗数值：处理 None/空字符串/NA/千分位逗号"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in ("na", "n/a", "null", "none", "-", "--", "——", "nan"):
            return None
        value = value.replace(",", "")
        try:
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        except ValueError:
            return None
    return None


def compute_mom_pct(by_month: dict) -> dict:
    """从月度绝对值 dict {YYYY-MM: value} 计算环比百分比 dict"""
    result = {}
    sorted_keys = sorted(by_month.keys())
    for i in range(1, len(sorted_keys)):
        prev_k = sorted_keys[i - 1]
        curr_k = sorted_keys[i]
        prev_v = by_month[prev_k]
        curr_v = by_month[curr_k]
        if prev_v is not None and curr_v is not None and prev_v != 0:
            mom = (curr_v - prev_v) / prev_v * 100
            if not math.isnan(mom) and not math.isinf(mom):
                result[curr_k] = round(mom, 2)
    return result
