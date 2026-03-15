"""
个人中心模块测试
"""
import pytest
from unittest.mock import patch

from app.core.security import create_access_token


class TestGetProfile:
    """获取个人信息测试"""
    
    @pytest.mark.asyncio
    async def test_get_profile_success(self, client, test_user):
        """测试获取个人信息成功"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        
        result = data["data"]
        assert result["id"] == test_user.id
        assert result["username"] == test_user.username
        assert result["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_get_profile_no_token(self, client):
        """测试未登录获取个人信息"""
        response = await client.get("/api/system/profile")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_profile_contains_all_fields(self, client, test_user):
        """测试个人信息包含所有字段"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        
        # 验证所有必要字段
        required_fields = [
            "id", "username", "real_name", "email", "phone",
            "desc", "avatar", "home_path", "status", "is_superuser",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in result, f"Field {field} should be in profile"


class TestUpdateProfile:
    """更新个人信息测试"""
    
    @pytest.mark.asyncio
    async def test_update_profile_success(self, client, test_user):
        """测试更新个人信息成功"""
        token = create_access_token(str(test_user.id))
        update_data = {
            "real_name": "Updated Name",
            "email": "updated@example.com",
            "phone": "13800138000",
            "desc": "Updated description"
        }
        
        response = await client.put(
            "/api/system/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
    
    @pytest.mark.asyncio
    async def test_update_profile_partial(self, client, test_user):
        """测试部分更新个人信息"""
        token = create_access_token(str(test_user.id))
        update_data = {
            "real_name": "New Name"
        }
        
        response = await client.put(
            "/api/system/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
    
    @pytest.mark.asyncio
    async def test_update_profile_avatar(self, client, test_user):
        """测试更新头像"""
        token = create_access_token(str(test_user.id))
        update_data = {
            "avatar": "https://example.com/avatar.png"
        }
        
        response = await client.put(
            "/api/system/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_update_profile_home_path(self, client, test_user):
        """测试更新首页路径"""
        token = create_access_token(str(test_user.id))
        update_data = {
            "home_path": "/dashboard"
        }
        
        response = await client.put(
            "/api/system/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_update_profile_no_token(self, client):
        """测试未登录更新个人信息"""
        update_data = {
            "real_name": "New Name"
        }
        
        response = await client.put(
            "/api/system/profile",
            json=update_data
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_profile_invalid_email(self, client, test_user):
        """测试无效邮箱格式"""
        token = create_access_token(str(test_user.id))
        update_data = {
            "email": "invalid-email"
        }
        
        response = await client.put(
            "/api/system/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 应该返回验证错误
        assert response.status_code == 422


class TestChangePassword:
    """修改密码测试"""
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, client, test_user):
        """测试修改密码成功"""
        token = create_access_token(str(test_user.id))
        password_data = {
            "old_password": "testpass123",  # 与 conftest.py 中 test_user 的密码一致
            "new_password": "newpassword123"
        }
        
        response = await client.put(
            "/api/system/profile/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, client, test_user):
        """测试旧密码错误"""
        token = create_access_token(str(test_user.id))
        password_data = {
            "old_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        
        response = await client.put(
            "/api/system/profile/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0  # 应该返回错误
    
    @pytest.mark.asyncio
    async def test_change_password_same_as_old(self, client, test_user):
        """测试新密码与旧密码相同"""
        token = create_access_token(str(test_user.id))
        password_data = {
            "old_password": "testpass123",  # 与 conftest.py 中 test_user 的密码一致
            "new_password": "testpass123"
        }
        
        response = await client.put(
            "/api/system/profile/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # 新密码不能与旧密码相同
        assert data["code"] != 0
    
    @pytest.mark.asyncio
    async def test_change_password_no_token(self, client):
        """测试未登录修改密码"""
        password_data = {
            "old_password": "oldpass",
            "new_password": "newpass"
        }
        
        response = await client.put(
            "/api/system/profile/password",
            json=password_data
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_change_password_missing_fields(self, client, test_user):
        """测试缺少必填字段"""
        token = create_access_token(str(test_user.id))
        password_data = {
            "old_password": "testpassword"
            # 缺少 new_password
        }
        
        response = await client.put(
            "/api/system/profile/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_change_password_empty_password(self, client, test_user):
        """测试空密码"""
        token = create_access_token(str(test_user.id))
        password_data = {
            "old_password": "",
            "new_password": ""
        }
        
        response = await client.put(
            "/api/system/profile/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 应该返回验证错误
        assert response.status_code == 422


class TestProfileIntegration:
    """个人中心集成测试"""
    
    @pytest.mark.asyncio
    async def test_update_and_verify_profile(self, client, test_user):
        """测试更新并验证个人信息"""
        token = create_access_token(str(test_user.id))
        # 更新个人信息
        update_data = {
            "real_name": "Integration Test User",
            "desc": "This is a test user for integration testing"
        }
        
        update_response = await client.put(
            "/api/system/profile",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert update_response.status_code == 200
        
        # 获取个人信息验证更新
        get_response = await client.get(
            "/api/system/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["data"]["real_name"] == "Integration Test User"
    
    @pytest.mark.asyncio
    async def test_change_password_and_login(self, client, test_user):
        """测试修改密码后重新登录"""
        token = create_access_token(str(test_user.id))
        # 修改密码
        password_data = {
            "old_password": "testpass123",  # 与 conftest.py 中 test_user 的密码一致
            "new_password": "newtestpassword123"
        }
        
        change_response = await client.put(
            "/api/system/profile/password",
            json=password_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert change_response.status_code == 200
        
        # 使用新密码登录
        login_data = {
            "username": test_user.username,
            "password": "newtestpassword123"
        }
        
        login_response = await client.post("/api/auth/login", json=login_data)
        
        assert login_response.status_code == 200
        data = login_response.json()
        assert data["code"] == 0
        assert "accessToken" in data["data"]
    
    @pytest.mark.asyncio
    async def test_superuser_profile(self, client, test_superuser):
        """测试超级管理员个人信息"""
        token = create_access_token(str(test_superuser.id))
        response = await client.get(
            "/api/system/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_superuser"] is True
    
    @pytest.mark.asyncio
    async def test_normal_user_profile(self, client, test_user):
        """测试普通用户个人信息"""
        token = create_access_token(str(test_user.id))
        response = await client.get(
            "/api/system/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_superuser"] is False
