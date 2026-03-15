"""
路由自动注册器

使用方式：
1. 在 api 目录下创建任意 .py 文件
2. 在文件中定义 router = APIRouter(prefix="/xxx", tags=["xxx"])
3. 路由会自动被注册，无需手动修改 __init__.py

目录结构支持：
- api/auth.py          -> /api/auth
- api/system/user.py   -> /api/system/user
- api/system/role.py   -> /api/system/role

注意：路由前缀会根据目录结构自动添加，例如：
- api/system/user.py 中定义 router = APIRouter(prefix="/user")
  最终路由前缀为 /api/system/user
"""
import importlib
from pathlib import Path
from typing import List, Tuple

from fastapi import APIRouter


def discover_routers(base_path: Path, base_package: str) -> List[Tuple[APIRouter, str]]:
    """
    自动发现并加载所有路由模块
    
    Args:
        base_path: 路由模块所在目录的路径
        base_package: 基础包名（用于 import）
    
    Returns:
        发现的所有 APIRouter 实例及其目录前缀的列表
        返回格式: [(router, directory_prefix), ...]
        例如: [(router, "/system"), ...]
    """
    routers = []
    
    # 遍历目录下的所有 Python 文件
    for file_path in base_path.rglob("*.py"):
        # 跳过 __init__.py 和 registry.py
        if file_path.name in ("__init__.py", "registry.py"):
            continue
        
        # 计算模块的导入路径
        relative_path = file_path.relative_to(base_path)
        
        # 计算目录前缀（去掉文件名，只保留目录路径）
        # 例如: system/user.py -> /system
        parent_parts = relative_path.parent.parts
        directory_prefix = "/" + "/".join(parent_parts) if parent_parts else ""
        
        # 将路径转换为模块名（去掉 .py 后缀，路径分隔符改为 .）
        module_name = relative_path.with_suffix("").as_posix().replace("/", ".")
        full_module_name = f"{base_package}.{module_name}"
        
        try:
            # 动态导入模块
            module = importlib.import_module(full_module_name)
            
            # 查找模块中的 router 对象
            if hasattr(module, "router") and isinstance(module.router, APIRouter):
                routers.append((module.router, directory_prefix))
        except Exception as e:
            import logging
            logging.warning(f"Failed to load router from {full_module_name}: {e}")
    
    return routers


def create_api_router() -> APIRouter:
    """
    创建并自动注册所有路由
    
    路由前缀会根据目录结构自动添加：
    - api/auth.py 中的 router(prefix="/auth") -> /api/auth
    - api/system/user.py 中的 router(prefix="/user") -> /api/system/user
    
    Returns:
        包含所有子路由的 APIRouter
    """
    api_router = APIRouter()
    
    # 获取当前目录和包名
    current_dir = Path(__file__).parent
    package_name = "app.api"
    
    # 自动发现并注册路由
    routers = discover_routers(current_dir, package_name)
    
    for router, directory_prefix in routers:
        # 使用 include_router 的 prefix 参数来添加目录前缀
        # 这样路由路径会正确拼接
        api_router.include_router(router, prefix=directory_prefix)
    
    return api_router
