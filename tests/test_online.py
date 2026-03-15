"""
在线用户管理模块测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.core.security import create_access_token


class TestOnlineUserList:
    """在线用户列表测试"""
    
    @pytest.mark.asyncio
    async def test_get_online_list_success(self, client, test_superuser, mock_redis):
        """测试获取在线用户列表成功"""
        token = create_access_token(str(test_superuser.id))
        
        with patch("app.api.system.online.get_redis", return_value=mock_redis):
            # API 使用 smembers 获取在线用户集合，不是 keys
            mock_redis.smembers = AsyncMock(return_value=["1"])
            mock_redis.get = AsyncMock(return_value='{"user_id": 1, "username": "admin", "real_name": "Admin", "ip": "127.0.0.1", "browser": "Chrome", "login_time": "2024-01-01T00:00:00", "last_access": "2024-01-01T00:00:00"}')
            
            response = await client.get(
                "/api/system/online/list",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
    
    @pytest.mark.asyncio
    async def test_get_online_list_empty(self, client, test_superuser):
        """测试获取在线用户列表为空"""
        token = create_access_token(str(test_superuser.id))
        
        with patch("app.api.system.online.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            # API 使用 smembers 获取在线用户集合，不是 keys
            mock_redis.smembers = AsyncMock(return_value=[])
            mock_get_redis.return_value = mock_redis
            
            response = await client.get(
                "/api/system/online/list",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["items"] == []
    
    @pytest.mark.asyncio
    async def test_get_online_list_unauthorized(self, client, test_user):
        """测试普通用户无权访问在线用户列表"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/online/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 普通用户无权访问，应返回403或401
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_get_online_list_no_token(self, client):
        """测试未登录访问在线用户列表"""
        response = await client.get("/api/system/online/list")
        
        assert response.status_code == 401


class TestForceLogout:
    """强制下线测试"""
    
    @pytest.mark.asyncio
    async def test_force_logout_success(self, client, test_superuser, test_user, mock_redis):
        """测试强制下线成功"""
        token = create_access_token(str(test_superuser.id))
        
        # 设置 mock_redis 的行为 - API 首先调用 get_online_user 获取用户在线信息
        mock_redis.get = AsyncMock(return_value='{"user_id": 2, "username": "test", "real_name": "Test", "ip": "127.0.0.1", "browser": "Chrome", "login_time": "2024-01-01T00:00:00", "last_access": "2024-01-01T00:00:00", "token": "test_token"}')
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.setex = AsyncMock(return_value=True)  # 用于 token 黑名单
        
        response = await client.delete(
            f"/api/system/online/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
    
    @pytest.mark.asyncio
    async def test_force_logout_user_not_online(self, client, test_superuser, mock_redis):
        """测试强制下线不在线的用户"""
        token = create_access_token(str(test_superuser.id))
        
        # 用户不在线，get 返回 None
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.delete = AsyncMock(return_value=0)  # 没有删除任何key
        
        response = await client.delete(
            "/api/system/online/999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 用户不在线，返回错误
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1  # 用户不在线是错误情况
    
    @pytest.mark.asyncio
    async def test_force_logout_unauthorized(self, client, test_user):
        """测试普通用户无权强制下线"""
        token = create_access_token(str(test_user.id))
        response = await client.delete(
            "/api/system/online/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_force_logout_no_token(self, client):
        """测试未登录强制下线"""
        response = await client.delete("/api/system/online/1")
        
        assert response.status_code == 401


class TestOnlineUserHelperFunctions:
    """在线用户辅助函数测试"""
    
    @pytest.mark.asyncio
    async def test_set_online_user(self, mock_redis):
        """测试设置在线用户"""
        from app.api.system.online import set_online_user
        from datetime import datetime
        
        user_data = {
            "user_id": 1,
            "username": "testuser",
            "real_name": "Test User",
            "ip": "127.0.0.1",
            "browser": "Chrome",
            "login_time": datetime.now().isoformat(),
        }
        
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.sadd = AsyncMock(return_value=1)  # 添加到在线用户集合
        
        await set_online_user(
            mock_redis,
            user_id=1,
            username="testuser",
            real_name="Test User",
            ip="127.0.0.1",
            browser="Chrome"
        )
        
        mock_redis.setex.assert_called_once()
        mock_redis.sadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_online_user(self, mock_redis):
        """测试移除在线用户"""
        from app.api.system.online import remove_online_user
        
        mock_redis.delete = AsyncMock(return_value=1)
        
        await remove_online_user(mock_redis, 1)
        
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_online_user(self, mock_redis):
        """测试获取在线用户"""
        from app.api.system.online import get_online_user
        import json
        
        user_data = {"user_id": 1, "username": "testuser"}
        mock_redis.get = AsyncMock(return_value=json.dumps(user_data))
        
        result = await get_online_user(mock_redis, 1)
        
        assert result is not None
        assert result["user_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_online_user_not_found(self, mock_redis):
        """测试获取不存在的在线用户"""
        from app.api.system.online import get_online_user
        
        mock_redis.get = AsyncMock(return_value=None)
        
        result = await get_online_user(mock_redis, 999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_refresh_online_user(self, mock_redis):
        """测试刷新在线用户过期时间"""
        from app.api.system.online import refresh_online_user
        import json
        
        # refresh_online_user 首先调用 get 获取用户数据，然后调用 setex 更新
        user_data = {
            "user_id": 1,
            "username": "testuser",
            "real_name": "Test User",
            "ip": "127.0.0.1",
            "browser": "Chrome",
            "login_time": "2024-01-01T00:00:00",
            "last_access": "2024-01-01T00:00:00"
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(user_data))
        mock_redis.setex = AsyncMock(return_value=True)
        
        await refresh_online_user(mock_redis, 1)
        
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()


class TestGetClientIP:
    """获取客户端IP测试"""
    
    def test_get_client_ip_from_x_forwarded(self):
        """测试从 X-Forwarded-For 获取IP"""
        from app.api.system.online import get_client_ip
        
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_from_x_real_ip(self):
        """测试从 X-Real-IP 获取IP"""
        from app.api.system.online import get_client_ip
        
        request = MagicMock()
        request.headers = {"X-Real-IP": "192.168.1.2"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        # X-Real-IP 不在当前实现中处理，会返回 client.host
        ip = get_client_ip(request)
        assert ip == "127.0.0.1"
    
    def test_get_client_ip_from_client(self):
        """测试从 client.host 获取IP"""
        from app.api.system.online import get_client_ip
        
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        ip = get_client_ip(request)
        assert ip == "127.0.0.1"


class TestGetBrowserInfo:
    """获取浏览器信息测试"""
    
    def test_get_browser_info_chrome(self):
        """测试识别 Chrome 浏览器"""
        from app.api.system.online import get_browser_info
        
        request = MagicMock()
        request.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/96.0"}
        
        info = get_browser_info(request)
        assert "Chrome" in info
    
    def test_get_browser_info_firefox(self):
        """测试识别 Firefox 浏览器"""
        from app.api.system.online import get_browser_info
        
        request = MagicMock()
        request.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Firefox/95.0"}
        
        info = get_browser_info(request)
        assert "Firefox" in info
    
    def test_get_browser_info_empty_ua(self):
        """测试空 User-Agent"""
        from app.api.system.online import get_browser_info
        
        request = MagicMock()
        request.headers = {}
        
        info = get_browser_info(request)
        assert info == "Unknown"
