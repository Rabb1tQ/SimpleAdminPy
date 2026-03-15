"""
修复仪表盘菜单问题
"""
import asyncio

from sqlalchemy import delete, select

from app.core.database import async_session_maker
from app.models import Menu, role_menu


async def fix_dashboard_menu():
    """删除有问题的仪表盘菜单"""
    async with async_session_maker() as db:
        # 查找所有 path 包含 dashboard 的菜单
        result = await db.execute(
            select(Menu).where(Menu.path.like("%dashboard%"))
        )
        dashboard_menus = result.scalars().all()
        
        if dashboard_menus:
            print(f"找到 {len(dashboard_menus)} 个仪表盘菜单:")
            for menu in dashboard_menus:
                print(f"  - ID: {menu.id}, Name: {menu.name}, Path: {menu.path}, Component: {menu.component}")
            
            # 删除角色关联
            for menu in dashboard_menus:
                await db.execute(
                    delete(role_menu).where(role_menu.c.menu_id == menu.id)
                )
            
            # 删除菜单
            for menu in dashboard_menus:
                await db.delete(menu)
            
            await db.commit()
            print("已删除有问题的仪表盘菜单")
        else:
            print("没有找到仪表盘菜单，无需修复")
        
        # 显示当前所有菜单
        result = await db.execute(select(Menu).order_by(Menu.id))
        all_menus = result.scalars().all()
        print("\n当前菜单列表:")
        for menu in all_menus:
            print(f"  ID: {menu.id}, Name: {menu.name}, Path: {menu.path}, Component: {menu.component}")


if __name__ == "__main__":
    asyncio.run(fix_dashboard_menu())
