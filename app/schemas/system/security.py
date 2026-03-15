"""
安全配置相关Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 安全配置 ====================

class SecurityConfigBase(BaseModel):
    """安全配置基类"""
    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    config_type: str = Field(default="STRING", description="值类型: STRING, NUMBER, BOOLEAN, JSON")
    group_name: Optional[str] = Field(None, description="配置分组")
    description: Optional[str] = Field(None, description="配置说明")


class SecurityConfigCreate(BaseModel):
    """创建安全配置"""
    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    config_type: str = Field(default="STRING", description="值类型")
    group_name: Optional[str] = Field(None, description="配置分组")
    description: Optional[str] = Field(None, description="配置说明")


class SecurityConfigUpdate(BaseModel):
    """更新安全配置"""
    config_value: str = Field(..., description="配置值")


class SecurityConfigBatchUpdate(BaseModel):
    """批量更新安全配置"""
    configs: List[dict] = Field(..., description="配置列表")


class SecurityConfigResponse(SecurityConfigBase):
    """安全配置响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== IP规则 ====================

class IpRuleBase(BaseModel):
    """IP规则基类"""
    ip_address: str = Field(..., description="IP地址或IP段")
    rule_type: str = Field(..., description="规则类型: WHITELIST, BLACKLIST")
    description: Optional[str] = Field(None, description="备注说明")


class IpRuleCreate(IpRuleBase):
    """创建IP规则"""
    pass


class IpRuleUpdate(BaseModel):
    """更新IP规则"""
    description: Optional[str] = Field(None, description="备注说明")
    status: Optional[int] = Field(None, description="状态")


class IpRuleStatusUpdate(BaseModel):
    """更新IP规则状态"""
    status: int = Field(..., description="状态: 0-禁用, 1-启用")


class IpRuleResponse(IpRuleBase):
    """IP规则响应"""
    id: int
    status: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IpRuleListResponse(BaseModel):
    """IP规则列表响应"""
    list: List[IpRuleResponse]
    total: int


# ==================== 锁定用户 ====================

class LockedUserResponse(BaseModel):
    """锁定用户响应"""
    user_id: int
    username: str
    real_name: Optional[str]
    locked_at: datetime
    fail_count: int
    unlock_at: Optional[datetime]

    class Config:
        from_attributes = True


class LockedUserListResponse(BaseModel):
    """锁定用户列表响应"""
    list: List[LockedUserResponse]
    total: int


# ==================== 登录失败信息 ====================

class LoginFailInfo(BaseModel):
    """登录失败信息"""
    fail_count: int = Field(default=0, description="失败次数")
    locked_until: Optional[datetime] = Field(None, description="锁定到期时间")
    is_locked: bool = Field(default=False, description="是否锁定")
