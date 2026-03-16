"""
SimpleAdmin 后端入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import setup_logging
from app.core.redis import RedisClient
from app.middleware.operation_log import OperationLogMiddleware
from app.utils.init_data import init_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    setup_logging()
    await init_db()
    await init_data()  # 自动初始化数据（已存在则跳过）
    # 初始化所有 Redis 连接池
    await RedisClient.get_session_client()
    await RedisClient.get_cache_client()
    await RedisClient.get_token_client()
    yield
    # 关闭时
    await close_db()
    await RedisClient.close()


# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    description="SimpleAdmin 后台管理系统 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 操作日志中间件
app.add_middleware(OperationLogMiddleware)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": str(exc) if settings.DEBUG else "服务器内部错误",
            "data": None,
        },
    )


# 注册路由
app.include_router(api_router, prefix="/api")


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    redis_health = await RedisClient.health_check()
    return {
        "status": "ok",
        "redis": redis_health,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
    )
