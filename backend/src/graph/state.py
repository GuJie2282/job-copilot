"""
LangGraph AgentState 定义

功能：
1. 定义求职 Copilot 的状态结构
2. 支持多轮对话记忆
3. 支持简历解析相关状态

作者：求职 Copilot 项目
日期：2026-07-03
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
from operator import add
from langgraph.graph.message import add_messages


# ============================================================================
# 基础状态定义
# ============================================================================

class AgentState(TypedDict):
    """
    求职 Copilot 的主状态（AgentState）

    用途：在 LangGraph 的各个节点间传递状态

    字段说明：
    - messages: 消息历史（自动累加）
    - user_id: 用户 ID
    - current_step: 当前步骤（用于路由）
    - intent: 用户意图（chat, profile_parse, jd_match, resume_optimize, mock_interview）
    - error: 错误信息
    """

    # 消息历史（使用 add_messages reducer 自动累加）
    messages: Annotated[Sequence, add_messages]

    # 用户标识
    user_id: Optional[str]

    # 当前步骤（用于路由）
    current_step: Optional[str]

    # 用户意图
    # - "chat": 普通对话
    # - "profile_parse": 解析简历
    # - "jd_match": JD 匹配
    # - "resume_optimize": 简历优化
    # - "mock_interview": 模拟面试
    intent: Optional[str]

    # 错误信息
    error: Optional[str]


# ============================================================================
# 简历解析相关状态（扩展）
# ============================================================================

class ResumeParseState(TypedDict):
    """
    简历解析专用状态

    用途：简历解析流程中的状态传递

    字段说明：
    - resume_source: 简历来源（file, text, manual）
    - resume_file_path: 文件路径（如果来源是 file）
    - resume_text: 提取的文本内容
    - resume_file_name: 文件名
    - user_profile: 解析后的个人画像
    - profile_confidence: 画像置信度
    - profile_quality_score: 文本质量分数
    - parse_status: 解析状态（success, warning, error）
    - parse_warnings: 解析警告列表
    - parse_error: 解析错误信息
    - awaiting_confirmation: 是否等待用户确认
    - user_confirmed: 用户是否确认
    """

    # 简历来源
    # - "file": 文件上传
    # - "text": 文本粘贴
    # - "manual": 手动填写
    resume_source: Optional[str]

    # 文件路径（如果来源是 file）
    resume_file_path: Optional[str]

    # 提取的文本内容
    resume_text: Optional[str]

    # 文件名
    resume_file_name: Optional[str]

    # 解析后的个人画像（结构化数据）
    user_profile: Optional[Dict[str, Any]]

    # 画像置信度（字段名 -> {"score": 0.95, "level": "高"}）
    profile_confidence: Optional[Dict[str, Dict[str, Any]]]

    # 文本质量分数（0.0-1.0）
    profile_quality_score: Optional[float]

    # 解析状态
    # - "success": 解析成功
    # - "warning": 解析成功但有警告
    # - "error": 解析失败
    parse_status: Optional[str]

    # 解析警告列表
    parse_warnings: Optional[List[str]]

    # 解析错误信息
    parse_error: Optional[str]

    # 是否等待用户确认
    awaiting_confirmation: Optional[bool]

    # 用户是否确认
    user_confirmed: Optional[bool]


# ============================================================================
# JD 匹配相关状态（扩展）
# ============================================================================

class JdMatchState(TypedDict):
    """
    JD 匹配专用状态

    字段说明：
    - jd_text:         JD 原文
    - job_profile:     JD 解析出的要求画像（硬技能/软技能/隐性/红线四分类）
    - match_result:    匹配结果（overall_score / level / dimension_scores / matched_items / redline_hit）
    - gaps:            差距清单（Gap 四分类 + 应对建议）
    - match_confidence:各项置信度
    - match_status:    匹配状态（success / profile_missing / jd_invalid / error）
    - result_id:       持久化的匹配结果 ID
    """

    # JD 原文
    jd_text: Optional[str]

    # JD 解析出的要求画像（结构化）
    job_profile: Optional[Dict[str, Any]]

    # 匹配结果（含总分、维度得分、匹配明细、红线标记）
    match_result: Optional[Dict[str, Any]]

    # 差距清单（Gap 四分类 + 建议）
    gaps: Optional[List[Dict[str, Any]]]

    # 各项置信度
    match_confidence: Optional[Dict[str, Any]]

    # 匹配状态
    # - "success":        匹配成功
    # - "profile_missing": 画像缺失，需先建立画像
    # - "jd_invalid":     JD 无效（过短/非 JD）
    # - "error":          匹配过程异常
    match_status: Optional[str]

    # 持久化的匹配结果 ID
    result_id: Optional[str]


# ============================================================================
# 模拟面试相关状态（扩展）
# ============================================================================

class MockInterviewState(TypedDict):
    """
    模拟面试专用状态

    模拟面试是「长程会话」（区别于简历/JD 的一次性流水线），状态需跨请求、
    抗重启持久化（由 checkpointer 负责，见 graph/checkpointer.py）。

    字段按职责分组：

    【会话元信息】一场面试的配置与生命周期标识
    - session_id:        会话标识（= checkpointer 的 thread_id）
    - interview_status:  会话状态（setup / interviewing / paused / finished）
    - interview_mode:    模式（real 实战 / coach 教练）
    - interview_type:    面试类型（behavioral / technical / case / motivation / full / stress）
    - intensity:         档位（short 简短 / normal 正常 / deep 深度 / full 全程）—— 语义化，不暴露时间

    【关联上下文】承上：消费画像 + 可选 JD 匹配结果
    - profile_snapshot:    画像快照（开始时拷贝，面试中画像改动不影响本场，保证一致性）
    - jd_result_id:        关联的 JD 匹配结果 ID（可空——无 JD 也能面试）
    - job_profile_snapshot: JD 要求画像快照（可空）
    - gaps_snapshot:       JD 差距清单快照（可空；有 JD 时作为考查重点）
    - persona:             面试官人设 {tone 风格, role 角色, stress_mode 压力开关, style_prompt}

    【题库与进度】出题节点生成，evaluator/router 推进
    - question_bank:     考查包题库（每个 QuestionPackage 含 stem/probing_points/ideal_signals）
    - question_plan:     问答计划 {question_count 题量, probing_limit 每题追问上限, has_qa_session 是否含反问}
    - current_q_idx:     当前题号
    - questions_asked:   已问题目（累加，防重复 + 复盘用）
    - current_q_probes:  本题已追问次数（上限由 question_plan.probing_limit 控制，默认≤3）

    【transcript】黄金字段：追问、评分、复盘、面经沉淀都依赖它
    - transcript:        对话流水，每轮 {round, question, answer, evaluation, action}

    【累积评估】每轮追加，复盘汇总
    - running_scores:    五维渐进分 {communication 沟通, logic 逻辑, expertise 专业, resilience 抗压, fit 匹配}
    - highlights:        亮点（累加）
    - weaknesses:        失分点（累加）

    【RAG 上下文】面经库检索结果（阶段 7 接入）
    - retrieved_company_qs:  从公司面经库检索的相关真题
    - retrieved_episodes:    从个人面经库检索的本人历史片段（复练/对比）

    【复盘产出】debrief 节点生成
    - debrief_report:  结构化复盘报告（逐题回顾/改进范例/卡壳/后续建议）
    - debrief_id:      持久化的复盘报告 ID

    【控制】
    - awaiting_answer: 是否等待用户回答（interrupt 标志，前端据此知道「该用户说话了」）
    """

    # --- 会话元信息 ---
    session_id: Optional[str]
    interview_status: Optional[str]
    interview_mode: Optional[str]
    interview_type: Optional[str]
    intensity: Optional[str]

    # --- 关联上下文（承上）---
    profile_snapshot: Optional[Dict[str, Any]]
    jd_result_id: Optional[str]
    job_profile_snapshot: Optional[Dict[str, Any]]
    gaps_snapshot: Optional[List[Dict[str, Any]]]
    persona: Optional[Dict[str, Any]]

    # --- 题库与进度 ---
    question_bank: Optional[List[Dict[str, Any]]]
    question_plan: Optional[Dict[str, Any]]
    current_q_idx: Optional[int]
    questions_asked: Annotated[List[str], add]
    current_q_probes: Optional[int]

    # --- transcript（黄金字段，累加）---
    transcript: Annotated[List[Dict[str, Any]], add]

    # --- 累积评估 ---
    running_scores: Optional[Dict[str, Any]]
    highlights: Annotated[List[str], add]
    weaknesses: Annotated[List[str], add]

    # --- RAG 上下文 ---
    retrieved_company_qs: Optional[List[Dict[str, Any]]]
    retrieved_episodes: Optional[List[Dict[str, Any]]]

    # --- 复盘产出 ---
    debrief_report: Optional[Dict[str, Any]]
    debrief_id: Optional[str]

    # --- 控制 ---
    awaiting_answer: Optional[bool]
    current_round: Optional[Dict[str, Any]]   # 当前轮 qa（interviewer→evaluator 传递）
    current_decision: Optional[str]           # evaluator 决策（probe/next/enter_qa/end）
    qa_done: Optional[bool]                   # 反问环节是否已做


# ============================================================================
# 简历优化相关状态（扩展）
# ============================================================================

class ResumeOptimizeState(TypedDict):
    """
    简历优化专用状态（路径 A 自动生成 + 路径 B 人机协同精修）。

    路径 A 同构 jd_match（流水线：prepare→generate→evaluate→validate→export→persist），
    路径 B 同构 mock-interview（interrupt + checkpointer 长程会话）。
    Phase 3 先实现路径 A；路径 B 相关字段（resume_mode / refine / awaiting_resume_feedback）预留。
    """

    # --- 输入 ---
    target_position: Optional[str]                      # 目标岗位
    jd_result_id: Optional[str]                         # 关联的 JD 匹配结果 ID（可空）
    gaps_snapshot: Optional[List[Dict[str, Any]]]       # Gap 清单快照（生成中保持一致）
    profile_snapshot: Optional[Dict[str, Any]]          # 画像快照

    # --- 生成与评估 ---
    resume_md: Optional[str]                            # 当前 Markdown 草稿
    resume_html: Optional[str]                          # 渲染后 HTML（Phase 4 导出后填）
    resume_eval: Optional[Dict[str, Any]]               # 6 维评估报告
    resume_round: Optional[int]                         # 当前迭代轮次（生成次数，含评估/校验重试）
    resume_max_rounds: Optional[int]                    # 迭代上限（默认 3）

    # --- 导出与持久化 ---
    resume_theme: Optional[str]                         # 使用的主题
    resume_id: Optional[str]                            # 持久化的 resume 记录 ID
    resume_version: Optional[int]                       # 当前版本号
    resume_status: Optional[str]                        # draft / refining / finalized

    # --- 模式与控制（路径 B 用，Phase 3 预留）---
    resume_mode: Optional[str]                          # "auto"（路径 A）/ "refine"（路径 B）
    resume_finalize_signal: Optional[bool]              # 路径 B：用户确认定稿信号（route 据此 → finalize）
    resume_user_feedback: Optional[str]                 # 路径 B 用户反馈
    resume_refine_offered: Optional[bool]               # 路径 A 完成后是否提供精修入口
    awaiting_resume_feedback: Optional[bool]            # 路径 B interrupt 标志
    resume_status_code: Optional[str]                   # success / profile_missing / gaps_missing / llm_failed / error


# ============================================================================
# 组合状态（完整状态）
# ============================================================================

class FullAgentState(AgentState, ResumeParseState, JdMatchState, MockInterviewState, ResumeOptimizeState):
    """
    完整的 Agent 状态（基础 + 简历解析 + JD 匹配 + 模拟面试）

    用途：支持所有功能的完整状态机
    """

    pass


# ============================================================================
# 状态辅助函数
# ============================================================================

def create_initial_state(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    创建初始状态

    Args:
        user_id: 用户 ID（可选）

    Returns:
        initial_state: 初始状态字典
    """
    return {
        "messages": [],
        "user_id": user_id,
        "current_step": None,
        "intent": None,
        "error": None,
        # 简历解析相关
        "resume_source": None,
        "resume_file_path": None,
        "resume_text": None,
        "resume_file_name": None,
        "user_profile": None,
        "profile_confidence": None,
        "profile_quality_score": None,
        "parse_status": None,
        "parse_warnings": None,
        "parse_error": None,
        "awaiting_confirmation": None,
        "user_confirmed": None,
        # JD 匹配相关
        "jd_text": None,
        "job_profile": None,
        "match_result": None,
        "gaps": None,
        "match_confidence": None,
        "match_status": None,
        "result_id": None,
        # 模拟面试相关（reducer 字段用 []，其余 None）
        "session_id": None,
        "interview_status": None,
        "interview_mode": None,
        "interview_type": None,
        "intensity": None,
        "profile_snapshot": None,
        "jd_result_id": None,
        "job_profile_snapshot": None,
        "gaps_snapshot": None,
        "persona": None,
        "question_bank": None,
        "question_plan": None,
        "current_q_idx": None,
        "questions_asked": [],
        "current_q_probes": None,
        "transcript": [],
        "running_scores": None,
        "highlights": [],
        "weaknesses": [],
        "retrieved_company_qs": None,
        "retrieved_episodes": None,
        "debrief_report": None,
        "debrief_id": None,
        "awaiting_answer": None,
        # 模拟面试控制流
        "current_round": None,
        "current_decision": None,
        "qa_done": None,
        # 简历优化相关
        "target_position": None,
        "jd_result_id": None,
        "gaps_snapshot": None,
        "profile_snapshot": None,
        "resume_md": None,
        "resume_html": None,
        "resume_eval": None,
        "resume_round": 0,
        "resume_max_rounds": 3,
        "resume_theme": None,
        "resume_id": None,
        "resume_version": None,
        "resume_status": None,
        "resume_mode": "auto",
        "resume_finalize_signal": False,
        "resume_user_feedback": None,
        "resume_refine_offered": False,
        "awaiting_resume_feedback": None,
        "resume_status_code": None,
    }


