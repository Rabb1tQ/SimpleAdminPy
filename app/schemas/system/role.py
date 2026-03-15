"""
角色相关 Schema
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """角色基础模型"""

    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    code: str = Field(..., min_length=2, max_length=50, description="角色编码")
    desc: Optional[str] = Field(None, description="描述")


class RoleCreate(RoleBase):
    """创建角色"""

    menu_ids: List[int] = Field(default=[], description="菜单ID列表")


class RoleUpdate(BaseModel):
    """更新角色"""

    name: Optional[str] = Field(None, min_length=2, max_length=50, description="角色名称")
    desc: Optional[str] = Field(None, description="描述")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    menu_ids: Optional[List[int]] = Field(None, description="菜单ID列表")


class RoleResponse(RoleBase):
    """角色响应"""

    id: int
    status: int = Field(description="状态: 0-禁用, 1-启用")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """角色列表响应"""

    id: int
    name: str
    code: str
    desc: Optional[str] = None
    status: int
    created_at: datetime

    class Config:
        from_attributes = True


class RoleDetailResponse(RoleResponse):
    """角色详情响应"""

    menu_ids: List[int] = Field(default=[], description="菜单ID列表")
