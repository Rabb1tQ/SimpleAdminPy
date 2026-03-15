"""
租户接口
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser
from app.core.database import get_db
from app.models import Tenant, User
from app.schemas import (
    success,
    error,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    TenantSelectResponse,
)

router = APIRouter(prefix="/tenant", tags=["租户管理"])


@router.get("/list", summary="获取租户列表")
async def get_tenant_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="租户名称"),
    code: str = Query(None, description="租户编码"),
    status: int = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取租户列表（分页）- 仅超级管理员可访问"""
    # 构建查询
    query = select(Tenant).where(Tenant.is_deleted == False)
    
    # 搜索条件
    if name:
        query = query.where(Tenant.name.contains(name))
    if code:
        query = query.where(Tenant.code.contains(code))
    if status is not None:
        query = query.where(Tenant.status == status)
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # 分页
    query = query.order_by(Tenant.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    # 构建响应
    items = [
        TenantListResponse(
            id=t.id,
            name=t.name,
            code=t.code,
            contact=t.contact,
            phone=t.phone,
            email=t.email,
            status=t.status,
            expire_at=t.expire_at,
            created_at=t.created_at,
        )
        for t in tenants
    ]
    
    return success({"items": items, "total": total})


@router.get("/all", summary="获取所有启用的租户")
async def get_all_tenants(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取所有启用的租户（用于下拉选择）- 仅超级管理员可访问"""
    query = select(Tenant).where(
        Tenant.is_deleted == False,
        Tenant.status == 1,
    ).order_by(Tenant.id)
    
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    items = [
        TenantSelectResponse(
            id=t.id,
            name=t.name,
            code=t.code,
            status=t.status,
        )
        for t in tenants
    ]
    
    return success(items)


@router.get("/{tenant_id}", summary="获取租户详情")
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取租户详情 - 仅超级管理员可访问"""
    query = select(Tenant).where(
        Tenant.id == tenant_id,
        Tenant.is_deleted == False,
    )
    result = await db.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    return success(TenantResponse.model_validate(tenant))


@router.post("", summary="创建租户")
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """创建租户 - 仅超级管理员可访问"""
    # 检查编码是否已存在
    existing_query = select(Tenant).where(
        Tenant.code == data.code,
        Tenant.is_deleted == False,
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="租户编码已存在")
    
    # 创建租户
    tenant = Tenant(
        name=data.name,
        code=data.code,
        contact=data.contact,
        phone=data.phone,
        email=data.email,
        address=data.address,
        status=data.status,
        expire_at=data.expire_at,
        remark=data.remark,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    return success(TenantResponse.model_validate(tenant))


@router.put("/{tenant_id}", summary="更新租户")
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """更新租户 - 仅超级管理员可访问"""
    # 查询租户
    query = select(Tenant).where(
        Tenant.id == tenant_id,
        Tenant.is_deleted == False,
    )
    result = await db.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # 如果更新编码，检查是否重复
    if data.code and data.code != tenant.code:
        existing_query = select(Tenant).where(
            Tenant.code == data.code,
            Tenant.is_deleted == False,
            Tenant.id != tenant_id,
        )
        existing = (await db.execute(existing_query)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="租户编码已存在")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)
    
    await db.commit()
    await db.refresh(tenant)
    
    return success(TenantResponse.model_validate(tenant))


@router.delete("/{tenant_id}", summary="删除租户")
async def delete_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """删除租户 - 仅超级管理员可访问"""
    # 查询租户
    query = select(Tenant).where(
        Tenant.id == tenant_id,
        Tenant.is_deleted == False,
    )
    result = await db.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # 检查租户下是否有用户
    user_query = select(func.count()).select_from(User).where(
        User.tenant_id == tenant_id,
        User.is_deleted == False,
    )
    user_count = (await db.execute(user_query)).scalar()
    
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"租户下存在 {user_count} 个用户，无法删除"
        )
    
    # 软删除
    tenant.is_deleted = 1
    await db.commit()
    
    return success(message="删除成功")
