"""
迁移文件: 003_create_users
描述: 创建用户表

支持 BYOK（用户自带大模型 key），llm_api_key_encrypted 存 Fernet 密文
数据库配置从 config.py 的 DATABASES 获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from migrations.env import get_engine


def upgrade():
    """
    执行迁移: 创建 users 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                llm_provider VARCHAR(32),
                llm_api_key_encrypted TEXT,
                llm_model VARCHAR(64),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 表/字段注释
        conn.execute(text("COMMENT ON TABLE users IS '用户表';"))
        conn.execute(text("COMMENT ON COLUMN users.id IS '主键ID';"))
        conn.execute(text("COMMENT ON COLUMN users.username IS '用户名（登录账号）';"))
        conn.execute(text("COMMENT ON COLUMN users.password_hash IS '密码哈希（bcrypt，不可逆）';"))
        conn.execute(text("COMMENT ON COLUMN users.llm_provider IS '聊天模型服务商: deepseek | minimax';"))
        conn.execute(text("COMMENT ON COLUMN users.llm_api_key_encrypted IS '用户自带的 LLM API key（Fernet 密文）';"))
        conn.execute(text("COMMENT ON COLUMN users.llm_model IS '用户选择的模型名，空则用服务商默认模型';"))
        conn.execute(text("COMMENT ON COLUMN users.created_at IS '注册时间';"))

        # username 唯一索引（登录时按用户名查）
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);"))

        conn.commit()
    print("✅ Migration 003: users table created successfully")


def downgrade():
    """
    回滚迁移: 删除 users 表

    注意: users 是所有业务表的外键来源，需先删掉引用它的表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        conn.commit()
    print("✅ Migration 003: users table dropped successfully")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration 003: create_users")
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()