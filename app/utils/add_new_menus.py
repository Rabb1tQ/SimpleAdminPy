"""
添加新功能菜单脚本
"""
import asyncio

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models import Menu, Role, role_menu


async def add_new_menus():
    """添加新功能菜单"""
    async with async_session_maker() as db:
        # 检查是否已有租户管理菜单
        result = await db.execute(select(Menu).where(Menu.name == "Tenant"))
        if result.scalar_one_or_none():
            print("新菜单已存在，跳过添加")
            return

        # 获取系统管理目录的ID
        result = await db.execute(select(Menu).where(Menu.name == "System"))
        system_menu = result.scalar_one_or_none()
        system_parent_id = system_menu.id if system_menu else 1

        # 获取管理员角色
        result = await db.execute(select(Role).where(Role.code == "admin"))
        admin_role = result.scalar_one_or_none()
        admin_role_id = admin_role.id if admin_role else 1

        # 新增菜单
        new_menus = [
            # 租户管理菜单（放在系统管理下）
            Menu(
                parent_id=system_parent_id,
                name="Tenant",
                path="/system/tenant/index",
                component="system/tenant/index",
                title="租户管理",
                icon="ep:office-building",
                sort=9,
                menu_type=2,
                permission="system:tenant:list",
                status=1,
            ),
            # 安全设置（放在系统管理下）
            Menu(
                parent_id=system_parent_id,
                name="Security",
                path="/system/security/index",
                component="system/security/index",
                title="安全设置",
                icon="ep:lock",
                sort=10,
                menu_type=2,
                permission="system:security:list",
                status=1,
            ),
            # 消息中心目录
            Menu(
                parent_id=0,
                name="Message",
                path="/message",
                component="",
                title="消息中心",
                icon="ep:message",
                sort=2,
                menu_type=1,
                status=1,
            ),
            # 消息列表
            Menu(
                parent_id=0,  # 需要后续更新
                name="MessageList",
                path="/message/list/index",
                component="message/list/index",
                title="我的消息",
                icon="ep:chat-dot-round",
                sort=1,
                menu_type=2,
                permission="message:list",
                status=1,
            ),
            # 发送消息
            Menu(
                parent_id=0,  # 需要后续更新
                name="MessageSend",
                path="/message/send/index",
                component="message/send/index",
                title="发送消息",
                icon="ep:position",
                sort=2,
                menu_type=2,
                permission="message:send",
                status=1,
            ),
            # 发送记录
            Menu(
                parent_id=0,  # 需要后续更新
                name="MessageLog",
                path="/message/send-log/index",
                component="message/send-log/index",
                title="发送记录",
                icon="ep:document",
                sort=3,
                menu_type=2,
                permission="message:log",
                status=1,
            ),
        ]

        for menu in new_menus:
            db.add(menu)

        await db.flush()

        # 获取消息中心目录的ID，更新子菜单的parent_id
        result = await db.execute(select(Menu).where(Menu.name == "Message"))
        message_menu = result.scalar_one_or_none()

        # 更新子菜单的parent_id
        if message_menu:
            result = await db.execute(select(Menu).where(Menu.name == "MessageList"))
            msg_list = result.scalar_one_or_none()
            if msg_list:
                msg_list.parent_id = message_menu.id
            
            result = await db.execute(select(Menu).where(Menu.name == "MessageSend"))
            msg_send = result.scalar_one_or_none()
            if msg_send:
                msg_send.parent_id = message_menu.id
            
            result = await db.execute(select(Menu).where(Menu.name == "MessageLog"))
            msg_log = result.scalar_one_or_none()
            if msg_log:
                msg_log.parent_id = message_menu.id

        await db.flush()

        # 给管理员角色分配新菜单
        for menu in new_menus:
            stmt = role_menu.insert().values(role_id=admin_role_id, menu_id=menu.id)
            await db.execute(stmt)

        await db.commit()
        print("新菜单添加完成！")
        print("新增菜单：")
        print("  - 租户管理（系统管理下）")
        print("  - 安全设置（系统管理下）")
        print("  - 消息中心目录")
        print("    - 我的消息")
        print("    - 发送消息")
        print("    - 发送记录")


if __name__ == "__main__":
    asyncio.run(add_new_menus())
