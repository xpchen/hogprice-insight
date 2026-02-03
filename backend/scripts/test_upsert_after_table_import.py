"""测试：导入到独立表后再调用upsert_observations"""
import sys
import os
import io
from pathlib import Path
from openpyxl import load_workbook

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.import_batch import ImportBatch
from app.models.sys_user import SysUser
from app.services.ingestors.observation_upserter import upsert_observations
from app.services.ingestors.dispatcher import create_dispatcher
from app.services.ingestors.parsers import get_parser
from app.services.ingestors.validator import ObservationValidator
from app.services.ingestors.error_collector import ErrorCollector
from app.services.column_mapper import ColumnMapper
from app.services.sheet_table_importer import SheetTableImporter


def test_after_table_import(file_path: str, sheet_name: str = "周度-体重", limit: int = 100):
    """测试：导入到独立表后再调用upsert_observations"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print(f"测试：导入到独立表后再调用upsert_observations")
        print(f"文件: {file_path}")
        print(f"Sheet: {sheet_name}")
        print(f"限制: {limit} 条")
        print("=" * 80)
        
        # 1. 获取用户
        user = db.query(SysUser).filter(SysUser.username == "admin").first()
        if not user:
            print("  ❌ 未找到admin用户")
            return
        
        print(f"  ✓ 使用用户: {user.username} (ID: {user.id})")
        
        # 2. 加载profile和解析数据（同之前的测试）
        print(f"\n  加载导入配置和解析数据...")
        dispatcher = create_dispatcher(db, dataset_type="YONGYI_WEEKLY")
        profile = dispatcher.profile
        
        wb = load_workbook(file_path, data_only=True)
        worksheet = wb[sheet_name]
        
        dispatch_result = dispatcher.dispatch_sheet(sheet_name, worksheet=worksheet)
        parser_type = dispatch_result["parser"]
        sheet_config = dispatch_result["sheet_config"]
        
        parser = get_parser(parser_type)
        observations = parser.parse(
            sheet_data=worksheet,
            sheet_config=sheet_config,
            profile_defaults=profile.defaults_json or {},
            source_code=profile.source_code,
            batch_id=0
        )
        wb.close()
        
        if limit and len(observations) > limit:
            observations = observations[:limit]
        
        print(f"  ✓ 解析完成: {len(observations)} 条观测值")
        
        # 3. 验证数据
        batch = ImportBatch(
            filename=Path(file_path).name,
            file_hash="test_hash",
            uploader_id=user.id,
            source_code=profile.source_code,
            status="processing",
            total_rows=0,
            success_rows=0,
            failed_rows=0
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        error_collector = ErrorCollector(db, batch.id)
        validator = ObservationValidator(error_collector)
        
        table_config = sheet_config.get("table_config")
        skip_metric_check = bool(table_config)
        
        valid_observations = validator.validate_batch(
            observations,
            sheet_name,
            skip_metric_key_check=skip_metric_check
        )
        
        print(f"  ✓ 验证完成: {len(valid_observations)} 条有效观测值")
        
        # 4. 先导入到独立表（模拟新架构）
        if table_config:
            table_name = sheet_config.get("table_name") or table_config.get("table_name")
            column_mapping = table_config.get("column_mapping", {})
            unique_key = table_config.get("unique_key", [])
            
            if not table_name:
                print(f"  ⚠️  table_name为空，跳过独立表导入")
                table_config = None
            
            print(f"\n  {'='*80}")
            print(f"  步骤1: 导入到独立表 {table_name}")
            print(f"  {'='*80}")
            
            # 转换数据
            mapper = ColumnMapper()
            records = mapper.map_observations_to_table_records(
                observations=valid_observations,
                column_mapping=column_mapping,
                table_name=table_name,
                batch_id=batch.id,
                sheet_config=sheet_config
            )
            
            print(f"    转换后记录数: {len(records)} 条")
            
            # 导入到表
            importer = SheetTableImporter(db)
            import_result = importer.import_to_table(
                table_name=table_name,
                records=records,
                unique_key=unique_key
            )
            
            inserted = import_result.get("inserted", 0)
            updated = import_result.get("updated", 0)
            errors = import_result.get("errors", 0)
            
            print(f"    独立表导入结果: 插入={inserted}, 更新={updated}, 错误={errors}")
            
            # 提交独立表的导入
            db.commit()
            print(f"    ✓ 独立表导入已提交")
        
        # 5. 再调用upsert_observations（模拟新架构的第二步）
        print(f"\n  {'='*80}")
        print(f"  步骤2: 导入到fact_observation")
        print(f"  {'='*80}")
        
        # 注意：这里使用原始的valid_observations，而不是records
        # 因为upsert_observations需要ObservationDict格式，而不是表记录格式
        
        upsert_result = upsert_observations(
            db=db,
            observations=valid_observations,
            batch_id=batch.id,
            sheet_name=sheet_name
        )
        
        obs_inserted = upsert_result.get("inserted", 0)
        obs_updated = upsert_result.get("updated", 0)
        obs_errors = upsert_result.get("errors", 0)
        
        print(f"    fact_observation导入结果: 插入={obs_inserted}, 更新={obs_updated}, 错误={obs_errors}")
        
        # 6. 显示最终结果
        print(f"\n  {'='*80}")
        print(f"  最终结果")
        print(f"  {'='*80}")
        if table_config:
            print(f"    独立表 ({table_name}): 插入={inserted}, 更新={updated}, 错误={errors}")
        print(f"    fact_observation: 插入={obs_inserted}, 更新={obs_updated}, 错误={obs_errors}")
        
        if obs_errors > 0:
            print(f"\n  ⚠️  fact_observation有 {obs_errors} 条错误")
            print(f"  请查看上方的详细错误日志")
        else:
            print(f"\n  ✅ 所有记录都成功处理！")
        
        print(f"\n  {'='*80}")
        print(f"  测试完成")
        print(f"  {'='*80}")
        
    except Exception as e:
        db.rollback()
        print(f"\n  ❌ 测试失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(f"  详细堆栈:\n{traceback.format_exc()}", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    # 查找测试文件
    project_root = Path(__file__).parent.parent.parent
    docs_dir = project_root / "docs"
    
    weekly_files = list(docs_dir.glob("*涌益咨询*周度数据*.xlsx"))
    
    if not weekly_files:
        print("❌ 未找到周度数据文件")
        sys.exit(1)
    
    file_path = str(weekly_files[0])
    print(f"使用文件: {file_path}\n")
    
    # 测试前100条数据
    import sys
    limit = 100
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
    
    test_after_table_import(file_path, sheet_name="周度-体重", limit=limit)
