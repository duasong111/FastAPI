# 配置有关的静态文件
# 正式环境配置
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'go_pg',
#         'USER': 'user_rthXrh',
#         'PASSWORD': 'password_prabtR',
#         'HOST': '1Panel-postgresql-iqTx',
#         'PORT': '5432',
#     }
# }
# 开发环境
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_pg',
        'USER': 'postgres',
        'PASSWORD': 'gsm200818534',
        'HOST': '10.1.1.136',
        'PORT': '5432',
    }
}
# 开发环境配置
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'intellicamera',
#         'USER': 'postgres',
#         'PASSWORD': 'gsm200818534',
#         'HOST': '10.1.1.136',
#         'PORT': '5432',
#     }
# }

securityCode = "rewcef10fSd08FDS3ADVTSSA"
CODE_ERROR = 400
CODE_SUCCESS = 200

# 正式环境配置
# REDIS_HOST = "1Panel-redis-NGma"
# REDIS_PORT = 6379
# REDIS_PASSWORD = "redis_password"
# REDIS_DB = 7


# 开发环境配置
REDIS_HOST = "10.1.1.136"
REDIS_PORT = 6379
REDIS_PASSWORD = "gsm200818534"
REDIS_DB = 7

REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# RUSTFS 设置桶
BUCKET_IP = "43.136.37.113"
BUCKET_PORT = "9000"
RUSTFS_BUCKET_NAME = "rustfsadmin"
RUSTFS_SECRET = "rustfsadmin_8bGjFM"

# 用户头像桶（需要新建桶或在 RUSTFS 控制台创建）
AVATAR_BUCKET_NAME = "avatar"

