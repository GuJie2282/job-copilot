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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

# 加载环境变量
load_dotenv()

# 创建 FastAPI 应用实例
app = FastAPI(
    title="求职 Copilot API",
    description="AI 求职教练后端服务 - 提供用户认证、JD 匹配、简历优化等功能",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI 文档地址
    redoc_url="/redoc"  # ReDoc 文档地址
)

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
app.include_router(auth_router, prefix="/auth", tags=["认证"])

# TODO: 注册用户路由
# from src.api.users import user_router
# app.include_router(user_router, prefix="/users", tags=["用户"])

# TODO: 注册业务路由（JD 匹配、简历优化等）
# from src.api.jd_matching import jd_router
# app.include_router(jd_router, prefix="/api", tags=["业务"])

if __name__ == "__main__":
    import uvicorn

    # 启动开发服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 监听所有网络接口
        port=8000,  # 端口
        reload=True,  # 开发模式：代码修改自动重载
        log_level="info"  # 日志级别
    )
