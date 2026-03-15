"""
修复安全设置菜单脚本
"""
import asyncio

from sqlalchemy import select, delete

from app.core.database import async_session_maker
from app.models import Menu, Role, role_menu


async def fix_security_menu():
    """修复安全设置菜单"""
    async with async_session_maker() as db:
        # 删除旧的安全相关菜单
        print("正在清理旧菜单...")
        result = await db.execute(select(Menu).where(Menu.name.in_(["SecurityConfig", "IpRule", "Security"])))
        old_menus = result.scalars().all()
        
        for menu in old_menus:
            # 删除角色关联
            await db.execute(delete(role_menu).where(role_menu.c.menu_id == menu.id))
            await db.delete(menu)
            print(f"  删除菜单: {menu.name}")
        
        await db.flush()
        
        # 获取系统管理目录的ID
        result = await db.execute(select(Menu).where(Menu.name == "System"))
        system_menu = result.scalar_one_or_none()
        system_parent_id = system_menu.id if system_menu else 1
        
        # 获取管理员角色
        result = await db.execute(select(Role).where(Role.code == "admin"))
        admin_role = result.scalar_one_or_none()
        admin_role_id = admin_role.id if admin_role else 1
        
        # 创建新的安全设置菜单
        security_menu = Menu(
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
        )
        db.add(security_menu)
        await db.flush()
        
        # 给管理员角色分配菜单
        stmt = role_menu.insert().values(role_id=admin_role_id, menu_id=security_menu.id)
        await db.execute(stmt)
        
        await db.commit()
        print("安全设置菜单修复完成！")
        print("菜单路径: /system/security/index")


if __name__ == "__main__":
    asyncio.run(fix_security_menu())
