from datetime import timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, get_password_hash
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models.sys_role import SysRole
from app.models.sys_user_role import SysUserRole

router = APIRouter(prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    roles: List[str]
    
    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """登录接口"""
    # 查询用户
    user = db.query(SysUser).filter(SysUser.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    # 创建token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户信息"""
    # 获取用户角色
    roles = db.query(SysRole.code).join(
        SysUserRole, SysUserRole.role_id == SysRole.id
    ).filter(SysUserRole.user_id == current_user.id).all()
    
    role_codes = [role[0] for role in roles]
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "roles": role_codes
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户修改自己的密码"""
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与旧密码相同",
        )

    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码长度至少为6位",
        )

    current_user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"message": "密码修改成功"}
