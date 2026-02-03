"""配置加载器 - 将 JSON 配置文件加载到数据库"""
import json
import os
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from pathlib import Path

from app.models.ingest_profile import IngestProfile, IngestProfileSheet
from app.models.dim_source import DimSource


def load_profile_from_json(db: Session, json_path: str) -> IngestProfile:
    """
    从 JSON 文件加载配置到数据库
    
    Args:
        db: 数据库会话
        json_path: JSON 配置文件路径
    
    Returns:
        IngestProfile 对象
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return save_profile_to_db(db, config)


def load_profile_from_dict(db: Session, config: Dict) -> IngestProfile:
    """
    从字典加载配置到数据库
    
    Args:
        db: 数据库会话
        config: 配置字典
    
    Returns:
        IngestProfile 对象
    """
    return save_profile_to_db(db, config)


def save_profile_to_db(db: Session, config: Dict) -> IngestProfile:
    """
    将配置保存到数据库
    
    Args:
        db: 数据库会话
        config: 配置字典
    
    Returns:
        IngestProfile 对象
    """
    # 验证必需字段
    required_fields = ['profile_code', 'profile_name', 'source_code', 'dataset_type']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"配置缺少必需字段: {field}")
    
    # 检查数据源是否存在
    source = db.query(DimSource).filter(DimSource.source_code == config['source_code']).first()
    if not source:
        raise ValueError(f"数据源不存在: {config['source_code']}")
    
    # 查找或创建 profile
    profile = db.query(IngestProfile).filter(
        IngestProfile.profile_code == config['profile_code']
    ).first()
    
    if profile:
        # 更新现有配置
        profile.profile_name = config['profile_name']
        profile.source_code = config['source_code']
        profile.dataset_type = config['dataset_type']
        profile.file_pattern = config.get('file_pattern')
        profile.target = config.get('target', 'fact_observation')
        profile.defaults_json = config.get('defaults', {})
        profile.dispatch_rules_json = config.get('dispatch_rules', [])
        profile.version = config.get('version', '1.0')
        profile.is_active = config.get('is_active', 'Y')
        
        # 删除旧的 sheet 配置
        db.query(IngestProfileSheet).filter(
            IngestProfileSheet.profile_id == profile.id
        ).delete()
    else:
        # 创建新配置
        profile = IngestProfile(
            profile_code=config['profile_code'],
            profile_name=config['profile_name'],
            source_code=config['source_code'],
            dataset_type=config['dataset_type'],
            file_pattern=config.get('file_pattern'),
            target=config.get('target', 'fact_observation'),
            defaults_json=config.get('defaults', {}),
            dispatch_rules_json=config.get('dispatch_rules', []),
            version=config.get('version', '1.0'),
            is_active=config.get('is_active', 'Y')
        )
        db.add(profile)
        db.flush()  # 获取 profile.id
    
    # 处理 sheets 配置
    sheets_config = config.get('sheets', [])
    for sheet_idx, sheet_config in enumerate(sheets_config):
        sheet = IngestProfileSheet(
            profile_id=profile.id,
            sheet_name=sheet_config.get('sheet_name', ''),
            parser=sheet_config.get('parser'),
            action=sheet_config.get('action'),
            config_json=sheet_config,  # 保存完整配置
            priority=sheet_config.get('priority', 100),
            note=sheet_config.get('note')
        )
        db.add(sheet)
    
    db.commit()
    db.refresh(profile)
    
    return profile


def get_profile_by_code(db: Session, profile_code: str) -> Optional[IngestProfile]:
    """根据 profile_code 获取配置"""
    return db.query(IngestProfile).filter(
        IngestProfile.profile_code == profile_code,
        IngestProfile.is_active == 'Y'
    ).first()


def get_profile_by_dataset_type(db: Session, dataset_type: str) -> Optional[IngestProfile]:
    """根据 dataset_type 获取配置"""
    return db.query(IngestProfile).filter(
        IngestProfile.dataset_type == dataset_type,
        IngestProfile.is_active == 'Y'
    ).order_by(IngestProfile.version.desc()).first()


def get_sheet_config(profile: IngestProfile, sheet_name: str) -> Optional[Dict]:
    """从 profile 中获取指定 sheet 的配置"""
    sheet = next(
        (s for s in profile.sheets if s.sheet_name == sheet_name),
        None
    )
    if sheet:
        return sheet.config_json
    return None


def match_sheet_by_dispatch_rules(profile: IngestProfile, sheet_name: str, sheet_columns: List[str]) -> Optional[Dict]:
    """
    根据 dispatch_rules 匹配 sheet 配置（用于周度文件）
    
    Args:
        profile: IngestProfile 对象
        sheet_name: sheet 名称
        sheet_columns: sheet 列名列表
    
    Returns:
        sheet 配置字典，如果匹配失败返回 None
    """
    dispatch_rules = profile.dispatch_rules_json or []
    
    # 按 priority 排序（priority 越小优先级越高）
    sorted_rules = sorted(dispatch_rules, key=lambda r: r.get('priority', 100))
    
    for rule in sorted_rules:
        when = rule.get('when', {})
        matched = True
        
        # 检查 sheet_name_in
        if 'sheet_name_in' in when:
            if sheet_name not in when['sheet_name_in']:
                matched = False
                continue
        
        # 检查 sheet_name_regex
        if 'sheet_name_regex' in when:
            import re
            if not re.match(when['sheet_name_regex'], sheet_name):
                matched = False
                continue
        
        # 检查 has_columns
        if 'has_columns' in when:
            required_cols = when['has_columns']
            if not all(col in sheet_columns for col in required_cols):
                matched = False
                continue
        
        # 检查 row_dim_any
        if 'row_dim_any' in when:
            # 这个需要在解析时检查，这里先跳过
            pass
        
        if matched:
            # 找到匹配的规则
            parser = rule.get('parser')
            action = rule.get('action')
            
            # 检查parser是否是特殊action值（如RAW_TABLE_STORE_ONLY）
            if parser in ['RAW_TABLE_STORE_ONLY', 'SKIP_META']:
                # 这些是action，不是parser
                return {
                    'sheet_name': sheet_name,
                    'action': parser,  # 使用parser值作为action
                    'parser': None
                }
            
            # 如果是 SKIP_META 或 RAW_TABLE_STORE_ONLY，返回 action
            if action:
                return {
                    'sheet_name': sheet_name,
                    'action': action,
                    'parser': None
                }
            
            # 查找对应的 sheet 配置
            if parser:
                sheet = next(
                    (s for s in profile.sheets if s.parser == parser),
                    None
                )
                if sheet:
                    return sheet.config_json
    
    # 如果没有匹配的规则，返回 None（使用默认处理）
    return None
