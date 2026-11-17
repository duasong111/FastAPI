"""
用户功能序列化器

定义用户注册、登录、模型设置相关的请求/响应数据模型
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ============== 请求模型 ==============

class RegisterRequest(BaseModel):
    """
    用户注册请求参数

    Attributes:
        username: 用户名，登录账号
        password: 明文密码，服务端只存 bcrypt 哈希
    """
    username: str = Field(
        ..., min_length=3, max_length=50, description="用户名，登录账号（3-50 字符）"
    )
    password: str = Field(
        ..., min_length=6, max_length=128, description="明文密码，服务端只存 bcrypt 哈希"
    )


class LoginRequest(BaseModel):
    """
    用户登录请求参数

    Attributes:
        username: 用户名
        password: 明文密码
    """
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="明文密码")


class LLMConfigRequest(BaseModel):
    """
    用户大模型配置请求（BYOK）

    Attributes:
        provider: 服务商，deepseek | minimax
        api_key: 用户自己的 API key，服务端加密后落库
        model: 模型名，留空则用该服务商的默认模型
    """
    provider: str = Field(..., description="模型服务商: deepseek | minimax")
    api_key: str = Field(..., min_length=8, max_length=200, description="用户自己的 API key")
    model: Optional[str] = Field(
        default=None, description="模型名，留空则使用该服务商的默认模型"
    )


# ============== 数据模型 ==============

class ProviderInfo(BaseModel):
    """
    可选的模型服务商信息

    Attributes:
        provider: 服务商标识
        models: 该服务商支持的模型列表
        default_model: 默认模型
    """
    provider: str = Field(..., description="服务商标识: deepseek | minimax")
    models: List[str] = Field(..., description="该服务商支持的模型列表")
    default_model: str = Field(..., description="默认模型")


class UserData(BaseModel):
    """
    用户信息数据模型

    Attributes:
        user_id: 用户主键
        username: 用户名
        llm_provider: 已配置的模型服务商，未配置为 None
        llm_model: 已配置的模型名
        has_llm_key: 是否已配置可用的 API key
        providers: 系统支持的服务商清单
        created_at: 注册时间
    """
    user_id: int = Field(..., description="用户主键ID")
    username: str = Field(..., description="用户名")
    llm_provider: Optional[str] = Field(default=None, description="已配置的模型服务商")
    llm_model: Optional[str] = Field(default=None, description="已配置的模型名")
    has_llm_key: bool = Field(default=False, description="是否已配置可用的 API key")
    providers: List[ProviderInfo] = Field(default_factory=list, description="系统支持的服务商清单")
    created_at: str = Field(..., description="注册时间")


# ============== 响应模型 ==============

class RegisterResponse(BaseModel):
    """
    用户注册统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 注册结果
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: UserData = Field(..., description="注册结果")


class LoginResponse(BaseModel):
    """
    用户登录统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 登录结果，含 JWT 令牌
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: "LoginData" = Field(..., description="登录结果")


class LoginData(BaseModel):
    """
    登录结果数据模型

    Attributes:
        access_token: JWT 令牌，后续请求放 Authorization: Bearer <token>
        token_type: 令牌类型
        expires_in: 有效期（秒）
        user: 用户信息
    """
    access_token: str = Field(..., description="JWT 令牌，后续请求放 Authorization: Bearer <token>")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(..., description="有效期（秒）")
    user: UserData = Field(..., description="用户信息")


class UserResponse(BaseModel):
    """
    用户信息统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 用户信息
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: UserData = Field(..., description="用户信息")


class LLMConfigResponse(BaseModel):
    """
    模型配置统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 配置结果，不回显 API key 明文
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: UserData = Field(..., description="配置结果，不回显 API key 明文")


# 解决 LoginResponse 对 LoginData 的前向引用
LoginResponse.model_rebuild()