"""
系统监控接口
"""
import platform
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends

from app.api.deps import get_current_superuser
from app.core.redis import RedisClient
from app.models import User
from app.schemas import success

router = APIRouter(prefix="/monitor", tags=["系统监控"])


@router.get("/server", summary="获取服务器信息")
async def get_server_info(
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取服务器基本信息"""
    # 系统信息
    system_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }
    
    # CPU 信息
    cpu_info = {
        "cpu_count": psutil.cpu_count(logical=False),  # 物理核心数
        "cpu_count_logical": psutil.cpu_count(logical=True),  # 逻辑核心数
        "cpu_percent": psutil.cpu_percent(interval=1),  # CPU 使用率
        "cpu_freq": None,
    }
    
    try:
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            cpu_info["cpu_freq"] = {
                "current": round(cpu_freq.current, 2),
                "min": round(cpu_freq.min, 2) if cpu_freq.min else None,
                "max": round(cpu_freq.max, 2) if cpu_freq.max else None,
            }
    except Exception:
        pass
    
    # 内存信息
    memory = psutil.virtual_memory()
    memory_info = {
        "total": round(memory.total / (1024 ** 3), 2),  # GB
        "available": round(memory.available / (1024 ** 3), 2),  # GB
        "used": round(memory.used / (1024 ** 3), 2),  # GB
        "percent": memory.percent,  # 使用率
    }
    
    # 磁盘信息
    disk = psutil.disk_usage("/")
    disk_info = {
        "total": round(disk.total / (1024 ** 3), 2),  # GB
        "used": round(disk.used / (1024 ** 3), 2),  # GB
        "free": round(disk.free / (1024 ** 3), 2),  # GB
        "percent": disk.percent,  # 使用率
    }
    
    # 网络信息
    try:
        net_io = psutil.net_io_counters()
        network_info = {
            "bytes_sent": round(net_io.bytes_sent / (1024 ** 2), 2),  # MB
            "bytes_recv": round(net_io.bytes_recv / (1024 ** 2), 2),  # MB
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
        }
    except Exception:
        network_info = None
    
    # 进程信息
    process_count = len(psutil.pids())
    
    # 系统启动时间
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    return success({
        "system": system_info,
        "cpu": cpu_info,
        "memory": memory_info,
        "disk": disk_info,
        "network": network_info,
        "process_count": process_count,
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": str(uptime).split(".")[0],  # 去掉微秒
    })


@router.get("/redis", summary="获取Redis信息")
async def get_redis_info(
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取 Redis 信息"""
    redis_health = await RedisClient.health_check()
    
    # 获取 Redis 详细信息
    info = {}
    try:
        client = await RedisClient.get_session_client()
        redis_info = await client.info()
        info = {
            "version": redis_info.get("redis_version", ""),
            "mode": redis_info.get("redis_mode", ""),
            "os": redis_info.get("os", ""),
            "uptime_days": redis_info.get("uptime_in_days", 0),
            "connected_clients": redis_info.get("connected_clients", 0),
            "used_memory_human": redis_info.get("used_memory_human", ""),
            "used_memory_peak_human": redis_info.get("used_memory_peak_human", ""),
            "total_connections_received": redis_info.get("total_connections_received", 0),
            "total_commands_processed": redis_info.get("total_commands_processed", 0),
            "keyspace_hits": redis_info.get("keyspace_hits", 0),
            "keyspace_misses": redis_info.get("keyspace_misses", 0),
        }
    except Exception as e:
        info = {"error": str(e)}
    
    return success({
        "health": redis_health,
        "info": info,
    })


@router.get("/database", summary="获取数据库信息")
async def get_database_info(
    _: User = Depends(get_current_superuser),
) -> dict:
    """获取数据库信息"""
    from app.core.database import engine
    from sqlalchemy import text
    
    db_info = {
        "status": "connected",
        "type": "PostgreSQL" if "postgresql" in str(engine.url) else "SQLite",
    }
    
    try:
        async with engine.connect() as conn:
            # 获取数据库版本
            if "postgresql" in str(engine.url):
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
                db_info["version"] = version
                
                # 获取数据库大小
                result = await conn.execute(text(
                    "SELECT pg_database_size(current_database())"
                ))
                size = result.scalar()
                db_info["size"] = round(size / (1024 ** 2), 2)  # MB
                
                # 获取连接数
                result = await conn.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                ))
                db_info["connections"] = result.scalar()
            else:
                # SQLite
                result = await conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                db_info["version"] = version
    except Exception as e:
        db_info["status"] = "error"
        db_info["error"] = str(e)
    
    return success(db_info)
