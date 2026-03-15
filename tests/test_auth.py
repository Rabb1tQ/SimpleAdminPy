"""
认证模块测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from fastapi import FastAPI

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
)
from app.models import User, Role, Menu


class TestPasswordHash:
    """密码哈希测试"""

    def test_password_hash(self):
        """测试密码哈希生成"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_success(self):
        """测试密码验证成功"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """测试密码验证失败"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_different_passwords_different_hashes(self):
        """测试不同密码生成不同哈希"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # bcrypt 每次生成的哈希不同（因为有盐值）
        assert hash1 != hash2


class TestJWTToken:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "1"
        token = create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        user_id = "1"
        token = create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """测试解码访问令牌"""
        user_id = "123"
        token = create_access_token(user_id)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        """测试解码刷新令牌"""
        user_id = "123"
        token = create_refresh_token(user_id)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_verify_access_token(self):
        """测试验证访问令牌"""
        user_id = "123"
        token = create_access_token(user_id)
        
        verified_user_id = verify_token(token, "access")
        
        assert verified_user_id == user_id

    def test_verify_refresh_token(self):
        """测试验证刷新令牌"""
        user_id = "123"
        token = create_refresh_token(user_id)
        
        verified_user_id = verify_token(token, "refresh")
        
        assert verified_user_id == user_id

    def test_verify_token_wrong_type(self):
        """测试验证令牌类型错误"""
        user_id = "123"
        token = create_access_token(user_id)
        
        # 用 refresh 类型验证 access token 应该失败
        verified_user_id = verify_token(token, "refresh")
        
        assert verified_user_id is None

    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        invalid_token = "invalid.token.here"
        
        payload = decode_token(invalid_token)
        
        assert payload is None

    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        invalid_token = "invalid.token.here"
        
        result = verify_token(invalid_token, "access")
        
        assert result is None


class TestCaptchaAPI:
    """验证码 API 测试"""

    @pytest.mark.asyncio
    async def test_get_captcha(self, client: AsyncClient, mock_redis_deps):
        """测试获取验证码"""
        with patch("app.api.auth.get_redis", return_value=mock_redis_deps):
            response = await client.get("/api/auth/captcha")
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "key" in data["data"]
            assert "image" in data["data"]
            assert data["data"]["image"].startswith("data:image/png;base64,")


class TestLoginAPI:
    """登录 API 测试"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user: User,
        mock_redis: AsyncMock,
    ):
        """测试登录成功"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            with patch("app.api.system.online.set_online_user", new_callable=AsyncMock):
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "username": "testuser",
                        "password": "testpass123",
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 0
                assert "accessToken" in data["data"]
                assert "refreshToken" in data["data"]
                assert data["data"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_user: User,
        mock_redis: AsyncMock,
    ):
        """测试登录密码错误"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "testuser",
                    "password": "wrongpassword",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self,
        client: AsyncClient,
        mock_redis: AsyncMock,
    ):
        """测试登录用户不存在"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "nonexistent",
                    "password": "anypassword",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_login_disabled_user(
        self,
        client: AsyncClient,
        db_session,
        mock_redis: AsyncMock,
    ):
        """测试登录被禁用用户"""
        # 创建被禁用用户
        disabled_user = User(
            username="disabled_user",
            password=get_password_hash("testpass123"),
            real_name="被禁用用户",
            status=0,  # 禁用状态
        )
        db_session.add(disabled_user)
        await db_session.commit()
        
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/login",
                json={
                    "username": "disabled_user",
                    "password": "testpass123",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_login_with_captcha(
        self,
        client: AsyncClient,
        test_user: User,
        mock_redis: AsyncMock,
    ):
        """测试带验证码登录"""
        # 模拟 Redis 中存储的验证码（Redis 配置了 decode_responses=True，返回字符串）
        mock_redis.get = AsyncMock(return_value="test")
        mock_redis.delete = AsyncMock(return_value=1)
        
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            with patch("app.api.system.online.set_online_user", new_callable=AsyncMock):
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "username": "testuser",
                        "password": "testpass123",
                        "captcha_key": "test_key",
                        "captcha_code": "TEST",
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_login_wrong_captcha(
        self,
        client: AsyncClient,
        test_user: User,
        mock_redis: AsyncMock,
    ):
        """测试验证码错误（Redis 配置了 decode_responses=True，返回字符串）"""
        mock_redis.get = AsyncMock(return_value="correct")
        mock_redis.delete = AsyncMock(return_value=1)
        
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            with patch("app.api.system.online.set_online_user", new_callable=AsyncMock):
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "username": "testuser",
                        "password": "testpass123",
                        "captcha_key": "test_key",
                        "captcha_code": "wrong",
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
            assert data["code"] != 0


class TestRegisterAPI:
    """注册 API 测试"""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        client: AsyncClient,
        mock_redis: AsyncMock,
    ):
        """测试注册成功"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "newuser",
                    "password": "newpass123",
                    "real_name": "新用户",
                    "email": "newuser@example.com",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_register_username_exists(
        self,
        client: AsyncClient,
        test_user: User,
        mock_redis: AsyncMock,
    ):
        """测试注册用户名已存在"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "testuser",  # 已存在的用户名
                    "password": "newpass123",
                    "real_name": "新用户",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_register_short_username(
        self,
        client: AsyncClient,
        mock_redis: AsyncMock,
    ):
        """测试注册用户名过短"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "a",  # 用户名过短
                    "password": "newpass123",
                    "real_name": "新用户",
                }
            )
            
            assert response.status_code == 422  # 验证错误

    @pytest.mark.asyncio
    async def test_register_short_password(
        self,
        client: AsyncClient,
        mock_redis: AsyncMock,
    ):
        """测试注册密码过短"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            response = await client.post(
                "/api/auth/register",
                json={
                    "username": "newuser",
                    "password": "123",  # 密码过短
                    "real_name": "新用户",
                }
            )
            
            assert response.status_code == 422  # 验证错误


class TestLogoutAPI:
    """退出登录 API 测试"""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        client: AsyncClient,
        test_user: User,
        mock_redis: AsyncMock,
    ):
        """测试退出登录成功"""
        token = create_access_token(str(test_user.id))
        
        with patch("app.api.auth.get_redis_token", return_value=mock_redis):
            with patch("app.api.auth.get_redis", return_value=mock_redis):
                with patch("app.api.system.online.remove_online_user", new_callable=AsyncMock):
                    response = await client.post(
                        "/api/auth/logout",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_logout_without_token(
        self,
        client: AsyncClient,
    ):
        """测试未登录退出"""
        response = await client.post("/api/auth/logout")
        
        assert response.status_code == 401


class TestRefreshTokenAPI:
    """刷新 Token API 测试"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试刷新 Token 成功"""
        refresh_token = create_refresh_token(str(test_user.id))
        
        response = await client.post(
            "/api/auth/refresh",
            json={"refreshToken": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "accessToken" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(
        self,
        client: AsyncClient,
    ):
        """测试无效刷新 Token"""
        response = await client.post(
            "/api/auth/refresh",
            json={"refreshToken": "invalid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_refresh_token_with_access_token(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试使用 access token 刷新（应该失败）"""
        access_token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/auth/refresh",
            json={"refreshToken": access_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_refresh_token_disabled_user(
        self,
        client: AsyncClient,
        db_session,
    ):
        """测试禁用用户刷新 Token"""
        # 创建禁用用户
        disabled_user = User(
            username="disabled_refresh",
            password=get_password_hash("testpass123"),
            real_name="禁用用户",
            status=0,
        )
        db_session.add(disabled_user)
        await db_session.commit()
        await db_session.refresh(disabled_user)
        
        refresh_token = create_refresh_token(str(disabled_user.id))
        
        response = await client.post(
            "/api/auth/refresh",
            json={"refreshToken": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestLoginWithRole:
    """带角色的登录测试"""

    @pytest.mark.asyncio
    async def test_login_with_role(
        self,
        client: AsyncClient,
        user_with_role: User,
        test_role: Role,
        mock_redis: AsyncMock,
    ):
        """测试带角色的用户登录"""
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            with patch("app.api.system.online.set_online_user", new_callable=AsyncMock):
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "username": "testuser",
                        "password": "testpass123",
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 0
                assert test_role.code in data["data"]["roles"]

    @pytest.mark.asyncio
    async def test_login_with_permissions(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_role: Role,
        test_menu: Menu,
        mock_redis: AsyncMock,
    ):
        """测试带权限的用户登录"""
        # 设置菜单权限
        from sqlalchemy import insert
        from app.models.system.role import user_role, role_menu
        
        test_menu.perms = "user:list,user:create"
        # 直接插入关联表，避免懒加载问题
        await db_session.execute(
            insert(role_menu).values(role_id=test_role.id, menu_id=test_menu.id)
        )
        await db_session.execute(
            insert(user_role).values(user_id=test_user.id, role_id=test_role.id)
        )
        await db_session.commit()
        
        with patch("app.api.auth.get_redis", return_value=mock_redis):
            with patch("app.api.system.online.set_online_user", new_callable=AsyncMock):
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "username": "testuser",
                        "password": "testpass123",
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 0
                assert "user:list" in data["data"]["permissions"]
                assert "user:create" in data["data"]["permissions"]
