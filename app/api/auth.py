"""
认证接口
"""
import base64
import io
import random
import string
from datetime import datetime
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis, get_redis_token, RedisKey
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models import LoginLog, User
from app.schemas import (
    success,
    error,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
)

router = APIRouter(prefix="/auth", tags=["认证"])


def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/captcha", summary="获取验证码")
async def get_captcha(
    redis: Redis = Depends(get_redis),
) -> dict:
    """生成图形验证码"""
    # 生成随机验证码
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # 生成唯一key
    key = "".join(random.choices(string.ascii_lowercase + string.digits, k=32))
    
    # 创建图片
    width, height = 150, 50
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        # Windows 系统字体路径
        font = ImageFont.truetype("arial.ttf", 32)
    except (OSError, IOError):
        try:
            # Linux 系统字体路径
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except (OSError, IOError):
            # 使用默认字体
            font = ImageFont.load_default()
    
    # 添加干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)
    
    # 添加验证码文字
    for i, char in enumerate(code):
        # 随机颜色
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        # 随机Y偏移
        y_offset = random.randint(5, 12)
        draw.text((20 + i * 30, y_offset), char, fill=color, font=font)
    
    # 转换为base64
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    
    # 存储到Redis
    await redis.setex(
        RedisKey.CAPTCHA.format(key=key),
        RedisKey.CAPTCHA_EXPIRE,
        code.lower(),
    )
    
    return success({
        "key": key,
        "image": image_base64,
    })


