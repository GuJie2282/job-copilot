"""
出题质量验证（add-mock-interview 阶段 2.4）
==========================================

用真实画像 + 可选 JD，验证出题的「个性化锚点命中」与「地图质量」：
  - anchor 是否真实命中画像经历（不是泛泛通用题）
  - probing_points 是否具体可问
  - ideal_signals 是否具体可判定
  - 有 JD 时是否围绕 Gap 重点出题

显式 load_dotenv，以便单独运行（不经过 main.py）也能拿到 LLM_API_KEY。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()  # 加载 backend/.env

from src.services.question_generator import generate_question_bank


# 含丰富经历细节的假画像（方便看锚点能否命中"字节/美团/推荐"）
PROFILE = {
    "name": "张三",
    "target_positions": ["产品经理"],
    "companies": ["字节跳动", "美团"],
    "positions": ["产品经理", "高级产品经理"],
    "work_descriptions": [
        "负责短视频 feed 推荐产品，主导策略迭代，DAU 提升 15%",
        "主导本地生活商家增长项目，GMV 翻倍",
    ],
    "project_names": ["推荐系统重构"],
    "project_descriptions": ["重构推荐召回策略，CTR 提升 20%"],
    "technical_skills": ["SQL", "A/B 测试", "数据分析"],
}

# 假 Gap 清单（有 JD 模式的考查重点）
GAPS = [
    {"type": "hard_skill", "requirement": "数据建模与指标体系经验", "severity": "high"},
    {"type": "soft_skill", "requirement": "跨团队沟通推动能力", "severity": "medium"},
    {"type": "implicit", "requirement": "大厂背景优先", "severity": "low"},
]


def show(title, packages, plan):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    print(f"问答计划：题量={plan['question_count']}  追问上限={plan['probing_limit']}  反问={plan['has_qa_session']}  档位={plan['label']}")
    for i, p in enumerate(packages, 1):
        print(f"\n题{i} [{p['category']}] {p['stem']}")
        print(f"   意图：{p.get('intent')}")
        print(f"   锚点：{p.get('anchor')}")
        print(f"   可挖掘：{p.get('probing_points')}")
        print(f"   理想信号：{p.get('ideal_signals')}")


def check_personalization(packages):
    """检查锚点是否命中画像关键词（字节/美团/推荐/增长/数据）。"""
    keywords = ["字节", "美团", "推荐", "增长", "数据", "feed", "CTR", "DAU", "GMV", "商家", "张三", "产品"]
    hit = 0
    for p in packages:
        anchor = (p.get("anchor") or "") + (p.get("stem") or "")
        if any(k in anchor for k in keywords):
            hit += 1
    return hit, len(packages)


def run():
    # ---------- 无 JD 模式 ----------
    pb1, plan1 = generate_question_bank(PROFILE, interview_type="full", intensity="short")
    show("【无 JD 模式】通用面试（基于目标岗位+画像）", pb1, plan1)
    hit1, total1 = check_personalization(pb1)

    # ---------- 有 JD 模式 ----------
    pb2, plan2 = generate_question_bank(PROFILE, gaps=GAPS, interview_type="full", intensity="short")
    show("【有 JD 模式】定向面试（基于 Gap 重点）", pb2, plan2)
    # 检查是否提到 gap 相关词
    gap_words = ["数据", "建模", "指标", "沟通", "推动", "团队", "背景"]
    gap_hit = sum(1 for p in pb2 if any(w in (p.get("stem", "") + (p.get("anchor") or "")) for w in gap_words))

    # ---------- 总结 ----------
    print(f"\n{'=' * 70}\n质量检查\n{'=' * 70}")
    degraded1 = all("降级" in (p.get("anchor") or "") for p in pb1)
    print(f"[{'⚠️ 降级' if degraded1 else '✓ LLM'}] 出题来源：{'LLM_API_KEY 未配置，走降级兜底' if degraded1 else 'LLM 真实出题'}")
    if not degraded1:
        print(f"[{'✓' if hit1 >= total1//2 else '△'}] 无 JD 个性化：{hit1}/{total1} 题锚点命中画像经历")
        print(f"[{'✓' if gap_hit >= len(pb2)//2 else '△'}] 有 JD 定向：{gap_hit}/{len(pb2)} 题涉及 Gap 关键词")
    print(f"\n题库结构完整性：每题含 probing_points + ideal_signals → {'✓' if all(p.get('probing_points') and p.get('ideal_signals') for p in pb1+pb2) else '✗'}")

    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    run()
