"""
Redis 连接配置（企业级）
"""
import logging
from typing import Optional

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from app.core.config import settings


logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端管理类"""

    # 不同业务的客户端实例
    _session_pool: Optional[ConnectionPool] = None  # 会话/验证码 (DB 0)
    _cache_pool: Optional[ConnectionPool] = None    # 缓存数据 (DB 1)
    _token_pool: Optional[ConnectionPool] = None    # Token 黑名单 (DB 2)

    @classmethod
    def _build_redis_url(cls, db: int) -> str:
        """构建 Redis 连接 URL"""
        if settings.REDIS_PASSWORD:
            return f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{db}"
        return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{db}"

    @classmethod
    def _create_pool(cls, db: int) -> ConnectionPool:
        """创建连接池"""
        url = cls._build_redis_url(db)
        return ConnectionPool.from_url(
            url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True,
            retry_on_timeout=True,
        )

    @classmethod
    async def get_session_client(cls) -> redis.Redis:
        """获取会话客户端 (DB 0) - 用于验证码、Session 等"""
        if cls._session_pool is None:
            cls._session_pool = cls._create_pool(settings.REDIS_DB_SESSION)
            logger.info(f"Redis session pool created: DB {settings.REDIS_DB_SESSION}")
        return redis.Redis(connection_pool=cls._session_pool)

    @classmethod
    async def get_cache_client(cls) -> redis.Redis:
        """获取缓存客户端 (DB 1) - 用于数据缓存"""
        if cls._cache_pool is None:
            cls._cache_pool = cls._create_pool(settings.REDIS_DB_CACHE)
            logger.info(f"Redis cache pool created: DB {settings.REDIS_DB_CACHE}")
        return redis.Redis(connection_pool=cls._cache_pool)

    @classmethod
    async def get_token_client(cls) -> redis.Redis:
        """获取 Token 客户端 (DB 2) - 用于 Token 黑名单"""
        if cls._token_pool is None:
            cls._token_pool = cls._create_pool(settings.REDIS_DB_TOKEN)
            logger.info(f"Redis token pool created: DB {settings.REDIS_DB_TOKEN}")
        return redis.Redis(connection_pool=cls._token_pool)

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """获取默认客户端 (兼容旧代码，使用 DB 0)"""
        return await cls.get_session_client()

    @classmethod
    async def close(cls):
        """关闭所有 Redis 连接"""
        pools = [
            ("session", cls._session_pool),
            ("cache", cls._cache_pool),
            ("token", cls._token_pool),
        ]
        for name, pool in pools:
            if pool:
                try:
                    await pool.disconnect()
                    logger.info(f"Redis {name} pool closed")
                except Exception as e:
                    logger.error(f"Error closing Redis {name} pool: {e}")
        
        cls._session_pool = None
        cls._cache_pool = None
        cls._token_pool = None

    @classmethod
    async def health_check(cls) -> dict:
        """健康检查"""
        result = {
            "session": False,
            "cache": False,
            "token": False,
        }
        
        checks = [
            ("session", cls.get_session_client),
            ("cache", cls.get_cache_client),
            ("token", cls.get_token_client),
        ]
        
        for name, get_client_func in checks:
            try:
                client = await get_client_func()
                await client.ping()
                result[name] = True
            except (RedisError, RedisConnectionError) as e:
                logger.error(f"Redis {name} health check failed: {e}")
        
        return result


# FastAPI 依赖注入
async def get_redis() -> redis.Redis:
    """获取 Redis 客户端依赖（默认会话客户端）"""
    return await RedisClient.get_session_client()


async def get_redis_cache() -> redis.Redis:
    """获取缓存 Redis 客户端依赖"""
    return await RedisClient.get_cache_client()


async def get_redis_token() -> redis.Redis:
    """获取 Token Redis 客户端依赖"""
    return await RedisClient.get_token_client()


# Redis Key 常量（企业级命名规范）
class RedisKey:
    """
    Redis Key 常量
    
    命名规范: simple_admin:模块:业务:标识
    """

    # 项目前缀
    PREFIX = "simple_admin"

    # ========== 验证码相关 (DB 0) ==========
    CAPTCHA = f"{PREFIX}:captcha:{{key}}"
    CAPTCHA_EXPIRE = 300  # 5分钟

    # ========== 用户会话相关 (DB 0) ==========
    USER_SESSION = f"{PREFIX}:session:{{user_id}}"
    USER_SESSION_EXPIRE = 86400  # 24小时

    # ========== Token 黑名单 (DB 2) ==========
    TOKEN_BLACKLIST = f"{PREFIX}:token:blacklist:{{user_id}}"
    TOKEN_BLACKLIST_EXPIRE = 604800  # 7天 (与 Refresh Token 过期时间一致)

    # ========== 用户权限缓存 (DB 1) ==========
    USER_PERMISSIONS = f"{PREFIX}:user:permissions:{{user_id}}"
    USER_PERMISSIONS_EXPIRE = 3600  # 1小时

    # ========== 用户菜单缓存 (DB 1) ==========
    USER_MENUS = f"{PREFIX}:user:menus:{{user_id}}"
    USER_MENUS_EXPIRE = 3600  # 1小时

    # ========== 字典缓存 (DB 1) ==========
    DICT_DATA = f"{PREFIX}:dict:{{code}}"
    DICT_DATA_EXPIRE = 7200  # 2小时

    # ========== 接口限流 (DB 0) ==========
    RATE_LIMIT = f"{PREFIX}:rate_limit:{{ip}}:{{endpoint}}"
    RATE_LIMIT_EXPIRE = 60  # 1分钟

    # ========== 在线用户 (DB 0) ==========
    ONLINE_USER = f"{PREFIX}:online:{{user_id}}"
    ONLINE_USERS_SET = f"{PREFIX}:online:users"
    ONLINE_USER_EXPIRE = 7200  # 2小时（无活动自动下线）

    # ========== 登录失败记录 (DB 0) ==========
    LOGIN_FAIL = f"{PREFIX}:login_fail:{{user_id}}"
    LOGIN_FAIL_EXPIRE = 3600  # 1小时
