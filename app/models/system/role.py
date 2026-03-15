"""
角色模型
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.system.user import User
    from app.models.system.menu import Menu


# 用户角色关联表（使用 Table，不需要额外字段）
user_role = Table(
    "sys_user_role",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), index=True, comment="用户ID"),
    Column("role_id", Integer, ForeignKey("sys_role.id", ondelete="CASCADE"), index=True, comment="角色ID"),
)

# 角色菜单关联表（使用 Table，不需要额外字段）
role_menu = Table(
    "sys_role_menu",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("role_id", Integer, ForeignKey("sys_role.id", ondelete="CASCADE"), index=True, comment="角色ID"),
    Column("menu_id", Integer, ForeignKey("sys_menu.id", ondelete="CASCADE"), index=True, comment="菜单ID"),
)


class Role(BaseModel):
    """角色表"""

    __tablename__ = "sys_role"

    name: Mapped[str] = mapped_column(String(50), unique=True, comment="角色名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="角色编码")
    desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-禁用, 1-启用")

    # 关联用户
    users: Mapped[List["User"]] = relationship(
        "User", secondary=user_role, back_populates="roles"
    )
    # 关联菜单
    menus: Mapped[List["Menu"]] = relationship(
        "Menu", secondary=role_menu, back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
