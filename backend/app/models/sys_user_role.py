from sqlalchemy import Column, BigInteger, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class SysUserRole(Base):
    __tablename__ = "sys_user_role"

    user_id = Column(BigInteger, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(BigInteger, ForeignKey("sys_role.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "role_id"),
    )

    user = relationship("SysUser", backref="user_roles")
    role = relationship("SysRole", backref="role_users")
