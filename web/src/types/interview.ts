/**
 * 模拟面试相关类型（与后端 /api/interview/* 响应对齐）
 *
 * 契约来源：backend/src/api/interview.py + graph/nodes/mock_interview.py
 * 字段命名严格对齐后端 snake_case。
 */

// ===== 枚举联合 =====

/** 面试类型（6 种） */
export type InterviewType = 'behavioral' | 'technical' | 'case' | 'motivation' | 'full' | 'stress'

/** 档位（语义化，去时间隐喻） */
export type Intensity = 'short' | 'normal' | 'deep' | 'full'

/**
 * 档位 key→label 映射。
 * 后端响应不返回 label，前端自维护（设计决策 6：语义化档位，不显示分钟）。
 */
export const INTENSITY_LABELS: Record<Intensity, string> = {
  short: '简短',
  normal: '正常',
  deep: '深度',
  full: '全程',
}

/** 档位副标题（题数 + 反问，用于配置页卡片说明） */
export const INTENSITY_SUBTITLES: Record<Intensity, string> = {
  short: '3 题 · 浅问 · 无反问',
  normal: '5 题 · 中问 · 可反问',
  deep: '7 题 · 深挖 · 含反问',
  full: '8 题 · 全流程 · 含反问',
}

/** 面试模式：real=实战（不实时评分）/ coach=教练（每轮给改进提示） */
export type InterviewMode = 'real' | 'coach'

/** 会话对外状态（profile_missing/finishing 仅 LangGraph 内部短暂出现，不落 DB） */
export type SessionStatus = 'interviewing' | 'paused' | 'finished' | 'error'

/** 题型分类 */
export type QuestionCategory = 'behavioral' | 'technical' | 'case' | 'motivation'

/** 本轮决策动作（evaluator 产出） */
export type RoundAction = 'probe' | 'next' | 'enter_qa' | 'end'


// ===== 核心结构 =====

/**
 * 面试官人设（前端组装 4 字段传入 CreateSessionRequest.persona）。
 * 后端 prompts.get_followup_prompt 消费全部 4 字段。
 */
export interface Persona {
  tone: string                         // 风格：专业/严肃/轻松/风趣/温和/压力
  role: {
    company?: string
    position?: string
  }
  stress_mode: boolean                 // 压力面开关（选"压力"tone 时 true）
  style_prompt: string                 // 自由文本风格描述
}

/**
 * 一次提问（first_question / next_question / pending_question 通用结构）。
 * qid === 'qa' 表示进入反问环节。
 */
export interface Question {
  question: string
  round: number
  is_probe: boolean
  qid: string
}

/** 评估结果（evaluator 信号差检测产出） */
export interface Evaluation {
  hit_signals: string[]
  miss_signals: string[]
  miss_probe_map: Record<string, string>  // 缺失信号 → 可挖掘点（追问方向）
  score: number                            // 0-100，降级时恒 70
  highlight: string | null
  weakness: string | null
}

/** 一轮对话记录（transcript 条目） */
export interface TranscriptItem {
  round: number
  question: string
  answer: string
  qid: string
  is_probe: boolean
  evaluation: Evaluation
  action: RoundAction
}

/** 逐题改进范例（复盘 LLM 产出，基于候选人【自身经历】改写，非标准答案） */
export interface RoundReview {
  round: number
  better_version: string
  improvement_point: string
}

/** 复盘报告（debrief 端点返回的 data.debrief） */
export interface DebriefReport {
  overview: {
    avg_score: number | null
    total_rounds: number
    one_line_summary: string          // LLM 失败时为空串（基础复盘兜底）
  }
  round_by_round: TranscriptItem[]    // 对话回放
  round_reviews: RoundReview[]        // 逐题改进（LLM 失败时空数组）
  inappropriate_answers: string[]     // 字符串数组（每条含轮次说明）
  stuck_points: string[]
  next_steps: string[]                // 可执行建议（非空话）
  highlights: string[]
  weaknesses: string[]
}


// ===== 会话 =====

/** 会话摘要（list 与 detail 共用） */
export interface SessionSummary {
  id: string
  status: SessionStatus
  interview_type?: string | null
  intensity?: string | null
  interview_mode?: string | null
  jd_result_id?: string | null
  avg_score?: number | null
  total_rounds?: number | null
  created_at: string
  finished_at?: string | null
}

/** 会话详情（detail 端点，含运行时 transcript + pending_question） */
export interface SessionDetail extends SessionSummary {
  transcript?: TranscriptItem[]
  pending_question?: Question | null
}


// ===== 请求/响应 =====

/** POST /sessions 请求体 */
export interface CreateSessionRequest {
  user_id: string
  interview_type?: InterviewType      // 默认 'full'
  intensity?: Intensity               // 默认 'normal'
  interview_mode?: InterviewMode      // 默认 'real'
  jd_result_id?: string               // 可选：关联 JD 匹配结果；不传=通用面试
  persona?: Persona
}

/** POST /sessions 响应 data */
export interface CreateSessionResponse {
  session_id: string
  interview_status: 'interviewing' | 'profile_missing'
  first_question: Question | null
  detail_warning?: string | null      // 画像经历不足时的软警告（非阻断，前端 toast）
}

/**
 * POST /answer 响应（多态：按 interview_status 分支）。
 * - interviewing：继续，渲染 next_question；coach 模式可能有 coach_hint
 * - finished：面试结束，跳复盘
 */
export type SubmitAnswerResponse =
  | { interview_status: 'interviewing'; next_question: Question | null; coach_hint?: string | null }
  | { interview_status: 'finished'; debrief_id: string; total_rounds: number; avg_score: number | null }

/** GET /debrief 响应 data */
export interface DebriefResponse {
  session_id: string
  debrief: DebriefReport
  avg_score: number | null
  total_rounds: number | null
}

/** GET /sessions（列表）响应 data */
export interface SessionListResponse {
  items: SessionSummary[]
}
