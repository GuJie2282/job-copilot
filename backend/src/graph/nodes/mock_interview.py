"""
模拟面试 LangGraph 节点（mock_interview）
=========================================

子图结构（对应 design.md 决策 1 / 5）：
  START → session_setup ─────────────────────────────────────────┐
            │ (画像缺失 → END)                                     │
            ▼                                                     │
         interviewer ──interrupt(提问)──► [等回答]                 │
            ▲                                       │              │
            │                                Command(resume=回答)   │
            │                                       ▼              │
            │                                   evaluator          │
            │                                  (信号差检测+决策)     │
            │                                       │              │
            │   route_after_eval: probe/next/enter_qa → interviewer │
            │                          end → debrief              │
            └──────────────────────────────┘                      │
                                          │                        │
                                          ▼                        │
                                       debrief ────────────────────┘ END

核心机制：
- interrupt：interviewer 提问后挂起，等用户回答（跨请求、抗重启，见 checkpointer.py）
- 信号差检测：evaluator 拿回答比对 ideal_signals，输出命中/缺失 + 缺失→追问方向映射
- 决策（route 逻辑）：缺失信号可追 且 未到上限 → probe；否则 next/enter_qa/end
- 追问按图索骥：interviewer 据 miss_probe_map 生成追问，非自由发挥

作者：求职 Copilot 项目
日期：2026-07-20
"""

import logging
from typing import Dict, Any, Optional

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from src.graph.state import FullAgentState
from src.graph.config import get_llm
from src.graph.prompts import get_evaluation_prompt, get_debrief_prompt
from src.graph.checkpointer import get_interview_checkpointer
from src.models.base import SessionLocal
from src.models.profile import JdMatchResultModel
from src.services.profile_service import get_profile
from src.services.question_generator import generate_question_bank
from src.services.llm_retry import invoke_llm_with_retry
from src.services.jd_parser import _extract_json

logger = logging.getLogger(__name__)


# ============================================================================
# 1. session_setup_node：会话初始化（读画像[+JD] → 出题 → 装配 state）
# ============================================================================

