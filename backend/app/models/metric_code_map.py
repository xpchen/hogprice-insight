"""
指标代码映射表
用于模板中的占位符映射到实际的 metric_id
"""
METRIC_CODE_MAP = {
    # 价格类
    "HOG_PRICE_NATIONAL": {
        "description": "全国标猪价格",
        "metric_group": "province",
        "keywords": ["商品猪：出栏均价：中国", "全国", "中国（日）"],  # 优先匹配"中国"的全国价格
        "preferred_match": "商品猪：出栏均价：中国（日）"  # 精确匹配
    },
    "HOG_PRICE_COMMODITY": {
        "description": "商品猪出栏均价",
        "metric_group": "province",
        "keywords": ["商品猪", "出栏均价", "中国"]
    },
    
    # 价差类
    "SPREAD_STANDARD_FATTY": {
        "description": "标肥价差",
        "metric_group": "spread",
        "keywords": ["生猪标肥：价差：中国", "标肥", "价差", "中国（日）"],  # 优先匹配全国的标肥价差
        "preferred_match": "生猪标肥：价差：中国（日）"
    },
    "SPREAD_MAO_BAI": {
        "description": "毛白价差",
        "metric_group": "spread",
        "keywords": ["毛白：价差：中国", "毛白", "价差", "中国（日）"],  # 优先匹配全国的毛白价差
        "preferred_match": "毛白：价差：中国（日）"
    },
    "REGIONAL_SPREAD_NORTH_SOUTH": {
        "description": "南北价差",
        "metric_group": "spread",
        "keywords": ["广东", "黑龙江", "价差"],  # 用广东-黑龙江作为南北价差示例
        "exclude_keywords": ["标肥", "毛白", "中国"]  # 排除标肥、毛白和全国价差
    },
    "REGIONAL_SPREAD_EAST_WEST": {
        "description": "东西价差",
        "metric_group": "spread",
        "keywords": ["浙江", "四川", "价差"],  # 用浙江-四川作为东西价差示例
        "exclude_keywords": ["标肥", "毛白", "中国"]  # 排除标肥、毛白和全国价差
    },
    
    # 区域价格（分省）
    "PRICE_BY_PROVINCE": {
        "description": "分省价格",
        "metric_group": "province",
        "keywords": ["商品猪：出栏均价", "黑龙江", "广东"],  # 匹配分省价格
        "exclude_keywords": ["中国"]  # 排除"中国"（全国价格）
        # 注意：这个会匹配所有省份的价格，使用时需要配合geo_ids筛选
    },
    
    # 企业价格
    "PRICE_BY_GROUP": {
        "description": "集团企业价格",
        "metric_group": "group",
        "keywords": ["外三元猪", "出栏价", "大北农", "牧原", "温氏"]  # 匹配企业价格
    },
    
    # 利润类
    "PROFIT_SELF_BREED": {
        "description": "自繁自养利润",
        "metric_group": "profit",
        "keywords": ["自繁自养", "利润", "屠宰利润"]  # 如果没有自繁自养，可以用屠宰利润
    },
    "PROFIT_PURCHASE_PIGLET": {
        "description": "外购仔猪利润",
        "metric_group": "profit",
        "keywords": ["外购利润", "外购", "利润", "猪：外购利润"]  # 精确匹配外购利润
    }
}


def resolve_metric_id(db, metric_code: str, metric_group: str = None):
    """
    根据 metric_code 占位符解析实际的 metric_id
    
    Args:
        db: 数据库会话
        metric_code: 占位符代码（如 "HOG_PRICE_NATIONAL"）
        metric_group: 可选的指标组过滤
    
    Returns:
        metric_id 或 None
    """
    from app.models.dim_metric import DimMetric
    
    if metric_code not in METRIC_CODE_MAP:
        return None
    
    mapping = METRIC_CODE_MAP[metric_code]
    keywords = mapping["keywords"]
    target_group = metric_group or mapping["metric_group"]
    
    # 查询匹配的指标
    query = db.query(DimMetric).filter(DimMetric.metric_group == target_group)
    
    # 优先精确匹配
    if "preferred_match" in mapping:
        exact_match = query.filter(DimMetric.raw_header == mapping["preferred_match"]).first()
        if exact_match:
            return exact_match.id
    
    # 尝试匹配关键词（按顺序，优先匹配更精确的关键词）
    exclude_keywords = mapping.get("exclude_keywords", [])
    
    for keyword in keywords:
        metrics = query.filter(DimMetric.raw_header.like(f"%{keyword}%")).all()
        
        # 过滤掉排除关键词
        filtered_metrics = []
        for m in metrics:
            should_exclude = False
            for exclude_kw in exclude_keywords:
                if exclude_kw in m.raw_header:
                    should_exclude = True
                    break
            if not should_exclude:
                filtered_metrics.append(m)
        
        if filtered_metrics:
            # 优先选择包含"中国"的全国指标（如果没有排除关键词）
            if not exclude_keywords:
                for m in filtered_metrics:
                    if "中国" in m.raw_header and "（日）" in m.raw_header:
                        return m.id
            # 否则返回第一个匹配的
            return filtered_metrics[0].id
    
    # 如果没有匹配，返回该组第一个指标
    first_metric = query.first()
    return first_metric.id if first_metric else None
