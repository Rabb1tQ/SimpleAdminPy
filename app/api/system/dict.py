"""
字典管理接口
"""
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_superuser
from app.core.database import get_db
from app.core.redis import get_redis_cache, RedisKey
from app.models import DictType, DictData, User
from app.schemas import success
from app.schemas.system.dict import DictTypeCreate, DictTypeUpdate, DictDataCreate, DictDataUpdate

router = APIRouter(prefix="/dict", tags=["字典管理"])


# ============ 字典类型 ============


@router.get("/type/list", summary="获取字典类型列表")
async def get_dict_type_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="字典名称"),
    code: str = Query(None, description="字典编码"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取字典类型列表（分页）"""
    query = select(DictType).where(DictType.is_deleted == False)
    count_query = select(func.count(DictType.id)).where(DictType.is_deleted == False)
    
    if name:
        query = query.where(DictType.name.ilike(f"%{name}%"))
        count_query = count_query.where(DictType.name.ilike(f"%{name}%"))
    if code:
        query = query.where(DictType.code.ilike(f"%{code}%"))
        count_query = count_query.where(DictType.code.ilike(f"%{code}%"))
    
    total = (await db.execute(count_query)).scalar()
    
    query = query.order_by(DictType.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    types = result.scalars().all()
    
    items = [
        {
            "id": t.id,
            "name": t.name,
            "code": t.code,
            "status": t.status,
            "remark": t.remark,
            "created_at": t.created_at.isoformat(),
        }
        for t in types
    ]
    
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.get("/type/all", summary="获取所有字典类型")
async def get_all_dict_types(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取所有字典类型"""
    result = await db.execute(
        select(DictType).where(DictType.is_deleted == False).order_by(DictType.code)
    )
    types = result.scalars().all()
    
    items = [
        {
            "id": t.id,
            "name": t.name,
            "code": t.code,
        }
        for t in types
    ]
    
    return success(items)


@router.get("/type/{type_id}", summary="获取字典类型详情")
async def get_dict_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取字典类型详情"""
    result = await db.execute(
        select(DictType).where(DictType.id == type_id, DictType.is_deleted == False)
    )
    t = result.scalar_one_or_none()
    
    if t is None:
        return {"code": 1, "message": "字典类型不存在", "data": None}
    
    return success({
        "id": t.id,
        "name": t.name,
        "code": t.code,
        "remark": t.remark,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    })


@router.post("/type", summary="创建字典类型")
async def create_dict_type(
    data: DictTypeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """创建字典类型"""
    # 检查编码是否已存在
    result = await db.execute(
        select(DictType).where(DictType.code == data.code, DictType.is_deleted == False)
    )
    if result.scalar_one_or_none():
        return {"code": 1, "message": "字典编码已存在", "data": None}
    
    dict_type = DictType(
        name=data.name,
        code=data.code,
        remark=data.remark,
    )
    db.add(dict_type)
    await db.commit()
    await db.refresh(dict_type)
    
    return success({"id": dict_type.id, "message": "创建成功"})


@router.put("/type/{type_id}", summary="更新字典类型")
async def update_dict_type(
    type_id: int,
    data: DictTypeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """更新字典类型"""
    result = await db.execute(
        select(DictType).where(DictType.id == type_id, DictType.is_deleted == False)
    )
    dict_type = result.scalar_one_or_none()
    
    if dict_type is None:
        return {"code": 1, "message": "字典类型不存在", "data": None}
    
    if data.name is not None:
        dict_type.name = data.name
    if data.code is not None:
        # 检查新编码是否已存在
        result = await db.execute(
            select(DictType).where(
                DictType.code == data.code,
                DictType.id != type_id,
                DictType.is_deleted == False
            )
        )
        if result.scalar_one_or_none():
            return {"code": 1, "message": "字典编码已存在", "data": None}
        dict_type.code = data.code
    if data.remark is not None:
        dict_type.remark = data.remark
    
    await db.commit()
    
    return success({"message": "更新成功"})


@router.delete("/type/{type_id}", summary="删除字典类型")
async def delete_dict_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> dict:
    """删除字典类型（软删除）"""
    result = await db.execute(
        select(DictType).where(DictType.id == type_id, DictType.is_deleted == False)
    )
    dict_type = result.scalar_one_or_none()
    
    if dict_type is None:
        return {"code": 1, "message": "字典类型不存在", "data": None}
    
    dict_type.is_deleted = True
    await db.commit()
    
    return success({"message": "删除成功"})


# ============ 字典数据 ============


@router.get("/data/list", summary="获取字典数据列表")
async def get_dict_data_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    dict_type_id: int = Query(None, description="字典类型ID"),
    label: str = Query(None, description="字典标签"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取字典数据列表（分页）"""
    query = select(DictData).where(DictData.is_deleted == False)
    count_query = select(func.count(DictData.id)).where(DictData.is_deleted == False)
    
    if dict_type_id:
        query = query.where(DictData.dict_type_id == dict_type_id)
        count_query = count_query.where(DictData.dict_type_id == dict_type_id)
    if label:
        query = query.where(DictData.label.ilike(f"%{label}%"))
        count_query = count_query.where(DictData.label.ilike(f"%{label}%"))
    
    total = (await db.execute(count_query)).scalar()
    
    query = query.order_by(DictData.sort.asc(), DictData.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # 获取字典类型编码
    data_list = []
    for item in items:
        type_result = await db.execute(
            select(DictType.code).where(DictType.id == item.dict_type_id)
        )
        dict_code = type_result.scalar_one_or_none()
        data_list.append({
            "id": item.id,
            "dict_type_id": item.dict_type_id,
            "dict_code": dict_code,
            "label": item.label,
            "value": item.value,
            "sort": item.sort,
            "status": item.status,
            "css_class": item.css_class,
            "list_class": item.list_class,
            "is_default": item.is_default,
            "remark": item.remark,
            "created_at": item.created_at.isoformat(),
        })
    
    return success({
        "items": data_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.get("/data/code/{code}", summary="根据字典编码获取字典数据")
async def get_dict_data_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """根据字典编码获取字典数据（公开接口）"""
    # 先获取字典类型
    type_result = await db.execute(
        select(DictType).where(DictType.code == code, DictType.is_deleted == False)
    )
    dict_type = type_result.scalar_one_or_none()
    
    if dict_type is None:
        return success([])
    
    # 获取字典数据
    result = await db.execute(
        select(DictData)
        .where(DictData.dict_type_id == dict_type.id, DictData.is_deleted == False)
        .order_by(DictData.sort.asc())
    )
    items = result.scalars().all()
    
    data = [
        {
            "label": item.label,
            "value": item.value,
        }
        for item in items
    ]
    
    return success(data)


@router.get("/data/{data_id}", summary="获取字典数据详情")
async def get_dict_data(
    data_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """获取字典数据详情"""
    result = await db.execute(
        select(DictData).where(DictData.id == data_id, DictData.is_deleted == False)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        return {"code": 1, "message": "字典数据不存在", "data": None}
    
    # 获取字典类型编码
    type_result = await db.execute(
        select(DictType.code).where(DictType.id == item.dict_type_id)
    )
    dict_code = type_result.scalar_one_or_none()
    
    return success({
        "id": item.id,
        "dict_type_id": item.dict_type_id,
        "dict_code": dict_code,
        "label": item.label,
        "value": item.value,
        "sort": item.sort,
        "status": item.status,
        "css_class": item.css_class,
        "list_class": item.list_class,
        "is_default": item.is_default,
        "remark": item.remark,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    })


async def clear_dict_cache(redis: Redis, dict_type_id: int, db: AsyncSession) -> None:
    """清除字典缓存"""
    # 获取字典类型编码
    result = await db.execute(
        select(DictType.code).where(DictType.id == dict_type_id)
    )
    dict_code = result.scalar_one_or_none()
    if dict_code:
        cache_key = RedisKey.DICT_DATA.format(code=dict_code)
        await redis.delete(cache_key)


@router.post("/data", summary="创建字典数据")
async def create_dict_data(
    data: DictDataCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
    _: User = Depends(get_current_superuser),
) -> dict:
    """创建字典数据"""
    # 检查字典类型是否存在
    result = await db.execute(
        select(DictType).where(DictType.id == data.dict_type_id, DictType.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        return {"code": 1, "message": "字典类型不存在", "data": None}
    
    # 如果设置为默认，先取消该字典类型下其他数据的默认状态
    if data.is_default:
        other_defaults_result = await db.execute(
            select(DictData).where(
                DictData.dict_type_id == data.dict_type_id,
                DictData.is_deleted == False,
                DictData.is_default == True
            )
        )
        for other in other_defaults_result.scalars().all():
            other.is_default = False
    
    dict_data = DictData(
        dict_type_id=data.dict_type_id,
        label=data.label,
        value=data.value,
        sort=data.sort,
        status=data.status,
        css_class=data.css_class,
        list_class=data.list_class,
        is_default=data.is_default,
        remark=data.remark,
    )
    db.add(dict_data)
    await db.commit()
    await db.refresh(dict_data)
    
    # 清除字典缓存
    await clear_dict_cache(redis, data.dict_type_id, db)
    
    return success({"id": dict_data.id, "message": "创建成功"})


@router.put("/data/{data_id}", summary="更新字典数据")
async def update_dict_data(
    data_id: int,
    data: DictDataUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
    _: User = Depends(get_current_superuser),
) -> dict:
    """更新字典数据"""
    result = await db.execute(
        select(DictData).where(DictData.id == data_id, DictData.is_deleted == False)
    )
    dict_data = result.scalar_one_or_none()
    
    if dict_data is None:
        return {"code": 1, "message": "字典数据不存在", "data": None}
    
    # 记录旧的字典类型ID
    old_dict_type_id = dict_data.dict_type_id
    
    if data.dict_type_id is not None:
        # 检查字典类型是否存在
        type_result = await db.execute(
            select(DictType).where(DictType.id == data.dict_type_id, DictType.is_deleted == False)
        )
        if not type_result.scalar_one_or_none():
            return {"code": 1, "message": "字典类型不存在", "data": None}
        dict_data.dict_type_id = data.dict_type_id
    if data.label is not None:
        dict_data.label = data.label
    if data.value is not None:
        dict_data.value = data.value
    if data.sort is not None:
        dict_data.sort = data.sort
    if data.status is not None:
        dict_data.status = data.status
    if data.css_class is not None:
        dict_data.css_class = data.css_class
    if data.list_class is not None:
        dict_data.list_class = data.list_class
    if data.is_default is not None:
        # 如果设置为默认，先取消该字典类型下其他数据的默认状态
        if data.is_default:
            target_dict_type_id = data.dict_type_id if data.dict_type_id is not None else old_dict_type_id
            # 使用 ORM 方式更新其他记录
            other_defaults_result = await db.execute(
                select(DictData).where(
                    DictData.dict_type_id == target_dict_type_id,
                    DictData.is_deleted == False,
                    DictData.id != data_id,
                    DictData.is_default == True
                )
            )
            for other in other_defaults_result.scalars().all():
                other.is_default = False
        dict_data.is_default = data.is_default
    if data.remark is not None:
        dict_data.remark = data.remark
    
    await db.commit()
    
    # 清除字典缓存（新旧类型都要清除）
    await clear_dict_cache(redis, old_dict_type_id, db)
    if data.dict_type_id is not None and data.dict_type_id != old_dict_type_id:
        await clear_dict_cache(redis, data.dict_type_id, db)
    
    return success({"message": "更新成功"})


@router.delete("/data/{data_id}", summary="删除字典数据")
async def delete_dict_data(
    data_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_cache),
    _: User = Depends(get_current_superuser),
) -> dict:
    """删除字典数据（软删除）"""
    result = await db.execute(
        select(DictData).where(DictData.id == data_id, DictData.is_deleted == False)
    )
    dict_data = result.scalar_one_or_none()
    
    if dict_data is None:
        return {"code": 1, "message": "字典数据不存在", "data": None}
    
    dict_type_id = dict_data.dict_type_id
    dict_data.is_deleted = True
    await db.commit()
    
    # 清除字典缓存
    await clear_dict_cache(redis, dict_type_id, db)
    
    return success({"message": "删除成功"})
