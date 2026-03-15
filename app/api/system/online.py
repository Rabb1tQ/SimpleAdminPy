"""
在线用户接口
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio import Redis

from app.api.deps import get_current_superuser
from app.core.redis import get_redis, get_redis_token, RedisKey
from app.models import User
from app.schemas import success, error

router = APIRouter(prefix="/online", tags=["在线用户"])


def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_browser_info(request: Request) -> str:
    """获取浏览器信息"""
    user_agent = request.headers.get("User-Agent", "")
    # 简单提取浏览器名称
    if "Chrome" in user_agent and "Edg" not in user_agent:
        return "Chrome"
    elif "Edg" in user_agent:
        return "Edge"
    elif "Firefox" in user_agent:
        return "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        return "Safari"
    elif "MSIE" in user_agent or "Trident" in user_agent:
        return "IE"
    else:
        return "Unknown"


async def set_online_user(
    redis: Redis,
    user_id: int,
    username: str,
    real_name: str,
    ip: str,
    browser: str,
    token: str = None,
    tenant_id: int = None,
    is_superuser: bool = False,
) -> None:
    """设置用户在线状态"""
    user_data = {
        "user_id": user_id,
        "username": username,
        "real_name": real_name,
        "ip": ip,
        "browser": browser,
        "login_time": datetime.now().isoformat(),
        "last_access": datetime.now().isoformat(),
        "token": token,
        "tenant_id": tenant_id,
        "is_superuser": is_superuser,
    }
    key = RedisKey.ONLINE_USER.format(user_id=user_id)
    await redis.setex(
        key,
        RedisKey.ONLINE_USER_EXPIRE,
        json.dumps(user_data, ensure_ascii=False)
    )
    # 添加到在线用户集合
    await redis.sadd(RedisKey.ONLINE_USERS_SET, str(user_id))


async def remove_online_user(redis: Redis, user_id: int) -> None:
    """移除用户在线状态"""
    key = RedisKey.ONLINE_USER.format(user_id=user_id)
    await redis.delete(key)
    await redis.srem(RedisKey.ONLINE_USERS_SET, str(user_id))


async def get_online_user(redis: Redis, user_id: int) -> Optional[dict]:
    """获取在线用户信息"""
    key = RedisKey.ONLINE_USER.format(user_id=user_id)
    data = await redis.get(key)
    if data:
        return json.loads(data)
    return None


async def refresh_online_user(redis: Redis, user_id: int) -> None:
    """刷新用户在线状态（延长过期时间）"""
    key = RedisKey.ONLINE_USER.format(user_id=user_id)
    # 更新最后访问时间
    data = await redis.get(key)
    if data:
        user_data = json.loads(data)
        user_data["last_access"] = datetime.now().isoformat()
        await redis.setex(
            key,
            RedisKey.ONLINE_USER_EXPIRE,
            json.dumps(user_data, ensure_ascii=False)
        )


@router.get("/list", summary="获取在线用户列表")
async def get_online_list(
    request: Request,
    username: str = Query(None, description="用户名"),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """获取在线用户列表
    
    - 超级管理员：可看所有在线用户
    - 租户管理员：只能看本租户在线用户
    """
    # 获取所有在线用户ID
    user_ids = await redis.smembers(RedisKey.ONLINE_USERS_SET)
    
    items = []
    for user_id in user_ids:
        user_data = await get_online_user(redis, int(user_id))
        if user_data:
            # 租户过滤：非超管只能看自己租户的在线用户
            if not current_user.is_superuser:
                if user_data.get("tenant_id") != current_user.tenant_id:
                    continue
            
            # 过滤用户名
            if username and username.lower() not in user_data.get("username", "").lower():
                continue
            items.append({
                "user_id": user_data["user_id"],
                "username": user_data["username"],
                "real_name": user_data["real_name"],
                "ip": user_data["ip"],
                "browser": user_data["browser"],
                "login_time": user_data["login_time"],
                "last_access": user_data["last_access"],
                "tenant_id": user_data.get("tenant_id"),
            })
    
    # 按登录时间倒序
    items.sort(key=lambda x: x["login_time"], reverse=True)
    
    return success({
        "items": items,
        "total": len(items),
    })


@router.delete("/{user_id}", summary="强制下线用户")
async def force_logout(
    user_id: int,
    redis: Redis = Depends(get_redis),
    token_redis: Redis = Depends(get_redis_token),
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """强制下线用户
    
    - 超级管理员：可强制下线任意用户
    - 租户管理员：只能强制下线本租户用户
    """
    # 不能强制下线自己
    if user_id == current_user.id:
        return error("不能强制下线自己")
    
    # 获取用户在线信息
    user_data = await get_online_user(redis, user_id)
    if not user_data:
        return error("用户不在线")
    
    # 权限检查：非超管只能操作本租户用户
    if not current_user.is_superuser:
        if user_data.get("tenant_id") != current_user.tenant_id:
            return error("无权限操作该用户")
    
    # 将用户加入黑名单（使用 token_redis 存储到 DB 2）
    blacklist_key = RedisKey.TOKEN_BLACKLIST.format(user_id=user_id)
    await token_redis.setex(
        blacklist_key,
        RedisKey.TOKEN_BLACKLIST_EXPIRE,
        "1"  # 使用 "1" 表示该用户所有 token 都失效
    )
    
    # 移除在线状态
    await remove_online_user(redis, user_id)
    
    return success()
