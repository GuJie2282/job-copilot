"""
模拟面试出题服务（question_generator）
=====================================

生成个性化面试题库，每道题是「考查包」（QuestionPackage）——
不只一个问题文本，还预埋两张地图：
  - probing_points: 可挖掘点（evaluator 追问的弹药）
  - ideal_signals:  理想信号（evaluator 评判回答 + 决定追问的标尺）

核心设计（对应 design.md 决策 4 / 5）：
出题时预埋地图 → evaluator「按图索骥」（信号差检测）→ 追问可控、可解释、可调。

三条职责：
  1. 出题上下文归一化：有 JD（画像+job_profile+gaps）与 无 JD（画像+目标岗位+强弱项）
     归一为统一的 {candidate_summary, focus_areas}，下游题库生成器只认这个结构。
  2. QuestionPackage 生成：LLM 生成考查包，失败降级为通用题库（不阻断）。
  3. 问答计划生成：按档位（简短/正常/深度/全程）决定题量、每题追问上限、是否反问。

本服务是纯函数式的：接收已读好的 profile/job_profile/gaps，不直接碰 DB。
DB 读取由 session_setup 节点负责（阶段 3）。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import uuid
import random
import logging
from typing import Dict, List, Optional, Tuple, Any

from pydantic import BaseModel, Field

from src.graph.config import get_llm
from src.graph.prompts import get_question_generation_prompt
from src.services.llm_retry import invoke_llm_with_retry
from src.services.jd_parser import _extract_json

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 档位配置（语义化，不暴露时间隐喻——对应 design.md 决策 6）
# ============================================================================

INTENSITY_CONFIG: Dict[str, Dict[str, Any]] = {
    "short":  {"question_count": 3, "probing_limit": 1, "has_qa_session": False, "label": "简短"},
    "normal": {"question_count": 5, "probing_limit": 2, "has_qa_session": True,  "label": "正常"},
    "deep":   {"question_count": 7, "probing_limit": 3, "has_qa_session": True,  "label": "深度"},
    "full":   {"question_count": 8, "probing_limit": 3, "has_qa_session": True,  "label": "全程"},
}

DEFAULT_INTENSITY = "normal"


def get_intensity_config(intensity: str) -> Dict[str, Any]:
    """取档位配置，未知档位回退 normal。"""
    return INTENSITY_CONFIG.get(intensity, INTENSITY_CONFIG[DEFAULT_INTENSITY])


# ============================================================================
# 2. QuestionPackage 数据模型（对应 spec 数据结构定义）
# ============================================================================

class QuestionPackage(BaseModel):
    """
    一道面试题的「考查包」。

    - stem / anchor / category / intent: 面试官要问什么、针对画像哪里
    - probing_points: 可挖掘点（追问弹药）—— evaluator 沿此追问
    - ideal_signals:  理想信号（评判标尺）—— evaluator 用它做信号差检测
    - estimated_minutes: 预估耗时（喂给问答计划，文字版用模拟时间）
    """
    category: str = Field(description="题型: behavioral/technical/case/motivation")
    intent: str = Field(description="出题意图：考查什么能力")
    stem: str = Field(description="主问题文本")
    anchor: Optional[str] = Field(default=None, description="画像中的经历依据（个性化锚点）")
    probing_points: List[str] = Field(default_factory=list, description="可挖掘点（追问弹药）")
    ideal_signals: List[str] = Field(default_factory=list, description="理想信号（评判标尺）")
    estimated_minutes: int = Field(default=4, description="预估耗时（分钟）")

    # 运行时补充（非 LLM 输出）
    qid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rag_source: str = Field(default="llm_gen", description="数据来源: llm_gen/company_lib/personal")


# ============================================================================
# 3. 出题上下文归一化（有/无 JD 双模式——对应 design.md 决策 3）
# ============================================================================

def _build_candidate_summary(profile: Dict[str, Any]) -> str:
    """
    从画像 dict 构造「候选人摘要」文本（喂给出题 LLM）。

    重点保留经历细节（work_descriptions / project_descriptions）——
    这是面试官「认识候选人」、个性化锚点命中的依据。
    """
    if not profile:
        return "（画像为空）"

    parts: List[str] = []

    # 姓名 + 目标岗位
    name = profile.get("name") or "候选人"
    targets = profile.get("target_positions") or []
    target_str = "、".join(targets) if targets else "未明确"
    parts.append(f"姓名：{name}　目标岗位：{target_str}")

    # 工作经历（含细节——追问命根子）
    companies = profile.get("companies") or []
    positions = profile.get("positions") or []
    work_descs = profile.get("work_descriptions") or []
    if companies:
        work_lines = []
        for i, comp in enumerate(companies):
            pos = positions[i] if i < len(positions) else ""
            desc = work_descs[i] if i < len(work_descs) else ""
            line = f"　- {comp}"
            if pos:
                line += f"（{pos}）"
            if desc:
                line += f"：{desc}"
            work_lines.append(line)
        parts.append("工作经历：\n" + "\n".join(work_lines))

    # 项目经历（含细节）
    proj_names = profile.get("project_names") or []
    proj_descs = profile.get("project_descriptions") or []
    if proj_names:
        proj_lines = []
        for i, pn in enumerate(proj_names):
            pd = proj_descs[i] if i < len(proj_descs) else ""
            line = f"　- {pn}"
            if pd:
                line += f"：{pd}"
            proj_lines.append(line)
        parts.append("项目经历：\n" + "\n".join(proj_lines))

    # 技能
    tech = profile.get("technical_skills") or []
    soft = profile.get("soft_skills") or []
    if tech or soft:
        skills = "、".join(tech) if tech else "无"
        parts.append(f"技术技能：{skills}")
        if soft:
            parts.append(f"软技能：{'、'.join(soft)}")

    # 教育（简略）
    schools = profile.get("schools") or []
    if schools:
        parts.append(f"教育：{'、'.join(schools)}")

    # 【7.0.1 锚点随机化】从画像多段经历/技能里随机抽 2-3 段作「本场锚点池」，
    # 引导 LLM 围绕这些出题——避免每次都锚定第一段经历，导致考查点固化、措辞重复。
    anchors = [f"工作·{d}" for d in work_descs if d] \
            + [f"项目·{d}" for d in proj_descs if d] \
            + [f"技能·{s}" for s in tech if s]
    if anchors:
        pool = random.sample(anchors, min(3, len(anchors)))
        parts.append("【本场锚点池（随机抽取，请优先围绕这几段经历/技能出题）】\n"
                     + "\n".join(f"  - {a}" for a in pool))

    return "\n".join(parts)


def _build_focus_from_gaps(gaps: List[Dict[str, Any]]) -> str:
    """有 JD 模式：从 Gap 清单构造考查重点。Gap 大的优先考，但随机抽样避免每次同序。"""
    if not gaps:
        return "（无 Gap 信息，请按岗位常规要求出题）"
    type_label = {"hard_skill": "硬技能", "soft_skill": "软技能", "implicit": "隐性偏好", "redline": "红线"}
    # 【7.0.2】先按严重度排序构建候选池（重的在前，保证重点被考），再随机抽样打乱顺序
    # ——兼顾「重点考」与「多样性」，避免每次 gaps 顺序一致导致考查点固化。
    sev_order = {"high": 0, "medium": 1, "low": 2}
    pool = sorted(gaps, key=lambda g: sev_order.get(str(g.get("severity", "")).lower(), 3))
    sampled = random.sample(pool[:10], min(8, len(pool[:10])))
    lines = []
    for g in sampled:
        t = type_label.get(g.get("type"), g.get("type", ""))
        req = g.get("requirement", "")
        sev = g.get("severity", "")
        lines.append(f"　- [{t}/{sev}] {req}")
    return "候选人相对岗位的差距（重点考查方向）：\n" + "\n".join(lines)


def _build_focus_from_profile(profile: Dict[str, Any]) -> str:
    """
    无 JD 模式：从画像本身推断考查重点（启发式，MVP 够用）。

    后续可用 LLM 增强弱项分析；这里先用规则占位：
      - 目标岗位已知 → 围绕岗位常见考查点
      - 建议覆盖行为/技术/动机面
    """
    targets = profile.get("target_positions") or []
    target_str = "、".join(targets) if targets else "通用岗位"

    work_descs = [d for d in (profile.get("work_descriptions") or []) if d]
    proj_descs = [d for d in (profile.get("project_descriptions") or []) if d]
    rich_experience = len(work_descs) + len(proj_descs) >= 2

    lines = [f"目标岗位：{target_str}"]
    if rich_experience:
        lines.append("画像经历较丰富 → 可对经历做行为面深挖（STAR + 数据化）。")
    else:
        lines.append("画像经历较少 → 侧重岗位通用能力与动机面，行为面用现有经历即可。")
    lines.append("建议题型覆盖：行为面（讲经历）、技术/专业面（岗位相关）、动机面（why）。")
    return "\n".join(lines)


def normalize_context(
    profile: Dict[str, Any],
    job_profile: Optional[Dict[str, Any]] = None,
    gaps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    出题上下文归一化：不管有没有 JD，都生成统一的 {candidate_summary, focus_areas}。

    - 有 JD（gaps 非空）：focus_areas 来自 Gap 清单（差距大的重点考）
    - 无 JD：focus_areas 来自画像目标岗位 + 强弱项推断
    """
    candidate_summary = _build_candidate_summary(profile)
    if gaps:
        focus_areas = _build_focus_from_gaps(gaps)
    else:
        focus_areas = _build_focus_from_profile(profile)
    return {"candidate_summary": candidate_summary, "focus_areas": focus_areas}


