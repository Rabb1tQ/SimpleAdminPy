"""
数据库初始化数据脚本

程序启动时会自动调用 init_data() 初始化数据。
命令行使用：
    python -m app.utils.init_data --reset      # 重置所有数据
    python -m app.utils.init_data --menu-only  # 仅重置菜单数据
"""
import asyncio
import argparse

from sqlalchemy import select, delete

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models import User, Role, Menu, DictType, DictData, SecurityConfig, role_menu


# ==================== 默认数据定义 ====================

DEFAULT_MENUS = [
    # 系统管理目录
    {"parent_id": 0, "name": "System", "path": "/system", "component": "",
     "title": "系统管理", "icon": "ep:setting", "sort": 1, "menu_type": 1, "status": 1},
    {"parent_id": 1, "name": "User", "path": "/system/user/index", "component": "system/user/index",
     "title": "用户管理", "icon": "ep:user", "sort": 1, "menu_type": 2, "permission": "system:user:list", "status": 1},
    {"parent_id": 1, "name": "Role", "path": "/system/role/index", "component": "system/role/index",
     "title": "角色管理", "icon": "ep:user-filled", "sort": 2, "menu_type": 2, "permission": "system:role:list", "status": 1},
    {"parent_id": 1, "name": "SystemMenu", "path": "/system/menu/index", "component": "system/menu/index",
     "title": "菜单管理", "icon": "ep:menu", "sort": 3, "menu_type": 2, "permission": "system:menu:list", "status": 1},
    {"parent_id": 1, "name": "Log", "path": "/system/log/index", "component": "system/log/index",
     "title": "操作日志", "icon": "ep:document", "sort": 4, "menu_type": 2, "permission": "system:log:list", "status": 1},
    {"parent_id": 1, "name": "Dict", "path": "/system/dict/index", "component": "system/dict/index",
     "title": "字典管理", "icon": "ep:collection", "sort": 5, "menu_type": 2, "permission": "system:dict:list", "status": 1},
    {"parent_id": 1, "name": "LoginLog", "path": "/system/login-log/index", "component": "system/login-log/index",
     "title": "登录日志", "icon": "ep:tickets", "sort": 6, "menu_type": 2, "permission": "system:login-log:list", "status": 1},
    {"parent_id": 1, "name": "Online", "path": "/system/online/index", "component": "system/online/index",
     "title": "在线用户", "icon": "ep:user-filled", "sort": 7, "menu_type": 2, "permission": "system:online:list", "status": 1},
    {"parent_id": 1, "name": "Monitor", "path": "/system/monitor/index", "component": "system/monitor/index",
     "title": "系统监控", "icon": "ep:monitor", "sort": 8, "menu_type": 2, "permission": "system:monitor:list", "status": 1},
    {"parent_id": 1, "name": "Tenant", "path": "/system/tenant/index", "component": "system/tenant/index",
     "title": "租户管理", "icon": "ep:office-building", "sort": 9, "menu_type": 2, "permission": "system:tenant:list", "status": 1},
    {"parent_id": 1, "name": "Security", "path": "/system/security/index", "component": "system/security/index",
     "title": "安全设置", "icon": "ep:lock", "sort": 10, "menu_type": 2, "permission": "system:security:list", "status": 1},
    # 消息中心
    {"parent_id": 0, "name": "Message", "path": "/message", "component": "",
     "title": "消息中心", "icon": "ep:message", "sort": 2, "menu_type": 1, "status": 1},
    {"parent_id": 0, "name": "MessageList", "path": "/message/list/index", "component": "message/list/index",
     "title": "我的消息", "icon": "ep:chat-dot-round", "sort": 1, "menu_type": 2, "permission": "message:list", "status": 1},
    {"parent_id": 0, "name": "MessageSend", "path": "/message/send/index", "component": "message/send/index",
     "title": "发送消息", "icon": "ep:position", "sort": 2, "menu_type": 2, "permission": "message:send", "status": 1},
    {"parent_id": 0, "name": "MessageLog", "path": "/message/send-log/index", "component": "message/send-log/index",
     "title": "发送记录", "icon": "ep:document", "sort": 3, "menu_type": 2, "permission": "message:log", "status": 1},
]

DEFAULT_DICT_TYPES = [
    {"name": "状态", "code": "status", "remark": "通用状态字典"},
    {"name": "性别", "code": "gender", "remark": "用户性别字典"},
    {"name": "菜单类型", "code": "menu_type", "remark": "菜单类型字典"},
]

DEFAULT_DICT_DATA = [
    {"dict_type_id": 1, "label": "启用", "value": "1", "sort": 1},
    {"dict_type_id": 1, "label": "禁用", "value": "0", "sort": 2},
    {"dict_type_id": 2, "label": "男", "value": "1", "sort": 1},
    {"dict_type_id": 2, "label": "女", "value": "2", "sort": 2},
    {"dict_type_id": 2, "label": "未知", "value": "0", "sort": 3},
    {"dict_type_id": 3, "label": "目录", "value": "1", "sort": 1},
    {"dict_type_id": 3, "label": "菜单", "value": "2", "sort": 2},
    {"dict_type_id": 3, "label": "按钮", "value": "3", "sort": 3},
]

