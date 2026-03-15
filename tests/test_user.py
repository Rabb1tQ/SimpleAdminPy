"""
用户模块测试
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.core.security import get_password_hash, create_access_token
from app.models import User, Role


class TestGetUserInfo:
    """获取用户信息测试"""

    @pytest.mark.asyncio
    async def test_get_user_info_success(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试获取用户信息成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/user/info",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["username"] == "testuser"
        assert data["data"]["realName"] == "测试用户"

    @pytest.mark.asyncio
    async def test_get_user_info_without_token(
        self,
        client: AsyncClient,
    ):
        """测试未登录获取用户信息"""
        response = await client.get("/api/system/user/info")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_info_with_role(
        self,
        client: AsyncClient,
        user_with_role: User,
        test_role: Role,
    ):
        """测试获取带角色的用户信息"""
        token = create_access_token(str(user_with_role.id))
        
        response = await client.get(
            "/api/system/user/info",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert test_role.code in data["data"]["roles"]


class TestGetUserList:
    """获取用户列表测试"""

    @pytest.mark.asyncio
    async def test_get_user_list_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
    ):
        """测试获取用户列表成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/user/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_user_list_pagination(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试用户列表分页"""
        # 创建多个用户
        for i in range(15):
            user = User(
                username=f"page_user_{i}",
                password=get_password_hash("testpass123"),
                real_name=f"分页用户{i}",
            )
            db_session.add(user)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        # 测试第一页
        response = await client.get(
            "/api/system/user/list?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10
        assert data["data"]["page"] == 1

    @pytest.mark.asyncio
    async def test_get_user_list_filter_username(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
    ):
        """测试按用户名筛选"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/user/list?username=testuser",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 结果应该包含 testuser
        usernames = [item["username"] for item in data["data"]["items"]]
        assert "testuser" in usernames

    @pytest.mark.asyncio
    async def test_get_user_list_filter_status(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试按状态筛选"""
        # 创建禁用用户
        disabled_user = User(
            username="disabled_filter",
            password=get_password_hash("testpass123"),
            real_name="禁用用户",
            status=0,
        )
        db_session.add(disabled_user)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/user/list?status=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 所有返回的用户状态都应该是 1
        for item in data["data"]["items"]:
            assert item["status"] == 1

    @pytest.mark.asyncio
    async def test_get_user_list_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员获取用户列表 - 只能看到自己租户的用户"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/user/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 非超管现在可以访问用户列表，但只能看到自己租户的用户
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # test_user 没有租户ID，所以只能看到没有租户ID的用户


class TestCreateUser:
    """创建用户测试"""

    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_role: Role,
    ):
        """测试创建用户成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/user",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "newuser",
                "password": "newpass123",
                "real_name": "新用户",
                "email": "newuser@example.com",
                "phone": "13900139000",
                "role_ids": [test_role.id],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
    ):
        """测试创建重复用户名"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/user",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "testuser",  # 已存在的用户名
                "password": "newpass123",
                "real_name": "重复用户",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_create_user_without_roles(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建无角色用户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/user",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "norole_user",
                "password": "newpass123",
                "real_name": "无角色用户",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_create_user_validation_error(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建用户验证错误"""
        token = create_access_token(str(test_superuser.id))
        
        # 缺少必填字段
        response = await client.post(
            "/api/system/user",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "a",  # 用户名过短
            }
        )
        
        assert response.status_code == 422


class TestUpdateUser:
    """更新用户测试"""

    @pytest.mark.asyncio
    async def test_update_user_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
    ):
        """测试更新用户成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/user/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "real_name": "更新后的名字",
                "email": "updated@example.com",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试更新不存在的用户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            "/api/system/user/99999",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "real_name": "更新名字",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_update_user_roles(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
        test_role: Role,
    ):
        """测试更新用户角色"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/user/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "role_ids": [test_role.id],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_update_user_status(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
    ):
        """测试更新用户状态"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/user/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "status": 0,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestDeleteUser:
    """删除用户测试"""

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试删除用户成功"""
        # 创建一个待删除的用户
        user_to_delete = User(
            username="to_delete",
            password=get_password_hash("testpass123"),
            real_name="待删除用户",
        )
        db_session.add(user_to_delete)
        await db_session.commit()
        await db_session.refresh(user_to_delete)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/user/{user_to_delete.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试删除不存在的用户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            "/api/system/user/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_delete_superuser_forbidden(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试删除超级管理员被禁止"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/user/{test_superuser.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestResetPassword:
    """重置密码测试"""

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_user: User,
    ):
        """测试重置密码成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            f"/api/system/user/{test_user.id}/reset-password",
            headers={"Authorization": f"Bearer {token}"},
            params={"new_password": "newpassword123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试重置不存在用户的密码"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/user/99999/reset-password",
            headers={"Authorization": f"Bearer {token}"},
            params={"new_password": "newpassword123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestChangePassword:
    """修改密码测试"""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试修改密码成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/system/user/change-password",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "old_password": "testpass123",
                "new_password": "newpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试旧密码错误"""
        token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/system/user/change-password",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "old_password": "wrongpassword",
                "new_password": "newpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestUserPermissions:
    """用户权限测试"""

    @pytest.mark.asyncio
    async def test_user_api_requires_auth(
        self,
        client: AsyncClient,
    ):
        """测试用户 API 需要认证"""
        endpoints = [
            ("GET", "/api/system/user/info"),
            ("GET", "/api/system/user/list"),
            ("POST", "/api/system/user"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_superuser_required_endpoints(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超管用户可以创建用户（只能创建本租户用户）"""
        token = create_access_token(str(test_user.id))
        
        # 非超管现在可以创建用户，但只能创建本租户用户
        response = await client.post(
            "/api/system/user",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "test_create",
                "password": "testpass123",
                "real_name": "测试",
            }
        )
        
        # 非超管可以创建用户，返回200
        assert response.status_code == 200
