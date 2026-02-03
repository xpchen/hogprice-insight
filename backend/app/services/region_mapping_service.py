"""统一的区域映射服务 - 规范化 dim_region 的创建和查询"""
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.dim_region import DimRegion
from app.utils.region_normalizer import normalize_province_name


# 完整的区域定义：region_code -> (region_name, region_level, parent_region_code)
REGION_DEFINITIONS: Dict[str, Tuple[str, str, Optional[str]]] = {
    # 全国 (level 0)
    "NATION": ("全国", "0", None),
    
    # 大区 (level 1)
    "NORTHEAST": ("东北", "1", "NATION"),
    "NORTH": ("华北", "1", "NATION"),
    "EAST": ("华东", "1", "NATION"),
    "CENTRAL": ("华中", "1", "NATION"),
    "SOUTH": ("华南", "1", "NATION"),
    "SOUTHWEST": ("西南", "1", "NATION"),
    "NORTHWEST": ("西北", "1", "NATION"),
    
    # 省份 (level 2) - 华北
    "BEIJING": ("北京", "2", "NORTH"),
    "TIANJIN": ("天津", "2", "NORTH"),
    "HEBEI": ("河北", "2", "NORTH"),
    "SHANXI": ("山西", "2", "NORTH"),
    "INNER_MONGOLIA": ("内蒙古", "2", "NORTH"),
    
    # 省份 - 东北
    "LIAONING": ("辽宁", "2", "NORTHEAST"),
    "JILIN": ("吉林", "2", "NORTHEAST"),
    "HEILONGJIANG": ("黑龙江", "2", "NORTHEAST"),
    
    # 省份 - 华东
    "SHANGHAI": ("上海", "2", "EAST"),
    "JIANGSU": ("江苏", "2", "EAST"),
    "ZHEJIANG": ("浙江", "2", "EAST"),
    "ANHUI": ("安徽", "2", "EAST"),
    "FUJIAN": ("福建", "2", "EAST"),
    "JIANGXI": ("江西", "2", "EAST"),
    "SHANDONG": ("山东", "2", "EAST"),
    
    # 省份 - 华中
    "HENAN": ("河南", "2", "CENTRAL"),
    "HUBEI": ("湖北", "2", "CENTRAL"),
    "HUNAN": ("湖南", "2", "CENTRAL"),
    
    # 省份 - 华南
    "GUANGDONG": ("广东", "2", "SOUTH"),
    "GUANGXI": ("广西", "2", "SOUTH"),
    "HAINAN": ("海南", "2", "SOUTH"),
    
    # 省份 - 西南
    "CHONGQING": ("重庆", "2", "SOUTHWEST"),
    "SICHUAN": ("四川", "2", "SOUTHWEST"),
    "GUIZHOU": ("贵州", "2", "SOUTHWEST"),
    "YUNNAN": ("云南", "2", "SOUTHWEST"),
    "TIBET": ("西藏", "2", "SOUTHWEST"),
    
    # 省份 - 西北
    "SHAANXI": ("陕西", "2", "NORTHWEST"),
    "GANSU": ("甘肃", "2", "NORTHWEST"),
    "QINGHAI": ("青海", "2", "NORTHWEST"),
    "NINGXIA": ("宁夏", "2", "NORTHWEST"),
    "XINJIANG": ("新疆", "2", "NORTHWEST"),
}

# 省份名称到 region_code 的映射（用于反向查找）
PROVINCE_NAME_TO_CODE: Dict[str, str] = {
    name: code for code, (name, _, _) in REGION_DEFINITIONS.items() if code not in ["NATION", "NORTHEAST", "NORTH", "EAST", "CENTRAL", "SOUTH", "SOUTHWEST", "NORTHWEST"]
}

# 大区名称到 region_code 的映射
REGION_NAME_TO_CODE: Dict[str, str] = {
    "全国": "NATION",
    "中国": "NATION",
    "东北": "NORTHEAST",
    "华北": "NORTH",
    "华东": "EAST",
    "华中": "CENTRAL",
    "华南": "SOUTH",
    "西南": "SOUTHWEST",
    "西北": "NORTHWEST",
}


def resolve_region_code(region_name: str) -> str:
    """
    根据区域名称解析 region_code
    
    Args:
        region_name: 区域名称（可以是省份名、大区名等）
    
    Returns:
        标准化的 region_code，如果找不到则返回 "NATION"
    
    Examples:
        >>> resolve_region_code("北京")
        'BEIJING'
        >>> resolve_region_code("东北")
        'NORTHEAST'
        >>> resolve_region_code("全国")
        'NATION'
    """
    if not region_name:
        return "NATION"
    
    # 标准化名称
    normalized = normalize_province_name(region_name.strip())
    
    # 先检查是否是大区名称
    if normalized in REGION_NAME_TO_CODE:
        return REGION_NAME_TO_CODE[normalized]
    
    # 再检查是否是省份名称
    if normalized in PROVINCE_NAME_TO_CODE:
        return PROVINCE_NAME_TO_CODE[normalized]
    
    # 如果都找不到，尝试模糊匹配（处理一些变体）
    # 例如："黑龙江省" -> "黑龙江" -> "HEILONGJIANG"
    for province_name, code in PROVINCE_NAME_TO_CODE.items():
        if normalized in province_name or province_name in normalized:
            return code
    
    # 默认返回全国
    return "NATION"


