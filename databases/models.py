# Database models
from sqlalchemy import Column, Integer, String, DateTime
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
