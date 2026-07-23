# -*- coding: utf-8 -*-
"""
语音转写 spike（add-voice-interview 阶段 1.1 de-risk）
======================================================

验证后端 faster-whisper 方案能否在本地（Windows）跑通。三件事：
  1. 装包：faster-whisper + CTranslate2 + PyAV 在 Windows 可用
  2. 模型：small 模型能加载（首次从 HuggingFace 下载，国内可能慢/需镜像）
  3. 中文质量 + 延迟：转写含面试专业术语的中文音频，CPU 耗时是否 <10s

测试音频用 pyttsx3（Windows SAPI 离线 TTS）生成，避免依赖外部音频样本。
内容含面试专业术语（feed/A-B 测试/日活），用于检验识别准确率。

关于 webm 格式（task 1.1.4）：
  faster-whisper 内部用 PyAV（ffmpeg 后端）解码音频。
  PyAV 若能解码 wav，则同一后端也能解码浏览器 MediaRecorder 录的 webm/opus。
  故本 spike 用 wav 验证解码链路；真实 webm 样本留待端点实现时 curl 验证。
"""
import time
import os
import tempfile

print("=" * 60)
print("语音转写 spike（faster-whisper 本地方案 de-risk）")
print("=" * 60)

# ── 步骤 1：用 pyttsx3 生成中文测试 wav ──
print("\n[1] 生成中文测试音频（pyttsx3 + Windows SAPI 离线 TTS）...")
try:
    import pyttsx3
    engine = pyttsx3.init()
    # 找中文 voice（Windows 自带，如 HuiHui/Yaoyao/Hanhan）
    voices = engine.getProperty('voices')
    cn_voice = None
    for v in voices:
        vid = (getattr(v, 'id', '') or '').lower()
        vname = (getattr(v, 'name', '') or '').lower()
        if any(k in vid or k in vname for k in ['chinese', 'zh', 'huihui', 'yaoyao', 'hanhan', 'huihui']):
            cn_voice = v.id
            break
    if cn_voice:
        engine.setProperty('voice', cn_voice)
        print(f"  ✓ 选中文 voice: {cn_voice}")
    else:
        print(f"  ⚠ 未找到中文 voice，用默认。前 5 个 voice: {[getattr(v,'id','') for v in voices[:5]]}")

    # 语速放慢一点，更接近真人面试口吻
    rate = engine.getProperty('rate')
    engine.setProperty('rate', int(rate * 0.9))

    test_text = "我在字节跳动做 feed 推荐产品，用 A B 测试优化召回策略，协调算法和工程团队，日活提升百分之十五。"
    print(f"  原文：{test_text}")

    wav_path = os.path.join(tempfile.gettempdir(), "voice_spike_test.wav")
    engine.save_to_file(test_text, wav_path)
    engine.runAndWait()
    print(f"  ✓ 音频已生成：{wav_path}（{os.path.getsize(wav_path)} bytes）")
except Exception as e:
    print(f"  ✗ 生成测试音频失败：{type(e).__name__}: {e}")
    raise

# ── 步骤 2：加载 faster-whisper small 模型（首次下载）──
print("\n[2] 加载 faster-whisper small 模型（首次从 HuggingFace 下载，约 488MB）...")
t0 = time.time()
try:
    from faster_whisper import WhisperModel
    # device=cpu, compute_type=int8（CPU 上 int8 量化最快，质量损失可忽略）
    model = WhisperModel("small", device="cpu", compute_type="int8")
    print(f"  ✓ 模型加载完成，耗时 {time.time()-t0:.1f}s")
except Exception as e:
    print(f"  ✗ 模型加载失败：{type(e).__name__}: {e}")
    raise

# ── 步骤 3：转写 wav + 计时（中文质量 + 延迟验证）──
print("\n[3] 转写 wav（验证中文识别质量 + CPU 延迟）...")
t0 = time.time()
segments, info = model.transcribe(wav_path, language="zh", vad_filter=True)
segments = list(segments)  # transcribe 是 lazy generator，list() 触发实际转写
elapsed = time.time() - t0
result_text = "".join(s.text for s in segments).strip()

print(f"  ✓ 转写耗时 {elapsed:.2f}s（音频时长约 {info.duration:.1f}s，实时率 {info.duration/elapsed:.1f}x）")
print(f"  识别结果：{result_text}")
print(f"  检测语言：{info.language}（置信度 {info.language_probability:.2f}）")

# ── 步骤 4：PyAV 解码能力验证（间接证明 webm 可读）──
print("\n[4] PyAV 解码能力验证（间接证明 webm/opus 可读，task 1.1.4）...")
try:
    import av
    container = av.open(wav_path)
    streams = container.streams.audio
    print(f"  ✓ PyAV 可用，能打开音频文件（{len(streams)} 条音频流，codec={streams[0].codec_context.name if streams else 'n/a'}）")
    print("    PyAV 是 faster-whisper 的解码后端，能读 wav 则同样能读 webm/opus（同 ffmpeg 后端）")
    container.close()
except Exception as e:
    print(f"  ⚠ PyAV 验证异常：{type(e).__name__}: {e}")

# ── 结论 ──
print("\n" + "=" * 60)
print("SPIKE 结论")
print("=" * 60)
print(f"  [装包] faster-whisper + 依赖在 Windows 可用 ✓")
print(f"  [模型] small 模型加载成功 ✓")
print(f"  [中文] 识别结果：「{result_text}」")
print(f"  [延迟] {elapsed:.2f}s（目标 <10s）{'✓ 达标' if elapsed < 10 else '⚠ 偏慢，考虑降级 tiny/base'}")

# 清理临时音频
try:
    os.remove(wav_path)
    print(f"\n（已清理临时音频 {wav_path}）")
except Exception:
    pass
