"""
JD 匹配计算服务（matcher）

核心：混合式匹配算法（对应 design.md 决策 1）。
- 硬技能 / 软技能：程序化逐项比对（归一化 + 子串匹配），确定性、可追溯
- 经验 / 学历：基于画像的规则启发式
- 隐性偏好：LLM 综合判断（规则判不了的「大厂背景」等）
- 加权汇总：四维度按可配置权重 → 总分
- 红线惩罚：任一红线未满足 → 总分 ×0.7 且封顶 60

每个匹配项都附 JD 依据 + 画像依据，保证可解释（对应决策 5）。

作者：求职 Copilot 项目
日期：2026-07-14
"""

import re
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple

from src.graph.config import get_llm
from src.graph.prompts import get_implicit_judgment_prompt
from src.services.jd_parser import _extract_json
from src.services.llm_retry import is_retryable

logger = logging.getLogger(__name__)


# ============================================================================
# 可配置参数
# ============================================================================

# 四维度权重（可调）—— 技能最重，经验次之，学历/软技能较轻
WEIGHTS = {"skill": 0.4, "experience": 0.3, "education": 0.15, "soft_skill": 0.15}
REDLINE_PENALTY = 0.7   # 任一红线未满足时，总分乘以此系数
REDLINE_CAP = 60        # 红线未满足时，总分封顶（红线为硬性门槛，不应给高分）

# 学历层级（用于学历维度比对）
DEGREE_LEVEL = {
    "大专": 1, "专科": 1,
    "本科": 2, "学士": 2, "bachelor": 2,
    "硕士": 3, "研究生": 3, "master": 3,
    "博士": 4, "phd": 4,
}


# ============================================================================
# 工具：归一化与画像信息抽取
# ============================================================================

def _normalize(s: Any) -> str:
    """归一化字符串：去空格/标点/转小写，便于技能匹配"""
    return re.sub(r'[\s\-_./,，、（）()·]', '', str(s)).lower()


def _skill_match(requirement: str, profile_skills: List[str]) -> Tuple[bool, Optional[str]]:
    """
    判断某技能要求是否在画像技能集中（双向子串包含，容错大小写/分隔符）。
    返回 (是否匹配, 匹配到的画像技能)。
    """
    nr = _normalize(requirement)
    if not nr:
        return False, None
    for ps in (profile_skills or []):
        nps = _normalize(ps)
        if nps and (nr in nps or nps in nr):
            return True, ps
    return False, None


def _profile_skill_pool(user_profile: Dict[str, Any]) -> List[str]:
    """汇总画像里所有技能（技术 + 软 + 语言）作为硬技能匹配池"""
    pool = []
    for key in ("technical_skills", "soft_skills", "languages"):
        pool.extend(user_profile.get(key) or [])
    return pool


def _estimate_experience_years(user_profile: Dict[str, Any]) -> int:
    """从画像工作经历估算工作年数（粗略启发式）"""
    durations = user_profile.get("durations") or []
    companies = user_profile.get("companies") or []
    total = 0
    for d in durations:
        years = re.findall(r'(19\d{2}|20\d{2})', str(d))
        if len(years) >= 2:
            try:
                total += max(0, int(years[-1]) - int(years[0]))
            except ValueError:
                pass
        elif len(years) == 1:
            total += 1
    # 解析不到但有公司记录 → 按公司数粗估
    if total == 0 and companies:
        total = len(companies) * 2
    return total


def _max_degree_level(user_profile: Dict[str, Any]) -> int:
    """取画像中的最高学历层级"""
    degrees = user_profile.get("degrees") or []
    level = 0
    for d in degrees:
        dl = str(d).lower()
        for k, v in DEGREE_LEVEL.items():
            if k in dl or k in str(d):
                level = max(level, v)
    return level


# ============================================================================
# JD 要求抽取（年限 / 学历）
# ============================================================================

