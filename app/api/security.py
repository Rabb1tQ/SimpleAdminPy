"""
安全配置API
"""
from datetime import datetime, timedelta
from typing import Optional, List
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

from app.core.database import get_db
from app.core.redis import RedisClient, get_redis_cache
from app.models.system.user import User
from app.models.system.security import SecurityConfig, IpRule
from app.schemas import (
    success,
    error,
    SecurityConfigResponse,
    SecurityConfigBatchUpdate,
    IpRuleCreate,
    IpRuleResponse,
    IpRuleListResponse,
    IpRuleStatusUpdate,
    LockedUserResponse,
    LockedUserListResponse,
    LoginFailInfo,
)
from app.api.deps import get_current_user, get_current_superuser
from app.core.redis import RedisKey

router = APIRouter(prefix="/security", tags=["安全配置"])


# ==================== 安全配置 ====================

@router.get("/config", summary="获取安全配置")
async def get_security_config(
    group: Optional[str] = None,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """获取安全配置列表 - 仅超级管理员可访问"""
    query = select(SecurityConfig).where(SecurityConfig.is_deleted == False)
    
    if group:
        query = query.where(SecurityConfig.group_name == group)
    
    query = query.order_by(SecurityConfig.group_name, SecurityConfig.id)
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return success(data=[
        {
            "id": config.id,
            "config_key": config.config_key,
            "config_value": config.config_value,
            "config_type": config.config_type,
            "group_name": config.group_name,
            "description": config.description,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
        for config in configs
    ])


@router.put("/config", summary="更新安全配置")
async def update_security_config(
    data: SecurityConfigBatchUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """批量更新安全配置 - 仅超级管理员可访问"""
    for config_data in data.configs:
        config_key = config_data.get("config_key")
        config_value = config_data.get("config_value")
        
        if not config_key:
            continue
        
        # 查找配置
        query = select(SecurityConfig).where(
            SecurityConfig.config_key == config_key,
            SecurityConfig.is_deleted == False,
        )
        result = await db.execute(query)
        config = result.scalar_one_or_none()
        
        if config:
            config.config_value = config_value
        else:
            # 创建新配置
            config = SecurityConfig(
                config_key=config_key,
                config_value=config_value,
                config_type="STRING",
            )
            db.add(config)
    
    await db.commit()
    return success(message="配置更新成功")


# ==================== IP规则 ====================

@router.get("/ip-rule/list", summary="获取IP规则列表")
async def get_ip_rule_list(
    page: int = 1,
    page_size: int = 10,
    rule_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """获取IP规则列表 - 仅超级管理员可访问"""
    query = select(IpRule).where(IpRule.is_deleted == False)
    count_query = select(func.count(IpRule.id)).where(IpRule.is_deleted == False)
    
    if rule_type:
        query = query.where(IpRule.rule_type == rule_type)
        count_query = count_query.where(IpRule.rule_type == rule_type)
    
    if ip_address:
        query = query.where(IpRule.ip_address.like(f"%{ip_address}%"))
        count_query = count_query.where(IpRule.ip_address.like(f"%{ip_address}%"))
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.order_by(IpRule.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return success(data={
        "list": [
            {
                "id": rule.id,
                "ip_address": rule.ip_address,
                "rule_type": rule.rule_type,
                "description": rule.description,
                "status": rule.status,
                "created_by": rule.created_by,
                "created_at": rule.created_at,
                "updated_at": rule.updated_at,
            }
            for rule in rules
        ],
        "total": total,
    })


@router.post("/ip-rule", summary="添加IP规则")
async def create_ip_rule(
    data: IpRuleCreate,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """添加IP规则 - 仅超级管理员可访问"""
    # 检查是否已存在
    query = select(IpRule).where(
        IpRule.ip_address == data.ip_address,
        IpRule.is_deleted == False,
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        return error(message="该IP规则已存在")
    
    rule = IpRule(
        ip_address=data.ip_address,
        rule_type=data.rule_type,
        description=data.description,
        status=1,
        created_by=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return success(data={
        "id": rule.id,
        "ip_address": rule.ip_address,
        "rule_type": rule.rule_type,
        "description": rule.description,
        "status": rule.status,
        "created_by": rule.created_by,
        "created_at": rule.created_at,
    })


@router.delete("/ip-rule/{rule_id}", summary="删除IP规则")
async def delete_ip_rule(
    rule_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """删除IP规则 - 仅超级管理员可访问"""
    query = select(IpRule).where(IpRule.id == rule_id, IpRule.is_deleted == False)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()
    
    if not rule:
        return error(message="IP规则不存在")
    
    rule.is_deleted = True
    await db.commit()
    
    return success(message="删除成功")


@router.put("/ip-rule/{rule_id}/status", summary="更新IP规则状态")
async def update_ip_rule_status(
    rule_id: int,
    data: IpRuleStatusUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """更新IP规则状态 - 仅超级管理员可访问"""
    query = select(IpRule).where(IpRule.id == rule_id, IpRule.is_deleted == False)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()
    
    if not rule:
        return error(message="IP规则不存在")
    
    rule.status = data.status
    await db.commit()
    
    return success(message="状态更新成功")


# ==================== 锁定用户管理 ====================

@router.get("/locked-users", summary="获取锁定用户列表")
async def get_locked_users(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """获取锁定用户列表 - 仅超级管理员可访问"""
    redis = await RedisClient.get_cache_client()
    
    # 获取所有锁定的用户
    pattern = f"{RedisKey.LOGIN_FAIL}:*"
    keys = []
    async for key in redis.scan_iter(match=pattern):
        keys.append(key)
    
    locked_users = []
    for key in keys:
        # 解析用户ID
        user_id = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
        
        # 获取锁定信息
        fail_info = await redis.get(key)
        if fail_info:
            info = json.loads(fail_info)
            if info.get("is_locked"):
                # 获取用户信息
                user_query = select(User).where(User.id == int(user_id))
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if user:
                    locked_users.append({
                        "user_id": user.id,
                        "username": user.username,
                        "real_name": user.real_name,
                        "locked_at": datetime.fromisoformat(info.get("locked_at", datetime.now().isoformat())),
                        "fail_count": info.get("fail_count", 0),
                        "unlock_at": datetime.fromisoformat(info["locked_until"]) if info.get("locked_until") else None,
                    })
    
    # 分页
    total = len(locked_users)
    start = (page - 1) * page_size
    end = start + page_size
    locked_users = locked_users[start:end]
    
    return success(data={
        "list": locked_users,
        "total": total,
    })


@router.delete("/locked-users/{user_id}", summary="解锁用户")
async def unlock_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
):
    """解锁用户 - 仅超级管理员可访问"""
    # 检查用户是否存在
    query = select(User).where(User.id == user_id, User.is_deleted == False)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return error(message="用户不存在")
    
    # 清除Redis中的锁定信息
    key = f"{RedisKey.LOGIN_FAIL}:{user_id}"
    await redis.delete(key)
    
    return success(message="解锁成功")


# ==================== 登录失败处理工具函数 ====================

async def get_login_fail_config(db: AsyncSession) -> dict:
    """获取登录失败相关配置"""
    query = select(SecurityConfig).where(
        SecurityConfig.config_key.in_([
            "login_fail_threshold",
            "lock_duration",
        ]),
        SecurityConfig.is_deleted == False,
    )
    result = await db.execute(query)
    configs = result.scalars().all()
    
    config_dict = {config.config_key: config.config_value for config in configs}
    
    return {
        "fail_threshold": int(config_dict.get("login_fail_threshold", 5)),
        "lock_duration": int(config_dict.get("lock_duration", 30)),
    }


async def record_login_fail(user_id: int, db: AsyncSession) -> LoginFailInfo:
    """记录登录失败"""
    redis = await RedisClient.get_cache_client()
    config = await get_login_fail_config(db)
    
    key = f"{RedisKey.LOGIN_FAIL}:{user_id}"
    
    # 获取当前失败信息
    fail_info_data = await redis.get(key)
    if fail_info_data:
        fail_info = json.loads(fail_info_data)
        fail_count = fail_info.get("fail_count", 0) + 1
    else:
        fail_count = 1
    
    # 检查是否需要锁定
    is_locked = False
    locked_until = None
    
    if fail_count >= config["fail_threshold"]:
        is_locked = True
        locked_until = datetime.now() + timedelta(minutes=config["lock_duration"])
    
    # 保存失败信息
    fail_info = {
        "fail_count": fail_count,
        "is_locked": is_locked,
        "locked_until": locked_until.isoformat() if locked_until else None,
        "locked_at": datetime.now().isoformat() if is_locked else None,
    }
    
    # 设置过期时间（锁定时长 + 5分钟缓冲）
    expire_seconds = (config["lock_duration"] + 5) * 60
    await redis.setex(key, expire_seconds, json.dumps(fail_info))
    
    return LoginFailInfo(
        fail_count=fail_count,
        locked_until=locked_until,
        is_locked=is_locked,
    )


async def check_user_locked(user_id: int, db: AsyncSession) -> tuple[bool, Optional[datetime]]:
    """检查用户是否被锁定"""
    redis = await RedisClient.get_cache_client()
    key = f"{RedisKey.LOGIN_FAIL}:{user_id}"
    
    fail_info_data = await redis.get(key)
    if not fail_info_data:
        return False, None
    
    fail_info = json.loads(fail_info_data)
    
    if not fail_info.get("is_locked"):
        return False, None
    
    # 检查锁定是否已过期
    locked_until = fail_info.get("locked_until")
    if locked_until:
        locked_until_dt = datetime.fromisoformat(locked_until)
        if datetime.now() > locked_until_dt:
            # 锁定已过期，清除锁定信息
            await redis.delete(key)
            return False, None
        return True, locked_until_dt
    
    return True, None


async def clear_login_fail(user_id: int):
    """清除登录失败记录（登录成功后调用）"""
    redis = await RedisClient.get_cache_client()
    key = f"{RedisKey.LOGIN_FAIL}:{user_id}"
    await redis.delete(key)


async def get_remaining_attempts(user_id: int, db: AsyncSession) -> int:
    """获取剩余尝试次数"""
    redis = await RedisClient.get_cache_client()
    config = await get_login_fail_config(db)
    
    key = f"{RedisKey.LOGIN_FAIL}:{user_id}"
    fail_info_data = await redis.get(key)
    
    if not fail_info_data:
        return config["fail_threshold"]
    
    fail_info = json.loads(fail_info_data)
    fail_count = fail_info.get("fail_count", 0)
    
    return max(0, config["fail_threshold"] - fail_count)


# ==================== IP检查工具函数 ====================

async def check_ip_allowed(ip: str, db: AsyncSession) -> tuple[bool, str]:
    """检查IP是否允许访问"""
    # 查询启用的IP规则
    query = select(IpRule).where(
        IpRule.is_deleted == False,
        IpRule.status == 1,
    )
    result = await db.execute(query)
    rules = result.scalars().all()
    
    if not rules:
        # 没有配置任何规则，允许所有IP
        return True, ""
    
    # 分离白名单和黑名单
    whitelist = [r for r in rules if r.rule_type == "WHITELIST"]
    blacklist = [r for r in rules if r.rule_type == "BLACKLIST"]
    
    # 先检查黑名单
    for rule in blacklist:
        if match_ip(ip, rule.ip_address):
            return False, f"IP {ip} 在黑名单中"
    
    # 如果有白名单，检查是否在白名单中
    if whitelist:
        for rule in whitelist:
            if match_ip(ip, rule.ip_address):
                return True, ""
        return False, f"IP {ip} 不在白名单中"
    
    return True, ""


def match_ip(client_ip: str, rule_ip: str) -> bool:
    """检查IP是否匹配规则"""
    # 支持 * 通配符
    if "*" in rule_ip:
        # 将通配符转换为正则表达式
        pattern = rule_ip.replace(".", "\\.").replace("*", ".*")
        import re
        return bool(re.match(f"^{pattern}$", client_ip))
    
    # 精确匹配
    return client_ip == rule_ip
