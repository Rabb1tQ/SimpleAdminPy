"""
用户接口
"""
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_superuser
from app.core.database import get_db
from app.core.redis import get_redis_cache, RedisKey
from app.core.security import get_password_hash, verify_password
from app.models import User, user_role
from app.schemas import success, error, UserCreate, UserUpdate

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/info", summary="获取用户信息")
async def get_user_info(
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前登录用户信息"""
    # 获取用户角色编码列表
    role_codes = [role.code for role in current_user.roles if role.status == 1]
    
    return success({
        "userId": str(current_user.id),
        "username": current_user.username,
        "realName": current_user.real_name,
        "avatar": current_user.avatar,
        "roles": role_codes,
        "desc": current_user.desc,
        "homePath": current_user.home_path,
    })


@router.get("/list", summary="获取用户列表")
async def get_user_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=1000, description="每页数量"),
    username: str = Query(None, description="用户名"),
    status: int = Query(None, description="状态"),
    tenant_id: int = Query(None, description="租户ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取用户列表（分页）
    
    - 超级管理员：可看所有用户，支持按租户筛选
    - 租户管理员：只能看本租户用户
    """
    # 构建查询
    query = select(User).where(User.is_deleted == False)
    count_query = select(func.count(User.id)).where(User.is_deleted == False)
    
    # 租户过滤：非超管只能看自己租户的用户
    if not current_user.is_superuser:
        query = query.where(User.tenant_id == current_user.tenant_id)
        count_query = count_query.where(User.tenant_id == current_user.tenant_id)
    elif tenant_id is not None:
        # 超管可按租户筛选
        query = query.where(User.tenant_id == tenant_id)
        count_query = count_query.where(User.tenant_id == tenant_id)
    
    # 搜索条件
    if username:
        query = query.where(User.username.ilike(f"%{username}%"))
        count_query = count_query.where(User.username.ilike(f"%{username}%"))
    if status is not None:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)
    
    # 获取总数
    total = (await db.execute(count_query)).scalar()
    
    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(User.roles))
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 构建响应
    items = []
    for user in users:
        items.append({
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "phone": user.phone,
            "avatar": user.avatar,
            "status": user.status,
            "is_superuser": user.is_superuser,
            "tenant_id": user.tenant_id,
            "created_at": user.created_at.isoformat(),
            "roles": [r.code for r in user.roles],
            "role_ids": [r.id for r in user.roles],
        })
    
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.post("", summary="创建用户")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """创建用户
    
    - 超级管理员：可选择租户创建用户
    - 租户管理员：只能创建本租户用户
    """
    # 检查用户名是否存在
    result = await db.execute(
        select(User).where(User.username == data.username, User.is_deleted == False)
    )
    if result.scalar_one_or_none():
        return error("用户名已存在")
    
    # 确定租户ID
    if current_user.is_superuser:
        # 超管可以指定租户
        user_tenant_id = data.tenant_id
    else:
        # 非超管只能创建本租户用户
        user_tenant_id = current_user.tenant_id
    
    # 创建用户
    user = User(
        username=data.username,
        password=get_password_hash(data.password),
        real_name=data.real_name,
        email=data.email,
        phone=data.phone,
        desc=data.desc,
        avatar=data.avatar,
        home_path=data.home_path,
        tenant_id=user_tenant_id,
    )
    db.add(user)
    await db.flush()
    
    # 分配角色
    if data.role_ids:
        for role_id in data.role_ids:
            stmt = user_role.insert().values(user_id=user.id, role_id=role_id)
            await db.execute(stmt)
    
    await db.commit()
    return success({"id": user.id})


async def clear_user_cache(redis: Redis, user_id: int) -> None:
    """清除指定用户的缓存"""
    menu_key = RedisKey.USER_MENUS.format(user_id=user_id)
    perm_key = RedisKey.USER_PERMISSIONS.format(user_id=user_id)
    await redis.delete(menu_key, perm_key)


@router.put("/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新用户
    
    - 超级管理员：可更新任意用户，可修改租户
    - 租户管理员：只能更新本租户用户，不能修改租户
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        return error("用户不存在")
    
    # 不能停用自己
    if user_id == current_user.id and data.status == 0:
        return error("不能停用自己的账户")
    
    # 权限检查：非超管只能操作本租户用户
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            return error("无权限操作该用户")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True, exclude={"role_ids", "tenant_id"})
    for key, value in update_data.items():
        setattr(user, key, value)
    
    # 只有超管可以修改租户
    if current_user.is_superuser and data.tenant_id is not None:
        user.tenant_id = data.tenant_id
    
    # 更新角色
    if data.role_ids is not None:
        # 删除旧角色关联
        stmt = user_role.delete().where(user_role.c.user_id == user_id)
        await db.execute(stmt)
        # 添加新角色关联
        for role_id in data.role_ids:
            stmt = user_role.insert().values(user_id=user.id, role_id=role_id)
            await db.execute(stmt)
        
        # 清除用户缓存
        await clear_user_cache(redis, user_id)
    
    await db.commit()
    return success()


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """删除用户
    
    - 超级管理员：可删除任意用户
    - 租户管理员：只能删除本租户用户
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        return error("用户不存在")
    
    if user.is_superuser:
        return error("不能删除超级管理员")
    
    # 权限检查：非超管只能操作本租户用户
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            return error("无权限操作该用户")
    
    # 先删除用户角色关联
    stmt = user_role.delete().where(user_role.c.user_id == user_id)
    await db.execute(stmt)
    
    # 软删除用户
    user.is_deleted = 1
    await db.commit()
    return success()


@router.post("/{user_id}/reset-password", summary="重置密码")
async def reset_password(
    user_id: int,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """重置用户密码
    
    - 超级管理员：可重置任意用户密码
    - 租户管理员：只能重置本租户用户密码
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        return error("用户不存在")
    
    # 权限检查：非超管只能操作本租户用户
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            return error("无权限操作该用户")
    
    user.password = get_password_hash(new_password)
    await db.commit()
    return success()


@router.post("/change-password", summary="修改密码")
async def change_password(
    old_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """修改当前用户密码"""
    if not verify_password(old_password, current_user.password):
        return error("旧密码错误")
    
    current_user.password = get_password_hash(new_password)
    await db.commit()
    return success()
