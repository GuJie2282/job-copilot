# -*- coding: utf-8 -*-
"""
语音转写端点测试（add-voice-interview task 1.3.5）

用 TestClient 测 POST /api/interview/voice/transcribe（不需外部启动服务）：
  1. 正常上传：pyttsx3 生成中文 wav → success + text 非空
  2. 空文件：→ error_code=EMPTY_AUDIO
  3. 非音频字节：→ error_code=DECODE_FAILED 或 TRANSCRIBE_ERROR

验证端点的 HTTP 层逻辑（大小校验、错误码透传、ApiResponse 范式）。
真实转写质量已在 test_voice_service 验证。

运行：cd backend && ./.venv/Scripts/python.exe test_voice_api.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def _make_chinese_wav(text: str) -> bytes:
    """pyttsx3 + Windows SAPI 生成中文 wav 字节。"""
    import pyttsx3
    engine = pyttsx3.init()
    for v in engine.getProperty('voices'):
        if 'ZH-CN' in (getattr(v, 'id', '') or '').upper():
            engine.setProperty('voice', v.id)
            break
    path = os.path.join(tempfile.gettempdir(), "voice_api_test.wav")
    engine.save_to_file(text, path)
    engine.runAndWait()
    with open(path, "rb") as f:
        data = f.read()
    os.remove(path)
    return data


def test_normal_upload():
    print("\n[端点1] 正常上传中文 wav...")
    audio = _make_chinese_wav("我在做产品经理的工作，关注用户转化率。")
    r = client.post(
        "/api/interview/voice/transcribe",
        files={"file": ("answer.wav", audio, "audio/wav")},
    )
    j = r.json()
    print(f"  HTTP {r.status_code}  status={j.get('status')}")
    print(f"  识别：{j.get('data', {}).get('text')}")
    assert r.status_code == 200
    assert j["status"] == "success"
    assert len(j["data"]["text"]) > 0
    print("  ✓ 通过")
    return True


def test_empty_file():
    print("\n[端点2] 空文件...")
    r = client.post(
        "/api/interview/voice/transcribe",
        files={"file": ("empty.webm", b"", "audio/webm")},
    )
    j = r.json()
    print(f"  status={j.get('status')} error_code={j.get('data', {}).get('error_code')}")
    assert j["status"] == "error"
    assert j["data"]["error_code"] == "EMPTY_AUDIO"
    print("  ✓ 通过")
    return True


def test_invalid_bytes():
    print("\n[端点3] 非音频字节...")
    fake = b"this is not an audio file, just plain text bytes for testing."
    r = client.post(
        "/api/interview/voice/transcribe",
        files={"file": ("fake.webm", fake, "audio/webm")},
    )
    j = r.json()
    code = j.get("data", {}).get("error_code")
    print(f"  status={j.get('status')} error_code={code}")
    assert j["status"] == "error"
    assert code in ("DECODE_FAILED", "TRANSCRIBE_ERROR"), f"应为解码/转写失败，实为 {code}"
    print("  ✓ 通过")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("语音转写端点测试（TestClient）")
    print("=" * 60)
    results = [
        ("正常上传", test_normal_upload()),
        ("空文件", test_empty_file()),
        ("非音频字节", test_invalid_bytes()),
    ]
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{passed}/{len(results)} 通过")
    sys.exit(0 if passed == len(results) else 1)
