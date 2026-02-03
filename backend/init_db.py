"""
数据库初始化脚本
用于创建数据库（如果使用本地MySQL而非Docker）
"""
import pymysql
from app.core.config import settings
import re
import sys
import traceback

def create_database():
    """创建数据库"""
    # 从DATABASE_URL中提取连接信息
    # mysql+pymysql://root:root@localhost:3306/hogprice?charset=utf8mb4
    url = settings.DATABASE_URL
    print(f"Database URL: {url}")
    
    # 解析URL
    match = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)', url)
    if not match:
        print("ERROR: Cannot parse DATABASE_URL")
        print(f"URL format: mysql+pymysql://user:password@host:port/database")
        return False
    
    user, password, host, port, database = match.groups()
    print(f"Connecting to MySQL server: {host}:{port}")
    print(f"User: {user}")
    print(f"Database: {database}")
    
    # 连接到MySQL服务器（不指定数据库）
    try:
        print("Attempting to connect...")
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            charset='utf8mb4'
        )
        print("Connection successful!")
        
        cursor = conn.cursor()
        
        # 创建数据库
        print(f"Creating database {database}...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database {database} created successfully (if not exists)")
        
        cursor.close()
        conn.close()
        return True
        
    except pymysql.Error as e:
        print(f"ERROR: MySQL error occurred: {e}")
        print(f"Error code: {e.args[0]}")
        print(f"Error message: {e.args[1]}")
        print("\nPlease manually create the database:")
        print(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        print("\nPlease check:")
        print("1. Is MySQL service running?")
        print("2. Are username and password correct? (root/root)")
        print("3. Is network connection normal?")
        print("4. Is MySQL port 3306 accessible?")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)
