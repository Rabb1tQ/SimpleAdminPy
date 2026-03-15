"""
菜单模型
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.system.role import role_menu

if TYPE_CHECKING:
    from app.models.system.role import Role


class Menu(BaseModel):
    """菜单表"""

    __tablename__ = "sys_menu"

    parent_id: Mapped[int] = mapped_column(Integer, default=0, comment="父菜单ID")
    name: Mapped[str] = mapped_column(String(50), comment="路由名称")
    path: Mapped[str] = mapped_column(String(255), comment="路由路径")
    component: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="组件路径")
    title: Mapped[str] = mapped_column(String(50), comment="菜单标题")
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="图标")
    sort: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-禁用, 1-启用")
    hide_in_menu: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否隐藏菜单")
    keep_alive: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否缓存页面")
    permission: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="权限标识")
    menu_type: Mapped[int] = mapped_column(Integer, default=1, comment="类型: 1-目录, 2-菜单, 3-按钮")

    # 关联角色
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=role_menu, back_populates="menus"
    )

    def __repr__(self) -> str:
        return f"<Menu {self.title}>"

    def to_route_dict(self) -> dict:
        """转换为路由格式（前端需要的格式）"""
        return {
            "id": self.id,
            "parentId": self.parent_id if self.parent_id != 0 else None,
            "name": self.name,
            "path": self.path,
            "component": self.component,
            "meta": {
                "title": self.title,
                "icon": self.icon,
                "hideInMenu": self.hide_in_menu,
                "keepAlive": self.keep_alive,
                "order": self.sort,
            },
        }
