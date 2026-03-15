"""
日志模块测试
"""
import pytest
from datetime import datetime
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models import User, OperationLog, LoginLog


class TestOperationLogList:
    """操作日志列表测试"""

    @pytest.mark.asyncio
    async def test_get_log_list_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试获取操作日志列表成功"""
        # 创建测试日志
        log = OperationLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            module="系统管理",
            action="测试操作",
            method="GET",
            url="/api/test",
            ip="127.0.0.1",
            status=1,
            duration=100,
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_log_list_pagination(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试操作日志列表分页"""
        # 创建多个日志
        for i in range(15):
            log = OperationLog(
                user_id=test_superuser.id,
                username=test_superuser.username,
                module=f"模块{i}",
                action="操作",
                method="GET",
                url=f"/api/test/{i}",
                ip="127.0.0.1",
                status=1,
                duration=100,
            )
            db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/list?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10

    @pytest.mark.asyncio
    async def test_get_log_list_filter_username(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试按用户名筛选操作日志"""
        log = OperationLog(
            user_id=test_superuser.id,
            username="admin",
            module="系统管理",
            action="测试",
            method="GET",
            url="/api/test",
            ip="127.0.0.1",
            status=1,
            duration=100,
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/list?username=admin",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_log_list_filter_module(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试按模块筛选操作日志"""
        log = OperationLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            module="用户管理",
            action="测试",
            method="GET",
            url="/api/test",
            ip="127.0.0.1",
            status=1,
            duration=100,
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/list?module=用户管理",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_log_list_filter_status(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试按状态筛选操作日志"""
        # 创建成功日志
        success_log = OperationLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            module="系统管理",
            action="成功操作",
            method="GET",
            url="/api/test",
            ip="127.0.0.1",
            status=1,
            duration=100,
        )
        db_session.add(success_log)
        
        # 创建失败日志
        fail_log = OperationLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            module="系统管理",
            action="失败操作",
            method="GET",
            url="/api/test",
            ip="127.0.0.1",
            status=0,
            duration=100,
            error_msg="测试错误",
        )
        db_session.add(fail_log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/list?status=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        for item in data["data"]["items"]:
            assert item["status"] == 1

    @pytest.mark.asyncio
    async def test_get_log_list_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员获取操作日志列表"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/log/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestOperationLogDetail:
    """操作日志详情测试"""

    @pytest.mark.asyncio
    async def test_get_log_detail_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试获取操作日志详情成功"""
        log = OperationLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            module="系统管理",
            action="测试操作",
            method="POST",
            url="/api/test",
            ip="127.0.0.1",
            status=1,
            duration=150,
            request_data='{"key": "value"}',
            response_data='{"result": "success"}',
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            f"/api/system/log/{log.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["module"] == "系统管理"
        assert data["data"]["action"] == "测试操作"

    @pytest.mark.asyncio
    async def test_get_log_detail_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试获取不存在的操作日志详情"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_get_log_detail_with_error(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试获取带错误信息的操作日志详情"""
        log = OperationLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            module="系统管理",
            action="失败操作",
            method="GET",
            url="/api/test",
            ip="127.0.0.1",
            status=0,
            duration=50,
            error_msg="操作失败：参数错误",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            f"/api/system/log/{log.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == 0
        assert data["data"]["error_msg"] == "操作失败：参数错误"


class TestLoginLogList:
    """登录日志列表测试"""

    @pytest.mark.asyncio
    async def test_get_login_log_list_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试获取登录日志列表成功"""
        log = LoginLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            ip="127.0.0.1",
            status=1,
            msg="登录成功",
            browser="Chrome",
            os="Windows",
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/login/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_login_log_list_pagination(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试登录日志列表分页"""
        # 创建多个登录日志
        for i in range(15):
            log = LoginLog(
                user_id=test_superuser.id,
                username=test_superuser.username,
                ip=f"192.168.1.{i}",
                status=1,
                msg="登录成功",
            )
            db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/login/list?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10

    @pytest.mark.asyncio
    async def test_get_login_log_list_filter_username(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试按用户名筛选登录日志"""
        log = LoginLog(
            user_id=test_superuser.id,
            username="admin",
            ip="127.0.0.1",
            status=1,
            msg="登录成功",
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/login/list?username=admin",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_login_log_list_filter_status(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试按状态筛选登录日志"""
        # 创建成功日志
        success_log = LoginLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            ip="127.0.0.1",
            status=1,
            msg="登录成功",
        )
        db_session.add(success_log)
        
        # 创建失败日志
        fail_log = LoginLog(
            user_id=None,
            username="unknown",
            ip="127.0.0.1",
            status=0,
            msg="密码错误",
        )
        db_session.add(fail_log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/login/list?status=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        for item in data["data"]["items"]:
            assert item["status"] == 1

    @pytest.mark.asyncio
    async def test_get_login_log_list_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员获取登录日志列表"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/log/login/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestLoginLogExport:
    """登录日志导出测试"""

    @pytest.mark.asyncio
    async def test_export_login_log_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试导出登录日志成功"""
        log = LoginLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            ip="127.0.0.1",
            status=1,
            msg="登录成功",
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/login-export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        # 检查是否是 CSV 响应
        assert "text/csv" in response.headers.get("content-type", "") or \
               response.headers.get("content-disposition") is not None

    @pytest.mark.asyncio
    async def test_export_login_log_with_filter(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试带筛选条件导出登录日志"""
        log = LoginLog(
            user_id=test_superuser.id,
            username=test_superuser.username,
            ip="127.0.0.1",
            status=1,
            msg="登录成功",
        )
        db_session.add(log)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/log/login-export?username=admin&status=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_login_log_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员导出登录日志"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/log/login-export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestLogPermissions:
    """日志权限测试"""

    @pytest.mark.asyncio
    async def test_log_api_requires_auth(
        self,
        client: AsyncClient,
    ):
        """测试日志 API 需要认证"""
        endpoints = [
            ("GET", "/api/system/log/list"),
            ("GET", "/api/system/log/login/list"),
            ("GET", "/api/system/log/login-export"),
        ]
        
        for method, endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"{method} {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_log_api_requires_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试日志 API 需要超级管理员权限"""
        token = create_access_token(str(test_user.id))
        
        endpoints = [
            "/api/system/log/list",
            "/api/system/log/login/list",
            "/api/system/log/1",
        ]
        
        for endpoint in endpoints:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 403, f"{endpoint} should require superuser"
