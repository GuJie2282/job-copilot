"""
src.core.sse 公共 SSE 工具的单元测试（对应 change add-streaming-pipeline 任务 1.1.3）。

验证：事件组装格式、心跳格式、JSON 序列化（中文不转义）、响应头常量。
独立可跑，不依赖 LLM / 数据库：
    cd backend && python test_sse.py
"""
import json
import sys
from pathlib import Path

# 让 test_*.py 在 backend/ 根直接跑（无需安装为包）：把 src 加入 path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.sse import (
    sse,
    sse_keepalive,
    STAGE,
    TOKEN,
    DONE,
    ERROR,
    STREAM_HEADERS,
    STREAM_MEDIA_TYPE,
)


def test_sse_event_format():
    """sse() 组装的事件：event 行 + data 行(JSON) + 空行结束"""
    out = sse(STAGE, {"message": "正在解析…"})
    assert out == 'event: stage\ndata: {"message": "正在解析…"}\n\n', f"实际: {out!r}"


def test_sse_data_json_serialized():
    """data 被序列化为 JSON，中文不转义（ensure_ascii=False）"""
    out = sse(TOKEN, {"delta": "你好"})
    lines = out.splitlines()
    assert lines[0] == "event: token"
    assert lines[1].startswith("data: ")
    payload = json.loads(lines[1][len("data: "):])
    assert payload == {"delta": "你好"}


def test_sse_keepalive_format():
    """心跳：SSE 注释行（以 : 开头），前端忽略但保活；以空行结束"""
    assert sse_keepalive() == ": keepalive\n\n"


def test_event_type_constants():
    """事件类型常量齐备"""
    assert {STAGE, TOKEN, DONE, ERROR} == {"stage", "token", "done", "error"}


def test_stream_headers_and_media_type():
    """流式响应头与 media_type 常量齐备"""
    assert STREAM_HEADERS["Cache-Control"] == "no-cache"
    assert STREAM_HEADERS["X-Accel-Buffering"] == "no"
    assert STREAM_MEDIA_TYPE == "text/event-stream"


if __name__ == "__main__":
    test_sse_event_format()
    test_sse_data_json_serialized()
    test_sse_keepalive_format()
    test_event_type_constants()
    test_stream_headers_and_media_type()
    print("✅ src.core.sse 工具测试全部通过")
