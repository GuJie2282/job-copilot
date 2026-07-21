"""
出题多样性验证（量化"每次模拟会不会问相同问题"）—— 阶段 7.0.4 回归测试
===========================================================================

同一画像 + 同一配置，连续出题 N 次，量化多样性：
  - 题干文本唯一率（措辞不重复）
  - 锚点唯一率（7.0.1 锚点池随机化的直接验证——锚点每次不同 = 考查点不固化）
  - 经典题关键词分布（同质化程度）

【为什么测锚点】题干文本 100% 唯一容易（LLM 换个说法），
但若每次都锚定同一段经历，考查点其实固化。锚点随机化（7.0.1）正是为此——
从画像多段经历随机抽 2-3 段作锚点池，引导 LLM 围绕不同经历出题。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()

from src.services.question_generator import generate_question_bank

PROFILE = {
    "name": "张三",
    "target_positions": ["产品经理"],
    "companies": ["字节跳动"],
    "positions": ["产品经理"],
    "work_descriptions": ["负责短视频 feed 推荐产品，DAU 提升 15%"],
    "project_names": ["推荐系统重构"],
    "project_descriptions": ["重构召回策略，CTR 提升 20%"],
    "technical_skills": ["SQL", "A/B 测试"],
}

GAPS = [
    {"type": "hard_skill", "requirement": "数据建模经验", "severity": "high"},
    {"type": "soft_skill", "requirement": "跨团队沟通", "severity": "medium"},
    {"type": "hard_skill", "requirement": "AB 实验设计", "severity": "high"},
    {"type": "implicit", "requirement": "抗压能力", "severity": "medium"},
]

ROUNDS = 3  # 连续出题次数


def collect(label, use_jd):
    print(f"\n{'=' * 70}\n{label}：连续出题 {ROUNDS} 次（同画像同配置）\n{'=' * 70}")
    all_stems, all_anchors = [], []
    for i in range(ROUNDS):
        gaps = GAPS if use_jd else None
        packages, _ = generate_question_bank(PROFILE, gaps=gaps, interview_type="full", intensity="short")
        stems = [p["stem"] for p in packages]
        anchors = [p.get("anchor") or "" for p in packages]
        all_stems.append(stems)
        all_anchors.append(anchors)
        print(f"\n第{i+1}次：")
        for s, a in zip(stems, anchors):
            print(f"  - {s[:50]}")
            print(f"      锚点：{a[:45]}")
    return all_stems, all_anchors


def analyze(all_stems, all_anchors):
    """统计跨次多样性：题干唯一率、锚点唯一率、经典关键词分布。"""
    flat_s = [s for stems in all_stems for s in stems]
    flat_a = [a for anchors in all_anchors for a in anchors if a]
    unique_s = len(set(flat_s))
    unique_a = len(set(flat_a))
    classic_keywords = ["push", "推动", "团队", "缺点", "优点", "为什么", "职业规划", "挑战", "STAR"]
    classic_hits = {}
    for s in flat_s:
        for kw in classic_keywords:
            if kw in s:
                classic_hits[kw] = classic_hits.get(kw, 0) + 1
    return len(flat_s), unique_s, len(flat_a), unique_a, classic_hits


def run():
    nojd_s, nojd_a = collect("【无 JD 模式】", use_jd=False)
    t1, us1, ta1, ua1, ch1 = analyze(nojd_s, nojd_a)
    print(f"\n  → 题干 {t1} 题 / 唯一 {us1}（{us1*100//t1}%）；锚点 {ta1} 个 / 唯一 {ua1}（{ua1*100//max(ta1,1)}%）")
    print(f"  → 经典关键词出现：{ch1}")

    jd_s, jd_a = collect("【有 JD 模式】", use_jd=True)
    t2, us2, ta2, ua2, ch2 = analyze(jd_s, jd_a)
    print(f"\n  → 题干 {t2} 题 / 唯一 {us2}（{us2*100//t2}%）；锚点 {ta2} 个 / 唯一 {ua2}（{ua2*100//max(ta2,1)}%）")
    print(f"  → 经典关键词出现：{ch2}")

    print(f"\n{'=' * 70}")
    print("结论（锚点唯一率 = 考查点多样性的直接指标）：")
    print(f"  无JD：题干唯一 {us1*100//t1}% | 锚点唯一 {ua1*100//max(ta1,1)}%")
    print(f"  有JD：题干唯一 {us2*100//t2}% | 锚点唯一 {ua2*100//max(ta2,1)}%")
    print("  （锚点唯一率越高 = 越能围绕不同经历出题，考查点不固化）")
    print("=" * 70)


if __name__ == "__main__":
    run()
