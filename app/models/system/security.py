"""
安全配置相关模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, SmallInteger, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SecurityConfig(BaseModel):
    """安全配置表"""
    __tablename__ = "sys_security_config"

    config_key: Mapped[str] = mapped_column(String(50), unique=True, comment="配置键")
    config_value: Mapped[str] = mapped_column(Text, comment="配置值")
    config_type: Mapped[str] = mapped_column(String(20), default="STRING", comment="值类型: STRING, NUMBER, BOOLEAN, JSON")
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="配置分组")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="配置说明")


class IpRule(BaseModel):
    """IP黑白名单表"""
    __tablename__ = "sys_ip_rule"

    ip_address: Mapped[str] = mapped_column(String(50), index=True, comment="IP地址或IP段")
    rule_type: Mapped[str] = mapped_column(String(10), index=True, comment="规则类型: WHITELIST, BLACKLIST")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="备注说明")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态: 0-禁用, 1-启用")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="创建者ID")
