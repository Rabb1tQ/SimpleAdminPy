"""
更新菜单数据脚本
"""
import asyncio

from sqlalchemy import delete

from app.core.database import async_session_maker
from app.models import Menu, role_menu


async def update_menu_data():
    """更新菜单数据"""
    async with async_session_maker() as db:
        # 删除旧的菜单关联
        await db.execute(delete(role_menu))
        # 删除旧的菜单
        await db.execute(delete(Menu))
        await db.commit()
        print("已删除旧菜单数据")

        # 创建系统管理目录
        system_menu = Menu(
            parent_id=0,
            name="System",
            path="/system",
            component="",
            title="系统管理",
            icon="ep:setting",
            sort=1,
            menu_type=1,
            status=1,
        )
        db.add(system_menu)
        await db.flush()  # 获取自增ID
        
        system_menu_id = system_menu.id
        print(f"系统管理菜单ID: {system_menu_id}")

        # 创建子菜单
        menus = [
            Menu(
                parent_id=system_menu_id,
                name="User",
                path="/system/user/index",
                component="system/user/index",
                title="用户管理",
                icon="ep:user",
                sort=1,
                menu_type=2,
                permission="system:user:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="Role",
                path="/system/role/index",
                component="system/role/index",
                title="角色管理",
                icon="ep:user-filled",
                sort=2,
                menu_type=2,
                permission="system:role:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="SystemMenu",
                path="/system/menu/index",
                component="system/menu/index",
                title="菜单管理",
                icon="ep:menu",
                sort=3,
                menu_type=2,
                permission="system:menu:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="Log",
                path="/system/log/index",
                component="system/log/index",
                title="操作日志",
                icon="ep:document",
                sort=4,
                menu_type=2,
                permission="system:log:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="Dict",
                path="/system/dict/index",
                component="system/dict/index",
                title="字典管理",
                icon="ep:collection",
                sort=5,
                menu_type=2,
                permission="system:dict:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="LoginLog",
                path="/system/login-log/index",
                component="system/login-log/index",
                title="登录日志",
                icon="ep:tickets",
                sort=6,
                menu_type=2,
                permission="system:login-log:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="Online",
                path="/system/online/index",
                component="system/online/index",
                title="在线用户",
                icon="ep:user-filled",
                sort=7,
                menu_type=2,
                permission="system:online:list",
                status=1,
            ),
            Menu(
                parent_id=system_menu_id,
                name="Monitor",
                path="/system/monitor/index",
                component="system/monitor/index",
                title="系统监控",
                icon="ep:monitor",
                sort=8,
                menu_type=2,
                permission="system:monitor:list",
                status=1,
            ),
        ]
        for menu in menus:
            db.add(menu)
        
        await db.commit()
        print("菜单数据更新完成！")


if __name__ == "__main__":
    asyncio.run(update_menu_data())

