# Serializer 序列化器开发规范

> 本文档定义了使用 AI 工具生成 Serializer 模块时必须遵守的规则和约定。

---

## 📌 核心原则

### 1. 文件命名规范

**每个具体功能对应一个独立的 .py 文件，文件命名规则：**

```
Serializer/
├── __init__.py
├── WeatherSerializer.py        # 天气功能的序列化器
├── TimeSerializer.py          # 时间功能的序列化器
├── UserSerializer.py          # 用户功能的序列化器
└── ...
```

**命名要求：**
- 文件名必须以 `Serializer` 结尾
- 使用帕斯卡命名法（PascalCase）
- 功能名在前，例如：`WeatherSerializer`、`UserSerializer`

---

### 2. 文件内部结构

每个序列化器文件必须包含以下结构：

```python
"""
[功能名称]序列化器

定义[功能]相关的请求/响应数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


# ============== 请求模型 ==============

class [功能]Request(BaseModel):
    """
    [功能]请求参数

    Attributes:
        [字段]: [说明]
    """
    [字段名]: [类型] = Field(..., description="[说明]")


# ============== 响应模型 ==============

class [功能]Data(BaseModel):
    """
    [功能]数据模型

    Attributes:
        [字段]: [说明]
    """
    [字段名]: [类型] = Field(..., description="[说明]")


class [功能]Response(BaseModel):
    """
    [功能]统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 数据
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: [功能]Data = Field(..., description="数据")
```

---

## 📋 编写规范详解

### 1. 必须遵守的规则

#### ✅ 必须做的事

| 规则 | 说明 | 示例 |
|------|------|------|
| 文件必须有 docstring | 文件顶部说明功能 | `"""天气功能序列化器"""` |
| 类必须有 docstring | 类说明用途 | `"""天气查询请求参数"""` |
| 字段必须有 description | 描述字段含义 | `Field(..., description="城市名称")` |
| 类属性使用 Field | 不要直接用类型注解 | `city: str = Field(..., max_length=50)` |
| 响应模型统一格式 | code/message/data 三件套 | 参考模板 |
| 中文注释 | 所有说明用中文 | 字段、类、模块都要注释 |

#### ❌ 禁止做的事

| 禁止 | 原因 |
|------|------|
| 业务逻辑 | Serializer 只负责数据格式，业务逻辑放在 functions/ |
| 数据库操作 | 数据访问放在 databases/ |
| 缓存操作 | 缓存操作放在 common/ |
| 硬编码配置 | 配置从 config.py 读取 |
| 多个功能混合 | 一个文件只对应一个功能 |

---

### 2. 字段定义规范

#### 必填字段

```python
field_name: type = Field(..., description="说明")
```

#### 可选字段

```python
field_name: Optional[type] = Field(default=默认值, description="说明")
```

#### 带验证的字段

```python
# 长度限制
name: str = Field(..., min_length=1, max_length=50, description="名称")

# 数值范围
age: int = Field(..., ge=0, le=150, description="年龄")

# 邮箱验证
email: EmailStr = Field(..., description="邮箱")

# 正则验证
phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")

# 枚举值
status: str = Field(..., regex="^(active|inactive)$", description="状态")
```

---

### 3. 响应模型规范

**统一响应格式（必须遵守）：**

```python
class [功能]Response(BaseModel):
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: [功能]Data = Field(..., description="业务数据")
```

**错误响应（可选）：**

```python
class ErrorResponse(BaseModel):
    code: int = Field(default=400, description="错误码")
    message: str = Field(..., description="错误信息")
    data: Optional[dict] = Field(default=None, description="错误详情")
```

---

## 📁 完整示例

### WeatherSerializer.py

```python
"""
天气功能序列化器

定义天气相关的请求/响应数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


# ============== 请求模型 ==============

class WeatherQueryRequest(BaseModel):
    """
    天气查询请求参数

    Attributes:
        city: 城市名称，默认武汉
    """
    city: Optional[str] = Field(
        default="武汉",
        min_length=1,
        max_length=50,
        description="城市名称，默认武汉"
    )


# ============== 响应模型 ==============

class WeatherData(BaseModel):
    """
    天气数据模型

    Attributes:
        city: 城市名称
        weather: 天气状况
        temperature: 温度（摄氏度）
        humidity: 湿度百分比
        wind: 风向和风力
        air_quality: 空气质量
        update_time: 更新时间
        cached: 是否来自缓存
        source: 数据来源
    """
    city: str = Field(..., description="城市名称")
    weather: str = Field(..., description="天气状况")
    temperature: int = Field(..., ge=-50, le=60, description="温度（摄氏度）")
    humidity: int = Field(..., ge=0, le=100, description="湿度百分比")
    wind: str = Field(..., description="风向和风力")
    air_quality: str = Field(..., description="空气质量")
    update_time: str = Field(..., description="更新时间")
    cached: bool = Field(default=True, description="是否来自缓存")
    source: str = Field(default="api", description="数据来源")


class WeatherResponse(BaseModel):
    """
    天气查询统一响应格式

    Attributes:
        code: 状态码，200 表示成功
        message: 响应消息
        data: 天气数据
    """
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: WeatherData = Field(..., description="天气数据")
```

---

## 🔧 在路由中使用

```python
# main.py
from Serializer.WeatherSerializer import WeatherQueryRequest, WeatherResponse

@app.get("/api/weather", response_model=WeatherResponse)
async def get_weather(
    request: Request,
    query: WeatherQueryRequest = Depends()
):
    """
    获取天气信息
    """
    weather_data = get_weather_data(query.city)

    return WeatherResponse(
        code=200,
        message="success",
        data=weather_data
    )
```

---

## 📊 检查清单

AI 生成 Serializer 时必须检查：

- [ ] 文件名是否符合 `XxxSerializer.py` 规范？
- [ ] 文件顶部是否有中文 docstring？
- [ ] 类是否有 docstring 描述？
- [ ] 字段是否使用 `Field(..., description="...")` 定义？
- [ ] 必填字段是否用 `...`？
- [ ] 可选字段是否有默认值？
- [ ] 数值字段是否有限制范围（ge/le）？
- [ ] 字符串字段是否限制长度（min_length/max_length）？
- [ ] 响应模型是否包含 `code/message/data`？
- [ ] 是否没有业务逻辑、数据库操作？

---

## 🔗 相关文档

- [AI_DESIGN_SPECIFICATION.md](AI_DESIGN_SPECIFICATION.md) - AI 辅助开发总规范
- [functions/](functions/) - 业务逻辑模块
- [databases/](databases/) - 数据库模型
- [common/](common/) - 公共工具

---

**版本：** v1.0
**最后更新：** 2026-07-21
**适用项目：** FastAPI 自动化 Docker 部署项目