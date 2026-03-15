"""
角色接口
"""
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_superuser
from app.core.database import get_db
from app.core.redis import get_redis_cache, get_redis_token, RedisKey
from app.models import Role, role_menu, user_role, User
from app.schemas import success, error, RoleCreate, RoleUpdate

router = APIRouter(prefix="/role", tags=["角色管理"])


@router.get("/list", summary="获取角色列表")
async def get_role_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="角色名称"),
    status: int = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取角色列表（分页）"""
    query = select(Role)
    count_query = select(func.count(Role.id))
    
    if name:
        query = query.where(Role.name.ilike(f"%{name}%"))
        count_query = count_query.where(Role.name.ilike(f"%{name}%"))
    if status is not None:
        query = query.where(Role.status == status)
        count_query = count_query.where(Role.status == status)
    
    total = (await db.execute(count_query)).scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    roles = result.scalars().all()
    
    items = [
        {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "desc": role.desc,
            "status": role.status,
            "created_at": role.created_at.isoformat(),
        }
        for role in roles
    ]
    
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.get("/all", summary="获取所有角色")
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取所有启用的角色"""
    result = await db.execute(
        select(Role).where(Role.status == 1).order_by(Role.id)
    )
    roles = result.scalars().all()
    
    items = [
        {
            "id": role.id,
            "name": role.name,
            "code": role.code,
        }
        for role in roles
    ]
    
    return success(items)


@router.get("/{role_id}", summary="获取角色详情")
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取角色详情"""
    result = await db.execute(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.menus))
    )
    role = result.scalar_one_or_none()
    
    if role is None:
        return error("角色不存在")
    
    return success({
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "desc": role.desc,
        "status": role.status,
        "menu_ids": [m.id for m in role.menus],
        "created_at": role.created_at.isoformat(),
    })


@router.post("", summary="创建角色")
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """创建角色"""
    # 检查角色编码是否存在
    result = await db.execute(select(Role).where(Role.code == data.code))
    if result.scalar_one_or_none():
        return error("角色编码已存在")
    
    role = Role(
        name=data.name,
        code=data.code,
        desc=data.desc,
    )
    db.add(role)
    await db.flush()
    
    # 分配菜单权限
    if data.menu_ids:
        for menu_id in data.menu_ids:
            stmt = role_menu.insert().values(role_id=role.id, menu_id=menu_id)
            await db.execute(stmt)
    
    await db.commit()
    return success({"id": role.id})


async def clear_user_cache_by_role(redis: Redis, role_id: int, db: AsyncSession) -> None:
    """清除角色下所有用户的缓存"""
    # 查询该角色下的所有用户ID
    result = await db.execute(
        select(user_role.c.user_id).where(user_role.c.role_id == role_id)
    )
    user_ids = result.scalars().all()
    
    if user_ids:
        # 清除每个用户的菜单和权限缓存
        for user_id in user_ids:
            menu_key = RedisKey.USER_MENUS.format(user_id=user_id)
            perm_key = RedisKey.USER_PERMISSIONS.format(user_id=user_id)
            await redis.delete(menu_key, perm_key)


async def force_logout_users_by_role(
    redis: Redis,
    token_redis: Redis,
    role_id: int,
    db: AsyncSession
) -> None:
    """强制角色下所有在线用户下线"""
    from app.api.system.online import get_online_user, remove_online_user
    
    # 查询该角色下的所有用户ID
    result = await db.execute(
        select(user_role.c.user_id).where(user_role.c.role_id == role_id)
    )
    user_ids = result.scalars().all()
    
    if user_ids:
        for user_id in user_ids:
            # 检查用户是否在线
            online_data = await get_online_user(redis, user_id)
            if online_data:
                # 将用户加入黑名单
                blacklist_key = RedisKey.TOKEN_BLACKLIST.format(user_id=user_id)
                await token_redis.setex(
                    blacklist_key,
                    RedisKey.TOKEN_BLACKLIST_EXPIRE,
                    "1"  # 使用 "1" 表示该用户所有 token 都失效
                )
                # 移除在线状态
                await remove_online_user(redis, user_id)


@router.put("/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
    token_redis: Redis = Depends(get_redis_token),
    _: User = Depends(get_current_superuser),
) -> dict:
    """更新角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if role is None:
        return error("角色不存在")
    
    # 记录原来的状态
    old_status = role.status
    
    update_data = data.model_dump(exclude_unset=True, exclude={"menu_ids"})
    for key, value in update_data.items():
        setattr(role, key, value)
    
    # 更新菜单权限
    if data.menu_ids is not None:
        # 删除旧权限关联
        stmt = role_menu.delete().where(role_menu.c.role_id == role_id)
        await db.execute(stmt)
        # 添加新权限关联
        for menu_id in data.menu_ids:
            stmt = role_menu.insert().values(role_id=role.id, menu_id=menu_id)
            await db.execute(stmt)
    
    # 如果更新了状态或菜单权限，清除该角色下所有用户的缓存
    if data.menu_ids is not None or "status" in update_data:
        await clear_user_cache_by_role(redis, role_id, db)
    
    # 如果角色被禁用（状态从1变为0），强制该角色下所有在线用户下线
    if old_status == 1 and data.status == 0:
        await force_logout_users_by_role(redis, token_redis, role_id, db)
    
    await db.commit()
    return success()


@router.delete("/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
    _: User = Depends(get_current_superuser),
) -> dict:
    """删除角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if role is None:
        return error("角色不存在")
    
    # 清除该角色下所有用户的缓存（在删除关联之前）
    await clear_user_cache_by_role(redis, role_id, db)
    
    # 删除角色菜单关联
    stmt = role_menu.delete().where(role_menu.c.role_id == role_id)
    await db.execute(stmt)
    
    # 删除用户角色关联
    stmt = user_role.delete().where(user_role.c.role_id == role_id)
    await db.execute(stmt)
    
    # 删除角色
    await db.delete(role)
    await db.commit()
    return success()
