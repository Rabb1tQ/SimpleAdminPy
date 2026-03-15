"""
基础响应模型
"""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """统一响应模型"""

    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PageModel(BaseModel, Generic[T]):
    """分页数据模型"""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def success(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {"code": 0, "message": message, "data": data}


def error(message: str = "error", code: int = 1, data: Any = None) -> dict:
    """错误响应"""
    return {"code": code, "message": message, "data": data}
