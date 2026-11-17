"""
迁移文件: 005_create_document_chunks
描述: 创建文档切片表

Chroma 只存向量与 metadata，此表额外存切片原文
数据库配置从 config.py 的 DATABASES 获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from migrations.env import get_engine


def upgrade():
    """
    执行迁移: 创建 document_chunks 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 表/字段注释
        conn.execute(text("COMMENT ON TABLE document_chunks IS '文档切片表（切片原文，向量在 Chroma）';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.id IS '主键ID';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.user_id IS '所属用户ID';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.document_id IS '所属文档ID';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.chunk_index IS '切片序号（从 0 开始）';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.content IS '切片原文';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.token_count IS 'token 数';"))
        conn.execute(text("COMMENT ON COLUMN document_chunks.created_at IS '创建时间';"))

        # 查文档切片列表 + 删除时定位向量，都走这个复合索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chunks_user_doc_index ON document_chunks(user_id, document_id, chunk_index);"))

        conn.commit()
    print("✅ Migration 005: document_chunks table created successfully")


def downgrade():
    """
    回滚迁移: 删除 document_chunks 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS document_chunks CASCADE;"))
        conn.commit()
    print("✅ Migration 005: document_chunks table dropped successfully")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration 005: create_document_chunks")
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()