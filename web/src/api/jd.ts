/**
 * JD 匹配 API
 *
 * 对应后端 /api/jd/*：
 * - POST /api/jd/match        提交 JD 执行匹配
 * - GET  /api/jd/history      查询历史匹配
 * - GET  /api/jd/results/:id  查看匹配详情
 *
 * 与 resume.ts 保持一致：不绑定严格响应泛型（client 响应拦截器返回后端响应体），
 * 调用方按后端实际字段（status / message / data）访问。
 */
import client from './client'
import { openSseStream } from '@/utils/sse'

/**
 * SSE 事件回调（match 端点流式输出）
 */
export interface MatchStreamHandlers {
  onStage?: (p: { message: string; node?: string }) => void
  onReasoning?: (p: { delta: string }) => void
  onScore?: (p: {
    overall_score?: number
    level?: string
    dimension_scores?: { skill?: number; experience?: number; education?: number; soft_skill?: number }
    redline_hit?: boolean
    result_id?: string
  }) => void
  onDone?: (p: { result_id?: string; job_profile?: any; gaps?: any[] }) => void
  /** 增补完成（Gap 含隐性判断 + 建议；degraded=true 表示降级为模板建议） */
  onEnriched?: (p: { gaps: any[]; degraded?: boolean }) => void
  onError?: (p: { error_code: string; error_message: string }) => void
}

/**
 * 提交 JD 执行匹配（SSE 流式：阶段进度 → 分数 → 规则 Gap 骨架）。
 *
 * 用原生 fetch + ReadableStream 手写 SSE 解析：match 是 POST（jd_text 长），
 * 而 EventSource 仅支持 GET，故不能用 EventSource。返回 AbortController 供取消。
 * 持续接收事件即保持连接活跃，不再有 90s 超时墙。
 */
export function matchJd(
  data: { jd_text: string; user_id?: string },
  handlers: MatchStreamHandlers,
): AbortController {
  // 复用公共 SSE 封装（fetch + ReadableStream 手写解析），逻辑见 src/utils/sse.ts。
  // 持续接收事件即保持连接活跃，不再有同步请求的超时墙。
  return openSseStream('/jd/match', data, handlers)
}

/**
 * Gap 增补（lazy）：补全隐性偏好判断 + Gap 建议。
 * 评分链已秒出分数与规则骨架；此处补 LLM 增补。超时放宽到 60s（2 段 strong 档 LLM）。
 */
export async function enrichGaps(resultId: string, data: { user_id?: string }) {
  return await client.post(`/jd/${resultId}/enrich`, data, { timeout: 60000 })
}

/**
 * 查询当前用户的历史匹配（时间倒序）
 */
export async function matchHistory(userId: string) {
  return await client.get('/jd/history', { params: { user_id: userId } })
}

/**
 * 查看某次匹配详情
 */
export async function matchDetail(resultId: string) {
  return await client.get(`/jd/results/${resultId}`)
}
