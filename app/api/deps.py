"""
API 依赖注入
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.redis import get_redis_token, RedisKey
from app.core.security import verify_token
from app.models import User, Role

# Bearer Token 认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_token),
) -> User:
    """
    获取当前登录用户
    
    Raises:
        HTTPException: 未认证或用户不存在
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = verify_token(token, "access")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 token 是否在黑名单中（单点登录：被踢下线或强制下线）
    blacklist_key = RedisKey.TOKEN_BLACKLIST.format(user_id=user_id)
    blacklisted_value = await redis.get(blacklist_key)
    if blacklisted_value:
        # 黑名单中存储的是失效的 token 或 "1"（强制下线标记）
        # 如果当前 token 与黑名单中的 token 相同，或者是强制下线标记，则拒绝访问
        if blacklisted_value == token or blacklisted_value == "1":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="您的账号在其他设备登录或已被强制下线，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 加载用户及其角色、菜单关系
    result = await db.execute(
        select(User)
        .where(User.id == int(user_id))
        .options(
            selectinload(User.roles).selectinload(Role.menus)
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 设置 request.state 供中间件使用
    request.state.username = user.username
    request.state.tenant_id = user.tenant_id

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户
    """
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前超级管理员
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return current_user


class PermissionChecker:
    """权限检查器"""

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """检查用户是否有指定权限"""
        # 超级管理员拥有所有权限
        if current_user.is_superuser:
            return current_user

        # 检查用户角色是否包含该权限
        # TODO: 实现权限检查逻辑
        return current_user
