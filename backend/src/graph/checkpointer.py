"""
面试会话 checkpointer（会话状态层）
================================

模拟面试是「长程会话」，状态需要跨 HTTP 请求、抗进程重启持久化。
本模块封装 LangGraph 的 checkpointer，提供会话状态层入口。

三层存储分层（对齐 design.md 决策 2）：
  ① 业务数据（job_copilot.db 的业务表）—— 画像、JD匹配、面经，跨会话长期资产
  ② 会话状态（interview_checkpoints.db，本模块）—— 面试进度/transcript，一次面试的生命周期
  ③ 对话记忆（MemorySaver）—— 通用 chat，临时

为什么独立文件：会话状态是「过程数据」，与业务「档案数据」分开，
便于清理/迁移，不污染业务库。

抗重启原理：SqliteSaver 把每轮 checkpoint 写进 db 文件；
进程重启后，新进程连同一个 db 文件、用同一个 thread_id，即可恢复到上次断点。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import os
import sqlite3
import logging
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

# 独立于业务库（job_copilot.db）的会话状态库文件
# __file__ = backend/src/graph/checkpointer.py → 上溯 3 层到 backend/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INTERVIEW_CHECKPOINT_DB_PATH = os.path.join(_BACKEND_DIR, "interview_checkpoints.db")


# ============================================================================
# 单例：SqliteSaver（一个进程共享一个连接 + saver）
# ============================================================================

_sqlite_saver: Optional[object] = None
_sqlite_conn: Optional[sqlite3.Connection] = None


def get_interview_checkpointer(use_memory: bool = False):
    """
    获取面试会话 checkpointer。

    Args:
        use_memory: True 时用 MemorySaver（仅内存，重启丢失）；
                    False（默认）用 SqliteSaver（持久化到 db 文件，抗重启）。

    Returns:
        LangGraph checkpointer 实例。

    说明：
    - SqliteSaver 采用进程级单例，避免反复建连接。
    - 若环境未安装 langgraph-checkpoint-sqlite，自动降级为 MemorySaver 并告警
      （保证面试能跑，但失去抗重启能力）。
    """
    # 测试/无持久化需求：直接用内存
    if use_memory:
        return MemorySaver()

    global _sqlite_saver, _sqlite_conn
    if _sqlite_saver is not None:
        return _sqlite_saver

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        logger.warning(
            "未安装 langgraph-checkpoint-sqlite，面试会话降级为 MemorySaver（无抗重启）。"
            "请运行 pip install langgraph-checkpoint-sqlite==2.0.11"
        )
        return MemorySaver()

    # 确保目录存在
    os.makedirs(os.path.dirname(INTERVIEW_CHECKPOINT_DB_PATH), exist_ok=True)

    # 建连接 + saver + 建表
    _sqlite_conn = sqlite3.connect(INTERVIEW_CHECKPOINT_DB_PATH, check_same_thread=False)
    _sqlite_saver = SqliteSaver(_sqlite_conn)
    _sqlite_saver.setup()  # 创建 checkpoint 表

    logger.info(f"面试会话 checkpointer 已就绪：{INTERVIEW_CHECKPOINT_DB_PATH}")
    return _sqlite_saver


def close_interview_checkpointer() -> None:
    """关闭 checkpointer 连接（应用停机/测试清理时调用）。"""
    global _sqlite_saver, _sqlite_conn
    if _sqlite_conn is not None:
        try:
            _sqlite_conn.close()
        except Exception:
            pass
    _sqlite_saver = None
    _sqlite_conn = None


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("面试 checkpointer 自检")
    print("=" * 60)

    cp = get_interview_checkpointer()
    cp_type = type(cp).__name__
    print(f"\n✓ checkpointer 类型：{cp_type}")
    print(f"  db 路径：{INTERVIEW_CHECKPOINT_DB_PATH}")
    print(f"  持久化：{'是（抗重启）' if 'Sqlite' in cp_type else '否（仅内存）'}")

    close_interview_checkpointer()
    print("\n✓ 自检完成")
