# migrations package
"""
数据库迁移模块

所有迁移文件使用 Python 格式，存放在 versions/ 目录下
每个迁移文件必须包含 upgrade() 和 downgrade() 两个函数
数据库配置从 config.py 的 DATABASES 获取
"""