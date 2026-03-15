"""
菜单相关 Schema
"""
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MenuMeta(BaseModel):
    """菜单元信息"""

    title: str = Field(description="菜单标题")
    icon: Optional[str] = Field(None, description="图标")
    hideInMenu: bool = Field(default=False, description="是否隐藏菜单")
    keepAlive: bool = Field(default=True, description="是否缓存页面")
    order: int = Field(default=0, description="排序")


class MenuBase(BaseModel):
    """菜单基础模型"""

    parent_id: int = Field(default=0, description="父菜单ID")
    name: str = Field(..., min_length=2, max_length=50, description="路由名称")
    path: str = Field(..., min_length=1, max_length=255, description="路由路径")
    component: Optional[str] = Field(None, max_length=255, description="组件路径")
    title: str = Field(..., min_length=1, max_length=50, description="菜单标题")
    icon: Optional[str] = Field(None, max_length=100, description="图标")
    sort: int = Field(default=0, description="排序")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0-禁用, 1-启用")
    hide_in_menu: bool = Field(default=False, description="是否隐藏菜单")
    keep_alive: bool = Field(default=True, description="是否缓存页面")
    permission: Optional[str] = Field(None, max_length=100, description="权限标识")
    menu_type: int = Field(default=1, ge=1, le=3, description="类型: 1-目录, 2-菜单, 3-按钮")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """验证路由路径必须以 / 开头"""
        if v and not v.startswith('/'):
            raise ValueError('路由路径必须以 "/" 开头')
        return v


class MenuCreate(MenuBase):
    """创建菜单"""


class MenuUpdate(BaseModel):
    """更新菜单"""

    parent_id: Optional[int] = Field(None, description="父菜单ID")
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="路由名称")
    path: Optional[str] = Field(None, min_length=1, max_length=255, description="路由路径")
    component: Optional[str] = Field(None, max_length=255, description="组件路径")
    title: Optional[str] = Field(None, min_length=1, max_length=50, description="菜单标题")
    icon: Optional[str] = Field(None, max_length=100, description="图标")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    hide_in_menu: Optional[bool] = Field(None, description="是否隐藏菜单")
    keep_alive: Optional[bool] = Field(None, description="是否缓存页面")
    permission: Optional[str] = Field(None, max_length=100, description="权限标识")
    menu_type: Optional[int] = Field(None, ge=1, le=3, description="类型")


class MenuResponse(MenuBase):
    """菜单响应"""

    id: int
    status: int = Field(description="状态: 0-禁用, 1-启用")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuTreeResponse(BaseModel):
    """菜单树响应（前端路由格式）"""

    id: int
    parentId: Optional[int] = None
    name: str
    path: str
    component: Optional[str] = None
    meta: MenuMeta
    children: Optional[List["MenuTreeResponse"]] = None

    class Config:
        from_attributes = False


class MenuListResponse(BaseModel):
    """菜单列表响应"""

    id: int
    parent_id: int
    name: str
    path: str
    component: Optional[str] = None
    title: str
    icon: Optional[str] = None
    sort: int
    status: int
    hide_in_menu: bool
    keep_alive: bool
    permission: Optional[str] = None
    menu_type: int
    created_at: datetime

    class Config:
        from_attributes = True
