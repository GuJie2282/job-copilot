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

/**
 * SSE 事件回调（match 端点流式输出）
 */
export interface MatchStreamHandlers {
  onStage?: (p: { message: string; node?: string }) => void
  onScore?: (p: {
    overall_score?: number
    level?: string
    dimension_scores?: { skill?: number; experience?: number; education?: number; soft_skill?: number }
    redline_hit?: boolean
    result_id?: string
  }) => void
  onDone?: (p: { result_id?: string; job_profile?: any; gaps?: any[] }) => void
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
  const controller = new AbortController()

  void (async () => {
    // SSE 直连后端（VITE_STREAM_BASE_URL），绕开 vite proxy——proxy 不流式转发 text/event-stream。
    // 未配置时回退到普通 API base（走 proxy，流式可能不工作但至少不报错）。
    const base = import.meta.env['VITE_STREAM_BASE_URL'] || import.meta.env.VITE_API_BASE_URL || ''
    const token = localStorage.getItem('token')
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    let resp: Response
    try {
      resp = await fetch(`${base}/jd/match`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
        signal: controller.signal,
      })
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      handlers.onError?.({ error_code: 'NETWORK', error_message: e?.message || '网络错误' })
      return
    }

    if (!resp.ok || !resp.body) {
      let message = `请求失败（${resp.status}）`
      try {
        const j = await resp.json()
        message = j?.message || message
      } catch { /* 非 JSON 错误体，保留默认文案 */ }
      handlers.onError?.({ error_code: 'HTTP_' + resp.status, error_message: message })
      return
    }

    // 手写 SSE 解析：流按 \n\n 切事件块，每块解析 event:/data: 行
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let sep = buffer.indexOf('\n\n')
        while (sep !== -1) {
          const evt = parseSse(buffer.slice(0, sep))
          buffer = buffer.slice(sep + 2)
          if (evt) dispatch(evt, handlers)
          sep = buffer.indexOf('\n\n')
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        handlers.onError?.({ error_code: 'STREAM', error_message: e?.message || '流读取中断' })
      }
    }
  })()

  return controller
}

/** 解析单个 SSE 事件块（event:/data: 行） */
function parseSse(raw: string): { event: string; data: any } | null {
  let event = 'message'
  let dataStr = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataStr += line.slice(5).trim()
  }
  if (!dataStr) return null
  try {
    return { event, data: JSON.parse(dataStr) }
  } catch {
    return null
  }
}

/** 把 SSE 事件分发到对应回调 */
function dispatch(evt: { event: string; data: any }, h: MatchStreamHandlers) {
  switch (evt.event) {
    case 'stage': h.onStage?.(evt.data); break
    case 'score': h.onScore?.(evt.data); break
    case 'done': h.onDone?.(evt.data); break
    case 'error': h.onError?.(evt.data); break
    default: break
  }
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