def session_setup_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    会话初始化节点。
    - 读用户画像（缺失 → 标记 profile_missing，由 route_after_setup 直达 END）
    - 读可选的 JD 匹配结果（job_profile / gaps）
    - 调 question_generator 生成题库 + 问答计划
    - 画像快照进 state（保证面试中画像改动不影响本场）
    """
    user_id = state.get("user_id")
    interview_type = state.get("interview_type") or "full"
    intensity = state.get("intensity") or "normal"
    jd_result_id = state.get("jd_result_id")
    persona = state.get("persona") or {}

    db = SessionLocal()
    try:
        profile = get_profile(db, user_id) if user_id else None
        if not profile:
            logger.warning(f"面试 session_setup：画像缺失 user_id={user_id}")
            return {
                "interview_status": "profile_missing",
                "messages": [AIMessage(content="❌ 未找到画像，请先建立个人画像后再进行模拟面试")],
                "current_decision": "end",
            }

        # 可选：读 JD 匹配结果（job_profile + gaps）
        job_profile = None
        gaps = None
        if jd_result_id:
            row = db.query(JdMatchResultModel).filter(
                JdMatchResultModel.id == jd_result_id,
                JdMatchResultModel.user_id == user_id,
            ).first()
            if row:
                job_profile = row.job_profile_json
                gaps = row.gaps_json

        # 【7.4.1 出题接入 RAG】检索公司库（真实面经增强）+ 个人库（避免重复 + 复练弱项）
        # 失败降级：RAG 检索任何异常都返回空 dict，出题不受影响（spec 7.4.4）
        rag_context = _retrieve_rag_context(db, user_id, profile, gaps)

        # 出题
        packages, plan = generate_question_bank(
            profile=profile,
            job_profile=job_profile,
            gaps=gaps,
            interview_type=interview_type,
            intensity=intensity,
            rag_context=rag_context,
        )

        logger.info(
            f"面试 session_setup 完成：{len(packages)} 题，档位={intensity}，"
            f"类型={interview_type}，JD={'有' if jd_result_id else '无'}，"
            f"RAG={'+'.join(k for k,v in rag_context.items() if v) or '无'}"
        )

        return {
            "profile_snapshot": profile,
            "job_profile_snapshot": job_profile,
            "gaps_snapshot": gaps,
            "persona": persona,
            "question_bank": packages,
            "question_plan": plan,
            "current_q_idx": 0,
            "current_q_probes": 0,
            "interview_status": "interviewing",
            "current_decision": None,
            "qa_done": False,
        }
    finally:
        db.close()


def route_after_setup(state: Dict[str, Any]) -> str:
    """画像缺失 → 结束；否则进入面试官。"""
    if state.get("interview_status") == "profile_missing":
        return "end"
    return "interview"


# ============================================================================
# 2. interviewer_node：提问 / 追问 / 反问 + interrupt 等回答
# ============================================================================

def interviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    面试官节点。根据 current_decision 决定本轮问什么：
      - probe:    基于上轮缺失信号（miss_probe_map）生成追问
      - enter_qa: 进入反问环节
      - None/next: 问 question_bank[current_q_idx] 的新题

    然后 interrupt({"question": ...}) 挂起，等用户回答。
    恢复后把本轮 qa 写入 current_round，交给 evaluator。
    """
    decision = state.get("current_decision")
    idx = state.get("current_q_idx", 0)
    bank = state.get("question_bank") or []
    transcript = state.get("transcript") or []

    question = None
    qid = None
    round_num = idx + 1
    is_probe = False

    if decision == "probe" and transcript:
        # 追问：评估时已按缺失信号生成人设化措辞（next_probe_followup）——合并 LLM，省一次往返
        last_eval = (transcript[-1].get("evaluation") or {})
        followup = last_eval.get("next_probe_followup")
        if followup:
            question = followup
            qid = transcript[-1].get("qid")
            round_num = transcript[-1].get("round", round_num)
            is_probe = True
        else:
            # 评估漏产追问措辞 → 模板降级（无 LLM，零成本兜底）
            miss_map = last_eval.get("miss_probe_map") or {}
            miss_signals = last_eval.get("miss_signals") or []
            followup_point = next((miss_map[s] for s in miss_signals if miss_map.get(s)), None)
            if followup_point:
                question = f"关于你刚才的回答，能具体讲讲——{followup_point}"
                qid = transcript[-1].get("qid")
                round_num = transcript[-1].get("round", round_num)
                is_probe = True

    if question is None and decision == "enter_qa":
        question = "我的问题问得差不多了。接下来，你有什么想问我的吗？"
        qid = "qa"
        round_num = len(transcript) + 1

    if question is None:
        # 新题（首次 或 next）
        if idx >= len(bank):
            return {"current_decision": "end"}
        pkg = bank[idx]
        question = pkg["stem"]
        qid = pkg["qid"]
        round_num = idx + 1

    # ⭐ interrupt：挂起，把问题交给前端，等用户回答
    answer = interrupt({
        "question": question,
        "round": round_num,
        "is_probe": is_probe,
        "qid": qid,
    })

    return {
        "current_round": {
            "round": round_num,
            "question": question,
            "answer": answer,
            "qid": qid,
            "is_probe": is_probe,
        }
    }


# ============================================================================
# 3. evaluator_node：信号差检测 + 评分 + 决策（核心）
# ============================================================================

