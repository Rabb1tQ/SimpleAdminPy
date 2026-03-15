"""
消息相关Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    """消息基础模型"""
    title: str = Field(..., max_length=200, description="消息标题")
    content: Optional[str] = Field(None, description="消息内容")
    type: str = Field(..., max_length=20, description="消息类型: SYSTEM, BUSINESS")


class MessageCreate(MessageBase):
    """创建消息"""
    pass


class MessageResponse(MessageBase):
    """消息响应"""
    id: int
    sender_id: Optional[int] = None
    sender_tenant_id: Optional[int] = None
    receiver_id: int
    is_read: int = 0
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """消息列表响应"""
    items: List[MessageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    """未读消息数量响应"""
    count: int


class MessageSend(BaseModel):
    """发送消息请求"""
    title: str = Field(..., max_length=200, description="消息标题")
    content: Optional[str] = Field(None, description="消息内容")
    type: str = Field(..., max_length=20, description="消息类型: SYSTEM, BUSINESS")
    receiver_type: str = Field(..., max_length=20, description="接收对象类型: ALL, TENANT, ROLE, USER")
    receiver_ids: List[int] = Field(default=[], description="接收对象ID列表")


class MessageSendResponse(BaseModel):
    """发送消息响应"""
    send_count: int


class MessageSendLogResponse(BaseModel):
    """发送记录响应"""
    id: int
    title: str
    content: Optional[str] = None
    type: str
    sender_id: Optional[int] = None
    sender_tenant_id: Optional[int] = None
    receiver_type: str
    receiver_ids: Optional[str] = None
    send_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageSendLogListResponse(BaseModel):
    """发送记录列表响应"""
    items: List[MessageSendLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
