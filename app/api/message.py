"""
消息通知API
"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_superuser, get_db
from app.models import User, Role, Tenant
from app.models.system.message import Message, MessageSendLog
from app.schemas.system.message import (
    MessageResponse,
    MessageListResponse,
    UnreadCountResponse,
    MessageSend,
    MessageSendResponse,
    MessageSendLogResponse,
    MessageSendLogListResponse,
)
from app.schemas.base import success, error

router = APIRouter(prefix="/message", tags=["消息通知"])


@router.get("/list", summary="获取消息列表")
async def get_message_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="消息类型"),
    is_read: Optional[bool] = Query(None, description="是否已读"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的消息列表"""
    query = select(Message).where(
        Message.receiver_id == current_user.id,
        Message.is_deleted == False,
    )

    # 过滤条件
    if type:
        query = query.where(Message.type == type)
    if is_read is not None:
        query = query.where(Message.is_read == (1 if is_read else 0))

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.order_by(Message.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    messages = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return success(
        data=MessageListResponse(
            items=[MessageResponse.model_validate(m) for m in messages],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ).model_dump()
    )


@router.get("/unread-count", summary="获取未读消息数量")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的未读消息数量"""
    query = select(func.count()).select_from(Message).where(
        Message.receiver_id == current_user.id,
        Message.is_read == 0,
        Message.is_deleted == False,
    )

    result = await db.execute(query)
    count = result.scalar()

    return success(data=UnreadCountResponse(count=count).model_dump())


@router.put("/{message_id}/read", summary="标记消息已读")
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记消息为已读"""
    query = select(Message).where(
        Message.id == message_id,
        Message.receiver_id == current_user.id,
        Message.is_deleted == False,
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    if message.is_read == 0:
        message.is_read = 1
        message.read_at = datetime.now()
        await db.commit()

    return success(message="标记成功")


@router.put("/{message_id}/unread", summary="标记消息未读")
async def mark_message_unread(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记消息为未读"""
    query = select(Message).where(
        Message.id == message_id,
        Message.receiver_id == current_user.id,
        Message.is_deleted == False,
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    if message.is_read == 1:
        message.is_read = 0
        message.read_at = None
        await db.commit()

    return success(message="标记成功")


@router.put("/read-all", summary="一键全部已读")
async def read_all_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """将当前用户的所有未读消息标记为已读"""
    query = select(Message).where(
        Message.receiver_id == current_user.id,
        Message.is_read == 0,
        Message.is_deleted == False,
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    now = datetime.now()
    for message in messages:
        message.is_read = 1
        message.read_at = now

    await db.commit()

    return success(message=f"已将{len(messages)}条消息标记为已读")


@router.delete("/{message_id}", summary="删除消息")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除消息（软删除）"""
    query = select(Message).where(
        Message.id == message_id,
        Message.receiver_id == current_user.id,
        Message.is_deleted == False,
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    message.is_deleted = 1
    await db.commit()

    return success(message="删除成功")


@router.post("/send", summary="发送消息")
async def send_message(
    data: MessageSend,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息（仅超级管理员和租户管理员可访问）
    
    接收对象类型:
    - ALL: 全员（仅超管可用）
    - TENANT: 指定租户（仅超管可用）
    - ROLE: 指定角色
    - USER: 指定用户
    """
    receiver_ids = []

    if data.receiver_type == "ALL":
        # 全员发送
        query = select(User.id).where(User.is_deleted == False, User.status == 1)
        result = await db.execute(query)
        receiver_ids = [row[0] for row in result.fetchall()]

    elif data.receiver_type == "TENANT":
        # 发送给指定租户的用户
        if not data.receiver_ids:
            raise HTTPException(status_code=400, detail="请选择租户")
        query = select(User.id).where(
            User.tenant_id.in_(data.receiver_ids),
            User.is_deleted == False,
            User.status == 1,
        )
        result = await db.execute(query)
        receiver_ids = [row[0] for row in result.fetchall()]

    elif data.receiver_type == "ROLE":
        # 发送给指定角色的用户
        if not data.receiver_ids:
            raise HTTPException(status_code=400, detail="请选择角色")
        query = (
            select(User.id)
            .join(User.roles)
            .where(
                Role.id.in_(data.receiver_ids),
                User.is_deleted == False,
                User.status == 1,
            )
            .distinct()
        )
        result = await db.execute(query)
        receiver_ids = [row[0] for row in result.fetchall()]

    elif data.receiver_type == "USER":
        # 发送给指定用户
        if not data.receiver_ids:
            raise HTTPException(status_code=400, detail="请选择用户")
        query = select(User.id).where(
            User.id.in_(data.receiver_ids),
            User.is_deleted == False,
            User.status == 1,
        )
        result = await db.execute(query)
        receiver_ids = [row[0] for row in result.fetchall()]

    else:
        raise HTTPException(status_code=400, detail="无效的接收对象类型")

    if not receiver_ids:
        raise HTTPException(status_code=400, detail="没有符合条件的接收者")

    # 创建消息
    messages = []
    for receiver_id in receiver_ids:
        message = Message(
            title=data.title,
            content=data.content,
            type=data.type,
            sender_id=current_user.id,
            sender_tenant_id=current_user.tenant_id,
            receiver_id=receiver_id,
            is_read=0,
        )
        messages.append(message)

    db.add_all(messages)

    # 创建发送记录
    send_log = MessageSendLog(
        title=data.title,
        content=data.content,
        type=data.type,
        sender_id=current_user.id,
        sender_tenant_id=current_user.tenant_id,
        receiver_type=data.receiver_type,
        receiver_ids=json.dumps(data.receiver_ids),
        send_count=len(receiver_ids),
    )
    db.add(send_log)

    await db.commit()

    return success(
        data=MessageSendResponse(send_count=len(receiver_ids)).model_dump()
    )


@router.get("/send-log", summary="获取发送记录")
async def get_send_log(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """获取消息发送记录（仅超级管理员和租户管理员可访问）"""
    query = select(MessageSendLog).where(MessageSendLog.is_deleted == False)

    # 非超级管理员只能看自己发送的记录
    if not current_user.is_superuser:
        query = query.where(MessageSendLog.sender_id == current_user.id)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.order_by(MessageSendLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return success(
        data=MessageSendLogListResponse(
            items=[MessageSendLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ).model_dump()
    )
