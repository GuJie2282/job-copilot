# -*- coding: utf-8 -*-
"""
voice_service 单元测试（add-voice-interview task 1.2.5）

三场景：
  1. 正常转写：pyttsx3 生成中文 wav → transcribe → ok=True，识别"产品经理/转化率"
  2. 空音频：b"" → ok=False，error=EMPTY_AUDIO（不触发模型加载，快速返回）
  3. 格式异常：非音频字节 → ok=False，error=DECODE_FAILED 或 TRANSCRIBE_ERROR

运行：cd backend && ./.venv/Scripts/python.exe test_voice_service.py
（首次会下载 small 模型权重，需 HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1）
"""
import os
import sys
import tempfile

# 确保能 import src.services.voice_service
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.voice_service import transcribe_audio, TranscribeResult


def _make_chinese_wav(text: str) -> bytes:
    """用 pyttsx3 + Windows SAPI 生成中文 wav 字节。"""
    import pyttsx3
    engine = pyttsx3.init()
    for v in engine.getProperty('voices'):
        if 'ZH-CN' in (getattr(v, 'id', '') or '').upper():
            engine.setProperty('voice', v.id)
            break
    path = os.path.join(tempfile.gettempdir(), "voice_test_case.wav")
    engine.save_to_file(text, path)
    engine.runAndWait()
    with open(path, "rb") as f:
        data = f.read()
    os.remove(path)
    return data


def test_normal_transcription():
    """场景 1：正常中文音频 → 转写成功。"""
    print("\n[场景1] 正常中文音频转写...")
    audio = _make_chinese_wav("我在做产品经理的工作，关注转化率和用户留存。")
    result = transcribe_audio(audio, "normal.wav")
    print(f"  ok={result.ok} error={result.error}")
    print(f"  识别：{result.text}")
    assert result.ok is True, f"应成功，但 error={result.error}"
    assert result.error is None
    assert len(result.text) > 0, "识别文本不应为空"
    # 关键术语应大致命中（繁简皆可，加 initial_prompt 后倾向简体）
    assert any(k in result.text for k in ("产品", "產品", "经理", "經理")), \
        f"未识别出关键词，识别为：{result.text}"
    print("  ✓ 通过")
    return True


def test_empty_audio():
    """场景 2：空音频 → EMPTY_AUDIO（不应触发模型加载）。"""
    print("\n[场景2] 空音频...")
    result = transcribe_audio(b"", "empty.webm")
    print(f"  ok={result.ok} error={result.error} message={result.message}")
    assert result.ok is False
    assert result.error == TranscribeResult.EMPTY_AUDIO
    print("  ✓ 通过")
    return True


def test_invalid_format():
    """场景 3：非音频字节 → 解码/转写失败。"""
    print("\n[场景3] 非音频字节（伪造内容）...")
    fake = "这不是音频文件，只是一段普通文本字节，没有有效的音频头。".encode("utf-8")
    result = transcribe_audio(fake, "fake.webm")
    print(f"  ok={result.ok} error={result.error} message={result.message}")
    assert result.ok is False
    assert result.error in (TranscribeResult.DECODE_FAILED, TranscribeResult.TRANSCRIBE_ERROR), \
        f"应为 DECODE_FAILED 或 TRANSCRIBE_ERROR，实为 {result.error}"
    print("  ✓ 通过")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("voice_service 单元测试")
    print("=" * 60)
    results = []
    results.append(("正常转写", test_normal_transcription()))
    results.append(("空音频", test_empty_audio()))
    results.append(("格式异常", test_invalid_format()))

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{passed}/{len(results)} 通过")
    sys.exit(0 if passed == len(results) else 1)