async def create_login_log(
    db: AsyncSession,
    user_id: Optional[int],
    username: str,
    ip: str,
    status: int,
    msg: str,
    user_agent: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> None:
    """创建登录日志"""
    log = LoginLog(
        user_id=user_id,
        username=username,
        tenant_id=tenant_id,
        ip=ip,
        status=status,
        msg=msg,
        browser=user_agent[:100] if user_agent else None,
    )
    db.add(log)
    await db.commit()


@router.post("/login", summary="登录")
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """用户登录"""
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    # 验证验证码（如果提供）
    if data.captcha_key and data.captcha_code:
        stored_code = await redis.get(RedisKey.CAPTCHA.format(key=data.captcha_key))
        if not stored_code or stored_code != data.captcha_code.lower():
            await create_login_log(db, None, data.username, ip, 0, "验证码错误", user_agent)
            return error("验证码错误")
        # 删除验证码
        await redis.delete(RedisKey.CAPTCHA.format(key=data.captcha_key))
    
    # 查询用户（预加载角色和菜单）
    from app.models import Role
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.menus))
        .where(User.username == data.username, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        await create_login_log(db, None, data.username, ip, 0, "用户不存在", user_agent, None)
        return error("用户名或密码错误")
    
    if user.status == 0:
        await create_login_log(db, user.id, data.username, ip, 0, "用户已被禁用", user_agent, user.tenant_id)
        return error("用户已被禁用")
    
    # 检查用户是否有至少一个启用的角色（超级管理员跳过此检查）
    if not user.is_superuser:
        enabled_roles = [role for role in user.roles if role.status == 1] if user.roles else []
        if not enabled_roles:
            await create_login_log(db, user.id, data.username, ip, 0, "用户无可用角色", user_agent, user.tenant_id)
            return error("用户无可用角色，请联系管理员")
    
    # 验证密码
    if not verify_password(data.password, user.password):
        await create_login_log(db, user.id, data.username, ip, 0, "密码错误", user_agent, user.tenant_id)
        return error("用户名或密码错误")
    
    # 更新最后登录信息
    user.last_login_time = datetime.now()
    user.last_login_ip = ip
    
    # 生成 token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # 计算过期时间
    from datetime import timedelta
    from app.core.config import settings
    expires = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 获取用户角色和权限
    if user.is_superuser:
        # 超级管理员拥有所有权限
        roles = ["admin"]
        permissions = ["*"]
    else:
        # 普通用户只使用启用的角色
        roles = [role.code for role in enabled_roles]
        permissions = []
        for role in enabled_roles:
            if role.menus:
                for menu in role.menus:
                    if menu.perms:
                        permissions.extend(menu.perms.split(","))
        permissions = list(set(permissions))  # 去重
    
    # 记录登录成功日志
    await create_login_log(db, user.id, data.username, ip, 1, "登录成功", user_agent, user.tenant_id)
    await db.commit()
    
    # 单点登录：将旧 token 加入黑名单，踢掉之前的登录
    from app.api.system.online import get_online_user
    token_redis = await get_redis_token()
    old_online_data = await get_online_user(redis, user.id)
    if old_online_data and old_online_data.get("token"):
        # 将旧 token 加入黑名单
        old_token = old_online_data.get("token")
        blacklist_key = RedisKey.TOKEN_BLACKLIST.format(user_id=user.id)
        await token_redis.setex(
            blacklist_key,
            RedisKey.TOKEN_BLACKLIST_EXPIRE,
            old_token  # 只让旧 token 失效
        )
    
    # 设置用户在线状态
    from app.api.system.online import set_online_user, get_browser_info
    await set_online_user(
        redis=redis,
        user_id=user.id,
        username=user.username,
        real_name=user.real_name,
        ip=ip,
        browser=get_browser_info(request),
        token=access_token,
        tenant_id=user.tenant_id,
        is_superuser=user.is_superuser,
    )
    
    return success({
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expires": expires,
        "username": user.username,
        "nickname": user.real_name,
        "avatar": user.avatar or "",
        "roles": roles,
        "permissions": permissions
    })


@router.post("/register", summary="注册")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """用户注册"""
    # 验证验证码
    if data.captcha_key and data.captcha_code:
        stored_code = await redis.get(RedisKey.CAPTCHA.format(key=data.captcha_key))
        if not stored_code or stored_code != data.captcha_code.lower():
            return error("验证码错误")
        await redis.delete(RedisKey.CAPTCHA.format(key=data.captcha_key))
    
    # 检查用户名是否存在
    result = await db.execute(
        select(User).where(User.username == data.username, User.is_deleted == False)
    )
    if result.scalar_one_or_none():
        return error("用户名已存在")
    
    # 创建用户
    user = User(
        username=data.username,
        password=get_password_hash(data.password),
        real_name=data.real_name,
        email=data.email,
    )
    db.add(user)
    await db.commit()
    
    return success({"message": "注册成功"})


@router.post("/logout", summary="退出登录")
async def logout(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis_token),
    session_redis: Redis = Depends(get_redis),
) -> dict:
    """退出登录 - 将 Token 加入黑名单"""
    # 将用户 Token 加入黑名单（使用用户 ID 作为标识）
    # 实际项目中应该使用具体的 token jti 或完整 token
    await redis.setex(
        RedisKey.TOKEN_BLACKLIST.format(user_id=current_user.id),
        RedisKey.TOKEN_BLACKLIST_EXPIRE,
        "1",
    )
    
    # 移除在线状态
    from app.api.system.online import remove_online_user
    await remove_online_user(session_redis, current_user.id)
    
    return success()


@router.post("/refresh", summary="刷新Token")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    刷新访问令牌
    
    使用 refresh token 获取新的 access token
    """
    # 验证 refresh token
    user_id = verify_token(request.refreshToken, "refresh")
    if not user_id:
        return error("无效的刷新令牌", 401)
    
    # 检查用户是否存在且有效
    result = await db.execute(
        select(User).where(User.id == int(user_id), User.status == 1)
    )
    user = result.scalar_one_or_none()
    if not user:
        return error("用户不存在或已禁用", 401)
    
    # 生成新的 access token
    access_token = create_access_token(user.id)
    return success({"accessToken": access_token})


@router.get("/codes", summary="获取权限码")
async def get_access_codes(
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前用户的权限码列表"""
    # 超级管理员拥有所有权限
    if current_user.is_superuser:
        return success(["*"])
    
    # 获取用户角色的权限码
    codes: List[str] = []
    for role in current_user.roles:
        if role.status == 1:
            for menu in role.menus:
                if menu.permission and menu.status == 1:
                    codes.append(menu.permission)
    
    return success(list(set(codes)))
