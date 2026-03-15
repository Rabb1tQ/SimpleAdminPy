"""
用户模型
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.system.role import user_role

if TYPE_CHECKING:
    from app.models.system.role import Role


class User(BaseModel):
    """用户表"""

    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), comment="密码")
    real_name: Mapped[str] = mapped_column(String(50), comment="真实姓名")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="头像")
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="邮箱")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="手机号")
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    home_path: Mapped[str] = mapped_column(String(255), default="/dashboard", comment="首页路径")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-禁用, 1-启用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否超级管理员")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="租户ID")
    last_login_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最后登录时间"
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="最后登录IP"
    )

    # 关联角色
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=user_role, back_populates="users"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"
