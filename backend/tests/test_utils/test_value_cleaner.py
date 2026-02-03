"""数值清洗测试"""
import pytest
from app.utils.value_cleaner import (
    clean_numeric_value,
    parse_interval_value,
    parse_value_with_unit,
    clean_numeric_value_enhanced
)


def test_clean_numeric_value():
    """测试基础数值清洗"""
    assert clean_numeric_value("15.5") == 15.5
    assert clean_numeric_value("1,000") == 1000.0
    assert clean_numeric_value("--") is None
    assert clean_numeric_value("") is None


def test_parse_interval_value():
    """测试区间字符串解析"""
    result = parse_interval_value("15.5-16.5")
    assert result is not None
    assert result["min"] == 15.5
    assert result["max"] == 16.5


def test_parse_value_with_unit():
    """测试带单位数值解析"""
    result = parse_value_with_unit("15.5元/公斤")
    assert result is not None
    assert result["value"] == 15.5
    assert result["unit"] == "元/公斤"


def test_clean_numeric_value_enhanced():
    """测试增强数值清洗"""
    value, raw = clean_numeric_value_enhanced("15.5-16.5")
    assert value is not None
    assert raw == "15.5-16.5"
