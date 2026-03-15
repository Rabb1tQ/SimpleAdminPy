"""
菜单模块测试
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models import Menu, Role, User


class TestGetUserMenus:
    """获取用户菜单测试"""

    @pytest.mark.asyncio
    async def test_get_user_menus_superuser(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_menu: Menu,
    ):
        """测试超级管理员获取菜单"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/menu/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_user_menus_normal_user(
        self,
        client: AsyncClient,
        user_with_role: User,
        role_with_menu: Role,
        test_menu: Menu,
    ):
        """测试普通用户获取菜单"""
        token = create_access_token(str(user_with_role.id))
        
        response = await client.get(
            "/api/system/menu/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_user_menus_without_token(
        self,
        client: AsyncClient,
    ):
        """测试未登录获取菜单"""
        response = await client.get("/api/system/menu/all")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_menus_no_permission(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试无权限用户获取菜单"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/menu/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 无权限用户应该返回空列表
        assert data["data"] == []


class TestGetMenuList:
    """获取菜单列表测试"""

    @pytest.mark.asyncio
    async def test_get_menu_list_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_menu: Menu,
    ):
        """测试获取菜单列表成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/menu/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_menu_list_filter_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_menu: Menu,
    ):
        """测试按状态筛选菜单"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/menu/list?status=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_menu_list_tree_structure(
        self,
        client: AsyncClient,
        test_user: User,
        db_session,
    ):
        """测试菜单树形结构"""
        # 创建父菜单
        parent_menu = Menu(
            name="父菜单",
            path="/parent",
            title="父菜单",
            icon="parent-icon",
            sort=1,
            status=1,
            menu_type=1,
        )
        db_session.add(parent_menu)
        await db_session.commit()
        await db_session.refresh(parent_menu)
        
        # 创建子菜单
        child_menu = Menu(
            name="子菜单",
            path="/parent/child",
            component="parent/child/index",
            title="子菜单",
            icon="child-icon",
            sort=1,
            status=1,
            parent_id=parent_menu.id,
            menu_type=2,
        )
        db_session.add(child_menu)
        await db_session.commit()
        
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/menu/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestGetMenuDetail:
    """获取菜单详情测试"""

    @pytest.mark.asyncio
    async def test_get_menu_detail_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_menu: Menu,
    ):
        """测试获取菜单详情成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            f"/api/system/menu/{test_menu.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试菜单"
        assert data["data"]["path"] == "/test"

    @pytest.mark.asyncio
    async def test_get_menu_detail_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试获取不存在的菜单详情"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/menu/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestCreateMenu:
    """创建菜单测试"""

    @pytest.mark.asyncio
    async def test_create_menu_success(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建菜单成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/menu",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "新菜单",
                "path": "/new-menu",
                "component": "new-menu/index",
                "title": "新菜单",
                "icon": "new-icon",
                "sort": 1,
                "menu_type": 2,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_directory_menu(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建目录类型菜单"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/menu",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "目录菜单",
                "path": "/directory",
                "title": "目录菜单",
                "icon": "directory-icon",
                "sort": 1,
                "menu_type": 1,  # 目录类型
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_create_menu_with_parent(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_menu: Menu,
    ):
        """测试创建子菜单"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/menu",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "parent_id": test_menu.id,
                "name": "子菜单",
                "path": "/test/child",
                "component": "test/child/index",
                "title": "子菜单",
                "icon": "child-icon",
                "sort": 1,
                "menu_type": 2,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_create_menu_with_permission(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建带权限标识的菜单"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/menu",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "权限菜单",
                "path": "/permission",
                "component": "permission/index",
                "title": "权限菜单",
                "icon": "permission-icon",
                "sort": 1,
                "menu_type": 2,
                "permission": "permission:view,permission:edit",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_create_menu_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员创建菜单"""
        token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/system/menu",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "普通用户创建",
                "path": "/user-menu",
                "title": "用户菜单",
                "sort": 1,
                "menu_type": 2,
            }
        )
        
        assert response.status_code == 403


class TestUpdateMenu:
    """更新菜单测试"""

    @pytest.mark.asyncio
    async def test_update_menu_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_menu: Menu,
    ):
        """测试更新菜单成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/menu/{test_menu.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "更新后的菜单",
                "icon": "updated-icon",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_update_menu_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试更新不存在的菜单"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            "/api/system/menu/99999",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "更新标题",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_update_menu_status(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_menu: Menu,
    ):
        """测试更新菜单状态"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/menu/{test_menu.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "status": 0,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestDeleteMenu:
    """删除菜单测试"""

    @pytest.mark.asyncio
    async def test_delete_menu_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试删除菜单成功"""
        # 创建一个待删除的菜单
        menu_to_delete = Menu(
            name="待删除菜单",
            path="/to-delete",
            title="待删除菜单",
            sort=99,
            status=1,
            menu_type=2,
        )
        db_session.add(menu_to_delete)
        await db_session.commit()
        await db_session.refresh(menu_to_delete)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/menu/{menu_to_delete.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_delete_menu_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试删除不存在的菜单"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            "/api/system/menu/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_delete_menu_with_children(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试删除有子菜单的菜单"""
        # 创建父菜单
        parent_menu = Menu(
            name="父菜单",
            path="/parent-delete",
            title="父菜单",
            sort=1,
            status=1,
            menu_type=1,
        )
        db_session.add(parent_menu)
        await db_session.commit()
        await db_session.refresh(parent_menu)
        
        # 创建子菜单
        child_menu = Menu(
            name="子菜单",
            path="/parent-delete/child",
            title="子菜单",
            sort=1,
            status=1,
            parent_id=parent_menu.id,
            menu_type=2,
        )
        db_session.add(child_menu)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        # 尝试删除父菜单（应该失败）
        response = await client.delete(
            f"/api/system/menu/{parent_menu.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0  # 应该失败

    @pytest.mark.asyncio
    async def test_delete_menu_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
        test_menu: Menu,
    ):
        """测试非超级管理员删除菜单"""
        token = create_access_token(str(test_user.id))
        
        response = await client.delete(
            f"/api/system/menu/{test_menu.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestMenuPermissions:
    """菜单权限测试"""

    @pytest.mark.asyncio
    async def test_menu_api_requires_auth(
        self,
        client: AsyncClient,
    ):
        """测试菜单 API 需要认证"""
        endpoints = [
            ("GET", "/api/system/menu/all"),
            ("GET", "/api/system/menu/list"),
            ("POST", "/api/system/menu"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_superuser_required_for_modify(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试修改操作需要超级管理员权限"""
        token = create_access_token(str(test_user.id))
        
        # 创建菜单需要超级管理员权限
        response = await client.post(
            "/api/system/menu",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "测试菜单",
                "path": "/test",
                "title": "测试",
                "sort": 1,
                "menu_type": 2,
            }
        )
        assert response.status_code == 403
        
        # 更新菜单需要超级管理员权限
        response = await client.put(
            "/api/system/menu/1",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "更新"}
        )
        assert response.status_code == 403
        
        # 删除菜单需要超级管理员权限
        response = await client.delete(
            "/api/system/menu/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


class TestMenuTree:
    """菜单树测试"""

    @pytest.mark.asyncio
    async def test_menu_tree_structure(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试菜单树结构正确性"""
        # 创建多级菜单
        level1 = Menu(
            name="一级菜单",
            path="/level1",
            title="一级菜单",
            icon="l1-icon",
            sort=1,
            status=1,
            menu_type=1,
        )
        db_session.add(level1)
        await db_session.commit()
        await db_session.refresh(level1)
        
        level2 = Menu(
            name="二级菜单",
            path="/level1/level2",
            component="level2/index",
            title="二级菜单",
            icon="l2-icon",
            sort=1,
            status=1,
            parent_id=level1.id,
            menu_type=2,
        )
        db_session.add(level2)
        await db_session.commit()
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.get(
            "/api/system/menu/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
