# Database models
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
)
from datetime import datetime
from databases.database import Base


class TimeRequestLog(Base):
    """时间接口请求日志表"""
    __tablename__ = "time_request_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_time = Column(DateTime, nullable=False, default=datetime.now, comment="请求时间")
    ip_address = Column(String(50), nullable=True, comment="请求IP地址")
    user_agent = Column(String(500), nullable=True, comment="用户代理")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="记录创建时间")

    def __repr__(self):
        return f"<TimeRequestLog(id={self.id}, request_time={self.request_time})>"


class WeatherRequestLog(Base):
    """天气查询请求日志表"""
    __tablename__ = "weather_request_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    city = Column(String(50), nullable=False, default="武汉", comment="查询城市")
    request_time = Column(DateTime, nullable=False, default=datetime.now, comment="请求时间")
    ip_address = Column(String(50), nullable=True, comment="请求IP地址")
    user_agent = Column(String(500), nullable=True, comment="用户代理")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="记录创建时间")

    def __repr__(self):
        return f"<WeatherRequestLog(id={self.id}, city={self.city})>"


# ============== 知识库 / 用户体系 ==============

class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    username = Column(
        String(50), nullable=False, unique=True, index=True, comment="用户名（登录账号）"
    )
    password_hash = Column(String(255), nullable=False, comment="密码哈希（bcrypt，不可逆）")

    # ---- BYOK：用户自带的聊天大模型配置 ----
    # 服务器不持有任何大模型 key，由用户自行上传，Fernet 加密后落库
    llm_provider = Column(
        String(32), nullable=True, comment="聊天模型服务商: deepseek | minimax"
    )
    llm_api_key_encrypted = Column(
        Text, nullable=True, comment="用户自带的 LLM API key（Fernet 密文）"
    )
    llm_model = Column(String(64), nullable=True, comment="用户选择的模型名，空则用服务商默认模型")

    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="注册时间")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"

    @property
    def has_llm_key(self) -> bool:
        """是否已配置可用的聊天模型 key"""
        return bool(self.llm_provider and self.llm_api_key_encrypted)


class Document(Base):
    """知识库文档表

    向量本身存 Chroma，这里存文档级元数据，用于列表展示与删除定位。
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID"
    )
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_type = Column(String(16), nullable=False, comment="文件类型: txt | md | pdf")
    file_size = Column(Integer, nullable=False, default=0, comment="文件大小（字节）")
    chunk_count = Column(Integer, nullable=False, default=0, comment="切分后的片段数")
    status = Column(
        String(16), nullable=False, default="ready", comment="状态: processing | ready | failed"
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="上传时间")

    __table_args__ = (
        Index("idx_documents_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Document(id={self.id}, user_id={self.user_id}, filename={self.filename})>"


class DocumentChunk(Base):
    """文档切片表

    Chroma 里只存向量与 metadata，这里额外存原文，
    便于"查看某文档的全部切片"与删除时按 metadata 清理向量。
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID"
    )
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="所属文档ID"
    )
    chunk_index = Column(Integer, nullable=False, comment="切片序号（从 0 开始）")
    content = Column(Text, nullable=False, comment="切片原文")
    token_count = Column(Integer, nullable=False, default=0, comment="token 数")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_chunks_user_doc_index", "user_id", "document_id", "chunk_index"),
    )

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"


class AskLog(Base):
    """知识库问答日志表"""
    __tablename__ = "ask_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="提问用户ID"
    )
    question = Column(Text, nullable=False, comment="用户提问")
    answer_preview = Column(String(500), nullable=True, comment="回答摘要（前 500 字）")
    source_count = Column(Integer, nullable=False, default=0, comment="命中的引用片段数")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="提问时间")

    __table_args__ = (
        Index("idx_ask_logs_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<AskLog(id={self.id}, user_id={self.user_id})>"