# ============================================================================
# 4. QuestionPackage 生成（LLM + 降级）
# ============================================================================

def _fallback_packages(
    context: Dict[str, str],
    interview_type: str,
    count: int,
    probing_limit: int,
) -> List[Dict[str, Any]]:
    """
    LLM 不可用 / 失败时的兜底题库（通用题，无个性化）。

    保证面试能跑起来（哪怕质量打折），不阻断流程。
    沿用 gap_analyzer 的「失败降级」哲学。
    """
    generic = {
        "behavioral": ("讲一次你推动团队达成目标的经历", "考察 STAR 叙事与主动性"),
        "technical":  ("你最近负责的一个项目，技术/专业上最大的挑战是什么？", "考察专业深度"),
        "case":       ("如果你的核心指标突然下滑 20%，你会如何排查？", "考察分析与结构化思维"),
        "motivation": ("为什么想离开现在的岗位？为什么选择我们？", "考察求职动机与匹配"),
    }
    # full 模式轮换各题型；单一类型用该类型。每题的 category/stem/intent 必须一致。
    if interview_type == "full":
        seq = ["behavioral", "technical", "case", "motivation"]
    elif interview_type in generic:
        seq = [interview_type]
    else:
        seq = ["behavioral"]

    packages = []
    for i in range(count):
        cat = seq[i % len(seq)]
        stem, intent = generic[cat]
        packages.append({
            "category": cat,
            "intent": intent,
            "stem": stem,
            "anchor": "通用考查（LLM 降级，未个性化）",
            "probing_points": ["具体的数据结果？", "你个人的贡献？"][:probing_limit],
            "ideal_signals": ["量化结果", "个人主动性"][:max(probing_limit, 2)],
            "estimated_minutes": 4,
            "rag_source": "llm_gen",
        })
    return packages


