"""
字典模型
"""
from typing import Optional, List

from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DictType(BaseModel):
    """字典类型表"""

    __tablename__ = "sys_dict_type"

    name: Mapped[str] = mapped_column(String(100), comment="字典名称")
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="字典编码")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-禁用, 1-启用")

    # 关联字典数据
    items: Mapped[List["DictData"]] = relationship(
        "DictData", back_populates="dict_type", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DictType {self.name}>"


class DictData(BaseModel):
    """字典数据表"""

    __tablename__ = "sys_dict_data"

    dict_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_dict_type.id"), index=True, comment="字典类型ID"
    )
    label: Mapped[str] = mapped_column(String(100), comment="字典标签")
    value: Mapped[str] = mapped_column(String(100), comment="字典值")
    sort: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 0-禁用, 1-启用")
    css_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="样式属性")
    list_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="表格回显样式")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认")

    # 关联字典类型
    dict_type: Mapped["DictType"] = relationship(
        "DictType", back_populates="items"
    )

    def __repr__(self) -> str:
        return f"<DictData {self.label}: {self.value}>"
