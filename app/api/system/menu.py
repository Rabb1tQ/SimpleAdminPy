"""
菜单接口
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_superuser
from app.core.database import get_db
from app.models import Menu, role_menu, User
from app.schemas import success, error, MenuCreate, MenuUpdate

router = APIRouter(prefix="/menu", tags=["菜单管理"])


def build_menu_tree(menus: List[Menu], parent_id: int = 0) -> List[dict]:
    """构建菜单树（用于前端路由）"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            # 先获取子菜单
            children = build_menu_tree(menus, menu.id)
            
            # 处理 component 路径，确保与前端 views 目录匹配
            component = menu.component
            if component and not component.startswith("/"):
                component = "/" + component
            
            # 目录类型（有子菜单）不返回 name 和 component
            # 参考纯前端模板的 mock 数据格式
            node = {
                "path": menu.path,
                "meta": {
                    "title": menu.title,
                    "icon": menu.icon,
                    "showLink": not menu.hide_in_menu,
                    "showParent": False,
                    "rank": menu.sort,
                },
            }
            
            # 只有叶子节点（没有子菜单）才有 name 和 component
            if not children:
                node["name"] = menu.name
                if component:
                    node["component"] = component
            else:
                node["children"] = children
            
            tree.append(node)
    return tree


def build_menu_list_tree(menus: List[Menu], parent_id: int = 0) -> List[dict]:
    """构建菜单列表树（用于菜单管理页面）"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            # 先获取子菜单
            children = build_menu_list_tree(menus, menu.id)
            
            node = {
                "id": menu.id,
                "parent_id": menu.parent_id,
                "name": menu.name,
                "path": menu.path,
                "component": menu.component,
                "title": menu.title,
                "icon": menu.icon,
                "sort": menu.sort,
                "status": menu.status,
                "hide_in_menu": menu.hide_in_menu,
                "keep_alive": menu.keep_alive,
                "permission": menu.permission,
                "menu_type": menu.menu_type,
            }
            
            if children:
                node["children"] = children
            
            tree.append(node)
    return tree


@router.get("/all", summary="获取用户菜单")
async def get_user_menus(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前用户的菜单列表（动态路由）"""
    # 超级管理员获取所有菜单
    if current_user.is_superuser:
        result = await db.execute(
            select(Menu)
            .where(Menu.status == 1, Menu.menu_type.in_([1, 2]))
            .order_by(Menu.sort)
        )
        menus = result.scalars().all()
    else:
        # 获取用户角色关联的菜单
        menu_ids = set()
        for role in current_user.roles:
            if role.status == 1:
                for menu in role.menus:
                    if menu.status == 1 and menu.menu_type in [1, 2]:
                        menu_ids.add(menu.id)
        
        if not menu_ids:
            return success([])
        
        # 获取菜单及其所有父菜单
        all_menu_ids = set(menu_ids)
        result = await db.execute(
            select(Menu).where(Menu.id.in_(menu_ids))
        )
        direct_menus = result.scalars().all()
        
        # 递归获取所有父菜单
        for menu in direct_menus:
            parent_id = menu.parent_id
            while parent_id != 0:
                if parent_id in all_menu_ids:
                    break
                all_menu_ids.add(parent_id)
                parent_result = await db.execute(
                    select(Menu).where(Menu.id == parent_id)
                )
                parent_menu = parent_result.scalar_one_or_none()
                if parent_menu:
                    parent_id = parent_menu.parent_id
                else:
                    break
        
        result = await db.execute(
            select(Menu)
            .where(Menu.id.in_(all_menu_ids), Menu.status == 1)
            .order_by(Menu.sort)
        )
        menus = result.scalars().all()
    
    # 构建菜单树
    tree = build_menu_tree(list(menus))
    return success(tree)


@router.get("/list", summary="获取菜单列表")
async def get_menu_list(
    status: int = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取菜单列表（树形）"""
    query = select(Menu)
    
    if status is not None:
        query = query.where(Menu.status == status)
    
    query = query.order_by(Menu.sort)
    result = await db.execute(query)
    menus = result.scalars().all()
    
    # 构建菜单列表树（用于菜单管理页面）
    tree = build_menu_list_tree(list(menus))
    return success(tree)


@router.get("/{menu_id}", summary="获取菜单详情")
async def get_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取菜单详情"""
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    
    if menu is None:
        return error("菜单不存在")
    
    return success({
        "id": menu.id,
        "parent_id": menu.parent_id,
        "name": menu.name,
        "path": menu.path,
        "component": menu.component,
        "title": menu.title,
        "icon": menu.icon,
        "sort": menu.sort,
        "status": menu.status,
        "hide_in_menu": menu.hide_in_menu,
        "keep_alive": menu.keep_alive,
        "permission": menu.permission,
        "menu_type": menu.menu_type,
        "created_at": menu.created_at.isoformat(),
    })


@router.post("", summary="创建菜单")
async def create_menu(
    data: MenuCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """创建菜单"""
    menu = Menu(
        parent_id=data.parent_id,
        name=data.name,
        path=data.path,
        component=data.component,
        title=data.title,
        icon=data.icon,
        sort=data.sort,
        status=data.status,
        hide_in_menu=data.hide_in_menu,
        keep_alive=data.keep_alive,
        permission=data.permission,
        menu_type=data.menu_type,
    )
    db.add(menu)
    await db.commit()
    return success({"id": menu.id})


@router.put("/{menu_id}", summary="更新菜单")
async def update_menu(
    menu_id: int,
    data: MenuUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """更新菜单"""
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    
    if menu is None:
        return error("菜单不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(menu, key, value)
    
    await db.commit()
    return success()


@router.delete("/{menu_id}", summary="删除菜单")
async def delete_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """删除菜单"""
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    
    if menu is None:
        return error("菜单不存在")
    
    # 检查是否有子菜单
    result = await db.execute(
        select(Menu).where(Menu.parent_id == menu_id)
    )
    if result.scalar_one_or_none():
        return error("存在子菜单，无法删除")
    
    # 删除角色菜单关联
    stmt = role_menu.delete().where(role_menu.c.menu_id == menu_id)
    await db.execute(stmt)
    
    await db.delete(menu)
    await db.commit()
    return success()
