"""
日志接口
"""
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser
from app.core.database import get_db
from app.models import OperationLog, LoginLog, User
from app.schemas import success

router = APIRouter(prefix="/log", tags=["日志管理"])


@router.get("/list", summary="获取操作日志列表")
async def get_log_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    username: str = Query(None, description="用户名"),
    module: str = Query(None, description="操作模块"),
    status: int = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """获取操作日志列表（分页）
    
    - 超级管理员：可看所有日志
    - 租户管理员：只能看本租户日志
    """
    query = select(OperationLog).where(OperationLog.is_deleted == False)
    count_query = select(func.count(OperationLog.id)).where(OperationLog.is_deleted == False)
    
    # 租户过滤：非超管只能看自己租户的日志
    if not current_user.is_superuser:
        query = query.where(OperationLog.tenant_id == current_user.tenant_id)
        count_query = count_query.where(OperationLog.tenant_id == current_user.tenant_id)
    
    if username:
        query = query.where(OperationLog.username.ilike(f"%{username}%"))
        count_query = count_query.where(OperationLog.username.ilike(f"%{username}%"))
    if module:
        query = query.where(OperationLog.module == module)
        count_query = count_query.where(OperationLog.module == module)
    if status is not None:
        query = query.where(OperationLog.status == status)
        count_query = count_query.where(OperationLog.status == status)
    
    total = (await db.execute(count_query)).scalar()
    
    query = query.order_by(OperationLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "tenant_id": log.tenant_id,
            "module": log.module,
            "action": log.action,
            "method": log.method,
            "url": log.url,
            "ip": log.ip,
            "status": log.status,
            "duration": log.duration,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
    
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


# ============ 登录日志 ============


@router.get("/login/list", summary="获取登录日志列表")
async def get_login_log_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    username: str = Query(None, description="用户名"),
    status: int = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """获取登录日志列表（分页）
    
    - 超级管理员：可看所有日志
    - 租户管理员：只能看本租户日志
    """
    query = select(LoginLog).where(LoginLog.is_deleted == False)
    count_query = select(func.count(LoginLog.id)).where(LoginLog.is_deleted == False)
    
    # 租户过滤：非超管只能看自己租户的日志
    if not current_user.is_superuser:
        query = query.where(LoginLog.tenant_id == current_user.tenant_id)
        count_query = count_query.where(LoginLog.tenant_id == current_user.tenant_id)
    
    if username:
        query = query.where(LoginLog.username.ilike(f"%{username}%"))
        count_query = count_query.where(LoginLog.username.ilike(f"%{username}%"))
    if status is not None:
        query = query.where(LoginLog.status == status)
        count_query = count_query.where(LoginLog.status == status)
    
    total = (await db.execute(count_query)).scalar()
    
    query = query.order_by(LoginLog.login_time.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "tenant_id": log.tenant_id,
            "ip": log.ip,
            "location": log.location,
            "browser": log.browser,
            "os": log.os,
            "status": log.status,
            "msg": log.msg,
            "login_time": log.login_time.isoformat() if log.login_time else None,
        }
        for log in logs
    ]
    
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.get("/login-export", summary="导出登录日志")
async def export_login_log(
    username: str = Query(None, description="用户名"),
    status: int = Query(None, description="状态"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> StreamingResponse:
    """导出登录日志为 Excel (CSV格式)"""
    import csv
    
    query = select(LoginLog)
    
    if username:
        query = query.where(LoginLog.username.ilike(f"%{username}%"))
    if status is not None:
        query = query.where(LoginLog.status == status)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.where(LoginLog.login_time >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.where(LoginLog.login_time <= end_dt)
        except ValueError:
            pass
    
    query = query.order_by(LoginLog.login_time.desc()).limit(10000)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # 创建 CSV
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # 写入表头
    writer.writerow([
        "ID", "用户ID", "用户名", "登录IP", "登录地点", "浏览器",
        "操作系统", "状态", "提示消息", "登录时间"
    ])
    
    # 写入数据
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id or "",
            log.username,
            log.ip,
            log.location or "",
            log.browser or "",
            log.os or "",
            "成功" if log.status == 1 else "失败",
            log.msg or "",
            log.login_time.strftime("%Y-%m-%d %H:%M:%S") if log.login_time else ""
        ])
    
    output.seek(0)
    
    # 生成文件名
    filename = f"login_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/login/{log_id}", summary="获取登录日志详情")
async def get_login_log_detail(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取登录日志详情"""
    result = await db.execute(
        select(LoginLog).where(LoginLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if log is None:
        return {"code": 1, "message": "日志不存在", "data": None}
    
    return success({
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "ip": log.ip,
        "status": log.status,
        "msg": log.msg,
        "login_time": log.login_time.isoformat() if log.login_time else None,
    })


# ============ 日志导出 ============


@router.get("/operation-export", summary="导出操作日志")
async def export_operation_log(
    username: str = Query(None, description="用户名"),
    module: str = Query(None, description="操作模块"),
    status: int = Query(None, description="状态"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> StreamingResponse:
    """导出操作日志为 Excel (CSV格式)"""
    import csv
    
    query = select(OperationLog)
    
    if username:
        query = query.where(OperationLog.username.ilike(f"%{username}%"))
    if module:
        query = query.where(OperationLog.module == module)
    if status is not None:
        query = query.where(OperationLog.status == status)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.where(OperationLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.where(OperationLog.created_at <= end_dt)
        except ValueError:
            pass
    
    query = query.order_by(OperationLog.created_at.desc()).limit(10000)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # 创建 CSV
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # 写入表头
    writer.writerow([
        "ID", "用户ID", "用户名", "操作模块", "操作动作", "请求方法",
        "请求URL", "IP地址", "状态", "执行时长(ms)", "创建时间"
    ])
    
    # 写入数据
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id,
            log.username,
            log.module,
            log.action,
            log.method,
            log.url,
            log.ip,
            "成功" if log.status == 1 else "失败",
            log.duration,
            log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        ])
    
    output.seek(0)
    
    # 生成文件名
    filename = f"operation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # 添加 BOM 以支持 Excel 打开
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ============ 动态路径（必须放在最后） ============


@router.get("/{log_id}", summary="获取日志详情")
async def get_log_detail(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取操作日志详情"""
    result = await db.execute(
        select(OperationLog).where(OperationLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if log is None:
        return {"code": 1, "message": "日志不存在", "data": None}
    
    return success({
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "module": log.module,
        "action": log.action,
        "method": log.method,
        "url": log.url,
        "ip": log.ip,
        "user_agent": log.user_agent,
        "request_data": log.request_data,
        "response_data": log.response_data,
        "status": log.status,
        "error_msg": log.error_msg,
        "duration": log.duration,
        "created_at": log.created_at.isoformat(),
    })
