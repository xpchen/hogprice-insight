from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.sys_user import SysUser

# OAuth2PasswordBearer的tokenUrl用于Swagger UI的OAuth2认证
# 实际的登录接口不需要token认证
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False  # 允许没有token的请求通过，由各个端点自己决定是否需要认证
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """生成密码hash"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_token_from_query_or_header(request: Request) -> Optional[str]:
    """从 query 参数 token 或 Authorization header 获取 token（用于 EventSource 等无法传 header 的场景）"""
    token = request.query_params.get("token")
    if token:
        return token
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> SysUser:
    """获取当前用户。快速图表预计算可携带 X-Quick-Chart-Secret 以系统用户访问。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    secret = getattr(settings, "QUICK_CHART_INTERNAL_SECRET", None)
    if secret and request.headers.get("X-Quick-Chart-Secret") == secret:
        user = db.query(SysUser).filter(SysUser.is_active == True).order_by(SysUser.id).first()
        if user:
            return user
    if token is None:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(SysUser).filter(SysUser.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return user


async def get_current_user_from_request(request: Request, db: Session = Depends(get_db)) -> SysUser:
    """从 Request 的 query param token 或 Authorization header 获取当前用户（用于 SSE 等）"""
    token = await get_token_from_query_or_header(request)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(SysUser).filter(SysUser.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user


def check_user_role(user: SysUser, allowed_roles: List[str], db: Session) -> bool:
    """
    检查用户是否有指定角色
    
    通过sys_user_role关联表查询用户的角色
    
    Args:
        user: 用户对象
        allowed_roles: 允许的角色列表（角色code，如 ['admin', 'analyst']）
        db: 数据库会话
    
    Returns:
        bool: 是否有权限
    """
    from app.models.sys_user_role import SysUserRole
    from app.models.sys_role import SysRole
    
    # 查询用户的所有角色
    user_roles = db.query(SysRole.code).join(
        SysUserRole, SysRole.id == SysUserRole.role_id
    ).filter(
        SysUserRole.user_id == user.id
    ).all()
    
    # 提取角色code列表
    user_role_codes = [role[0] for role in user_roles]
    
    # 检查是否有任一允许的角色
    for allowed_role in allowed_roles:
        if allowed_role in user_role_codes:
            return True
    
    # admin角色自动拥有所有权限
    if "admin" in user_role_codes:
        return True
    
    return False


def require_role(*allowed_roles: str):
    """
    角色权限检查依赖函数（FastAPI风格）
    
    Usage:
        @router.post("/import")
        async def import_data(
            current_user: SysUser = Depends(get_current_user),
            role_check: bool = Depends(lambda u=Depends(get_current_user), db=Depends(get_db): require_role("analyst", "admin")(u, db))
        ):
            ...
    """
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user和db
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not db:
                # 尝试从依赖注入获取
                from app.core.database import get_db
                db_gen = get_db()
                db = next(db_gen)
            
            if not check_user_role(current_user, list(allowed_roles), db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
