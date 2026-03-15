"""
字典模块测试
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models import DictType, DictData, User


class TestDictTypeList:
    """字典类型列表测试"""

    @pytest.mark.asyncio
    async def test_get_dict_type_list_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
    ):
        """测试获取字典类型列表成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/type/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_dict_type_list_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        db_session,
    ):
        """测试字典类型列表分页"""
        # 创建多个字典类型
        for i in range(15):
            dict_type = DictType(
                name=f"分页字典{i}",
                code=f"page_dict_{i}",
                status=1,
            )
            db_session.add(dict_type)
        await db_session.commit()
        
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/type/list?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10

    @pytest.mark.asyncio
    async def test_get_dict_type_list_filter_name(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
    ):
        """测试按名称筛选字典类型"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/type/list?name=测试",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_dict_type_list_filter_code(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
    ):
        """测试按编码筛选字典类型"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/type/list?code=test_dict",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestDictTypeAll:
    """获取所有字典类型测试"""

    @pytest.mark.asyncio
    async def test_get_all_dict_types_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
    ):
        """测试获取所有字典类型成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/type/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)


class TestDictTypeDetail:
    """字典类型详情测试"""

    @pytest.mark.asyncio
    async def test_get_dict_type_detail_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
    ):
        """测试获取字典类型详情成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            f"/api/system/dict/type/{test_dict.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试字典"
        assert data["data"]["code"] == "test_dict"

    @pytest.mark.asyncio
    async def test_get_dict_type_detail_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试获取不存在的字典类型详情"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/type/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestCreateDictType:
    """创建字典类型测试"""

    @pytest.mark.asyncio
    async def test_create_dict_type_success(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建字典类型成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/dict/type",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "新字典类型",
                "code": "new_dict_type",
                "remark": "新创建的字典类型",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_dict_type_duplicate_code(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_dict: DictType,
    ):
        """测试创建重复编码的字典类型"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/dict/type",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "重复编码字典",
                "code": "test_dict",  # 已存在的编码
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_create_dict_type_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试非超级管理员创建字典类型"""
        token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/system/dict/type",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "普通用户创建",
                "code": "user_created_dict",
            }
        )
        
        assert response.status_code == 403


class TestUpdateDictType:
    """更新字典类型测试"""

    @pytest.mark.asyncio
    async def test_update_dict_type_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_dict: DictType,
    ):
        """测试更新字典类型成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/dict/type/{test_dict.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "更新后的字典名",
                "remark": "更新后的备注",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_update_dict_type_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试更新不存在的字典类型"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            "/api/system/dict/type/99999",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "更新名字",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestDeleteDictType:
    """删除字典类型测试"""

    @pytest.mark.asyncio
    async def test_delete_dict_type_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
    ):
        """测试删除字典类型成功"""
        # 创建一个待删除的字典类型
        dict_to_delete = DictType(
            name="待删除字典",
            code="to_delete_dict",
            status=1,
        )
        db_session.add(dict_to_delete)
        await db_session.commit()
        await db_session.refresh(dict_to_delete)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/dict/type/{dict_to_delete.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_delete_dict_type_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试删除不存在的字典类型"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            "/api/system/dict/type/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestDictDataList:
    """字典数据列表测试"""

    @pytest.mark.asyncio
    async def test_get_dict_data_list_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict_item: DictData,
    ):
        """测试获取字典数据列表成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/data/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_dict_data_list_filter_dict_type(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
        test_dict_item: DictData,
    ):
        """测试按字典类型筛选字典数据"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            f"/api/system/dict/data/list?dict_type_id={test_dict.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_dict_data_list_filter_label(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict_item: DictData,
    ):
        """测试按标签筛选字典数据"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/data/list?label=测试",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestDictDataByCode:
    """根据编码获取字典数据测试"""

    @pytest.mark.asyncio
    async def test_get_dict_data_by_code_success(
        self,
        client: AsyncClient,
        test_dict: DictType,
        test_dict_item: DictData,
    ):
        """测试根据编码获取字典数据成功"""
        response = await client.get(
            f"/api/system/dict/data/code/{test_dict.code}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_dict_data_by_code_not_found(
        self,
        client: AsyncClient,
    ):
        """测试根据不存在的编码获取字典数据"""
        response = await client.get(
            "/api/system/dict/data/code/nonexistent_code"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] == []


