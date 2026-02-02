"""
初始化8套预设模板的脚本
运行方式：python -m app.api.init_templates
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import SessionLocal
from app.services.template_service import init_templates_to_db


def main():
    """初始化预设模板"""
    import sys
    import io
    # 设置UTF-8编码输出
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    db = SessionLocal()
    try:
        print("Starting to initialize 8 preset templates...")
        init_templates_to_db(db)
        print("Success: Preset templates initialized!")
    except Exception as e:
        print(f"Error: Initialization failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
