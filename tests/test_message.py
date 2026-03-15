"""
消息通知中心测试用例
"""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Role, Tenant
from app.models.system.message import Message, MessageSendLog


class TestGetMessageList:
    """获取消息列表测试"""

    @pytest.mark.asyncio
    async def test_get_message_list_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试获取消息列表成功"""
        # 创建测试消息
        message = Message(
            title="测试消息",
            content="这是一条测试消息",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
        )
        db_session.add(message)
        await db_session.commit()

        response = await client.get(
            "/api/message/list",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_message_list_pagination(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试消息列表分页"""
        # 创建多条测试消息
        for i in range(15):
            message = Message(
                title=f"测试消息{i}",
                content=f"这是第{i}条测试消息",
                type="SYSTEM",
                sender_id=1,
                sender_tenant_id=None,
                receiver_id=test_user.id,
            )
            db_session.add(message)
        await db_session.commit()

        response = await client.get(
            "/api/message/list",
            params={"page": 1, "page_size": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10
        assert data["data"]["total"] == 15

    @pytest.mark.asyncio
    async def test_get_message_list_filter_type(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试按类型过滤消息列表"""
        # 创建不同类型的消息
        message1 = Message(
            title="系统消息",
            content="系统消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
        )
        message2 = Message(
            title="业务消息",
            content="业务消息内容",
            type="BUSINESS",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
        )
        db_session.add_all([message1, message2])
        await db_session.commit()

        response = await client.get(
            "/api/message/list",
            params={"type": "SYSTEM"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["type"] == "SYSTEM"

    @pytest.mark.asyncio
    async def test_get_message_list_filter_is_read(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试按已读状态过滤消息列表"""
        # 创建已读和未读消息
        message1 = Message(
            title="已读消息",
            content="已读消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
            is_read=1,
        )
        message2 = Message(
            title="未读消息",
            content="未读消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
            is_read=0,
        )
        db_session.add_all([message1, message2])
        await db_session.commit()

        response = await client.get(
            "/api/message/list",
            params={"is_read": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["is_read"] == 0

    @pytest.mark.asyncio
    async def test_get_message_list_without_token(self, client: AsyncClient):
        """测试未登录获取消息列表"""
        response = await client.get("/api/message/list")
        assert response.status_code == 401


class TestGetUnreadCount:
    """获取未读消息数量测试"""

    @pytest.mark.asyncio
    async def test_get_unread_count_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试获取未读消息数量成功"""
        # 创建未读消息
        for i in range(3):
            message = Message(
                title=f"未读消息{i}",
                content=f"未读消息内容{i}",
                type="SYSTEM",
                sender_id=1,
                sender_tenant_id=None,
                receiver_id=test_user.id,
                is_read=0,
            )
            db_session.add(message)
        # 创建已读消息
        message_read = Message(
            title="已读消息",
            content="已读消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
            is_read=1,
        )
        db_session.add(message_read)
        await db_session.commit()

        response = await client.get(
            "/api/message/unread-count",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["count"] == 3

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试无未读消息时返回0"""
        response = await client.get(
            "/api/message/unread-count",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["count"] == 0


class TestMarkMessageRead:
    """标记消息已读测试"""

    @pytest.mark.asyncio
    async def test_mark_message_read_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试标记消息已读成功"""
        # 创建未读消息
        message = Message(
            title="测试消息",
            content="测试消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
            is_read=0,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        response = await client.put(
            f"/api/message/{message.id}/read",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # 验证消息已标记为已读
        await db_session.refresh(message)
        assert message.is_read == 1
        assert message.read_at is not None

    @pytest.mark.asyncio
    async def test_mark_message_read_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """测试标记不存在的消息已读"""
        response = await client.put(
            "/api/message/99999/read",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_message_read_other_user(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """测试标记其他用户的消息已读（应该失败）"""
        # 创建属于其他用户的消息
        other_user = User(
            username="other_user",
            password="hashed_password",
            real_name="其他用户",
            is_superuser=False,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        message = Message(
            title="其他用户的消息",
            content="其他用户的消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=other_user.id,
            is_read=0,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        response = await client.put(
            f"/api/message/{message.id}/read",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestMarkMessageUnread:
    """标记消息未读测试"""

    @pytest.mark.asyncio
    async def test_mark_message_unread_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试标记消息未读成功"""
        # 创建已读消息
        message = Message(
            title="测试消息",
            content="测试消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
            is_read=1,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        response = await client.put(
            f"/api/message/{message.id}/unread",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # 验证消息已标记为未读
        await db_session.refresh(message)
        assert message.is_read == 0
        assert message.read_at is None


class TestReadAllMessages:
    """一键全部已读测试"""

    @pytest.mark.asyncio
    async def test_read_all_messages_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试一键全部已读成功"""
        # 创建多条未读消息
        for i in range(5):
            message = Message(
                title=f"未读消息{i}",
                content=f"未读消息内容{i}",
                type="SYSTEM",
                sender_id=1,
                sender_tenant_id=None,
                receiver_id=test_user.id,
                is_read=0,
            )
            db_session.add(message)
        await db_session.commit()

        response = await client.put(
            "/api/message/read-all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # 验证所有消息都已标记为已读
        from sqlalchemy import select
        result = await db_session.execute(
            select(Message).where(Message.receiver_id == test_user.id, Message.is_read == 0)
        )
        unread_messages = result.scalars().all()
        assert len(unread_messages) == 0


class TestDeleteMessage:
    """删除消息测试"""

    @pytest.mark.asyncio
    async def test_delete_message_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试删除消息成功"""
        # 创建测试消息
        message = Message(
            title="测试消息",
            content="测试消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=test_user.id,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        response = await client.delete(
            f"/api/message/{message.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # 验证消息已被软删除
        await db_session.refresh(message)
        assert message.is_deleted == 1

    @pytest.mark.asyncio
    async def test_delete_message_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """测试删除不存在的消息"""
        response = await client.delete(
            "/api/message/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestSendMessage:
    """发送消息测试"""

    @pytest.mark.asyncio
    async def test_send_message_to_user_success(
        self, client: AsyncClient, superuser_auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """测试发送消息给指定用户成功"""
        response = await client.post(
            "/api/message/send",
            json={
                "title": "测试消息",
                "content": "这是一条测试消息",
                "type": "SYSTEM",
                "receiver_type": "USER",
                "receiver_ids": [test_user.id],
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["send_count"] == 1

        # 验证消息已创建
        from sqlalchemy import select
        result = await db_session.execute(
            select(Message).where(Message.receiver_id == test_user.id)
        )
        messages = result.scalars().all()
        assert len(messages) == 1
        assert messages[0].title == "测试消息"

    @pytest.mark.asyncio
    async def test_send_message_to_all_users(
        self, client: AsyncClient, superuser_auth_headers: dict, test_user: User, test_superuser: User, db_session: AsyncSession
    ):
        """测试发送消息给全员成功"""
        response = await client.post(
            "/api/message/send",
            json={
                "title": "全员消息",
                "content": "这是一条全员消息",
                "type": "SYSTEM",
                "receiver_type": "ALL",
                "receiver_ids": [],
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["send_count"] >= 2  # 至少有test_user和test_superuser

    @pytest.mark.asyncio
    async def test_send_message_to_tenant(
        self, client: AsyncClient, superuser_auth_headers: dict, test_tenant: Tenant, tenant_admin: User, db_session: AsyncSession
    ):
        """测试发送消息给指定租户成功"""
        response = await client.post(
            "/api/message/send",
            json={
                "title": "租户消息",
                "content": "这是一条租户消息",
                "type": "BUSINESS",
                "receiver_type": "TENANT",
                "receiver_ids": [test_tenant.id],
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["send_count"] >= 1  # 至少有tenant_admin

    @pytest.mark.asyncio
    async def test_send_message_to_role(
        self, client: AsyncClient, superuser_auth_headers: dict, test_role: Role, user_with_role: User, db_session: AsyncSession
    ):
        """测试发送消息给指定角色成功"""
        response = await client.post(
            "/api/message/send",
            json={
                "title": "角色消息",
                "content": "这是一条角色消息",
                "type": "BUSINESS",
                "receiver_type": "ROLE",
                "receiver_ids": [test_role.id],
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["send_count"] >= 1  # 至少有user_with_role

    @pytest.mark.asyncio
    async def test_send_message_validation_error(
        self, client: AsyncClient, superuser_auth_headers: dict
    ):
        """测试发送消息参数校验失败"""
        response = await client.post(
            "/api/message/send",
            json={
                "title": "",  # 标题为空
                "content": "测试内容",
                "type": "SYSTEM",
                "receiver_type": "USER",
                "receiver_ids": [],
            },
            headers=superuser_auth_headers,
        )

        # API返回400 Bad Request而不是422
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_send_message_non_superuser_forbidden(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """测试非管理员发送消息被拒绝"""
        response = await client.post(
            "/api/message/send",
            json={
                "title": "测试消息",
                "content": "这是一条测试消息",
                "type": "SYSTEM",
                "receiver_type": "USER",
                "receiver_ids": [test_user.id],
            },
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestGetSendLog:
    """获取发送记录测试"""

    @pytest.mark.asyncio
    async def test_get_send_log_success(
        self, client: AsyncClient, superuser_auth_headers: dict, test_superuser: User, db_session: AsyncSession
    ):
        """测试获取发送记录成功"""
        # 创建发送记录
        send_log = MessageSendLog(
            title="测试消息",
            content="测试消息内容",
            type="SYSTEM",
            sender_id=test_superuser.id,
            sender_tenant_id=None,
            receiver_type="USER",
            receiver_ids="[1, 2]",
            send_count=2,
        )
        db_session.add(send_log)
        await db_session.commit()

        response = await client.get(
            "/api/message/send-log",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_send_log_pagination(
        self, client: AsyncClient, superuser_auth_headers: dict, test_superuser: User, db_session: AsyncSession
    ):
        """测试发送记录分页"""
        # 创建多条发送记录
        for i in range(15):
            send_log = MessageSendLog(
                title=f"测试消息{i}",
                content=f"测试消息内容{i}",
                type="SYSTEM",
                sender_id=test_superuser.id,
                sender_tenant_id=None,
                receiver_type="USER",
                receiver_ids="[1]",
                send_count=1,
            )
            db_session.add(send_log)
        await db_session.commit()

        response = await client.get(
            "/api/message/send-log",
            params={"page": 1, "page_size": 10},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 10
        assert data["data"]["total"] == 15

    @pytest.mark.asyncio
    async def test_get_send_log_non_superuser_forbidden(
        self, client: AsyncClient, auth_headers: dict
    ):
        """测试非管理员获取发送记录被拒绝"""
        response = await client.get(
            "/api/message/send-log",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestTenantIsolation:
    """租户隔离测试"""

    @pytest.mark.asyncio
    async def test_tenant_user_can_only_see_own_messages(
        self, client: AsyncClient, test_tenant: Tenant, tenant_admin: User, db_session: AsyncSession
    ):
        """测试租户用户只能看到自己的消息"""
        # 创建属于租户管理员的消息
        message1 = Message(
            title="租户管理员消息",
            content="租户管理员消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=test_tenant.id,
            receiver_id=tenant_admin.id,
        )
        db_session.add(message1)

        # 创建属于其他用户的消息
        other_user = User(
            username="other_tenant_user",
            password="hashed_password",
            real_name="其他租户用户",
            is_superuser=False,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        message2 = Message(
            title="其他用户消息",
            content="其他用户消息内容",
            type="SYSTEM",
            sender_id=1,
            sender_tenant_id=None,
            receiver_id=other_user.id,
        )
        db_session.add(message2)
        await db_session.commit()

        # 使用create_access_token直接生成token
        from app.core.security import create_access_token
        token = create_access_token(str(tenant_admin.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 获取消息列表
        response = await client.get(
            "/api/message/list",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # 只能看到自己的消息
        for item in data["data"]["items"]:
            assert item["receiver_id"] == tenant_admin.id