class TestDictDataDetail:
    """字典数据详情测试"""

    @pytest.mark.asyncio
    async def test_get_dict_data_detail_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict_item: DictData,
    ):
        """测试获取字典数据详情成功"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            f"/api/system/dict/data/{test_dict_item.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["label"] == "测试项"
        assert data["data"]["value"] == "test_value"

    @pytest.mark.asyncio
    async def test_get_dict_data_detail_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """测试获取不存在的字典数据详情"""
        token = create_access_token(str(test_user.id))
        
        response = await client.get(
            "/api/system/dict/data/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestCreateDictData:
    """创建字典数据测试"""

    @pytest.mark.asyncio
    async def test_create_dict_data_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_dict: DictType,
    ):
        """测试创建字典数据成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/dict/data",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dict_type_id": test_dict.id,
                "label": "新字典项",
                "value": "new_value",
                "sort": 1,
                "status": 1,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_dict_data_invalid_dict_type(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试创建字典数据时使用无效的字典类型"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.post(
            "/api/system/dict/data",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dict_type_id": 99999,
                "label": "无效类型",
                "value": "invalid",
                "sort": 1,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0

    @pytest.mark.asyncio
    async def test_create_dict_data_non_superuser(
        self,
        client: AsyncClient,
        test_user: User,
        test_dict: DictType,
    ):
        """测试非超级管理员创建字典数据"""
        token = create_access_token(str(test_user.id))
        
        response = await client.post(
            "/api/system/dict/data",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dict_type_id": test_dict.id,
                "label": "普通用户创建",
                "value": "user_created",
                "sort": 1,
            }
        )
        
        assert response.status_code == 403


class TestUpdateDictData:
    """更新字典数据测试"""

    @pytest.mark.asyncio
    async def test_update_dict_data_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_dict_item: DictData,
    ):
        """测试更新字典数据成功"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            f"/api/system/dict/data/{test_dict_item.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "label": "更新后的标签",
                "sort": 99,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_update_dict_data_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试更新不存在的字典数据"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.put(
            "/api/system/dict/data/99999",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "label": "更新标签",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestDeleteDictData:
    """删除字典数据测试"""

    @pytest.mark.asyncio
    async def test_delete_dict_data_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        db_session,
        test_dict: DictType,
    ):
        """测试删除字典数据成功"""
        # 创建一个待删除的字典数据
        dict_data_to_delete = DictData(
            dict_type_id=test_dict.id,
            label="待删除项",
            value="to_delete",
            sort=99,
            status=1,
        )
        db_session.add(dict_data_to_delete)
        await db_session.commit()
        await db_session.refresh(dict_data_to_delete)
        
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            f"/api/system/dict/data/{dict_data_to_delete.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_delete_dict_data_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
    ):
        """测试删除不存在的字典数据"""
        token = create_access_token(str(test_superuser.id))
        
        response = await client.delete(
            "/api/system/dict/data/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 0


class TestDictPermissions:
    """字典权限测试"""

    @pytest.mark.asyncio
    async def test_dict_api_requires_auth(
        self,
        client: AsyncClient,
    ):
        """测试字典 API 需要认证"""
        endpoints = [
            ("GET", "/api/system/dict/type/list"),
            ("GET", "/api/system/dict/type/all"),
            ("GET", "/api/system/dict/data/list"),
            ("POST", "/api/system/dict/type"),
            ("POST", "/api/system/dict/data"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_dict_data_by_code_is_public(
        self,
        client: AsyncClient,
    ):
        """测试根据编码获取字典数据是公开接口"""
        response = await client.get("/api/system/dict/data/code/any_code")
        
        # 这个接口不需要认证
        assert response.status_code == 200
