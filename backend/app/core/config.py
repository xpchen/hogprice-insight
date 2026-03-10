from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

# 加载.env文件
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)  # override 确保 .env 覆盖已有环境变量


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/hogprice_v3?charset=utf8mb4"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30天
    
    # 应用配置
    PROJECT_NAME: str = "HogPrice Insight API"
    API_V1_STR: str = "/api"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:8080", "http://localhost:5173"]

    # 快速图表预计算：内部请求携带此 header 时以首名用户身份访问（仅本地使用）
    QUICK_CHART_INTERNAL_SECRET: Optional[str] = None
    # 预计算单次请求超时（秒），农历等计算较久时可调大，默认 15 分钟
    QUICK_CHART_PRECOMPUTE_TIMEOUT: float = 900.0
    # 审计对账时暂时禁用图表缓存，保证拿到真实数据库结果。.env 中设置 DISABLE_CHART_CACHE=true 禁用
    DISABLE_CHART_CACHE: bool = False
    # 预计算请求的 base URL（默认本机）
    BACKEND_BASE_URL: str = "http://127.0.0.1:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
