"""Load ingest_profile configs to database"""
import sys
import os
import io

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.services.ingestors.profile_loader import load_profile_from_json
from pathlib import Path


def load_all_profiles():
    """Load all profile configs"""
    db = SessionLocal()
    try:
        # Get config files from docs directory (project root)
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent  # backend -> project root
        docs_dir = project_root / 'docs'
        
        profiles = [
            'ingest_profile_yongyi_daily_v1.json',
            'ingest_profile_yongyi_weekly_v1.json'
        ]
        
        for profile_file in profiles:
            json_path = docs_dir / profile_file
            if json_path.exists():
                print(f"Loading config: {profile_file}")
                try:
                    profile = load_profile_from_json(db, str(json_path))
                    print(f"  [OK] Loaded: {profile.profile_code} ({len(profile.sheets)} sheets)")
                except Exception as e:
                    print(f"  [ERROR] Failed: {e}")
            else:
                print(f"  [WARN] File not found: {json_path}")
        
        print("Config loading completed")
        
    except Exception as e:
        db.rollback()
        print(f"Loading failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    load_all_profiles()