def get_region_info(region_code: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """
    获取区域信息
    
    Args:
        region_code: 区域代码
    
    Returns:
        (region_name, region_level, parent_region_code) 或 None
    """
    return REGION_DEFINITIONS.get(region_code)


def is_valid_region_name(region_name: str) -> bool:
    """
    验证区域名称是否有效
    
    Args:
        region_name: 区域名称
    
    Returns:
        如果是有效的区域名称返回 True，否则返回 False
    """
    if not region_name:
        return False
    
    normalized = normalize_province_name(region_name.strip())
    
    # 检查是否是大区或省份名称
    if normalized in REGION_NAME_TO_CODE or normalized in PROVINCE_NAME_TO_CODE:
        return True
    
    # 检查是否是已知的无效名称（指标名称、企业类型等）
    invalid_names = {
        "出栏价", "出栏均价", "均价", "场均价", "场价",
        "样本养殖企业", "规模化养殖场", "规模场", "小散户",
        "标猪", "肥猪", "商品猪", "外三元", "内三元", "土杂",
        "白条", "仔猪", "利润", "价差", "价格", "市场价",
        "到厂价", "报价", "基差", "区域价差", "肥标价差",
        "毛白价差", "自繁自养利润", "外购仔猪利润", "养殖利润",
        "猪粮比", "饲料比价", "料肉比"
    }
    
    if normalized in invalid_names:
        return False
    
    return False


def get_or_create_region(
    db: Session,
    region_name: Optional[str] = None,
    region_code: Optional[str] = None,
    strict: bool = True
) -> Optional[DimRegion]:
    """
    获取或创建 DimRegion 记录
    
    优先使用 region_code，如果没有提供则从 region_name 解析
    
    Args:
        db: 数据库会话
        region_name: 区域名称（可选）
        region_code: 区域代码（可选）
        strict: 是否严格验证（默认 True）。如果为 True，无效的区域名称会返回 None
    
    Returns:
        DimRegion 对象，如果 strict=True 且区域名称无效则返回 None
    
    Examples:
        >>> region = get_or_create_region(db, region_name="北京")
        >>> region.region_code
        'BEIJING'
        >>> region.region_level
        '2'
        >>> region.parent_region_code
        'NORTH'
        
        >>> # 无效的区域名称
        >>> region = get_or_create_region(db, region_name="出栏价", strict=True)
        >>> region is None
        True
    """
    # 如果没有提供 region_code，从 region_name 解析
    if not region_code:
        if not region_name:
            region_code = "NATION"
        else:
            # 严格模式下验证区域名称
            if strict and not is_valid_region_name(region_name):
                return None
            region_code = resolve_region_code(region_name)
    
    # 验证 region_code 是否在定义中
    if strict and region_code not in REGION_DEFINITIONS:
        return None
    
    # 查询现有记录
    region = db.query(DimRegion).filter(DimRegion.region_code == region_code).first()
    if region:
        return region
    
    # 获取区域信息
    region_info = get_region_info(region_code)
    if not region_info:
        # 如果找不到定义且不是严格模式，使用默认值（全国）
        if not strict:
            region_code = "NATION"
            region_info = get_region_info(region_code)
        else:
            return None
    
    region_name, region_level, parent_region_code = region_info
    
    # 创建新记录
    region = DimRegion(
        region_code=region_code,
        region_name=region_name,
        region_level=region_level,
        parent_region_code=parent_region_code
    )
    db.add(region)
    db.flush()
    
    return region


def get_region_by_code(db: Session, region_code: str) -> Optional[DimRegion]:
    """
    根据 region_code 查询区域
    
    Args:
        db: 数据库会话
        region_code: 区域代码
    
    Returns:
        DimRegion 对象或 None
    """
    return db.query(DimRegion).filter(DimRegion.region_code == region_code).first()


def get_region_by_name(db: Session, region_name: str) -> Optional[DimRegion]:
    """
    根据区域名称查询区域
    
    Args:
        db: 数据库会话
        region_name: 区域名称
    
    Returns:
        DimRegion 对象或 None
    """
    region_code = resolve_region_code(region_name)
    return get_region_by_code(db, region_code)


def list_all_regions(db: Session, level: Optional[str] = None) -> list[DimRegion]:
    """
    列出所有区域
    
    Args:
        db: 数据库会话
        level: 可选的层级过滤（"0"/"1"/"2"）
    
    Returns:
        DimRegion 对象列表
    """
    query = db.query(DimRegion)
    if level:
        query = query.filter(DimRegion.region_level == level)
    return query.order_by(DimRegion.region_level, DimRegion.region_code).all()


def rebuild_all_regions(db: Session, dry_run: bool = False) -> Dict[str, int]:
    """
    重新构建所有区域数据
    
    Args:
        db: 数据库会话
        dry_run: 是否只是预览（不实际写入）
    
    Returns:
        {
            "total": int,  # 总定义数
            "created": int,  # 新创建数
            "updated": int,  # 更新数
            "skipped": int  # 跳过数（已存在且正确）
        }
    """
    created_count = 0
    updated_count = 0
    skipped_count = 0
    
    for region_code, (region_name, region_level, parent_region_code) in REGION_DEFINITIONS.items():
        existing = db.query(DimRegion).filter(DimRegion.region_code == region_code).first()
        
        if existing:
            # 检查是否需要更新
            needs_update = (
                existing.region_name != region_name or
                existing.region_level != region_level or
                existing.parent_region_code != parent_region_code
            )
            
            if needs_update:
                if not dry_run:
                    existing.region_name = region_name
                    existing.region_level = region_level
                    existing.parent_region_code = parent_region_code
                    updated_count += 1
                else:
                    updated_count += 1
            else:
                skipped_count += 1
        else:
            # 创建新记录
            if not dry_run:
                region = DimRegion(
                    region_code=region_code,
                    region_name=region_name,
                    region_level=region_level,
                    parent_region_code=parent_region_code
                )
                db.add(region)
                created_count += 1
            else:
                created_count += 1
    
    if not dry_run:
        db.commit()
    
    return {
        "total": len(REGION_DEFINITIONS),
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count
    }