def evaluator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    评估节点：拿本轮回答比对该题 ideal_signals（信号差检测），
    输出命中/缺失信号 + 缺失→追问方向映射 + 评分；并计算本轮决策。

    决策逻辑（route 放这里，条件边只转发 current_decision）：
      - 有可追问的缺失信号 且 未到 probing_limit → probe
      - 还有下一题 → next
      - 还有反问环节 → enter_qa
      - 否则 → end
    """
    current = state.get("current_round") or {}
    qid = current.get("qid")
    pkg = _find_pkg(state.get("question_bank") or [], qid) or {}
    ideal = pkg.get("ideal_signals", [])
    probing = pkg.get("probing_points", [])

    # 整场进度上下文（供评估 LLM 做整场判断，如是否提前结束）
    plan = state.get("question_plan") or {}
    rs_pre = state.get("running_scores") or {}
    rc_pre = rs_pre.get("_round_count", 0)
    ss_pre = rs_pre.get("_score_sum", 0)
    avg_so_far = round(ss_pre / rc_pre, 1) if rc_pre else None
    interview_context = {
        "round": current.get("round"),
        "total_questions": plan.get("question_count", len(state.get("question_bank") or [])),
        "has_qa_session": plan.get("has_qa_session"),
        "qa_done": state.get("qa_done"),
        "avg_score_so_far": avg_so_far,
    }

    # LLM 信号差检测 + 节奏决策(action) + 追问措辞（一次合并产出）
    # 失败降级：保守认为充分、不追问，action=None 交规则 fallback
    eval_result = _llm_evaluate(
        current.get("question", ""), ideal, probing, current.get("answer", ""),
        state.get("persona"), interview_context,
    )

    # 决策（LLM 自主 action + 防崩盘护栏；缺失/非法 → 规则 fallback）
    decision = _decide(state, eval_result)

    # 组装 transcript 条目（本轮完整记录：qa + evaluation + action + 节奏理由）
    entry = {
        "round": current.get("round"),
        "question": current.get("question"),
        "answer": current.get("answer"),
        "qid": qid,
        "is_probe": current.get("is_probe", False),
        "evaluation": eval_result,
        "action": decision,
        "decision_reason": eval_result.get("action_reason"),
    }

    update: Dict[str, Any] = {
        "transcript": [entry],
        "current_decision": decision,
    }

    # 按决策更新计数
    if decision == "probe":
        update["current_q_probes"] = state.get("current_q_probes", 0) + 1
    elif decision == "next":
        update["current_q_idx"] = state.get("current_q_idx", 0) + 1
        update["current_q_probes"] = 0
    elif decision == "enter_qa":
        update["qa_done"] = True
    elif decision == "end":
        update["interview_status"] = "finishing"

    # 累积评分（简化：滚动均值；阶段 6 细化为五维）
    rs = dict(state.get("running_scores") or {})
    if eval_result.get("score") is not None:
        rs["_round_count"] = rs.get("_round_count", 0) + 1
        rs["_score_sum"] = rs.get("_score_sum", 0) + eval_result["score"]
    update["running_scores"] = rs

    # 亮点 / 失分（累加）
    if eval_result.get("highlight"):
        update["highlights"] = [eval_result["highlight"]]
    if eval_result.get("weakness"):
        update["weaknesses"] = [eval_result["weakness"]]

    return update


def _clean_eval_text(value) -> Optional[str]:
    """清洗 LLM 返回的 highlight/weakness 文本：去除占位符与 null 语义。"""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    low = s.lower()
    # LLM 常见的"无"占位
    if low in ("null", "none", "无", "无。", "暂无", "na", "n/a", ""):
        return None
    # 把 prompt 示例文本当值返回的情况（如 "回答亮点（无则 null）"）
    if "无则" in s or "此处填" in s or "可选" in s:
        return None
    return s


# 合法节奏动作集合（评估 LLM 的 action 必须落在此集合内，否则视为非法 → 规则 fallback）
_VALID_ACTIONS = {"probe", "next", "enter_qa", "end"}


def _llm_evaluate(
    question: str,
    ideal_signals: list,
    probing_points: list,
    answer: str,
    persona: Optional[Dict[str, Any]] = None,
    interview_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    调 LLM 做信号差检测 + 节奏决策（action）+ 追问措辞（一次合并产出）。

    【evolve-interview-pacing】除原有信号/评分/追问措辞外，一并产出自主节奏决策
    action（probe|next|enter_qa|end）+ action_reason。action 供 _decide 经护栏校验后
    采用；非法/缺失则返回 None，由 _decide 回退规则。
    任何失败 → 降级（保守追问：miss=ideal_signals 交规则 fallback 判断，失败 ≠ 充分）。
    """
    try:
        llm = get_llm(temperature=0, timeout=20, tier="fast")  # 评估：快档（延迟敏感）+ 20s 短超时快速降级
        prompt = get_evaluation_prompt(question, ideal_signals, probing_points, answer, persona, interview_context)
        resp = invoke_llm_with_retry(llm, prompt, max_retries=0)  # 不重试：偶发超时即降级（20s 上限），不拖到 43s；降级已保守追问，失败不再=不追
        data = _extract_json(resp.content)
        if not isinstance(data, dict):
            raise ValueError("评估 LLM 未返回 JSON 对象")
        # action 合法性校验：非法/缺失 → None（触发 _decide 规则 fallback）
        action = data.get("action")
        action = action if action in _VALID_ACTIONS else None
        return {
            "hit_signals": data.get("hit_signals") or [],
            "miss_signals": data.get("miss_signals") or [],
            "miss_probe_map": data.get("miss_probe_map") or {},
            "score": data.get("score"),
            "highlight": _clean_eval_text(data.get("highlight")),
            "weakness": _clean_eval_text(data.get("weakness")),
            "action": action,
            "action_reason": _clean_eval_text(data.get("action_reason")),
            "next_probe_followup": _clean_eval_text(data.get("next_probe_followup")),
        }
    except Exception as e:
        # 保守追问（fix：原降级假设充分=不追问，致评估偶发超时时"完全不追问"）：
        # 评估失败 ≠ 回答充分。假设信号未验证（miss=ideal_signals），按可挖掘点给追问方向；
        # action=None 交规则 fallback——看到 miss 非空且 miss_probe_map 有值 → probe（受 probing_limit 上限保护）；
        # interviewer probe 分支 next_probe_followup 虽为 None，模板降级会用 miss_probe_map 生成"能具体讲讲——{点}"。
        logger.warning(f"评估 LLM 失败，降级（保守追问：miss=ideal，交规则 fallback 判断）：{type(e).__name__}: {e}")
        miss_map = {}
        for i, sig in enumerate(ideal_signals):
            miss_map[sig] = probing_points[i] if i < len(probing_points) else (probing_points[0] if probing_points else sig)
        return {
            "hit_signals": [],
            "miss_signals": list(ideal_signals),
            "miss_probe_map": miss_map,
            "score": 70,
            "highlight": None,
            "weakness": None,
            "action": None,
            "action_reason": f"评估服务异常（{type(e).__name__}），保守追问",
            "next_probe_followup": None,
        }


