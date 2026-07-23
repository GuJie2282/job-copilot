# -*- coding: utf-8 -*-
"""
评估容错验证（add-voice-interview task 4.1.3）
================================================
验证 get_evaluation_prompt 规则 7（语音识别容错）生效：
构造「含同音错字」（模拟 Whisper 转写小瑕）与「正确字」两版同一回答，
对比 evaluator 的 score / hit_signals，确认不因错字误判。

若容错生效：两版 score 接近、hit_signals 都命中「量化结果」（不被「日火/漏豆」误导）。
若容错失效：含错字版 score 显著低 / miss_signals 错误地包含「量化结果」。

运行：cd backend && ./.venv/Scripts/python.exe test_eval_voice_tolerance.py
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 backend/.env（LLM_API_KEY 等），让 _llm_evaluate 能真调 LLM
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.graph.nodes.mock_interview import _llm_evaluate

# 题：考察数据驱动 + 量化结果
question = "讲一次你用数据驱动决策的经历。"
ideal_signals = ["量化结果（具体数据提升）", "数据驱动决策过程", "明确的优化行动"]
probing_points = ["具体提升了多少？", "数据如何支撑决策？"]

# 含同音错字版（模拟 Whisper 识别小瑕）：漏斗→漏豆，日活→日火，复购→负购，转化→转花
answer_err = (
    "我用SQL做漏豆分析定位流失节点，针对性优化后转花率提升12%，"
    "日火提升15%，负购率也涨了。这是典型的数据驱动决策。"
)
# 正确字对照版
answer_ok = (
    "我用SQL做漏斗分析定位流失节点，针对性优化后转化率提升12%，"
    "日活提升15%，复购率也涨了。这是典型的数据驱动决策。"
)


def norm_signals(sigs):
    """信号命中里找『量化』相关（验证数据结果未被错字误判为缺失）。"""
    return [s for s in (sigs or []) if "量化" in s or "数据" in s]


print("=" * 60)
print("评估容错验证：含同音错字(语音转写) vs 正确字(对照)")
print("=" * 60)

results = {}
for label, ans in [("含错字(语音转写)", answer_err), ("正确字(对照)", answer_ok)]:
    print(f"\n[{label}]")
    print(f"  answer：{ans}")
    r = _llm_evaluate(question, ideal_signals, probing_points, ans, persona={"tone": "专业"})
    score = r.get("score")
    hit = r.get("hit_signals") or []
    miss = r.get("miss_signals") or []
    print(f"  score：{score}")
    print(f"  hit_signals：{hit}")
    print(f"  miss_signals：{miss}")
    print(f"  weakness：{r.get('weakness')}")
    results[label] = {"score": score, "hit": hit, "miss": miss}

# ── 容错判定 ──
print("\n" + "=" * 60)
print("容错判定")
print("=" * 60)
err_hit_quant = any("量化" in s for s in results["含错字(语音转写)"]["hit"])
err_miss_quant = any("量化" in s for s in results["含错字(语音转写)"]["miss"])
score_diff = abs((results["含错字(语音转写)"]["score"] or 0) - (results["正确字(对照)"]["score"] or 0))

print(f"含错字版是否命中「量化结果」信号：{'是 ✓' if err_hit_quant else '否 ✗'}")
print(f"含错字版是否误判「量化结果」为缺失：{'否 ✓' if not err_miss_quant else '是 ✗（误判）'}")
print(f"两版 score 差：{score_diff}（≤15 视为容错生效）")
ok = err_hit_quant and not err_miss_quant and score_diff <= 15
print(f"\n容错{'生效 ✓' if ok else '不足 ✗'}")
