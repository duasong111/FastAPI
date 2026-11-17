"""
迁移文件: 004_create_documents
描述: 创建知识库文档表

向量存 Chroma，此表只存文档级元数据
数据库配置从 config.py 的 DATABASES 获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from migrations.env import get_engine


def upgrade():
    """
    执行迁移: 创建 documents 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                file_type VARCHAR(16) NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(16) NOT NULL DEFAULT 'ready',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 表/字段注释
        conn.execute(text("COMMENT ON TABLE documents IS '知识库文档表（向量存 Chroma，此处存元数据）';"))
        conn.execute(text("COMMENT ON COLUMN documents.id IS '主键ID';"))
        conn.execute(text("COMMENT ON COLUMN documents.user_id IS '所属用户ID';"))
        conn.execute(text("COMMENT ON COLUMN documents.filename IS '原始文件名';"))
        conn.execute(text("COMMENT ON COLUMN documents.file_type IS '文件类型: txt | md | pdf';"))
        conn.execute(text("COMMENT ON COLUMN documents.file_size IS '文件大小（字节）';"))
        conn.execute(text("COMMENT ON COLUMN documents.chunk_count IS '切分后的片段数';"))
        conn.execute(text("COMMENT ON COLUMN documents.status IS '状态: processing | ready | failed';"))
        conn.execute(text("COMMENT ON COLUMN documents.created_at IS '上传时间';"))

        # 列表接口固定按 (user_id, created_at) 过滤排序
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_user_created ON documents(user_id, created_at);"))

        conn.commit()
    print("✅ Migration 004: documents table created successfully")


def downgrade():
    """
    回滚迁移: 删除 documents 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS documents CASCADE;"))
        conn.commit()
    print("✅ Migration 004: documents table dropped successfully")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration 004: create_documents")
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()