# 节奏护栏常量（防崩盘，非业务限制；design 决策 2）
# 业务护栏（追问几次、是否走完题库）已交给 LLM 自主；这里只兜"不死不崩"的底线。
_PACE_MIN_ROUNDS = 2            # 最低总轮数：防 LLM 开场一两轮就 end，体验过短（可调）
_PACE_PROBE_LIMIT = 5           # 单题最高追问：防在某一题上死循环（业务不限，仅防崩盘）
_PACE_QA_MAX = 1                # 反问至多次数：防反复 enter_qa


def _decide(state: Dict[str, Any], eval_result: Dict[str, Any]) -> str:
    """
    本轮节奏决策：优先采用评估 LLM 的自主 action，经防崩盘护栏校验；
    action 缺失/非法时回退规则 _rule_decide_fallback。

    护栏只在越界时纠正（design 决策 2）：
      - 已达最高总轮数 → 强制结束（防永不收尾）
      - 单题追问达上限却选 probe → 换题/收尾
      - 反问已进行却选 enter_qa → 换题/结束
      - 无下一题却选 next → 转反问/结束
      - 过早 end（且还有题）→ 继续问
    """
    action = eval_result.get("action")
    if action not in _VALID_ACTIONS:
        # action 缺失/非法 → 规则 fallback（降级与紧急回滚通道）
        return _rule_decide_fallback(state, eval_result)
    return _apply_guardrails(state, action)


