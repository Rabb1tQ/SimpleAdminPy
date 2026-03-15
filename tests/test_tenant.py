"""
租户模块测试
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models import User, Tenant


class TestGetTenantList:
    """获取租户列表测试"""

    @pytest.mark.asyncio
    async def test_get_tenant_list_as_superuser(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
        test_tenant2: Tenant,
    ):
        """测试超级管理员获取租户列表"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/tenant/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_tenant_list_pagination(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试租户列表分页"""
        # 创建多个租户
        for i in range(15):
            tenant = Tenant(
                name=f"租户{i}",
                code=f"tenant_{i}",
                status=1,
            )
            db_session.add(tenant)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        # 测试第一页
        response = await client.get(
            "/api/system/tenant/list?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10

    @pytest.mark.asyncio
    async def test_get_tenant_list_forbidden_for_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员无法获取租户列表"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/tenant/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_tenant_list_search_by_name(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
        test_tenant2: Tenant,
    ):
        """测试按名称搜索租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/tenant/list?name=测试租户",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["total"] >= 1


class TestGetTenantDetail:
    """获取租户详情测试"""

    @pytest.mark.asyncio
    async def test_get_tenant_detail_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
    ):
        """测试获取租户详情成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试租户"
        assert data["data"]["code"] == "test_tenant"

    @pytest.mark.asyncio
    async def test_get_tenant_detail_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试获取不存在的租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/tenant/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tenant_detail_forbidden_for_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
    ):
        """测试非超级管理员无法获取租户详情"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestCreateTenant:
    """创建租户测试"""

    @pytest.mark.asyncio
    async def test_create_tenant_success(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建租户成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/tenant",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "新租户",
                "code": "new_tenant",
                "contact": "联系人",
                "phone": "13800000000",
                "email": "new@example.com",
                "status": 1,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "新租户"

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_code(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
    ):
        """测试创建重复编码的租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/tenant",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "另一个租户",
                "code": "test_tenant",  # 已存在的编码
                "status": 1,
            }
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_tenant_forbidden_for_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员无法创建租户"""
        token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/system/tenant",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "新租户",
                "code": "new_tenant",
                "status": 1,
            }
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_tenant_missing_required_fields(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建租户缺少必填字段"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/tenant",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "新租户",
                # 缺少 code 字段
            }
        )
        
        assert response.status_code == 422


class TestUpdateTenant:
    """更新租户测试"""

    @pytest.mark.asyncio
    async def test_update_tenant_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
    ):
        """测试更新租户成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "更新后的租户",
                "code": "test_tenant",
                "contact": "新联系人",
                "status": 1,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试更新不存在的租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            "/api/system/tenant/99999",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "更新后的租户",
                "code": "test_code",
                "status": 1,
            }
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_tenant_forbidden_for_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
    ):
        """测试非超级管理员无法更新租户"""
        token = create_access_token(str(test_user.id))
        
        response = await client.put(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "更新后的租户",
                "code": "test_tenant",
                "status": 1,
            }
        )
        
        assert response.status_code == 403


class TestDeleteTenant:
    """删除租户测试"""

    @pytest.mark.asyncio
    async def test_delete_tenant_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试删除租户成功"""
        # 创建一个新租户用于删除
        tenant = Tenant(
            name="待删除租户",
            code="to_delete",
            status=1,
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/tenant/{tenant.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_delete_tenant_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试删除不存在的租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            "/api/system/tenant/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_tenant_forbidden_for_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
    ):
        """测试非超级管理员无法删除租户"""
        token = create_access_token(str(test_user.id))
        
        response = await client.delete(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_tenant_with_users(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
        tenant_admin: User,
    ):
        """测试删除有用户的租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 应该返回错误，因为租户下有用户
        assert response.status_code == 400


class TestTenantStatus:
    """租户状态测试"""

    @pytest.mark.asyncio
    async def test_disable_tenant(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
    ):
        """测试禁用租户"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/tenant/{test_tenant.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": test_tenant.name,
                "code": test_tenant.code,
                "status": 0,  # 禁用
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_all_tenants_for_select(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_tenant: Tenant,
        test_tenant2: Tenant,
    ):
        """测试获取所有启用的租户（用于下拉选择）"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/tenant/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 2
