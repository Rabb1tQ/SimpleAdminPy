"""
更新菜单路径脚本
"""
import asyncio

from sqlalchemy import select, update

from app.core.database import async_session_maker
from app.models import Menu


async def update_menu_paths():
    """更新菜单路径"""
    async with async_session_maker() as db:
        # 更新发送记录菜单路径
        result = await db.execute(select(Menu).where(Menu.name == "MessageLog"))
        msg_log = result.scalar_one_or_none()
        if msg_log:
            msg_log.path = "/message/send-log/index"
            msg_log.component = "message/send-log/index"
            print(f"更新 MessageLog: path={msg_log.path}, component={msg_log.component}")

        await db.commit()
        print("菜单路径更新完成！")


if __name__ == "__main__":
    asyncio.run(update_menu_paths())
