"""
系统监控模块测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.security import create_access_token


class TestServerMonitor:
    """服务器监控测试"""
    
    @pytest.mark.asyncio
    async def test_get_server_info_success(self, client, test_superuser):
        """测试获取服务器信息成功"""
        token = create_access_token(str(test_superuser.id))
        response = await client.get(
            "/api/system/monitor/server",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        # 验证返回的数据结构
        result = data["data"]
        assert "system" in result
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        
        # 验证系统信息
        system = result["system"]
        assert "os" in system
        assert "python_version" in system
        
        # 验证CPU信息
        cpu = result["cpu"]
        assert "cpu_count" in cpu
        assert "cpu_percent" in cpu
        
        # 验证内存信息
        memory = result["memory"]
        assert "total" in memory
        assert "used" in memory
        assert "percent" in memory
        
        # 验证磁盘信息
        disk = result["disk"]
        assert "total" in disk
        assert "used" in disk
        assert "percent" in disk
    
    @pytest.mark.asyncio
    async def test_get_server_info_unauthorized(self, client, test_user):
        """测试普通用户无权访问服务器监控"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/monitor/server",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_get_server_info_no_token(self, client):
        """测试未登录访问服务器监控"""
        response = await client.get("/api/system/monitor/server")
        
        assert response.status_code == 401


class TestRedisMonitor:
    """Redis监控测试"""
    
    @pytest.mark.asyncio
    async def test_get_redis_info_success(self, client, test_superuser):
        """测试获取Redis信息成功"""
        token = create_access_token(str(test_superuser.id))
        with patch("app.api.system.monitor.RedisClient") as mock_redis_client:
            mock_redis_client.health_check = AsyncMock(return_value=True)
            mock_redis_client.get_session_client = AsyncMock()
            
            mock_session_client = AsyncMock()
            mock_session_client.info = AsyncMock(return_value={
                "redis_version": "7.0.0",
                "redis_mode": "standalone",
                "os": "Linux",
                "uptime_in_days": 1,
                "connected_clients": 5,
                "used_memory_human": "1.5M",
                "used_memory_peak_human": "2.0M",
                "total_connections_received": 100,
                "total_commands_processed": 1000,
                "keyspace_hits": 500,
                "keyspace_misses": 50,
            })
            mock_redis_client.get_session_client.return_value = mock_session_client
            
            response = await client.get(
                "/api/system/monitor/redis",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        result = data["data"]
        assert "health" in result
        assert "info" in result
    
    @pytest.mark.asyncio
    async def test_get_redis_info_connection_error(self, client, test_superuser):
        """测试Redis连接失败"""
        token = create_access_token(str(test_superuser.id))
        with patch("app.api.system.monitor.RedisClient") as mock_redis_client:
            mock_redis_client.health_check = AsyncMock(return_value=False)
            mock_redis_client.get_session_client = AsyncMock()
            mock_redis_client.get_session_client.side_effect = Exception("Connection refused")
            
            response = await client.get(
                "/api/system/monitor/redis",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # 即使连接失败，接口也应该返回响应
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
    
    @pytest.mark.asyncio
    async def test_get_redis_info_unauthorized(self, client, test_user):
        """测试普通用户无权访问Redis监控"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/monitor/redis",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_get_redis_info_no_token(self, client):
        """测试未登录访问Redis监控"""
        response = await client.get("/api/system/monitor/redis")
        
        assert response.status_code == 401


class TestDatabaseMonitor:
    """数据库监控测试"""
    
    @pytest.mark.asyncio
    async def test_get_database_info_success(self, client, test_superuser):
        """测试获取数据库信息成功"""
        token = create_access_token(str(test_superuser.id))
        response = await client.get(
            "/api/system/monitor/database",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        result = data["data"]
        assert "status" in result
        assert "type" in result
    
    @pytest.mark.asyncio
    async def test_get_database_info_sqlite(self, client, test_superuser):
        """测试获取数据库信息"""
        token = create_access_token(str(test_superuser.id))
        response = await client.get(
            "/api/system/monitor/database",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查返回的数据库信息结构
        result = data["data"]
        assert "type" in result
        # 数据库类型取决于实际配置，可能是 SQLite 或 PostgreSQL
        assert result["type"] in ["SQLite", "PostgreSQL"]
        # 如果连接成功，应该有 version 字段；如果连接失败，应该有 error 字段
        assert "version" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_get_database_info_unauthorized(self, client, test_user):
        """测试普通用户无权访问数据库监控"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/monitor/database",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_get_database_info_no_token(self, client):
        """测试未登录访问数据库监控"""
        response = await client.get("/api/system/monitor/database")
        
        assert response.status_code == 401


class TestMonitorIntegration:
    """监控模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_all_monitor_endpoints_require_superuser(self, client, test_user, test_superuser):
        """测试所有监控端点都需要超级管理员权限"""
        endpoints = [
            "/api/system/monitor/server",
            "/api/system/monitor/redis",
            "/api/system/monitor/database",
        ]
        
        user_token = create_access_token(str(test_user.id))
        superuser_token = create_access_token(str(test_superuser.id))
        
        # 普通用户访问应被拒绝
        for endpoint in endpoints:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should be forbidden"
        
        # 超级管理员访问应成功
        # 需要mock Redis客户端，否则会尝试实际连接导致错误
        with patch("app.api.system.monitor.RedisClient") as mock_redis_client:
            mock_redis_client.health_check = AsyncMock(return_value=True)
            mock_redis_client.get_session_client = AsyncMock()
            mock_session_client = AsyncMock()
            mock_session_client.info = AsyncMock(return_value={
                "redis_version": "7.0.0",
                "redis_mode": "standalone",
                "os": "Linux",
                "uptime_in_days": 1,
                "connected_clients": 5,
                "used_memory_human": "1.5M",
                "used_memory_peak_human": "2.0M",
                "total_connections_received": 100,
                "total_commands_processed": 1000,
                "keyspace_hits": 500,
                "keyspace_misses": 50,
            })
            mock_redis_client.get_session_client.return_value = mock_session_client
            
            for endpoint in endpoints:
                response = await client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {superuser_token}"}
                )
                assert response.status_code == 200, f"Endpoint {endpoint} should be accessible"
    
    @pytest.mark.asyncio
    async def test_monitor_data_consistency(self, client, test_superuser):
        """测试监控数据一致性"""
        token = create_access_token(str(test_superuser.id))
        # 多次请求服务器信息，验证数据格式一致
        responses = []
        for _ in range(3):
            response = await client.get(
                "/api/system/monitor/server",
                headers={"Authorization": f"Bearer {token}"}
            )
            responses.append(response.json())
        
        # 验证所有响应结构一致
        keys = ["system", "cpu", "memory", "disk", "network", "process_count", "boot_time", "uptime"]
        for resp in responses:
            for key in keys:
                assert key in resp["data"], f"Key {key} should be in response"
