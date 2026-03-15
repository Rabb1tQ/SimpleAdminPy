"""
操作日志中间件
自动记录用户操作日志
"""
import json
import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.database import async_session_maker
from app.core.security import verify_token
from app.models import OperationLog

# 不需要记录日志的路径
EXCLUDE_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/auth/captcha",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/log",
    "/api/login-log",
    "/api/online",
    "/api/monitor",
]

# 不需要记录响应数据的路径（避免记录大量数据）
EXCLUDE_RESPONSE_PATHS = [
    "/api/user/list",
    "/api/role/list",
    "/api/menu/list",
    "/api/dict",
    "/api/log/list",
    "/api/login-log/list",
]


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只记录 API 请求
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        # 排除不需要记录的路径
        for exclude_path in EXCLUDE_PATHS:
            if request.url.path.startswith(exclude_path):
                return await call_next(request)

        # 只记录 POST、PUT、DELETE 请求（修改操作）
        if request.method not in ["POST", "PUT", "DELETE"]:
            return await call_next(request)

        # 记录开始时间
        start_time = time.time()

        # 获取请求体
        request_body = None
        if request.method in ["POST", "PUT"]:
            try:
                body = await request.body()
                if body:
                    request_body = body.decode("utf-8")
                    # 尝试解析 JSON，如果失败则保留原始字符串
                    try:
                        parsed = json.loads(request_body)
                        # 过滤敏感信息
                        if "password" in parsed:
                            parsed["password"] = "******"
                        if "old_password" in parsed:
                            parsed["old_password"] = "******"
                        if "new_password" in parsed:
                            parsed["new_password"] = "******"
                        request_body = json.dumps(parsed, ensure_ascii=False)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                request_body = None

        # 调用下一个中间件/路由
        response = await call_next(request)

        # 记录结束时间
        end_time = time.time()
        duration = int((end_time - start_time) * 1000)  # 毫秒

        # 获取用户信息
        user_id = None
        username = "anonymous"
        tenant_id = None
        token = request.headers.get("Authorization", "")
        if token and token.startswith("Bearer "):
            token = token[7:]
            try:
                user_id_str = verify_token(token)
                if user_id_str:
                    # 将字符串类型的 user_id 转换为整数
                    user_id = int(user_id_str)
                    # 从请求状态中获取用户名和租户ID（如果有）
                    username = getattr(request.state, "username", f"user_{user_id}")
                    tenant_id = getattr(request.state, "tenant_id", None)
            except Exception:
                pass

        # 获取客户端 IP
        ip = self.get_client_ip(request)

        # 获取响应体（如果需要）
        response_body = None
        if response.status_code == 200:
            for exclude_path in EXCLUDE_RESPONSE_PATHS:
                if request.url.path.startswith(exclude_path):
                    break
            else:
                # 尝试读取响应体
                try:
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk
                    
                    # 限制响应体大小
                    if len(response_body) > 2000:
                        response_body = response_body[:2000] + b"...(truncated)"
                    
                    response_body = response_body.decode("utf-8")
                    
                    # 重新创建响应
                    from fastapi.responses import Response as FastAPIResponse
                    response = FastAPIResponse(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                except Exception:
                    response_body = None

        # 异步保存日志
        try:
            await self.save_log(
                user_id=user_id,
                username=username,
                tenant_id=tenant_id,
                method=request.method,
                url=request.url.path,
                ip=ip,
                user_agent=request.headers.get("User-Agent", ""),
                request_data=request_body,
                response_data=response_body,
                status=1 if response.status_code == 200 else 0,
                duration=duration,
            )
        except Exception as e:
            print(f"保存操作日志失败: {e}")

        return response

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """获取客户端 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def get_module_and_action(url: str, method: str) -> tuple:
        """根据 URL 和方法获取模块和操作"""
        # 解析 URL 获取模块
        parts = url.strip("/").split("/")
        module = parts[1] if len(parts) > 1 else "unknown"
        
        # 根据方法获取操作
        action_map = {
            "POST": "新增",
            "PUT": "修改",
            "DELETE": "删除",
        }
        action = action_map.get(method, "操作")
        
        # 模块名称映射
        module_map = {
            "user": "用户管理",
            "role": "角色管理",
            "menu": "菜单管理",
            "dict": "字典管理",
            "log": "日志管理",
            "auth": "认证管理",
            "profile": "个人中心",
            "online": "在线用户",
            "monitor": "系统监控",
        }
        
        module_name = module_map.get(module, module)
        
        return module_name, f"{action}"

    @staticmethod
    async def save_log(
        user_id: Optional[int],
        username: str,
        tenant_id: Optional[int],
        method: str,
        url: str,
        ip: str,
        user_agent: str,
        request_data: Optional[str],
        response_data: Optional[str],
        status: int,
        duration: int,
    ):
        """保存操作日志"""
        module, action = OperationLogMiddleware.get_module_and_action(url, method)
        
        async with async_session_maker() as db:
            log = OperationLog(
                user_id=user_id or 0,
                username=username,
                tenant_id=tenant_id,
                module=module,
                action=action,
                method=method,
                url=url,
                ip=ip,
                user_agent=user_agent[:255] if user_agent else None,
                request_data=request_data,
                response_data=response_data,
                status=status,
                duration=duration,
            )
            db.add(log)
            await db.commit()