DEFAULT_SECURITY_CONFIGS = [
    {"config_key": "login_fail_threshold", "config_value": "5", "config_type": "NUMBER", "group_name": "login", "description": "登录失败锁定阈值"},
    {"config_key": "lock_duration", "config_value": "30", "config_type": "NUMBER", "group_name": "login", "description": "锁定时长(分钟)"},
]


# ==================== 初始化函数 ====================

async def init_data(reset: bool = False):
    """初始化数据（程序启动时自动调用，数据已存在则跳过）"""
    async with async_session_maker() as db:
        # 检查是否已有数据
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() and not reset:
            return  # 数据已存在，静默跳过

        if reset:
            print("正在重置数据...")
            await db.execute(delete(role_menu))
            await db.execute(delete(Menu))
            await db.execute(delete(DictData))
            await db.execute(delete(DictType))
            await db.execute(delete(Role))
            await db.execute(delete(User))
            await db.execute(delete(SecurityConfig))

        # 创建用户
        db.add(User(
            username="admin",
            password=get_password_hash("admin123"),
            real_name="超级管理员",
            is_superuser=True,
            status=1,
        ))

        # 创建角色
        db.add(Role(name="管理员", code="admin", desc="系统管理员", status=1))
        db.add(Role(name="普通用户", code="user", desc="普通用户", status=1))

        # 创建菜单
        for menu_data in DEFAULT_MENUS:
            db.add(Menu(**menu_data))

        # 创建字典
        for dict_type_data in DEFAULT_DICT_TYPES:
            db.add(DictType(**dict_type_data))

        await db.flush()

        # 创建字典数据
        for dict_data_item in DEFAULT_DICT_DATA:
            db.add(DictData(**dict_data_item))

        # 创建安全配置
        for config_data in DEFAULT_SECURITY_CONFIGS:
            db.add(SecurityConfig(**config_data))

        # 更新消息中心子菜单的 parent_id
        result = await db.execute(select(Menu).where(Menu.name == "Message"))
        message_menu = result.scalar_one_or_none()
        if message_menu:
            for menu_name in ["MessageList", "MessageSend", "MessageLog"]:
                result = await db.execute(select(Menu).where(Menu.name == menu_name))
                menu = result.scalar_one_or_none()
                if menu:
                    menu.parent_id = message_menu.id

        await db.flush()

        # 给管理员角色分配所有菜单权限
        result = await db.execute(select(Role).where(Role.code == "admin"))
        admin_role = result.scalar_one_or_none()
        if admin_role:
            result = await db.execute(select(Menu))
            for menu in result.scalars().all():
                await db.execute(role_menu.insert().values(role_id=admin_role.id, menu_id=menu.id))

        await db.commit()

        if reset:
            print("✓ 数据重置完成！账号: admin, 密码: admin123")
        else:
            print("✓ 初始数据创建完成！账号: admin, 密码: admin123")


async def reset_menu_only():
    """仅重置菜单数据"""
    async with async_session_maker() as db:
        print("正在重置菜单数据...")

        await db.execute(delete(role_menu))
        await db.execute(delete(Menu))
        await db.flush()

        for menu_data in DEFAULT_MENUS:
            db.add(Menu(**menu_data))

        await db.flush()

        # 更新消息中心子菜单的 parent_id
        result = await db.execute(select(Menu).where(Menu.name == "Message"))
        message_menu = result.scalar_one_or_none()
        if message_menu:
            for menu_name in ["MessageList", "MessageSend", "MessageLog"]:
                result = await db.execute(select(Menu).where(Menu.name == menu_name))
                menu = result.scalar_one_or_none()
                if menu:
                    menu.parent_id = message_menu.id

        await db.flush()

        # 给管理员角色分配所有菜单权限
        result = await db.execute(select(Role).where(Role.code == "admin"))
        admin_role = result.scalar_one_or_none()
        if admin_role:
            result = await db.execute(select(Menu))
            for menu in result.scalars().all():
                await db.execute(role_menu.insert().values(role_id=admin_role.id, menu_id=menu.id))

        await db.commit()
        print("✓ 菜单数据重置完成！")


# ==================== 命令行入口 ====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据库初始化脚本")
    parser.add_argument("--reset", action="store_true", help="重置所有数据")
    parser.add_argument("--menu-only", action="store_true", help="仅重置菜单数据")

    args = parser.parse_args()

    if args.menu_only:
        asyncio.run(reset_menu_only())
    elif args.reset:
        asyncio.run(init_data(reset=True))
    else:
        print("用法: python -m app.utils.init_data --reset 或 --menu-only")
