"""
SQLAlchemy 基类和数据库配置

这个模块定义了：
1. SQLAlchemy Base 类 - 所有数据库模型的基类
2. 数据库引擎配置
3. Session 管理
4. Base 模型（包含通用字段）

使用方式：
    from src.models.base import Base
    from src.models.user import User

    # 创建表
    Base.metadata.create_all(bind=engine)
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 从环境变量读取数据库 URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job_copilot.db")

# 创建数据库引擎
# SQLite 需要 check_same_thread=False 来支持多线程
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL 或其他数据库
    engine = create_engine(DATABASE_URL)

# 创建 SessionLocal 类
# 每次调用 SessionLocal() 都会创建一个新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 Base 类
# 所有数据库模型都应该继承自这个 Base
Base = declarative_base()


class BaseModel(Base):
    """
    所有数据库模型的基类
    包含通用的字段和方法
    """
    __abstract__ = True  # 抽象基类，不会创建对应的表

    # 所有表都会有的通用字段（可选）
    # id = Column(Integer, primary_key=True, index=True)
    # created_at = Column(DateTime, default=datetime.utcnow)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    """
    数据库会话依赖注入函数

    使用方式（在 FastAPI 路由中）：
        @app.get("/users/{user_id}")
        def read_user(user_id: int, db: Session = Depends(get_db)):
            user = db.query(User).filter(User.id == user_id).first()
            return user

    返回：
        Session: 数据库会话对象

    注意：
        使用完后会自动关闭会话（通过 yield）
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
