"""
数据库迁移脚本 - 添加新功能所需的字段和表
运行方式: python -m app.utils.migrate_db
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def migrate():
    """执行数据库迁移"""
    async with engine.begin() as conn:
        # 1. 检查并添加 tenant_id 字段到 sys_user 表
        try:
            result = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'sys_user' AND column_name = 'tenant_id'
            """))
            if not result.fetchone():
                print("添加 sys_user.tenant_id 字段...")
                await conn.execute(text("""
                    ALTER TABLE sys_user ADD COLUMN tenant_id INTEGER NULL
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_user_tenant_id ON sys_user(tenant_id)
                """))
                print("✓ sys_user.tenant_id 字段添加成功")
            else:
                print("✓ sys_user.tenant_id 字段已存在")
        except Exception as e:
            print(f"添加 tenant_id 字段失败: {e}")

        # 1.1 检查并添加 tenant_id 字段到 sys_login_log 表
        try:
            result = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'sys_login_log' AND column_name = 'tenant_id'
            """))
            if not result.fetchone():
                print("添加 sys_login_log.tenant_id 字段...")
                await conn.execute(text("""
                    ALTER TABLE sys_login_log ADD COLUMN tenant_id INTEGER NULL
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_login_log_tenant_id ON sys_login_log(tenant_id)
                """))
                print("✓ sys_login_log.tenant_id 字段添加成功")
            else:
                print("✓ sys_login_log.tenant_id 字段已存在")
        except Exception as e:
            print(f"添加 sys_login_log.tenant_id 字段失败: {e}")

        # 1.2 检查并添加 tenant_id 字段到 sys_operation_log 表
        try:
            result = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'sys_operation_log' AND column_name = 'tenant_id'
            """))
            if not result.fetchone():
                print("添加 sys_operation_log.tenant_id 字段...")
                await conn.execute(text("""
                    ALTER TABLE sys_operation_log ADD COLUMN tenant_id INTEGER NULL
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_operation_log_tenant_id ON sys_operation_log(tenant_id)
                """))
                print("✓ sys_operation_log.tenant_id 字段添加成功")
            else:
                print("✓ sys_operation_log.tenant_id 字段已存在")
        except Exception as e:
            print(f"添加 sys_operation_log.tenant_id 字段失败: {e}")

        # 2. 创建租户表
        try:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'sys_tenant'
            """))
            if not result.fetchone():
                print("创建 sys_tenant 表...")
                await conn.execute(text("""
                    CREATE TABLE sys_tenant (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        code VARCHAR(50) NOT NULL UNIQUE,
                        contact VARCHAR(50),
                        phone VARCHAR(20),
                        email VARCHAR(100),
                        address VARCHAR(255),
                        status INTEGER DEFAULT 1,
                        expire_at TIMESTAMP,
                        remark VARCHAR(500),
                        is_deleted INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_tenant_code ON sys_tenant(code)
                """))
                print("✓ sys_tenant 表创建成功")
            else:
                print("✓ sys_tenant 表已存在")
        except Exception as e:
            print(f"创建 sys_tenant 表失败: {e}")

        # 3. 创建消息表
        try:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'sys_message'
            """))
            if not result.fetchone():
                print("创建 sys_message 表...")
                await conn.execute(text("""
                    CREATE TABLE sys_message (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        content TEXT,
                        message_type VARCHAR(20) DEFAULT 'SYSTEM',
                        sender_id INTEGER,
                        receiver_id INTEGER,
                        is_read INTEGER DEFAULT 0,
                        read_at TIMESTAMP,
                        is_deleted INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_message_receiver_id ON sys_message(receiver_id)
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_message_sender_id ON sys_message(sender_id)
                """))
                print("✓ sys_message 表创建成功")
            else:
                print("✓ sys_message 表已存在")
        except Exception as e:
            print(f"创建 sys_message 表失败: {e}")

        # 4. 创建消息发送记录表
        try:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'sys_message_send_log'
            """))
            if not result.fetchone():
                print("创建 sys_message_send_log 表...")
                await conn.execute(text("""
                    CREATE TABLE sys_message_send_log (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        content TEXT,
                        message_type VARCHAR(20) DEFAULT 'SYSTEM',
                        send_type VARCHAR(20) DEFAULT 'USER',
                        receiver_count INTEGER DEFAULT 0,
                        sender_id INTEGER,
                        is_deleted INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_message_send_log_sender_id ON sys_message_send_log(sender_id)
                """))
                print("✓ sys_message_send_log 表创建成功")
            else:
                print("✓ sys_message_send_log 表已存在")
        except Exception as e:
            print(f"创建 sys_message_send_log 表失败: {e}")

        # 5. 创建安全配置表
        try:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'sys_security_config'
            """))
            if not result.fetchone():
                print("创建 sys_security_config 表...")
                await conn.execute(text("""
                    CREATE TABLE sys_security_config (
                        id SERIAL PRIMARY KEY,
                        config_key VARCHAR(50) NOT NULL UNIQUE,
                        config_value TEXT,
                        config_type VARCHAR(20) DEFAULT 'STRING',
                        group_name VARCHAR(50),
                        description VARCHAR(255),
                        is_deleted INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                print("✓ sys_security_config 表创建成功")
                
                # 插入默认配置
                await conn.execute(text("""
                    INSERT INTO sys_security_config (config_key, config_value, config_type, group_name, description)
                    VALUES 
                        ('login_fail_threshold', '5', 'NUMBER', 'login', '登录失败锁定阈值'),
                        ('lock_duration', '30', 'NUMBER', 'login', '锁定时长(分钟)')
                """))
                print("✓ 默认安全配置插入成功")
            else:
                print("✓ sys_security_config 表已存在")
        except Exception as e:
            print(f"创建 sys_security_config 表失败: {e}")

        # 6. 创建IP规则表
        try:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'sys_ip_rule'
            """))
            if not result.fetchone():
                print("创建 sys_ip_rule 表...")
                await conn.execute(text("""
                    CREATE TABLE sys_ip_rule (
                        id SERIAL PRIMARY KEY,
                        ip_address VARCHAR(50) NOT NULL,
                        rule_type VARCHAR(10) NOT NULL,
                        description VARCHAR(255),
                        status INTEGER DEFAULT 1,
                        created_by INTEGER,
                        is_deleted INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_ip_rule_ip_address ON sys_ip_rule(ip_address)
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_sys_ip_rule_rule_type ON sys_ip_rule(rule_type)
                """))
                print("✓ sys_ip_rule 表创建成功")
            else:
                print("✓ sys_ip_rule 表已存在")
        except Exception as e:
            print(f"创建 sys_ip_rule 表失败: {e}")

        print("\n数据库迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate())
