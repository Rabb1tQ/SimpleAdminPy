"""
用户相关 Schema
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    real_name: str = Field(..., min_length=2, max_length=50, description="真实姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    desc: Optional[str] = Field(None, description="描述")
    avatar: Optional[str] = Field(None, max_length=255, description="头像")
    home_path: str = Field(default="/dashboard", max_length=255, description="首页路径")


class UserCreate(UserBase):
    """创建用户"""

    password: str = Field(..., min_length=6, max_length=50, description="密码")
    role_ids: List[int] = Field(default=[], description="角色ID列表")
    tenant_id: Optional[int] = Field(None, description="租户ID（仅超管可设置）")


class UserUpdate(BaseModel):
    """更新用户"""

    real_name: Optional[str] = Field(None, min_length=2, max_length=50, description="真实姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    desc: Optional[str] = Field(None, description="描述")
    avatar: Optional[str] = Field(None, max_length=255, description="头像")
    home_path: Optional[str] = Field(None, max_length=255, description="首页路径")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    role_ids: Optional[List[int]] = Field(None, description="角色ID列表")
    tenant_id: Optional[int] = Field(None, description="租户ID（仅超管可设置）")


class UserResponse(UserBase):
    """用户响应"""

    id: int
    status: int = Field(description="状态: 0-禁用, 1-启用")
    is_superuser: bool = Field(description="是否超级管理员")
    tenant_id: Optional[int] = Field(None, description="租户ID")
    roles: List[str] = Field(default=[], description="角色编码列表")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInfoResponse(BaseModel):
    """用户信息响应（前端需要的格式）"""

    userId: str = Field(alias="userId")
    username: str
    realName: str
    avatar: Optional[str] = None
    roles: List[str] = []
    desc: Optional[str] = None
    homePath: str = "/dashboard"

    class Config:
        populate_by_name = True


class UserListResponse(BaseModel):
    """用户列表响应"""

    id: int
    username: str
    real_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: int
    is_superuser: bool
    tenant_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResetPassword(BaseModel):
    """重置密码"""

    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class ChangePassword(BaseModel):
    """修改密码"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class ProfileUpdate(BaseModel):
    """更新个人信息"""

    real_name: Optional[str] = Field(None, min_length=2, max_length=50, description="真实姓名")
    email: Optional[EmailStr] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    desc: Optional[str] = Field(None, description="描述")
    home_path: Optional[str] = Field(None, max_length=255, description="首页路径")
