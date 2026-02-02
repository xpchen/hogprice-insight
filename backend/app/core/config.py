from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# 加载.env文件
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/hogprice?charset=utf8mb4"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30天
    
    # 应用配置
    PROJECT_NAME: str = "HogPrice Insight API"
    API_V1_STR: str = "/api"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:8080", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
