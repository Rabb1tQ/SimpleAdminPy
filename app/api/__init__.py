"""
API 路由

路由自动注册说明：
1. 在 api 目录下创建任意 .py 文件
2. 定义 router = APIRouter(prefix="/xxx", tags=["xxx"])
3. 路由会自动被注册

支持目录结构：
- api/user.py          -> /api/user
- api/system/user.py   -> /api/system/user
"""
from app.api.registry import create_api_router

api_router = create_api_router()
