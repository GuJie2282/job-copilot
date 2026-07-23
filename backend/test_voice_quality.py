# -*- coding: utf-8 -*-
"""
语音识别质量多样本验证（add-voice-interview task 4.1 / 4.1.2）
================================================================
验证 faster-whisper small 对面试场景「中文 + 专业术语」的识别准确率。

8 个样本覆盖常见 PM/运营术语：feed / AB测试 / DAU / SQL / 漏斗 / 转化率 /
GMV / 复购率 / STAR / 数据驱动 / 敏捷 / 迭代 / 站会 / 留存率 / OKR / KPI / 月活。
统计关键词命中率。

【诚实声明】这是 pyttsx3 TTS → Whisper STT 的往返测试。英文术语（feed/SQL/GMV）
受 pyttsx3 中文 TTS 发音影响（HuiHui 念英文可能音译/念字母），真实人声通常更清晰，
故本测试给的是识别质量「下限」参考，不是真实人声的准确率。

运行：cd backend && HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
      ./.venv/Scripts/python.exe test_voice_quality.py
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.services.voice_service import transcribe_audio

# (原文, 期望命中的关键词——中文直接匹配，英文小写匹配)
SAMPLES = [
    ("我在字节跳动做feed推荐，用AB测试优化策略，日活提升百分之十五。",
     ["字节", "feed", "ab", "日活"]),
    ("我用SQL做漏斗分析，定位流失节点，转化率提升百分之十二。",
     ["sql", "漏斗", "转化率", "流失"]),
    ("我负责电商大促，GMV同比增长百分之三十，复购率提升。",
     ["gmv", "复购率", "同比"]),
    ("我用STAR法则讲故事，强调数据驱动决策。",
     ["star", "数据驱动", "决策"]),
    ("我们用敏捷开发，两周一个迭代，站会同步进度。",
     ["敏捷", "迭代", "站会"]),
    ("用户留存率下降，我分析是新功能导致，下线后恢复。",
     ["留存率", "新功能"]),
    ("OKR对齐团队目标，KPI考核个人产出。",
     ["okr", "kpi", "团队"]),
    ("月活百万级产品，日活峰值出现在晚上八点。",
     ["月活", "百万", "日活"]),
]


def make_wav(text: str) -> bytes:
    import pyttsx3
    engine = pyttsx3.init()
    for v in engine.getProperty('voices'):
        if 'ZH-CN' in (getattr(v, 'id', '') or '').upper():
            engine.setProperty('voice', v.id)
            break
    path = os.path.join(tempfile.gettempdir(), "voice_quality.wav")
    engine.save_to_file(text, path)
    engine.runAndWait()
    with open(path, 'rb') as f:
        data = f.read()
    os.remove(path)
    return data


def norm(s: str) -> str:
    """去标点 + 小写，便于关键词匹配（Whisper 输出英文大小写、繁简不一）。"""
    return re.sub(r'[，。、,.!?；;：:、\s]', '', s or '').lower()


print("=" * 60)
print("语音识别质量多样本验证（8 样本，含 PM/运营专业术语）")
print("=" * 60)

total_kw = 0
hit_kw = 0
perfect = 0

for i, (text, keywords) in enumerate(SAMPLES, 1):
    audio = make_wav(text)
    result = transcribe_audio(audio, "quality.wav")
    if not result.ok:
        print(f"\n[{i}] ✗ 转写失败：{result.error} - {result.message}")
        total_kw += len(keywords)
        continue
    n = norm(result.text)
    hits = [kw for kw in keywords if kw.lower() in n]
    total_kw += len(keywords)
    hit_kw += len(hits)
    if len(hits) == len(keywords):
        perfect += 1
    mark = "✓" if len(hits) == len(keywords) else ("○" if hits else "✗")
    print(f"\n[{i}] {mark} 命中 {len(hits)}/{len(keywords)}")
    print(f"    原文：{text}")
    print(f"    识别：{result.text}")
    miss = [kw for kw in keywords if kw.lower() not in n]
    if miss:
        print(f"    漏识：{miss}")

print("\n" + "=" * 60)
pct = hit_kw / total_kw * 100 if total_kw else 0
print(f"关键词命中率：{hit_kw}/{total_kw} = {pct:.0f}%")
print(f"全中样本：{perfect}/{len(SAMPLES)}")
print("=" * 60)
print("注：TTS→STT 往返测试，英文术语受 pyttsx3 发音影响，为质量下限。")
