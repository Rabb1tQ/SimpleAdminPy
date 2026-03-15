"""
租户相关 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """租户基础模型"""

    name: str = Field(..., min_length=2, max_length=100, description="租户名称")
    code: str = Field(..., min_length=2, max_length=50, description="租户编码")
    contact: Optional[str] = Field(None, max_length=50, description="联系人")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, max_length=255, description="地址")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0-禁用, 1-启用")
    expire_at: Optional[datetime] = Field(None, description="过期时间")
    remark: Optional[str] = Field(None, description="备注")


class TenantCreate(TenantBase):
    """创建租户"""

    pass


class TenantUpdate(BaseModel):
    """更新租户"""

    name: Optional[str] = Field(None, min_length=2, max_length=100, description="租户名称")
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="租户编码")
    contact: Optional[str] = Field(None, max_length=50, description="联系人")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, max_length=255, description="地址")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态: 0-禁用, 1-启用")
    expire_at: Optional[datetime] = Field(None, description="过期时间")
    remark: Optional[str] = Field(None, description="备注")


class TenantResponse(TenantBase):
    """租户响应"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    """租户列表响应"""

    id: int
    name: str
    code: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: int
    expire_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TenantSelectResponse(BaseModel):
    """租户下拉选择响应"""

    id: int
    name: str
    code: str
    status: int

    class Config:
        from_attributes = True