def reset_resume_parse_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    重置简历解析相关状态

    Args:
        state: 当前状态

    Returns:
        updated_state: 更新后的状态
    """
    state.update({
        "resume_source": None,
        "resume_file_path": None,
        "resume_text": None,
        "resume_file_name": None,
        "user_profile": None,
        "profile_confidence": None,
        "profile_quality_score": None,
        "parse_status": None,
        "parse_warnings": None,
        "parse_error": None,
        "awaiting_confirmation": None,
        "user_confirmed": None,
    })
    return state


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LangGraph State 定义测试")
    print("=" * 60)

    # 测试创建初始状态
    print("\n[TEST] 创建初始状态")
    initial_state = create_initial_state(user_id="test_user")
    print(f"✓ 初始状态创建成功")
    print(f"  - user_id: {initial_state['user_id']}")
    print(f"  - messages: {initial_state['messages']}")
    print(f"  - resume_source: {initial_state['resume_source']}")

    # 测试重置状态
    print("\n[TEST] 重置简历解析状态")
    state = create_initial_state()
    state['resume_source'] = 'file'
    state['resume_text'] = 'test text'
    print(f"  重置前: resume_source={state['resume_source']}, resume_text={state['resume_text']}")
    reset_resume_parse_state(state)
    print(f"  重置后: resume_source={state['resume_source']}, resume_text={state['resume_text']}")

    print("\n" + "=" * 60)