def _extract_year_requirement(job_profile: Dict[str, Any]) -> Optional[int]:
    """从 JD 要求中提取年限要求（如 '3 年以上经验' → 3）"""
    for cat in ("hard_skills", "red_lines"):
        for req in job_profile.get(cat, []):
            r = req.get("requirement", "")
            m = re.search(r'(\d+)\s*年', r)
            if m and any(k in r for k in ("经验", "工作", "以上")):
                try:
                    return int(m.group(1))
                except ValueError:
                    pass
    return None


def _extract_degree_requirement(job_profile: Dict[str, Any]) -> Optional[int]:
    """从 JD 要求中提取学历层级要求"""
    for cat in ("hard_skills", "red_lines"):
        for req in job_profile.get(cat, []):
            r = req.get("requirement", "")
            rl = r.lower()
            for k, v in DEGREE_LEVEL.items():
                if k in rl or k in r:
                    return v
    return None


# ============================================================================
# 各维度匹配
# ============================================================================

def _match_skills(hard_skills: List[Dict], user_profile: Dict) -> Tuple[float, List[Dict]]:
    """
    硬技能逐项比对。
    年限类要求（如"3 年经验"）跳过，归经验维度计分。
    """
    pool = _profile_skill_pool(user_profile)
    items: List[Dict] = []
    satisfied = 0.0
    for req in hard_skills:
        r = req.get("requirement", "")
        if re.search(r'\d+\s*年', r) and any(k in r for k in ("经验", "工作")):
            continue  # 年限类归经验维度
        matched, hit = _skill_match(r, pool)
        if matched:
            satisfied += 1
        items.append({
            "category": "hard_skill",
            "requirement": r,
            "must_have": req.get("must_have", True),
            "status": "satisfied" if matched else "missing",
            "jd_evidence": req.get("evidence"),
            "profile_evidence": hit,
        })
    score = round(satisfied / len(items) * 100, 1) if items else 70.0
    return score, items


def _match_soft_skills(soft_skills: List[Dict], user_profile: Dict) -> Tuple[float, List[Dict]]:
    """软技能比对（在画像软技能池里匹配）"""
    pool = user_profile.get("soft_skills") or []
    items: List[Dict] = []
    satisfied = 0.0
    for req in soft_skills:
        r = req.get("requirement", "")
        matched, hit = _skill_match(r, pool)
        if matched:
            satisfied += 1
        items.append({
            "category": "soft_skill",
            "requirement": r,
            "must_have": req.get("must_have", False),
            "status": "satisfied" if matched else "missing",
            "jd_evidence": req.get("evidence"),
            "profile_evidence": hit,
        })
    score = round(satisfied / len(items) * 100, 1) if items else 70.0
    return score, items


def _match_experience(job_profile: Dict, user_profile: Dict) -> Tuple[float, List[Dict]]:
    """经验维度：画像工作年数 vs JD 年限要求"""
    years = _estimate_experience_years(user_profile)
    req_years = _extract_year_requirement(job_profile)
    if req_years:
        if years >= req_years:
            status, score = "satisfied", min(100.0, 70 + (years - req_years) * 5)
        elif years >= req_years * 0.7:
            status, score = "partial", 55.0
        else:
            status, score = "missing", 35.0
        return round(score, 1), [{
            "category": "experience",
            "requirement": f"{req_years} 年以上经验",
            "status": status,
            "profile_evidence": f"画像估算约 {years} 年工作经历",
        }]
    # 无明确年限要求：有工作经历即给中性偏高
    score = 75.0 if years > 0 else 50.0
    return score, [{
        "category": "experience",
        "requirement": "相关工作经验",
        "status": "satisfied" if years > 0 else "missing",
        "profile_evidence": f"画像估算约 {years} 年工作经历",
    }]


