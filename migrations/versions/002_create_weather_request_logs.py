"""
迁移文件: 002_create_weather_request_logs
创建时间: 2026-07-20
描述: 创建天气查询请求日志表

数据库配置从 config.py 的 DATABASES 获取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from migrations.env import get_engine


def upgrade():
    """
    执行迁移: 创建 weather_request_logs 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        # 创建表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather_request_logs (
                id SERIAL PRIMARY KEY,
                city VARCHAR(50) NOT NULL DEFAULT '武汉',
                request_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(50),
                user_agent VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 添加表注释
        conn.execute(text("COMMENT ON TABLE weather_request_logs IS '天气查询请求日志表';"))
        conn.execute(text("COMMENT ON COLUMN weather_request_logs.id IS '主键ID';"))
        conn.execute(text("COMMENT ON COLUMN weather_request_logs.city IS '查询城市';"))
        conn.execute(text("COMMENT ON COLUMN weather_request_logs.request_time IS '请求时间';"))
        conn.execute(text("COMMENT ON COLUMN weather_request_logs.ip_address IS '请求IP地址';"))
        conn.execute(text("COMMENT ON COLUMN weather_request_logs.user_agent IS '用户代理';"))
        conn.execute(text("COMMENT ON COLUMN weather_request_logs.created_at IS '记录创建时间';"))

        # 创建索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_weather_request_logs_city ON weather_request_logs(city);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_weather_request_logs_request_time ON weather_request_logs(request_time);"))

        conn.commit()
    print("✅ Migration 002: weather_request_logs table created successfully")


def downgrade():
    """
    回滚迁移: 删除 weather_request_logs 表
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS weather_request_logs;"))
        conn.commit()
    print("✅ Migration 002: weather_request_logs table dropped successfully")


if __name__ == "__main__":
    # 直接运行此文件执行迁移
    import argparse
    parser = argparse.ArgumentParser(description="Migration 002: create_weather_request_logs")
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()