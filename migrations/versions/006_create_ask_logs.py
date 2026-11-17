"""
迁移文件: 006_create_ask_logs
描述: 创建知识库问答日志表

数据库配置从 config.py 的 DATABASES 获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from migrations.env import get_engine


def upgrade():
    """
    执行迁移: 创建 ask_logs 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ask_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer_preview VARCHAR(500),
                source_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 表/字段注释
        conn.execute(text("COMMENT ON TABLE ask_logs IS '知识库问答日志表';"))
        conn.execute(text("COMMENT ON COLUMN ask_logs.id IS '主键ID';"))
        conn.execute(text("COMMENT ON COLUMN ask_logs.user_id IS '提问用户ID';"))
        conn.execute(text("COMMENT ON COLUMN ask_logs.question IS '用户提问';"))
        conn.execute(text("COMMENT ON COLUMN ask_logs.answer_preview IS '回答摘要（前 500 字）';"))
        conn.execute(text("COMMENT ON COLUMN ask_logs.source_count IS '命中的引用片段数';"))
        conn.execute(text("COMMENT ON COLUMN ask_logs.created_at IS '提问时间';"))

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ask_logs_user_created ON ask_logs(user_id, created_at);"))

        conn.commit()
    print("✅ Migration 006: ask_logs table created successfully")


def downgrade():
    """
    回滚迁移: 删除 ask_logs 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ask_logs CASCADE;"))
        conn.commit()
    print("✅ Migration 006: ask_logs table dropped successfully")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration 006: create_ask_logs")
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()