def _llm_generate_packages(
    context: Dict[str, str],
    interview_type: str,
    count: int,
    probing_limit: int,
    company_hints: Optional[List[str]] = None,
    recent_questions: Optional[List[str]] = None,
    weakness_hints: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """调 LLM 生成考查包。任何失败抛异常，由上层降级。"""
    llm = get_llm(temperature=0.7)  # 出题适度创造性
    prompt = get_question_generation_prompt(
        candidate_summary=context["candidate_summary"],
        focus_areas=context["focus_areas"],
        interview_type=interview_type,
        question_count=count,
        probing_limit=probing_limit,
        company_hints=company_hints,
        recent_questions=recent_questions,
        weakness_hints=weakness_hints,
    )
    resp = invoke_llm_with_retry(llm, prompt)
    data = _extract_json(resp.content)
    if isinstance(data, dict):
        # 兼容 LLM 把数组包在对象里的情况
        data = data.get("questions") or data.get("items") or []
    if not isinstance(data, list) or not data:
        raise ValueError("出题 LLM 未返回有效数组")

    packages = []
    for item in data:
        if not isinstance(item, dict):
            continue
        packages.append({
            "category": item.get("category", "behavioral"),
            "intent": item.get("intent", ""),
            "stem": item.get("stem", ""),
            "anchor": item.get("anchor"),
            "probing_points": item.get("probing_points") or [],
            "ideal_signals": item.get("ideal_signals") or [],
            "estimated_minutes": item.get("estimated_minutes", 4),
            "rag_source": "llm_gen",
        })
    return packages


# ============================================================================
# 5. 对外主接口：生成题库 + 问答计划
# ============================================================================

def generate_question_bank(
    profile: Dict[str, Any],
    job_profile: Optional[Dict[str, Any]] = None,
    gaps: Optional[List[Dict[str, Any]]] = None,
    interview_type: str = "full",
    intensity: str = "normal",
    rag_context: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    生成个性化面试题库 + 问答计划。

    Args:
        profile:        用户画像 dict（来自 profile_service.get_profile）
        job_profile:    JD 要求画像（可选，无 JD 时为 None）
        gaps:           JD 差距清单（可选；有 JD 时作为考查重点）
        interview_type: 面试类型（behavioral/technical/case/motivation/full）
        intensity:      档位（short/normal/deep/full）
        rag_context:    RAG 检索结果（可选，spec 7.4 出题接入 RAG）：
                          {company_hints: List[str]   公司库真实面经（借鉴风格）
                           recent_questions: List[str] 个人库近期题（避免重复）
                           weakness_hints: List[str]   个人库弱项（复练）}

    Returns:
        (question_bank, question_plan):
          question_bank: List[QuestionPackage dict]，每个含 stem/probing_points/ideal_signals/qid
          question_plan: {question_count, probing_limit, has_qa_session, intensity, label}
    """
    cfg = get_intensity_config(intensity)
    count = cfg["question_count"]
    probing_limit = cfg["probing_limit"]

    context = normalize_context(profile, job_profile, gaps)

    # RAG 上下文（session_setup 已检索好传入；缺失/失败则为空，出题不受影响）
    rag_context = rag_context or {}
    company_hints = rag_context.get("company_hints") or None
    recent_questions = rag_context.get("recent_questions") or None
    weakness_hints = rag_context.get("weakness_hints") or None

    # LLM 生成（失败降级兜底）
    try:
        packages = _llm_generate_packages(
            context, interview_type, count, probing_limit,
            company_hints=company_hints,
            recent_questions=recent_questions,
            weakness_hints=weakness_hints,
        )
        logger.info(f"出题成功（LLM），{len(packages)} 题")
    except Exception as e:
        logger.warning(f"出题 LLM 失败，降级通用题库：{type(e).__name__}: {e}")
        packages = _fallback_packages(context, interview_type, count, probing_limit)

    # 补 qid + 裁剪 probing_points 到上限
    for p in packages:
        p["qid"] = str(uuid.uuid4())
        p["probing_points"] = p.get("probing_points", [])[:probing_limit]
        p["ideal_signals"] = p.get("ideal_signals", [])[:max(probing_limit, 2)]

    question_plan = {
        "question_count": len(packages),
        "probing_limit": probing_limit,
        "has_qa_session": cfg["has_qa_session"],
        "intensity": intensity,
        "label": cfg["label"],
        # 【7.4.3 来源透明】记录本场 RAG 命中数，供前端展示「本场参考了 N 条真实面经 / 避开 M 道近期题」
        "rag_used": {
            "company_hints": len(company_hints or []),
            "recent_questions": len(recent_questions or []),
            "weakness_hints": len(weakness_hints or []),
        },
    }

    return packages, question_plan


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("出题服务自检（用假画像，验证流程 + 降级）")
    print("=" * 60)

    fake_profile = {
        "name": "张三",
        "target_positions": ["产品经理"],
        "companies": ["字节跳动", "美团"],
        "positions": ["产品经理", "高级产品经理"],
        "work_descriptions": [
            "负责短视频feed推荐产品，DAU提升15%",
            "主导本地生活商家增长，GMV翻倍",
        ],
        "project_names": ["推荐系统重构"],
        "project_descriptions": ["重构推荐策略，CTR提升20%"],
        "technical_skills": ["SQL", "A/B测试", "数据分析"],
    }

    packages, plan = generate_question_bank(
        profile=fake_profile,
        interview_type="full",
        intensity="short",
    )

    print(f"\n问答计划：{plan}")
    print(f"\n题库（{len(packages)} 题）：")
    for i, p in enumerate(packages, 1):
        print(f"\n  题{i} [{p['category']}] {p['stem']}")
        print(f"     锚点：{p.get('anchor')}")
        print(f"     可挖掘：{p.get('probing_points')}")
        print(f"     理想信号：{p.get('ideal_signals')}")
