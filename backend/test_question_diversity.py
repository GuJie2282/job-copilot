"""
出题多样性验证（量化"每次模拟会不会问相同问题"）
==================================================

同一画像 + 同一配置，连续出题 N 次，量化题目重复度：
  - 完全相同题数
  - 高度相似题数（前缀/关键词重合）
  - 不同题数

预期：当前实现（temperature=0.7，无去重）会有一定重复，尤其经典题。

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
]

ROUNDS = 3  # 连续出题次数


def collect(label, use_jd):
    print(f"\n{'=' * 70}\n{label}：连续出题 {ROUNDS} 次（同画像同配置）\n{'=' * 70}")
    all_stems = []
    for i in range(ROUNDS):
        gaps = GAPS if use_jd else None
        packages, _ = generate_question_bank(PROFILE, gaps=gaps, interview_type="full", intensity="short")
        stems = [p["stem"] for p in packages]
        all_stems.append(stems)
        print(f"\n第{i+1}次：")
        for s in stems:
            print(f"  - {s[:55]}")
    return all_stems


def analyze(all_stems):
    """统计跨次重复：把所有题拉平，看唯一题占比。"""
    flat = [s for stems in all_stems for s in stems]
    unique = len(set(flat))
    total = len(flat)
    # 关键词视角：看经典题是否反复出现
    classic_keywords = ["push", "推动", "团队", "缺点", "优点", "为什么", "职业规划", "挑战", "STAR"]
    classic_hits = {}
    for s in flat:
        for kw in classic_keywords:
            if kw in s:
                classic_hits[kw] = classic_hits.get(kw, 0) + 1
    return total, unique, classic_hits


def run():
    nojd = collect("【无 JD 模式】", use_jd=False)
    t1, u1, ch1 = analyze(nojd)
    print(f"\n  → 共 {t1} 题，完全不同 {u1} 题（{u1*100//t1}% 唯一）")
    print(f"  → 经典题关键词出现：{ch1}")

    jd = collect("【有 JD 模式】", use_jd=True)
    t2, u2, ch2 = analyze(jd)
    print(f"\n  → 共 {t2} 题，完全不同 {u2} 题（{u2*100//t2}% 唯一）")
    print(f"  → 经典题关键词出现：{ch2}")

    print(f"\n{'=' * 70}")
    print("结论：")
    print(f"  无JD 唯一率 {u1*100//t1}% | 有JD 唯一率 {u2*100//t2}%")
    print("  （唯一率越低 = 越容易每次问相同/相似题；经典题关键词反复出现 = 题库同质化）")
    print("=" * 70)


if __name__ == "__main__":
    run()
