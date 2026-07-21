/**
 * 面经库相关类型（与后端 /api/knowledge/* 响应对齐）
 * 隐私：公司库类型已剔除 contributor_id / embedding_json（后端 _company_public）。
 */

/** 个人面经条目（per-user 私有） */
export interface PersonalEpisode {
  id: string
  position?: string | null
  company?: string | null
  category?: string | null
  question: string
  my_answer?: string | null
  score?: number | null
  better_version?: string | null
  happened_at?: string | null
  source: string  // 固定 'personal'
}

/** 公司面经条目（全局共享，已脱敏） */
export interface CompanyQuestion {
  id: string
  company?: string | null
  position?: string | null
  category?: string | null
  question: string
  context?: string | null
  source: 'curated' | 'ugc' | 'llm_generated'
}

/** 公司库 facets（侧边导航） */
export interface CompanyFacets {
  companies: string[]
  positions: string[]
}

/** 来源标签映射（来源透明展示——spec 数据治理） */
export const SOURCE_LABELS: Record<string, string> = {
  curated: '精选真题',
  ugc: '用户贡献',
  llm_generated: 'AI 拟题',
  personal: '个人历史',
}

/** 来源 pill 配色类（curated > ugc > llm_generated 视觉区分） */
export function sourceClass(source: string): string {
  if (source === 'curated') return 'src-curated'
  if (source === 'ugc') return 'src-ugc'
  if (source === 'llm_generated') return 'src-llm'
  return 'src-personal'
}
