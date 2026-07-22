/**
 * 简历优化相关类型（与后端 /api/resume/* 响应对齐）
 *
 * Gap 类型复用 types/jd.ts（简历优化的输入契约就是 JD 匹配的 Gap 清单）。
 */
import type { Gap } from './jd'

/** 6 维评估的单个检查项 */
export interface EvalCheckItem {
  check: string
  result: 'pass' | 'fail' | 'partial'
  note?: string | null
}

/** 一个评估维度 */
export interface EvalDimension {
  score: number
  weight: number
  passed: boolean
  items: EvalCheckItem[]
}

/** 改进优先级条目 */
export interface FeedbackPriority {
  priority: 'high' | 'medium' | 'low'
  suggestion: string
}

/**
 * 6 维评估报告（对应后端 ResumeEvalReport）
 * 维度 key：basic_norm / jd_match / quantification / structure / differentiation / language
 * format_validation：格式校验结果（resume_validator 产出，并入此结构）
 */
export interface ResumeEvalReport {
  overall_score?: number
  passed?: boolean
  dimensions?: Record<string, EvalDimension>
  feedback_priorities?: FeedbackPriority[]
  format_validation?: {
    passed: boolean
    errors: string[]
    warnings: string[]
  }
}

/** 简历记录（list / detail / generate 返回的 data） */
export interface Resume {
  id: string
  user_id?: string
  target_position: string
  version?: number
  status?: 'draft' | 'refining' | 'finalized'
  theme?: string | null
  content_md?: string | null
  html?: string | null
  eval_report?: ResumeEvalReport | null
  eval_score?: number | null
  jd_result_id?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** 生成请求（POST /api/resume/generate） */
export interface GenerateResumeRequest {
  target_position: string
  jd_result_id?: string
  gaps?: Gap[]
  user_id?: string
}

/** 精修请求（POST /api/resume/{id}/refine） */
export interface RefineResumeRequest {
  user_id: string
  feedback?: string
}

/** 精修 interrupt 响应的 data */
export interface RefinePendingData {
  status: 'awaiting_feedback'
  resume_md?: string
  eval_report?: ResumeEvalReport | null
  round?: number
  pending_hints?: string[]
}