def _match_education(job_profile: Dict, user_profile: Dict) -> Tuple[float, List[Dict]]:
    """学历维度：画像最高学历 vs JD 学历要求"""
    level = _max_degree_level(user_profile)
    req_level = _extract_degree_requirement(job_profile)
    if req_level:
        if level >= req_level:
            status, score = "satisfied", 90.0
        elif level >= req_level - 1:
            status, score = "partial", 55.0
        else:
            status, score = "missing", 30.0
        req_name = next((k for k, v in DEGREE_LEVEL.items() if v == req_level), "学历")
        return round(score, 1), [{
            "category": "education",
            "requirement": f"{req_name}及以上",
            "status": status,
            "profile_evidence": f"画像最高学历层级 {level}",
        }]
    score = 80.0 if level >= 2 else 60.0
    return score, [{
        "category": "education",
        "requirement": "学历背景",
        "status": "satisfied" if level >= 2 else "partial",
        "profile_evidence": f"画像最高学历层级 {level}",
    }]


def _check_redlines(red_lines: List[Dict], user_profile: Dict) -> List[Dict]:
    """
    检查红线项（硬性门槛）。
    学历类红线用学历层级判断；其他红线在技能/资质池里找。
    """
    pool = _profile_skill_pool(user_profile)
    level = _max_degree_level(user_profile)
    items: List[Dict] = []
    for req in red_lines:
        r = req.get("requirement", "")
        req_level = None
        for k, v in DEGREE_LEVEL.items():
            if k in r.lower() or k in r:
                req_level = v
                break
        if req_level is not None:
            ok = level >= req_level
        else:
            ok, _ = _skill_match(r, pool)
        items.append({
            "category": "redline",
            "requirement": r,
            "must_have": True,
            "status": "satisfied" if ok else "missing",
            "jd_evidence": req.get("evidence"),
        })
    return items


def judge_implicit(implicit_prefs: List[Dict], user_profile: Dict, max_retries: int = 2) -> List[Dict]:
    """
    LLM 判断隐性偏好的满足程度（规则判不了的「大厂背景」「创业经历」等）。

    - 无隐性偏好时返回空列表。
    - LLM 调用失败时降级为统一 partial（不阻断主流程，标注"待确认"）。
    """
    if not implicit_prefs:
        return []

    # 画像摘要文本（供 LLM 判断），截断防止 token 过长
    profile_text = json.dumps(
        {k: v for k, v in user_profile.items() if v}, ensure_ascii=False
    )[:1500]

    llm = get_llm(temperature=0.0, tier="strong")  # JD 匹配：主力档（质量敏感）
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            prompt = get_implicit_judgment_prompt(implicit_prefs, profile_text)
            if attempt > 0:
                prompt = "上次失败，请严格输出 ```json 包裹的合法 JSON。\n\n" + prompt
            resp = llm.invoke(prompt)
            data = _extract_json(resp.content)
            # 兼容 LLM 返回 list 或 dict 包装
            if isinstance(data, dict):
                data = data.get("results") or data.get("items") or [data]
            items = []
            for pref, judged in zip(implicit_prefs, data):
                status = judged.get("status", "partial") if isinstance(judged, dict) else "partial"
                if status not in ("satisfied", "partial", "missing"):
                    status = "partial"
                items.append({
                    "category": "implicit",
                    "requirement": pref.get("requirement"),
                    "must_have": False,
                    "status": status,
                    "jd_evidence": pref.get("evidence"),
                    "profile_evidence": judged.get("reason") if isinstance(judged, dict) else None,
                })
            return items
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                break
            if attempt < max_retries:
                time.sleep(1.0 * (2 ** attempt))

    # LLM 失败：降级为统一 partial，不阻断主流程
    logger.warning(f"隐性偏好 LLM 判断失败，降级为 partial：{last_error}")
    return [{
        "category": "implicit",
        "requirement": p.get("requirement"),
        "must_have": False,
        "status": "partial",
        "jd_evidence": p.get("evidence"),
        "profile_evidence": "（LLM 判断失败，待确认）",
    } for p in implicit_prefs]