def _after_questions(state: Dict[str, Any]) -> str:
    """题库问完后的去向：有反问环节且未进行 → enter_qa；否则 end。"""
    plan = state.get("question_plan") or {}
    if plan.get("has_qa_session") and not state.get("qa_done"):
        return "enter_qa"
    return "end"


def _apply_guardrails(state: Dict[str, Any], action: str) -> str:
    """对 LLM 的 action 套防崩盘护栏，越界则纠正为合法动作。"""
    idx = state.get("current_q_idx", 0)
    bank = state.get("question_bank") or []
    plan = state.get("question_plan") or {}
    probe_count = state.get("current_q_probes", 0)
    qa_done = bool(state.get("qa_done"))
    completed_rounds = len(state.get("transcript") or [])  # 已入库轮数（本轮尚未入库）

    total_q = plan.get("question_count", len(bank))
    max_rounds = total_q * (1 + _PACE_PROBE_LIMIT)  # 最高总轮数上限（防永不收尾）
    has_next = idx + 1 < total_q

    # 1) 已达最高总轮数 → 强制结束
    if completed_rounds + 1 >= max_rounds:
        return "end"

    # 2) probe 护栏：单题追问上限（防死循环）→ 换题或收尾
    if action == "probe" and probe_count >= _PACE_PROBE_LIMIT:
        return "next" if has_next else _after_questions(state)

    # 3) enter_qa 护栏：反问至多 _PACE_QA_MAX 次（这里以 qa_done 布尔兜底，已进行则不再进）
    if action == "enter_qa" and qa_done:
        return "next" if has_next else "end"

    # 4) next 护栏：无下一题时转反问/结束
    if action == "next" and not has_next:
        return _after_questions(state)

    # 5) 最低轮数护栏：过早 end（且还有下一题）→ 继续问
    if action == "end" and completed_rounds + 1 < _PACE_MIN_ROUNDS and has_next:
        return "next"

    return action


def _rule_decide_fallback(state: Dict[str, Any], eval_result: Dict[str, Any]) -> str:
    """
    原计数器规则决策（保留作降级与紧急回滚）。

    逻辑：有可追问缺失信号且未到上限 → probe；否则按题库顺序 next / enter_qa / end。
    注：fallback 用问答计划的 probing_limit（业务值，默认 3），与护栏的 _PACE_PROBE_LIMIT
    （防崩盘值）职责分离——前者是 fallback 的业务节奏，后者是 LLM 自主时的崩盘底线。
    """
    miss_map = eval_result.get("miss_probe_map") or {}
    miss_signals = eval_result.get("miss_signals") or []
    probe_count = state.get("current_q_probes", 0)
    plan = state.get("question_plan") or {}
    idx = state.get("current_q_idx", 0)
    bank = state.get("question_bank") or []

    # 1) 有可追问的缺失信号 且 未到上限
    has_probe_target = any(miss_map.get(s) for s in miss_signals)
    if has_probe_target and probe_count < plan.get("probing_limit", 3):
        return "probe"
    # 2) 还有下一题
    total = plan.get("question_count", len(bank))
    if idx + 1 < total:
        return "next"
    # 3) 还有反问环节
    if plan.get("has_qa_session") and not state.get("qa_done"):
        return "enter_qa"
    # 4) 结束
    return "end"


def route_after_eval(state: Dict[str, Any]) -> str:
    """条件边：转发 evaluator 的决策。"""
    return state.get("current_decision") or "end"


# ============================================================================
# 4. debrief_node：复盘（阶段 5 详细实现，这里先骨架）
# ============================================================================

