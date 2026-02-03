"""测试周度-体重sheet的indicator单位映射是否正确"""
import sys
import os
import io
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.services.ingestors.profile_loader import get_profile_by_dataset_type
from app.services.ingestors.dispatcher import Dispatcher
from app.services.ingestors.parsers import get_parser
from openpyxl import load_workbook

def test_indicator_units():
    """测试indicator单位映射"""
    print("=" * 80)
    print("测试周度-体重sheet的indicator单位映射")
    print("=" * 80)
    
    # 查找Excel文件
    project_root = Path(__file__).parent.parent
    excel_files = list(project_root.glob("docs/*涌益咨询 周度数据*.xlsx"))
    if not excel_files:
        print("❌ 未找到Excel文件")
        return
    
    excel_file = excel_files[0]
    print(f"✓ 找到Excel文件: {excel_file}")
    
    db = SessionLocal()
    try:
        # 加载profile
        profile = get_profile_by_dataset_type(db, "YONGYI_WEEKLY")
        if not profile:
            print("❌ 未找到profile")
            return
        
        # 查找"周度-体重"的sheet配置
        sheet_config = None
        for sheet in profile.sheets:
            if sheet.sheet_name == "周度-体重":
                sheet_config = sheet.config_json
                break
        
        if not sheet_config:
            print("❌ 未找到'周度-体重'的sheet配置")
            return
        
        print(f"\n✓ 找到'周度-体重'的sheet配置")
        print(f"\n配置内容:")
        print(f"  indicator_mapping: {sheet_config.get('indicator_mapping', {})}")
        print(f"  indicator_unit_mapping: {sheet_config.get('indicator_unit_mapping', {})}")
        print(f"  metric_template.unit: {sheet_config.get('metric_template', {}).get('unit', 'N/A')}")
        
        # 测试解析
        print(f"\n测试解析...")
        wb = load_workbook(excel_file, data_only=True)
        ws = wb["周度-体重"]
        
        dispatcher = Dispatcher(db, profile)
        dispatch_result = dispatcher.dispatch_sheet("周度-体重", worksheet=ws)
        
        parser_name = dispatch_result.get('parser')
        if not parser_name:
            print(f"❌ 未找到parser")
            return
        
        print(f"✓ Parser: {parser_name}")
        
        parser = get_parser(parser_name)
        profile_defaults = profile.defaults_json or {}
        
        observations = parser.parse(
            sheet_data=ws,
            sheet_config=sheet_config,
            profile_defaults=profile_defaults,
            source_code="YONGYI",
            batch_id=0
        )
        
        print(f"\n✓ 解析出 {len(observations)} 条观测值")
        
        # 检查不同indicator的单位
        print(f"\n检查不同indicator的单位:")
        indicator_units = {}
        for obs in observations:
            indicator = obs.get('tags', {}).get('indicator')
            unit = obs.get('unit')
            value = obs.get('value')
            if indicator:
                if indicator not in indicator_units:
                    indicator_units[indicator] = {
                        'unit': unit,
                        'sample_values': []
                    }
                if len(indicator_units[indicator]['sample_values']) < 5:
                    indicator_units[indicator]['sample_values'].append(value)
        
        for indicator, info in sorted(indicator_units.items()):
            print(f"  {indicator}:")
            print(f"    单位: {info['unit']}")
            print(f"    示例值: {info['sample_values'][:5]}")
        
        # 特别检查90kg和150kg的单位
        print(f"\n特别检查90kg和150kg的单位:")
        for obs in observations:
            indicator = obs.get('tags', {}).get('indicator')
            if indicator in ['90Kg出栏占比', '150Kg出栏占重']:
                print(f"  {indicator}:")
                print(f"    单位: {obs.get('unit')}")
                print(f"    值: {obs.get('value')}")
                print(f"    原始值: {obs.get('raw_value')}")
                break
        
    except Exception as e:
        print(f"\n❌ 测试失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_indicator_units()
