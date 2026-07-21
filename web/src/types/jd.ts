/**
 * JD 匹配相关类型（与后端 /api/jd/* 响应对齐）
 */

/** JD 单条要求 */
export interface JdRequirement {
  requirement: string
  must_have?: boolean
  evidence?: string | null
  confidence?: number | null
}

/** JD 解析出的要求画像（四分类：硬技能/软技能/隐性偏好/红线项） */
export interface JobProfile {
  position_title?: string | null
  summary?: string | null
  hard_skills?: JdRequirement[]
  soft_skills?: JdRequirement[]
  implicit_preferences?: JdRequirement[]
  red_lines?: JdRequirement[]
}

/** 匹配明细项（可解释：含 JD 依据 + 画像依据 + 置信度） */
export interface MatchedItem {
  category: 'hard_skill' | 'soft_skill' | 'implicit' | 'redline' | 'experience' | 'education'
  requirement?: string
  must_have?: boolean
  status: 'satisfied' | 'partial' | 'missing'
  jd_evidence?: string | null
  profile_evidence?: string | null
  need_confirm?: boolean
}

/** 差距项（Gap 四分类，简历优化模块的输入契约） */
export interface Gap {
  type: 'hard_skill' | 'soft_skill' | 'implicit' | 'redline'
  requirement?: string
  current_state?: string
  status?: string
  suggestion?: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  need_confirm?: boolean
}

/** 匹配结果（match 接口返回的 data） */
export interface MatchResult {
  result_id?: string | null
  overall_score?: number
  level?: string
  dimension_scores?: {
    skill?: number
    experience?: number
    education?: number
    soft_skill?: number
  }
  redline_hit?: boolean
  job_profile?: JobProfile
  gaps?: Gap[]
}

/** 匹配详情（results/{id} 接口返回的 data，比 match 多原始 JD 与置信度） */
export interface MatchDetail extends MatchResult {
  id?: string
  user_id?: string
  jd_text?: string
  confidence?: any
  created_at?: string
}

/** 历史匹配项 */
export interface MatchHistoryItem {
  id: string
  overall_score?: number
  dimension_scores?: Record<string, number>
  position_title?: string | null
  created_at?: string | null
}
