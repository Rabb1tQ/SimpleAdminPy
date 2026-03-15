"""
初始化数据脚本
"""
import asyncio

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models import DictType, DictData, Menu, Role, role_menu, User


async def init_data():
    """初始化数据"""
    async with async_session_maker() as db:
        # 检查是否已有数据
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("数据已存在，跳过初始化")
            return

        # 创建超级管理员
        admin = User(
            username="admin",
            password=get_password_hash("admin123"),
            real_name="超级管理员",
            is_superuser=True,
            status=1,
        )
        db.add(admin)

        # 创建角色
        admin_role = Role(
            name="管理员",
            code="admin",
            desc="系统管理员",
            status=1,
        )
        user_role_obj = Role(
            name="普通用户",
            code="user",
            desc="普通用户",
            status=1,
        )
        db.add(admin_role)
        db.add(user_role_obj)

        # 创建菜单（首页由前端静态路由提供）
        menus = [
            # 系统管理目录
            Menu(
                parent_id=0,
                name="System",
                path="/system",
                component="",
                title="系统管理",
                icon="ep:setting",
                sort=1,
                menu_type=1,
                status=1,
            ),
            # 系统管理子菜单
            Menu(
                parent_id=1,
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
                parent_id=1,
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
                parent_id=1,
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
                parent_id=1,
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
                parent_id=1,
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
                parent_id=1,
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
                parent_id=1,
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
                parent_id=1,
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

        # 创建字典类型
        dict_types = [
            DictType(name="状态", code="status", remark="通用状态字典"),
            DictType(name="性别", code="gender", remark="用户性别字典"),
            DictType(name="菜单类型", code="menu_type", remark="菜单类型字典"),
        ]
        for dt in dict_types:
            db.add(dt)

        await db.flush()

        # 创建字典数据
        dict_data_list = [
            # 状态字典
            DictData(dict_type_id=1, label="启用", value="1", sort=1),
            DictData(dict_type_id=1, label="禁用", value="0", sort=2),
            # 性别字典
            DictData(dict_type_id=2, label="男", value="1", sort=1),
            DictData(dict_type_id=2, label="女", value="2", sort=2),
            DictData(dict_type_id=2, label="未知", value="0", sort=3),
            # 菜单类型字典
            DictData(dict_type_id=3, label="目录", value="1", sort=1),
            DictData(dict_type_id=3, label="菜单", value="2", sort=2),
            DictData(dict_type_id=3, label="按钮", value="3", sort=3),
        ]
        for dd in dict_data_list:
            db.add(dd)

        # 给管理员角色分配所有菜单
        for menu in menus:
            stmt = role_menu.insert().values(role_id=1, menu_id=menu.id)
            await db.execute(stmt)

        # 给普通用户角色分配仪表盘菜单
        stmt = role_menu.insert().values(role_id=2, menu_id=1)
        await db.execute(stmt)

        await db.commit()
        print("初始化数据完成！")
        print("超级管理员账号: admin")
        print("超级管理员密码: admin123")


if __name__ == "__main__":
    asyncio.run(init_data())
