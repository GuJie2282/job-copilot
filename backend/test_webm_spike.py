# -*- coding: utf-8 -*-
"""
webm 直读验证（add-voice-interview task 1.1.4 补强）
=====================================================

spike 主链路用 wav 验证了 faster-whisper 引擎。本脚本彻底验证
faster-whisper 能直读浏览器 MediaRecorder 录的真实格式 webm/opus：

  wav(pyttsx3生成) --av编码--> webm/opus --faster-whisper--> 文本

若此往返成功，则端点实现时无需 pydub+ffmpeg 转码层，架构更简。
"""
import time
import os
import tempfile

print("=" * 60)
print("webm 直读验证（faster-whisper 能否直读 webm/opus）")
print("=" * 60)

# ── 1. 生成 wav ──
print("\n[1] 生成中文 wav（pyttsx3）...")
import pyttsx3
engine = pyttsx3.init()
for v in engine.getProperty('voices'):
    if 'ZH-CN' in (getattr(v, 'id', '') or '').upper():
        engine.setProperty('voice', v.id)
        break
test_text = "我用 SQL 做漏斗分析定位流失节点，针对性优化后转化率提升百分之十二。"
wav_path = os.path.join(tempfile.gettempdir(), "webm_spike.wav")
engine.save_to_file(test_text, wav_path)
engine.runAndWait()
print(f"  ✓ wav 已生成：{os.path.getsize(wav_path)} bytes")

# ── 2. av 把 wav 转 webm/opus（模拟浏览器 MediaRecorder 产出）──
print("\n[2] av 将 wav 转码为 webm/opus（模拟浏览器录音格式）...")
import av
webm_path = os.path.join(tempfile.gettempdir(), "webm_spike.webm")
inp = av.open(wav_path)
out = av.open(webm_path, 'w')
ostream = out.add_stream('libopus')  # opus 编码，MediaRecorder 常用
ostream.bit_rate = 32000
# av 10+ 新 API：stream.encode(frame) 返回 packet 列表，用 container.mux 写入
for frame in inp.decode(audio=0):
    for packet in ostream.encode(frame):
        out.mux(packet)
for packet in ostream.encode(None):  # flush
    out.mux(packet)
inp.close()
out.close()
print(f"  ✓ webm/opus 已生成：{os.path.getsize(webm_path)} bytes")

# ── 3. faster-whisper 直读 webm ──
print("\n[3] faster-whisper 直读 webm（不转 wav）...")
t0 = time.time()
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(webm_path, language="zh", vad_filter=True)
segments = list(segments)
elapsed = time.time() - t0
result_text = "".join(s.text for s in segments).strip()
print(f"  ✓ webm 直读成功，转写耗时 {elapsed:.2f}s")
print(f"  原文：{test_text}")
print(f"  识别：{result_text}")

# ── 结论 ──
print("\n" + "=" * 60)
ok = len(result_text) > 0
print(f"webm 直读验证：{'✓ 通过 —— 端点无需 pydub/ffmpeg 转码层' if ok else '✗ 失败'}")
print("=" * 60)

for p in (wav_path, webm_path):
    try:
        os.remove(p)
    except Exception:
        pass
