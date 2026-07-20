"""
结构化日志配置模块

提供统一的日志配置和格式化：
- JsonFormatter: JSON格式化器
- setup_logging: 开发环境日志配置
- setup_logging_production: 生产环境日志配置

作者：求职 Copilot 项目
创建时间：2025-01-01
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from logging import LogRecord


class JsonFormatter(logging.Formatter):
    """JSON 格式化器

    将日志记录格式化为 JSON 字符串，便于日志分析和查询
    """

    def format(self, record: LogRecord) -> str:
        """格式化日志记录为 JSON

        参数：
            record: 日志记录

        返回：
            str: JSON 字符串
        """
        # 基础字段
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }

        # 添加 extra 字段（如果存在）
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "email"):
            log_data["email"] = record.email
        if hasattr(record, "ip"):
            log_data["ip"] = record.ip
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "error"):
            log_data["error"] = record.error
        if hasattr(record, "reason"):
            log_data["reason"] = record.reason
        if hasattr(record, "code"):
            log_data["code"] = record.code

        # 添加异常信息（如果存在）
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加文件名和行号
        log_data["file"] = record.pathname
        log_data["line"] = record.lineno

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """配置开发环境日志

    开发环境使用 DEBUG 级别，输出到控制台
    """
    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 清除现有处理器
    logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(JsonFormatter())

    # 添加处理器
    logger.addHandler(console_handler)

    # 设置第三方库日志级别（减少噪音）
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def setup_logging_production() -> None:
    """配置生产环境日志

    生产环境使用 INFO 级别，输出到文件（按日期轮转）
    """
    from logging.handlers import TimedRotatingFileHandler
    from pathlib import Path

    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 清除现有处理器
    logger.handlers.clear()

    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 创建文件处理器（按天轮转，保留30天）
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "job-copilot.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JsonFormatter())

    # 添加处理器
    logger.addHandler(file_handler)

    # 同时输出到控制台（可选，便于容器日志收集）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


# 在模块导入时自动配置日志
if __name__ != "__main__":
    # 检查环境变量决定使用哪个配置
    import os

    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        setup_logging_production()
    else:
        setup_logging()
