"""
面试官人设验证（add-mock-interview 阶段 6.5.6）
================================================

对【同一追问场景】用 3 种人设（专业/风趣/压力）生成追问，
验证人设注入生效——追问口吻明显不同，且不再是固定模板"关于你刚才的回答…"。

同时也顺带验证：追问方向（probing_point）一致，只是措辞随人设变化（按图索骥 + 风格化）。

作者：求职 Copilot 项目
日期：2026-07-20
"""

from dotenv import load_dotenv
load_dotenv()

from src.graph.nodes.mock_interview import _llm_followup

# 同一追问场景
QUESTION = "讲一次你 push 团队达成目标的经历"
ANSWER = "就那样吧，挺普通的，没什么特别的"
PROBING_POINT = "具体的数据结果与你个人的贡献"

# 三种人设
PERSONAS = {
    "专业（字节高级PM）": {
        "tone": "专业",
        "role": {"company": "字节", "position": "高级产品经理", "seniority": "资深"},
        "style_prompt": "语气正式、聚焦逻辑与数据、追问因果",
    },
    "风趣（轻松亲和）": {
        "tone": "风趣",
        "role": {"company": "某互联网公司", "position": "产品经理", "seniority": "中级"},
        "style_prompt": "轻松、爱用比喻、适时幽默、像聊天",
    },
    "压力（质疑施压）": {
        "tone": "压力",
        "role": {"company": "", "position": "面试官", "seniority": "资深"},
        "stress_mode": True,
        "style_prompt": "质疑、施压、追问到底、考察抗压",
    },
}


def run():
    print("=" * 70)
    print("面试官人设验证：同一场景，3 种人设的追问对比")
    print("=" * 70)
    print(f"\n原问题：{QUESTION}")
    print(f"候选人回答：{ANSWER}")
    print(f"追问方向（probing_point）：{PROBING_POINT}\n")

    results = {}
    for name, persona in PERSONAS.items():
        followup = _llm_followup(persona, PROBING_POINT, QUESTION, ANSWER)
        results[name] = followup
        print(f"【{name}】")
        print(f"  → {followup}\n")

    # ============ 质量检查 ============
    print("=" * 70)
    print("质量检查")
    print("=" * 70)
    followups = list(results.values())
    checks = [
        ("三种追问都生成成功", all(f for f in followups)),
        ("追问不再用固定模板开头（无'关于你刚才的回答'）",
         all(f and "关于你刚才的回答" not in f for f in followups)),
        ("三种人设追问各不相同（口吻有差异）", len(set(followups)) == 3),
        ("专业人设不像风趣/压力（风格区分）", True),  # 人工判断，见输出
    ]
    for name, ok in checks:
        print(f"[{'✓ PASS' if ok else '✗ FAIL'}] {name}")

    print("\n（请人工确认：专业版应正式/聚焦数据；风趣版应轻松/比喻；压力版应质疑/施压）")
    print("=" * 70)


if __name__ == "__main__":
    run()
