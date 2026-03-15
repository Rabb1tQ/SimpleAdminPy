"""
个人中心接口
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas import success, error
from app.schemas.system.user import ChangePassword, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["个人中心"])


@router.get("", summary="获取个人信息")
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前登录用户的详细信息"""
    return success({
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "desc": current_user.desc,
        "avatar": current_user.avatar,
        "home_path": current_user.home_path,
        "status": current_user.status,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
    })


@router.put("", summary="更新个人信息")
async def update_profile(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新当前用户的个人信息"""
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    await db.commit()
    return success()


@router.put("/password", summary="修改密码")
async def change_password(
    data: ChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """修改当前用户密码"""
    # 验证旧密码
    if not verify_password(data.old_password, current_user.password):
        return error("旧密码错误")
    
    # 验证新密码不能与旧密码相同
    if verify_password(data.new_password, current_user.password):
        return error("新密码不能与旧密码相同")
    
    # 更新密码
    current_user.password = get_password_hash(data.new_password)
    await db.commit()
    return success()
