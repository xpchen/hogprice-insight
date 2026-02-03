import re
from typing import Dict, Optional, List


# 省份集合
PROVINCES = {
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
    "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
    "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
    "台湾", "香港", "澳门"
}

# 区域集合
REGIONS = {"东北", "华北", "华东", "华中", "华南", "西南", "西北"}

# 指标关键词字典（按长度从长到短排序，优先匹配长关键词）
METRIC_KEYWORDS = [
    "区域价差", "肥标价差", "毛白价差", "基差",
    "自繁自养利润", "外购仔猪利润", "养殖利润",
    "出栏均价", "出栏价", "均价", "报价", "到厂价",
    "猪粮比", "饲料比价", "料肉比",
    "利润", "价差", "价格"
]

# 猪种候选
PIG_TYPES = ["标猪", "商品猪", "外三元", "内三元", "土杂", "白条", "仔猪", "肥猪"]


def infer_group(sheet_name: str) -> str:
    """根据sheet_name推断指标组"""
    if not sheet_name:
        return "misc"
    
    sheet_lower = sheet_name.lower()
    if "分省" in sheet_name or "省区" in sheet_name:
        return "province"
    elif "集团" in sheet_name or "企业" in sheet_name:
        return "group"
    elif "交割库" in sheet_name or "库" in sheet_name:
        return "warehouse"
    elif "价差" in sheet_name:
        return "spread"
    elif "利润" in sheet_name:
        return "profit"
    else:
        return "misc"


def infer_metric_name(parts: List[str], metric_group: str) -> str:
    """从parts中推断指标名"""
    # 遍历所有parts，寻找最长匹配
    best_match = None
    best_length = 0
    
    for part in parts:
        for keyword in METRIC_KEYWORDS:
            if keyword in part:
                if len(keyword) > best_length:
                    best_match = keyword
                    best_length = len(keyword)
    
    if best_match:
        return best_match
    
    # 默认值
    if metric_group == "spread":
        return "价差"
    elif metric_group == "profit":
        return "利润"
    else:
        return "价格"


def parse_header(raw_header: str, sheet_name: str = "") -> Dict:
    """
    解析指标名称raw_header，返回结构化维度
    
    Args:
        raw_header: 原始指标名称，如 "商品猪：出栏均价：黑龙江（日）"
        sheet_name: Sheet名称，用于推断指标组
    
    Returns:
        {
            "metric_group": "province|group|warehouse|spread|profit|misc",
            "metric_name": "出栏价|出栏均价|区域价差|...",
            "freq": "daily|weekly",
            "geo": "黑龙江",
            "region": "东北",
            "company": "辽宁大北农",
            "warehouse": "xx交割库",
            "tags": {
                "pig_type": "商品猪",
                "weight_range": "110-125kg",
                "pair": "河南-山东",
                "raw_parts": [...]
            }
        }
    """
    # 1. 标准化预处理
    s = (raw_header or "").strip()
    s = s.replace(":", "：")  # 全角/半角统一
    s = re.sub(r"\s+", " ", s)  # 去除多余空格
    
    # 2. 频率解析（最高优先级）
    freq_match = re.search(r"[（(](日|周)[)）]\s*$", s)
    if freq_match:
        freq = "daily" if freq_match.group(1) == "日" else "weekly"
        s = re.sub(r"\s*[（(](日|周)[)）]\s*$", "", s)
    else:
        # 从sheet_name推断
        freq = "weekly" if ("周" in (sheet_name or "")) else "daily"
    
    # 3. 分段parts拆分
    parts = [p.strip() for p in s.split("：") if p.strip()]
    
    if not parts:
        # 空parts，返回默认值
        return {
            "metric_group": infer_group(sheet_name),
            "metric_name": "价格",
            "freq": freq,
            "geo": None,
            "region": None,
            "company": None,
            "warehouse": None,
            "tags": {"raw_parts": []}
        }
    
    # 4. 指标组推断
    metric_group = infer_group(sheet_name)
    
    # 5. 指标名推断
    metric_name = infer_metric_name(parts, metric_group)
    
    # 6. 初始化tags
    tags = {"raw_parts": parts}
    
    # 7. 提取体重段weight_range
    for p in parts:
        weight_match = re.search(r"(\d+\s*[-—～]\s*\d+\s*kg)", p, re.I)
        if weight_match:
            w = weight_match.group(1)
            w = re.sub(r"\s+", "", w).replace("—", "-").replace("～", "-").lower()
            tags["weight_range"] = w
            break
    
    # 8. 提取价差对pair
    for p in parts:
        if any(k in p for k in ["价差", "基差"]) and re.search(r".+[-—～].+", p):
            pair = p.replace("—", "-").replace("～", "-")
            tags["pair"] = pair
            break
    
    # 9. 提取猪种pig_type
    if parts:
        first_part = parts[0]
        if "猪" in first_part or first_part in PIG_TYPES:
            tags["pig_type"] = first_part
    
    # 10. 提取geo/company/warehouse（根据metric_group优先级推断）
    geo = None
    company = None
    warehouse = None
    region = None
    
    if metric_group == "province":
        # 分省区：最后一段通常是省
        if parts:
            last = parts[-1]
            if last in PROVINCES:
                geo = last
            elif last in REGIONS:
                region = last
    elif metric_group == "group":
        # 集团企业：倒数第二段是省，最后一段是企业
        if len(parts) >= 2:
            maybe_geo = parts[-2]
            maybe_company = parts[-1]
            if maybe_geo in PROVINCES:
                geo = maybe_geo
            elif maybe_geo in REGIONS:
                region = maybe_geo
            company = maybe_company
        elif len(parts) == 1:
            # 只有一段，可能是企业名
            company = parts[0]
    elif metric_group == "warehouse":
        # 交割库：最后一段是库点，倒数第二段可能是省
        if len(parts) >= 2:
            maybe_geo = parts[-2]
            if maybe_geo in PROVINCES:
                geo = maybe_geo
            elif maybe_geo in REGIONS:
                region = maybe_geo
            warehouse = parts[-1]
        elif len(parts) == 1:
            warehouse = parts[0]
    elif metric_group == "spread":
        # 价差：通常无geo/company，靠pair或其它tags
        pass
    elif metric_group == "profit":
        # 利润：通常无geo/company
        pass
    
    # 推断value_type
    value_type = "price"  # 默认
    if metric_group == "spread":
        value_type = "spread"
    elif metric_group == "profit":
        value_type = "profit"
    elif "比" in metric_name or "比率" in metric_name:
        value_type = "ratio"
    
    # 推断preferred_agg（默认mean）
    preferred_agg = "mean"
    
    # 推断suggested_axis
    suggested_axis = "auto"
    if metric_group == "spread" or metric_group == "profit":
        suggested_axis = "right"
    elif metric_group in ["province", "group", "warehouse"]:
        suggested_axis = "left"
    
    return {
        "metric_group": metric_group,
        "metric_name": metric_name,
        "freq": freq,
        "geo": geo,
        "region": region,
        "company": company,
        "warehouse": warehouse,
        "tags": tags,
        # 新增元数据字段
        "value_type": value_type,
        "preferred_agg": preferred_agg,
        "suggested_axis": suggested_axis,
        "seasonality_supported": True
    }
