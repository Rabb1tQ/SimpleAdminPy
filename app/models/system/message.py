"""
消息模型
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Message(BaseModel):
    """消息表"""
    __tablename__ = "sys_message"

    title: Mapped[str] = mapped_column(String(200), comment="消息标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="消息内容")
    type: Mapped[str] = mapped_column(String(20), comment="消息类型: SYSTEM, BUSINESS")
    sender_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="发送者ID")
    sender_tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="发送者租户ID")
    receiver_id: Mapped[int] = mapped_column(Integer, index=True, comment="接收者ID")
    is_read: Mapped[int] = mapped_column(SmallInteger, default=0, comment="是否已读: 0-未读, 1-已读")
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="阅读时间")


class MessageSendLog(BaseModel):
    """消息发送记录表"""
    __tablename__ = "sys_message_send_log"

    title: Mapped[str] = mapped_column(String(200), comment="消息标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="消息内容")
    type: Mapped[str] = mapped_column(String(20), comment="消息类型: SYSTEM, BUSINESS")
    sender_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="发送者ID")
    sender_tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="发送者租户ID")
    receiver_type: Mapped[str] = mapped_column(String(20), comment="接收对象类型: ALL, TENANT, ROLE, USER")
    receiver_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="接收对象ID列表(JSON)")
    send_count: Mapped[int] = mapped_column(Integer, default=0, comment="发送数量")
