"""管理员用户管理（仅 admin 可访问）"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import check_user_role, get_current_user, get_password_hash
from app.models.sys_role import SysRole
from app.models.sys_user import SysUser
from app.models.sys_user_role import SysUserRole

router = APIRouter(prefix=f"{settings.API_V1_STR}/admin", tags=["admin-users"])


def _require_admin(current_user: SysUser, db: Session) -> None:
    if not check_user_role(current_user, ["admin"], db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )


class RoleOut(BaseModel):
    id: int
    code: str
    name: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    is_active: bool
    roles: List[str]
    created_at: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=64)
    role_codes: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None
    role_codes: Optional[List[str]] = None


def _user_roles_codes(db: Session, user_id: int) -> List[str]:
    rows = (
        db.query(SysRole.code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .filter(SysUserRole.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


def _count_active_admins(db: Session) -> int:
    admin_role = db.query(SysRole).filter(SysRole.code == "admin").first()
    if not admin_role:
        return 0
    return (
        db.query(SysUser)
        .join(SysUserRole, SysUserRole.user_id == SysUser.id)
        .filter(
            SysUserRole.role_id == admin_role.id,
            SysUser.is_active == True,
        )
        .count()
    )


@router.get("/roles", response_model=List[RoleOut])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _require_admin(current_user, db)
    roles = db.query(SysRole).order_by(SysRole.id).all()
    return [RoleOut(id=r.id, code=r.code, name=r.name) for r in roles]


@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _require_admin(current_user, db)
    users = db.query(SysUser).order_by(SysUser.id).all()
    out: List[UserOut] = []
    for u in users:
        out.append(
            UserOut(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                is_active=u.is_active,
                roles=_user_roles_codes(db, u.id),
                created_at=u.created_at.isoformat() if u.created_at else "",
            )
        )
    return out


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _require_admin(current_user, db)
    if db.query(SysUser).filter(SysUser.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    role_rows = []
    for code in body.role_codes:
        r = db.query(SysRole).filter(SysRole.code == code).first()
        if not r:
            raise HTTPException(status_code=400, detail=f"未知角色: {code}")
        role_rows.append(r)

    user = SysUser(
        username=body.username,
        password_hash=get_password_hash(body.password),
        display_name=body.display_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    for r in role_rows:
        db.add(SysUserRole(user_id=user.id, role_id=r.id))
    db.commit()
    db.refresh(user)

    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=_user_roles_codes(db, user.id),
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _require_admin(current_user, db)
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.is_active is False and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能停用当前登录账号")

    before_roles = set(_user_roles_codes(db, user.id))

    if body.role_codes is not None:
        role_rows = []
        for code in body.role_codes:
            r = db.query(SysRole).filter(SysRole.code == code).first()
            if not r:
                raise HTTPException(status_code=400, detail=f"未知角色: {code}")
            role_rows.append(r)

        if "admin" in before_roles and "admin" not in set(body.role_codes):
            if _count_active_admins(db) <= 1 and user.is_active:
                raise HTTPException(status_code=400, detail="不能移除最后一个活跃管理员的角色")

        db.query(SysUserRole).filter(SysUserRole.user_id == user.id).delete()
        for r in role_rows:
            db.add(SysUserRole(user_id=user.id, role_id=r.id))

    if body.is_active is False and "admin" in before_roles:
        if _count_active_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="不能停用最后一个活跃管理员")

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    db.refresh(user)

    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=_user_roles_codes(db, user.id),
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


class AdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    body: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _require_admin(current_user, db)
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"message": "密码已更新"}
