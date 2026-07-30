"""
求职 Copilot 后端服务 - FastAPI 应用入口

这是后端服务的入口文件，负责：
1. 初始化 FastAPI 应用
2. 配置 CORS 跨域支持
3. 注册所有 API 路由
4. 配置限流中间件
5. 启动数据库连接

作者：求职 Copilot 项目
创建时间：2025-01-01
"""

# 第一步：设置UTF-8编码（必须在所有导入之前）
import sys
import io

# 修复Windows下的文件读取编码问题
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# 加载环境变量
load_dotenv()

# 配置日志系统（尽早配置）
from src.core.logging import setup_logging

setup_logging()

# 导入数据库模型和 Base
from src.models.base import Base, engine
from src.models import user  # 导入模型以注册到 Base.metadata
from src.models import profile  # 导入画像与匹配结果模型以注册到 Base.metadata
from src.models import interview  # 导入面试会话模型以注册到 Base.metadata
from src.models import knowledge  # 导入面经库模型（个人/公司）以注册到 Base.metadata
from src.models import resume  # 导入简历模型（简历优化产物）以注册到 Base.metadata

# 创建数据库表（如果不存在）
Base.metadata.create_all(bind=engine)

# 轻量迁移（add-resume-avatar）：create_all 不给已有表加列，
# 启动时检查 user_profiles 是否缺 avatar_url，缺则自动 ALTER（重启即生效，不丢数据）
try:
    from sqlalchemy import inspect, text as _sa_text
    _insp = inspect(engine)
    if _insp.has_table("user_profiles"):
        _cols = [c["name"] for c in _insp.get_columns("user_profiles")]
        if "avatar_url" not in _cols:
            with engine.begin() as conn:
                conn.execute(_sa_text("ALTER TABLE user_profiles ADD COLUMN avatar_url VARCHAR(500)"))
            print("[INFO] migrated: added user_profiles.avatar_url")
except Exception as _me:
    print(f"[WARNING] avatar_url migration skipped: {_me}")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="求职 Copilot API",
    description="AI 求职教练后端服务 - 提供用户认证、JD 匹配、简历优化等功能",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI 文档地址
    redoc_url="/redoc"  # ReDoc 文档地址
)

# 头像等静态资源服务（add-resume-avatar）：挂 /static → backend/data
# 头像存 data/avatars/{user_id}.{ext}，前端 <img src="/static/avatars/...">；PDF 导出时后端转 base64 兜底
# 用 __file__ 算绝对路径，不受 uvicorn 启动工作目录影响（main.py 在 backend/src/，data 在 backend/data）
from fastapi.staticfiles import StaticFiles
STATIC_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(os.path.join(STATIC_DATA_DIR, "avatars"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DATA_DIR), name="static")

# 导入限流器
from src.core.limiter import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 配置 CORS 跨域支持
# 允许前端（Vue 3 应用）跨域访问后端 API
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],  # 允许的前端地址
    # 公网测试：额外放行 cpolar 内网穿透的随机域名（免费版每次重启域名都变，用正则一劳永逸匹配）
    allow_origin_regex=r"https://[a-z0-9]+\.r\d+\.cpolar\.cn",
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET、POST、PUT、DELETE 等）
    allow_headers=["*"],  # 允许所有请求头（包括 Authorization）
)

# 应用根路径
@app.get("/")
async def root():
    """
    API 根路径
    返回服务基本信息
    """
    return {
        "message": "欢迎使用求职 Copilot API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """
    健康检查端点
    用于容器编排和服务监控
    """
    return {
        "status": "healthy",
        "service": "job-copilot-backend"
    }

# 注册认证路由
from src.api.auth import auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])

# 注册简历解析路由
from src.api.resume import resume_router
app.include_router(resume_router, prefix="/api/resume", tags=["简历解析"])

# TODO: 注册用户路由
# from src.api.users import user_router
# app.include_router(user_router, prefix="/users", tags=["用户"])

# 注册 JD 匹配路由
from src.api.jd import jd_router
app.include_router(jd_router, prefix="/api/jd", tags=["JD 匹配"])

# 注册简历优化路由（路径 A：自动生成；与简历解析共用 /api/resume 前缀，路径不冲突）
from src.api.resume_optimize import resume_optimize_router
app.include_router(resume_optimize_router, prefix="/api/resume", tags=["简历优化"])

# 注册模拟面试路由
from src.api.interview import interview_router
app.include_router(interview_router, prefix="/api/interview", tags=["模拟面试"])

# 注册语音转写路由（add-voice-interview：语音回答模式的后端转写端点，零侵入面试链路）
from src.api.voice import voice_router
app.include_router(voice_router, prefix="/api/interview/voice", tags=["语音转写"])

from src.api.knowledge import knowledge_router
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["面经库"])

if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取配置，使用默认值作为后备
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    # 启动开发服务器
    uvicorn.run(
        "src.main:app",  # 修正模块路径
        host=host,  # 监听所有网络接口
        port=port,  # 从环境变量读取端口
        reload=True,  # 开发模式：代码修改自动重载
        log_level="info"  # 日志级别
    )
