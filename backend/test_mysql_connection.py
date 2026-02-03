"""
测试MySQL连接脚本
用于诊断数据库连接问题
"""
import sys
import pymysql
import re
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.config import settings
except Exception as e:
    print(f"ERROR: Cannot import settings: {e}")
    sys.exit(1)

def test_connection():
    """测试MySQL连接"""
    url = settings.DATABASE_URL
    print("=" * 60)
    print("MySQL Connection Test")
    print("=" * 60)
    print(f"Database URL: {url}")
    print()
    
    # 解析URL
    match = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)', url)
    if not match:
        print("ERROR: Cannot parse DATABASE_URL")
        print("Expected format: mysql+pymysql://user:password@host:port/database")
        return False
    
    user, password, host, port, database = match.groups()
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"Password: {'*' * len(password)}")
    print(f"Database: {database}")
    print()
    
    # 测试1: 检查pymysql是否安装
    print("[Test 1] Checking pymysql installation...")
    try:
        import pymysql
        print("OK: pymysql is installed")
    except ImportError:
        print("ERROR: pymysql is not installed")
        print("Please run: pip install pymysql")
        return False
    print()
    
    # 测试2: 尝试连接到MySQL服务器（不指定数据库）
    print("[Test 2] Testing connection to MySQL server...")
    try:
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            charset='utf8mb4',
            connect_timeout=5
        )
        print("OK: Successfully connected to MySQL server")
        
        # 测试3: 检查数据库是否存在
        print()
        print("[Test 3] Checking if database exists...")
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE %s", (database,))
        result = cursor.fetchone()
        
        if result:
            print(f"OK: Database '{database}' already exists")
        else:
            print(f"INFO: Database '{database}' does not exist (will be created)")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 60)
        print("All tests passed! You can proceed with database creation.")
        print("=" * 60)
        return True
        
    except pymysql.Error as e:
        print(f"ERROR: MySQL error occurred")
        print(f"Error code: {e.args[0]}")
        print(f"Error message: {e.args[1]}")
        print()
        print("Possible solutions:")
        print("1. Check if MySQL service is running")
        print("2. Verify username and password are correct")
        print("3. Check if MySQL is listening on port", port)
        print("4. Check firewall settings")
        return False
        
    except Exception as e:
        print(f"ERROR: Connection failed: {type(e).__name__}: {e}")
        print()
        print("Possible solutions:")
        print("1. Check if MySQL service is running")
        print("2. Verify host and port are correct")
        print("3. Check network connectivity")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
