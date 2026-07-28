"""
SSE（Server-Sent Events）公共工具

为长耗时 LLM 任务的流式管线提供统一的事件组装能力（对应 change
add-streaming-pipeline）。三条链路（简历解析 / 简历优化 / JD 匹配）共用。

SSE 协议：每个事件由若干行组成，以空行（\\n\\n）结束：
    event: <事件名>\\n
    data: <JSON 字符串>\\n
    \\n
前端按 \\n\\n 切块、解析 event:/data: 行（见 web/src/utils/sse.ts）。

心跳（保活）：SSE 注释行（以 : 开头）不会触发前端事件，但会刷新连接、
防止 idle 超时——长任务某段无内容可推时定期 yield 它保活。

作者：求职 Copilot 项目
日期：2026-07-23
"""
import json
from typing import Any, Dict


# ============================================================================
# 事件类型常量（三模块共用，对应 design.md「事件协议」表）
# ============================================================================
STAGE = "stage"          # 阶段进度 {message, node?}
SEGMENT = "segment"      # 分段中间结果（结构化任务，如画像的一段）{section, data, confidence?}
TOKEN = "token"          # 增量文本内容（自由文本任务，如简历生成）{delta}
REASONING = "reasoning"  # AI 思考过程（glm-4.5 的 reasoning_content）{delta}
SCORE = "score"          # 评分（JD 匹配）{overall_score, dimension_scores, ...}
DONE = "done"            # 任务完成（最终结果）
ENRICHED = "enriched"    # 增补完成（JD 匹配）{gaps}
ERROR = "error"          # 失败 {error_code, error_message}


# ============================================================================
# 流式响应头
# ============================================================================
# Cache-Control: no-cache —— 禁止中间代理缓存流式响应
# X-Accel-Buffering: no  —— 禁用 nginx 缓冲（若有反代），确保事件即时下发
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
STREAM_MEDIA_TYPE = "text/event-stream"


def sse(event: str, data: Dict[str, Any]) -> str:
    """
    组装一条 SSE 事件字符串。

    Args:
        event: 事件名（用上面的常量）
        data:  事件数据（会被 JSON 序列化，ensure_ascii=False 保留中文）
    Returns:
        形如 "event: stage\\ndata: {...}\\n\\n" 的字符串，可直接 yield

    示例：
        >>> sse("stage", {"message": "正在解析…"})
        'event: stage\\ndata: {"message": "正在解析…"}\\n\\n'
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_keepalive() -> str:
    """
    保活心跳：SSE 注释行（前端忽略，但连接保持活跃）。

    长任务执行中若某段暂时无内容可推（如单段 LLM 仍在生成、未到整段下发时机），
    定期 yield 本函数返回值，防止前端 / 代理 / 浏览器因 idle 而切断连接。

    Returns:
        ': keepalive\\n\\n'
    """
    return ": keepalive\n\n"
