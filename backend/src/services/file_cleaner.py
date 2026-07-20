"""
临时文件清理服务

功能：
1. 清理过期的临时上传文件
2. 支持手动清理和定时清理
3. 记录清理日志

作者：求职 Copilot 项目
日期：2026-07-03
"""

import os
import time
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple, List

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================================
# 配置常量
# ============================================================================

# 临时文件目录
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "resume_uploads")

# 文件过期时间（24 小时）
FILE_EXPIRATION_HOURS = 24

# 清理批次大小（每次最多清理多少个文件）
CLEAN_BATCH_SIZE = 100


# ============================================================================
# 文件清理功能
# ============================================================================

def get_file_age(file_path: str) -> float:
    """
    获取文件年龄（小时）

    Args:
        file_path: 文件路径

    Returns:
        age_hours: 文件年龄（小时）
    """
    if not os.path.exists(file_path):
        return 0.0

    # 获取文件的修改时间
    file_mtime = os.path.getmtime(file_path)

    # 计算文件年龄（小时）
    current_time = time.time()
    age_seconds = current_time - file_mtime
    age_hours = age_seconds / 3600

    return age_hours


def is_file_expired(file_path: str, expiration_hours: float = FILE_EXPIRATION_HOURS) -> bool:
    """
    判断文件是否过期

    Args:
        file_path: 文件路径
        expiration_hours: 过期时间（小时）

    Returns:
        is_expired: 是否过期
    """
    age_hours = get_file_age(file_path)
    return age_hours >= expiration_hours


def clean_expired_files(
    upload_dir: str = UPLOAD_DIR,
    expiration_hours: float = FILE_EXPIRATION_HOURS,
    dry_run: bool = False
) -> Tuple[int, int, List[str]]:
    """
    清理过期的临时文件

    Args:
        upload_dir: 上传目录
        expiration_hours: 过期时间（小时）
        dry_run: 是否只是模拟运行（不实际删除）

    Returns:
        (total_files, deleted_files, errors)
        - total_files: 总文件数
        - deleted_files: 删除的文件数
        - errors: 错误列表
    """
    total_files = 0
    deleted_files = 0
    errors = []

    # 检查目录是否存在
    if not os.path.exists(upload_dir):
        logger.warning(f"上传目录不存在: {upload_dir}")
        return 0, 0, []

    try:
        # 遍历目录中的所有文件
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)

            # 跳过目录
            if os.path.isdir(file_path):
                continue

            total_files += 1

            # 检查是否过期
            if is_file_expired(file_path, expiration_hours):
                try:
                    if not dry_run:
                        os.remove(file_path)
                        logger.info(f"已删除过期文件: {filename}")

                    deleted_files += 1

                except Exception as e:
                    error_msg = f"删除文件失败 {filename}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

    except Exception as e:
        error_msg = f"遍历目录失败: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)

    return total_files, deleted_files, errors


def clean_all_files(upload_dir: str = UPLOAD_DIR, dry_run: bool = False) -> Tuple[int, List[str]]:
    """
    清理所有临时文件（不考虑过期时间）

    Args:
        upload_dir: 上传目录
        dry_run: 是否只是模拟运行

    Returns:
        (deleted_files, errors)
        - deleted_files: 删除的文件数
        - errors: 错误列表
    """
    deleted_files = 0
    errors = []

    if not os.path.exists(upload_dir):
        logger.warning(f"上传目录不存在: {upload_dir}")
        return 0, []

    try:
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)

            if os.path.isfile(file_path):
                try:
                    if not dry_run:
                        os.remove(file_path)
                        logger.info(f"已删除文件: {filename}")

                    deleted_files += 1

                except Exception as e:
                    error_msg = f"删除文件失败 {filename}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

    except Exception as e:
        error_msg = f"遍历目录失败: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)

    return deleted_files, errors


def get_upload_stats(upload_dir: str = UPLOAD_DIR) -> dict:
    """
    获取上传目录统计信息

    Args:
        upload_dir: 上传目录

    Returns:
        stats: 统计信息字典
    """
    if not os.path.exists(upload_dir):
        return {
            "exists": False,
            "total_files": 0,
            "total_size": 0,
            "oldest_file": None,
            "newest_file": None
        }

    total_files = 0
    total_size = 0
    oldest_file = None
    newest_file = None
    oldest_age = 0
    newest_age = float('inf')

    try:
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)

            if os.path.isfile(file_path):
                total_files += 1
                file_size = os.path.getsize(file_path)
                total_size += file_size

                age = get_file_age(file_path)

                if age > oldest_age:
                    oldest_age = age
                    oldest_file = filename

                if age < newest_age:
                    newest_age = age
                    newest_file = filename

    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")

    return {
        "exists": True,
        "upload_dir": upload_dir,
        "total_files": total_files,
        "total_size": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "oldest_file": oldest_file,
        "oldest_age_hours": round(oldest_age, 2) if oldest_file else None,
        "newest_file": newest_file,
        "newest_age_hours": round(newest_age, 2) if newest_file else None
    }


# ============================================================================
# 定时清理任务（需要 APScheduler）
# ============================================================================

def schedule_cleanup():
    """
    启动定时清理任务

    注意：需要在应用启动时调用此函数
    需要安装 APScheduler: pip install apscheduler

    示例：
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            clean_expired_files,
            'interval',
            hours=1,
            id='cleanup_resume_files'
        )
        scheduler.start()
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()

        # 每小时执行一次清理
        scheduler.add_job(
            clean_expired_files,
            'interval',
            hours=1,
            id='cleanup_resume_files',
            name='清理过期简历文件'
        )

        scheduler.start()

        logger.info("定时清理任务已启动（每小时执行一次）")

        return scheduler

    except ImportError:
        logger.warning("APScheduler 未安装，定时清理任务未启动")
        logger.info("安装方式: pip install apscheduler")
        return None
    except Exception as e:
        logger.error(f"启动定时清理任务失败: {str(e)}")
        return None


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("临时文件清理测试")
    print("=" * 60)

    # 测试 1：获取统计信息
    print("\n[TEST 1] 获取上传目录统计")
    stats = get_upload_stats()
    print(f"✓ 目录存在: {stats['exists']}")
    print(f"✓ 总文件数: {stats['total_files']}")
    print(f"✓ 总大小: {stats['total_size_mb']} MB")
    if stats['oldest_file']:
        print(f"✓ 最旧文件: {stats['oldest_file']} ({stats['oldest_age_hours']} 小时前)")
    if stats['newest_file']:
        print(f"✓ 最新文件: {stats['newest_file']} ({stats['newest_age_hours']} 小时前)")

    # 测试 2：清理过期文件（模拟运行）
    print("\n[TEST 2] 清理过期文件（模拟运行）")
    total, deleted, errors = clean_expired_files(dry_run=True)
    print(f"✓ 总文件数: {total}")
    print(f"✓ 将删除: {deleted} 个文件")
    if errors:
        print(f"✗ 错误数: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

    # 测试 3：实际清理（如果需要）
    print("\n[TEST 3] 是否实际清理？")
    print("如需实际清理，请设置 dry_run=False")

    print("\n" + "=" * 60)