def debrief_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    复盘节点：基础汇总 + LLM 详细复盘（改进范例 / 卡壳 / 可执行后续建议）。

    详细复盘（对应 design.md 决策 7）：
      - round_reviews：每题 better_version（基于候选人自身经历改写，非标准答案）
      - inappropriate_answers / stuck_points：失分与卡壳
      - next_steps：可执行后续建议
    LLM 失败则降级为基础复盘（不阻断）。
    """
    transcript = state.get("transcript") or []
    profile = state.get("profile_snapshot") or {}
    rs = state.get("running_scores") or {}
    round_count = rs.get("_round_count", 0)
    score_sum = rs.get("_score_sum", 0)
    avg = round(score_sum / round_count, 1) if round_count else None

    # 详细复盘（LLM，失败降级）
    detail = _llm_debrief(profile, transcript)

    debrief = {
        "overview": {
            "avg_score": avg,
            "total_rounds": len(transcript),
            "one_line_summary": detail.get("overall_summary") or "",
        },
        "round_by_round": transcript,
        "round_reviews": detail.get("round_reviews") or [],
        "inappropriate_answers": detail.get("inappropriate_answers") or [],
        "stuck_points": detail.get("stuck_points") or [],
        "next_steps": detail.get("next_steps") or [],
        "highlights": state.get("highlights") or [],
        "weaknesses": state.get("weaknesses") or [],
    }

    logger.info(f"面试复盘完成：{len(transcript)} 轮，平均分={avg}，详细字段={'有' if detail else '降级基础'}")

    # 【7.4.2 复盘接入个人库】沉淀本场面经到个人库（数据飞轮：下次出题反哺）
    # 失败不阻断复盘返回（spec：沉淀是 best-effort，复盘报告已生成）
    _archive_to_personal_library(state, debrief)

    return {
        "interview_status": "finished",
        "debrief_report": debrief,
    }


def _llm_debrief(profile: Dict[str, Any], transcript: list) -> Dict[str, Any]:
    """LLM 生成详细复盘。失败返回空 dict（保留基础复盘）。"""
    import json
    try:
        llm = get_llm(temperature=0.3, timeout=90, tier="strong")  # 复盘：主力档（质量敏感），大 JSON 90s
        name = profile.get("name") or "候选人"
        targets = profile.get("target_positions") or []
        target = "、".join(targets) if targets else "通用岗位"

        # 简短画像摘要
        parts = [f"姓名：{name}", f"目标岗位：{target}"]
        work = profile.get("work_descriptions") or []
        proj = profile.get("project_descriptions") or []
        if work:
            parts.append("主要经历：" + "；".join(work[:2]))
        if proj:
            parts.append("项目：" + "；".join(proj[:2]))
        profile_summary = "\n".join(parts)

        # transcript 精简（含评估关键信息）
        tj = json.dumps([
            {
                "round": t.get("round"),
                "question": t.get("question"),
                "answer": t.get("answer"),
                "score": (t.get("evaluation") or {}).get("score"),
                "miss_signals": (t.get("evaluation") or {}).get("miss_signals"),
                "action": t.get("action"),
                "decision_reason": t.get("decision_reason"),
            }
            for t in transcript
        ], ensure_ascii=False)

        prompt = get_debrief_prompt(profile_summary, tj, target)
        resp = invoke_llm_with_retry(llm, prompt)
        data = _extract_json(resp.content)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"详细复盘 LLM 失败，降级基础复盘：{type(e).__name__}: {e}")
        return {}


# ============================================================================
# 5. 辅助函数
# ============================================================================

def _find_pkg(bank: list, qid: Optional[str]) -> Optional[Dict[str, Any]]:
    """按 qid 从题库找考查包。"""
    if not qid:
        return None
    for p in bank:
        if p.get("qid") == qid:
            return p
    return None


# ----------------------------------------------------------------------------
# RAG 接入辅助（阶段 7.4）
# ----------------------------------------------------------------------------

def _retrieve_rag_context(db, user_id: str, profile: Dict[str, Any], gaps) -> Dict[str, Any]:
    """
    出题前 RAG 检索（spec 7.4.1）：公司库增强真实感 + 个人库避免重复/复练弱项。
    任何异常都降级为空 dict（出题不依赖检索，spec 7.4.4）。
    """
    try:
        from src.services.knowledge_service import (
            search_company, get_recent_questions, get_weakness_questions,
        )
        rag: Dict[str, Any] = {}

        # ── 公司库：按目标岗位 + 重点 gap 构造 query，检索真实面经 ──
        targets = profile.get("target_positions") or []
        position = targets[0] if targets else None
        query_parts = [p for p in [position] if p]
        for g in (gaps or [])[:3]:
            if g.get("requirement"):
                query_parts.append(g["requirement"])
        query = " ".join(query_parts)
        if query:
            hits = search_company(db, query, top_k=5, position=position)
            hints = [h.get("text") for h in hits if h.get("text")]
            if hints:
                rag["company_hints"] = hints[:5]

        # ── 个人库：近期题（避免重复）+ 弱项（复练）——数据飞轮反哺 ──
        recent = get_recent_questions(db, user_id, limit=8)
        if recent:
            rag["recent_questions"] = recent
        weak = get_weakness_questions(db, user_id, limit=5)
        if weak:
            rag["weakness_hints"] = [w.get("text") for w in weak if w.get("text")][:5]

        return rag
    except Exception as e:
        logger.warning(f"出题 RAG 检索失败，降级无 RAG：{type(e).__name__}: {e}")
        return {}


def _archive_to_personal_library(state: Dict[str, Any], debrief: Dict[str, Any]) -> None:
    """
    复盘后把 transcript 沉淀到个人面经库（spec 7.4.2 / 数据飞轮）。
    失败仅告警，不阻断复盘（报告已生成，沉淀是 best-effort）。
    """
    try:
        from src.services.knowledge_service import archive_episodes_from_session
        user_id = state.get("user_id")
        transcript = state.get("transcript") or []
        if not user_id or not transcript:
            return
        session_id = state.get("session_id") or state.get("thread_id") or "unknown"
        profile = state.get("profile_snapshot") or {}
        bank = state.get("question_bank") or []
        early = bool(state.get("early_terminated"))

        db = SessionLocal()
        try:
            archive_episodes_from_session(
                db, user_id, session_id, transcript, debrief, profile, bank,
                early_terminated=early,
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"复盘沉淀个人库失败（不阻断复盘）：{type(e).__name__}: {e}")


# ============================================================================
# 6. 构建面试子图
# ============================================================================

def build_interview_graph(checkpointer=None):
    """
    构建模拟面试子图并编译。

    Args:
        checkpointer: LangGraph checkpointer（默认用面试会话 checkpointer，支持 interrupt + 抗重启）

    Returns:
        编译后的图（带 checkpointer，可 interrupt）
    """
    if checkpointer is None:
        checkpointer = get_interview_checkpointer()

    builder = StateGraph(FullAgentState)

    builder.add_node("session_setup", session_setup_node)
    builder.add_node("interviewer", interviewer_node)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("debrief", debrief_node)

    builder.set_entry_point("session_setup")

    # session_setup → 画像缺失 END，否则进 interviewer
    builder.add_conditional_edges(
        "session_setup", route_after_setup,
        {"interview": "interviewer", "end": END},
    )
    # interviewer 提问后 → evaluator 评估
    builder.add_edge("interviewer", "evaluator")
    # evaluator 决策：probe/next/enter_qa 回 interviewer，end 去 debrief
    builder.add_conditional_edges(
        "evaluator", route_after_eval,
        {"probe": "interviewer", "next": "interviewer", "enter_qa": "interviewer", "end": "debrief"},
    )
    builder.add_edge("debrief", END)

    return builder.compile(checkpointer=checkpointer)