# ============================================================================
# 加权汇总与红线惩罚
# ============================================================================

def _weighted_total(dims: Dict[str, float]) -> float:
    return round(sum(dims[k] * WEIGHTS[k] for k in WEIGHTS), 1)


def _score_to_level(score: float) -> str:
    if score >= 75:
        return "高度匹配"
    if score >= 50:
        return "部分匹配"
    return "匹配度较低"


def _mark_low_confidence(items: List[Dict], profile_confidence: Dict) -> None:
    """
    画像整体置信度偏低时，给 missing/partial 项标注 need_confirm（待确认）。
    简化策略：取画像字段置信度均值，低于阈值则标注。
    """
    scores = []
    for v in profile_confidence.values():
        if isinstance(v, dict) and "score" in v:
            scores.append(v["score"])
        elif isinstance(v, (int, float)):
            scores.append(v)
    avg = sum(scores) / len(scores) if scores else 1.0
    if avg < 0.6:
        for it in items:
            if it.get("status") in ("missing", "partial"):
                it["need_confirm"] = True


# ============================================================================
# 主入口
# ============================================================================

def calculate_match(
    job_profile: Dict[str, Any],
    user_profile: Dict[str, Any],
    profile_confidence: Optional[Dict] = None,
    with_implicit: bool = True,
) -> Dict[str, Any]:
    """
    计算画像与 JD 的匹配度（混合式）。

    Args:
        job_profile:        JD 解析出的要求画像（四分类 dict）
        user_profile:       用户个人画像（dict）
        profile_confidence: 画像字段置信度（可选，用于标注低置信度项）
        with_implicit:      是否调用 LLM 判断隐性偏好（默认 True）。
                            评分链传 False 跳过——隐性判断不影响总分（overall 仅由
                            技能/经验/学历/软技能 + 红线惩罚得出），隐性项交由增补链
                            enrich 处理，从而把评分链的 LLM 调用压到 1 次（仅 JD 解析）。
    Returns:
        match_result dict：
          overall_score, level, dimension_scores, matched_items, redline_hit
    """
    # 1. 四维度（规则）
    skill_score, skill_items = _match_skills(job_profile.get("hard_skills", []), user_profile)
    soft_score, soft_items = _match_soft_skills(job_profile.get("soft_skills", []), user_profile)
    exp_score, exp_items = _match_experience(job_profile, user_profile)
    edu_score, edu_items = _match_education(job_profile, user_profile)

    # 2. 隐性偏好（LLM）—— 评分链（with_implicit=False）跳过，交由增补链 enrich 处理
    if with_implicit:
        implicit_items = judge_implicit(job_profile.get("implicit_preferences", []), user_profile)
    else:
        implicit_items = []

    # 3. 红线
    redline_items = _check_redlines(job_profile.get("red_lines", []), user_profile)

    # 4. 加权总分
    dimensions = {
        "skill": skill_score,
        "experience": exp_score,
        "education": edu_score,
        "soft_skill": soft_score,
    }
    overall = _weighted_total(dimensions)

    # 5. 红线惩罚：任一红线未满足 → 总分 ×0.7 且封顶 60
    redline_hit = any(it["status"] == "missing" for it in redline_items)
    if redline_hit:
        overall = round(min(overall * REDLINE_PENALTY, REDLINE_CAP), 1)

    # 6. 合并匹配明细（可解释展示）
    matched_items = skill_items + soft_items + exp_items + edu_items + implicit_items + redline_items

    # 7. 低置信度标注（画像字段置信度低 → 相关项标"待确认"）
    if profile_confidence:
        _mark_low_confidence(matched_items, profile_confidence)

    return {
        "overall_score": overall,
        "level": _score_to_level(overall),
        "dimension_scores": dimensions,
        "matched_items": matched_items,
        "redline_hit": redline_hit,
    }
