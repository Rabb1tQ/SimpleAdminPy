"""
日志模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class OperationLog(BaseModel):
    """操作日志表"""

    __tablename__ = "sys_operation_log"

    user_id: Mapped[int] = mapped_column(Integer, index=True, comment="操作用户ID")
    username: Mapped[str] = mapped_column(String(50), comment="操作用户名")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="租户ID")
    module: Mapped[str] = mapped_column(String(50), comment="操作模块")
    action: Mapped[str] = mapped_column(String(100), comment="操作动作")
    method: Mapped[str] = mapped_column(String(10), comment="请求方法")
    url: Mapped[str] = mapped_column(String(255), comment="请求URL")
    ip: Mapped[str] = mapped_column(String(50), comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="用户代理")
    request_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="请求数据")
    response_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="响应数据")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-失败, 1-成功")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    duration: Mapped[int] = mapped_column(Integer, default=0, comment="执行时长(ms)")

    def __repr__(self) -> str:
        return f"<OperationLog {self.module} - {self.action}>"


class LoginLog(BaseModel):
    """登录日志表"""

    __tablename__ = "sys_login_log"

    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), comment="用户名")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="租户ID")
    ip: Mapped[str] = mapped_column(String(50), comment="登录IP")
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="登录地点")
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="浏览器")
    os: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="操作系统")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-失败, 1-成功")
    msg: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="提示消息")
    login_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="登录时间"
    )

    def __repr__(self) -> str:
        return f"<LoginLog {self.username} - {self.ip}>"
