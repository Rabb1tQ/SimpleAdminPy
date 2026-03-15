"""
日志相关 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ============ 操作日志 ============

class LogResponse(BaseModel):
    """操作日志响应"""

    id: int
    user_id: int
    username: str
    module: str
    action: str
    method: str
    url: str
    ip: str
    user_agent: Optional[str] = None
    status: int
    error_msg: Optional[str] = None
    duration: int
    created_at: datetime

    class Config:
        from_attributes = True


class LogListResponse(BaseModel):
    """操作日志列表响应"""

    id: int
    user_id: int
    username: str
    module: str
    action: str
    method: str
    url: str
    ip: str
    status: int
    duration: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 登录日志 ============

class LoginLogResponse(BaseModel):
    """登录日志响应"""

    id: int
    user_id: Optional[int] = None
    username: str
    ip: str
    status: int
    msg: Optional[str] = None
    login_time: datetime

    class Config:
        from_attributes = True


class LoginLogListResponse(BaseModel):
    """登录日志列表响应"""

    id: int
    user_id: Optional[int] = None
    username: str
    ip: str
    status: int
    msg: Optional[str] = None
    login_time: datetime

    class Config:
        from_attributes = True
