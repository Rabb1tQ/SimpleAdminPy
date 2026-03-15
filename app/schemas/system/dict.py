"""
字典相关 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============ 字典类型 ============

class DictTypeCreate(BaseModel):
    """创建字典类型"""

    name: str = Field(..., max_length=100, description="字典名称")
    code: str = Field(..., max_length=100, description="字典编码")
    status: int = Field(1, description="状态: 0-禁用, 1-启用")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class DictTypeUpdate(BaseModel):
    """更新字典类型"""

    name: Optional[str] = Field(None, max_length=100, description="字典名称")
    code: Optional[str] = Field(None, max_length=100, description="字典编码")
    status: Optional[int] = Field(None, description="状态: 0-禁用, 1-启用")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class DictTypeResponse(BaseModel):
    """字典类型响应"""

    id: int
    name: str
    code: str
    status: int = 1
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 字典数据 ============

class DictDataCreate(BaseModel):
    """创建字典数据"""

    dict_type_id: int = Field(..., description="字典类型ID")
    label: str = Field(..., max_length=100, description="字典标签")
    value: str = Field(..., max_length=100, description="字典值")
    sort: int = Field(0, description="排序")
    status: int = Field(1, description="状态: 0-禁用, 1-启用")
    css_class: Optional[str] = Field(None, max_length=100, description="样式属性")
    list_class: Optional[str] = Field(None, max_length=100, description="表格回显样式")
    is_default: bool = Field(False, description="是否默认")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class DictDataUpdate(BaseModel):
    """更新字典数据"""

    dict_type_id: Optional[int] = Field(None, description="字典类型ID")
    label: Optional[str] = Field(None, max_length=100, description="字典标签")
    value: Optional[str] = Field(None, max_length=100, description="字典值")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, description="状态: 0-禁用, 1-启用")
    css_class: Optional[str] = Field(None, max_length=100, description="样式属性")
    list_class: Optional[str] = Field(None, max_length=100, description="表格回显样式")
    is_default: Optional[bool] = Field(None, description="是否默认")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class DictDataResponse(BaseModel):
    """字典数据响应"""

    id: int
    dict_type_id: int
    label: str
    value: str
    sort: int
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DictDataWithCodeResponse(BaseModel):
    """带字典编码的字典数据响应"""

    id: int
    dict_type_id: int
    dict_code: str
    label: str
    value: str
    sort: int
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
