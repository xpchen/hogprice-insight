"""直接测试冻品库存导入"""
import sys
import os
import io
from pathlib import Path

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.sys_user import SysUser
from app.services.ingestors.unified_ingestor import unified_import
from app.services.ingestors.dispatcher import Dispatcher
from app.services.ingestors.parsers import get_parser
from app.services.ingestors.profile_loader import get_profile_by_dataset_type
from app.models.import_batch import ImportBatch
from app.models.raw_sheet import RawSheet
from app.services.ingestors.raw_writer import save_raw_file
from app.services.ingestors.observation_upserter import upsert_observations
from app.services.ingestors.validator import ObservationValidator
from app.services.ingestors.error_collector import ErrorCollector
from openpyxl import load_workbook
import hashlib

# 项目根目录
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent

def main():
    sheet_name = "周度-冻品库存"
    file_path = project_root / "docs" / "2026.1.16-2026.1.22涌益咨询 周度数据.xlsx"
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    db = SessionLocal()
    try:
        # 获取用户
        user = db.query(SysUser).filter(SysUser.username == "admin").first()
        if not user:
            print("❌ 未找到admin用户")
            return
        
        # 加载profile
        profile = get_profile_by_dataset_type(db, "YONGYI_WEEKLY")
        if not profile:
            print("❌ 未找到profile")
            return
        
        print(f"📋 测试Sheet: {sheet_name}")
        
        # 创建Dispatcher
        dispatcher = Dispatcher(db, profile)
        wb = load_workbook(file_path, data_only=True)
        ws = wb[sheet_name]
        
        # 分派
        dispatch_result = dispatcher.dispatch_sheet(sheet_name, worksheet=ws)
        sheet_config = dispatch_result.get('sheet_config', {})
        parser_name = dispatch_result.get('parser')
        
        if not parser_name:
            print(f"❌ 未匹配到parser")
            return
        
        print(f"✓ Parser: {parser_name}")
        
        # 解析
        parser = get_parser(parser_name)
        observations = parser.parse(
            sheet_data=ws,
            sheet_config=sheet_config,
            profile_defaults=profile.defaults_json or {},
            source_code=profile.source_code,
            batch_id=0
        )
        
        print(f"✓ 解析出 {len(observations)} 条数据")
        
        if len(observations) == 0:
            print("⚠️  没有数据可导入")
            return
        
        # 创建批次
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        file_hash = hashlib.sha256(file_content).hexdigest()
        batch = ImportBatch(
            filename=file_path.name,
            file_hash=file_hash,
            uploader_id=user.id,
            source_code=profile.source_code or profile.dataset_type,
            status="processing",
            total_rows=0,
            success_rows=0,
            failed_rows=0
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        print(f"✓ 创建批次: ID={batch.id}")
        
        # 验证
        error_collector = ErrorCollector(db, batch.id)
        validator = ObservationValidator(error_collector)
        valid_observations = validator.validate_batch(
            observations,
            sheet_name,
            skip_metric_key_check=False
        )
        
        print(f"✓ 验证通过: {len(valid_observations)} 条")
        
        # 保存raw_file和raw_sheet
        raw_file = save_raw_file(
            db=db,
            batch_id=batch.id,
            filename=file_path.name,
            file_content=file_content
        )
        raw_sheet = RawSheet(
            raw_file_id=raw_file.id,
            sheet_name=sheet_name,
            parse_status="parsed",
            parser_type=parser_name,
            observation_count=len(valid_observations)
        )
        db.add(raw_sheet)
        db.commit()
        
        # 更新batch_id
        for obs in valid_observations:
            obs['batch_id'] = batch.id
        
        # 导入
        print("🚀 开始导入...")
        result = upsert_observations(
            db=db,
            observations=valid_observations,
            batch_id=batch.id,
            sheet_name=sheet_name
        )
        
        batch.status = "completed"
        db.commit()
        
        print(f"✅ 导入完成!")
        print(f"   - 插入: {result.get('inserted', 0)} 条")
        print(f"   - 更新: {result.get('updated', 0)} 条")
        print(f"   - 错误: {result.get('errors', 0)} 条")
        
        wb.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
