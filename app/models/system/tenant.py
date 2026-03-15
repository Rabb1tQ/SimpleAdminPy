"""
租户模型
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Tenant(BaseModel):
    """租户表"""

    __tablename__ = "sys_tenant"

    name: Mapped[str] = mapped_column(String(100), comment="租户名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="租户编码")
    contact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="联系人")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="联系电话")
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="邮箱")
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="地址")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-禁用, 1-启用")
    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="过期时间")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")

    def __repr__(self) -> str:
        return f"<Tenant {self.name}>"
