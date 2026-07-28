/**
 * SSE 公共消费封装（对应 change add-streaming-pipeline 任务 1.2.1）。
 *
 * 用原生 fetch + ReadableStream 手写 SSE 解析（零依赖）：
 * - POST + Authorization 鉴权头（浏览器原生 EventSource 仅支持 GET 且不便带自定义头，不可用）
 * - 按 \n\n 切事件块，每块解析 event:/data: 行（注释行如心跳 : keepalive 忽略）
 * - 流式端点直连后端（VITE_STREAM_BASE_URL），绕开 vite dev proxy（proxy 不转发 text/event-stream）
 * - 返回 AbortController，调用方可随时取消
 *
 * 三模块（简历解析 / 简历优化 / JD 匹配）共用。
 */

/** SSE 事件回调：按 event 类型分发，只需提供关心的回调（其余可省略） */
export interface SseHandlers {
  /** 阶段进度 */
  onStage?: (p: { message: string; node?: string }) => void
  /** 分段中间结果（结构化任务，如画像的一段） */
  onSegment?: (p: { section: string; data: any; confidence?: any }) => void
  /** 增量文本内容（自由文本任务，如简历生成） */
  onToken?: (p: { delta: string }) => void
  /** AI 思考过程（glm-4.5 的 reasoning_content 思考 token） */
  onReasoning?: (p: { delta: string }) => void
  /** 评分（JD 匹配） */
  onScore?: (p: any) => void
  /** 任务完成（最终结果） */
  onDone?: (p: any) => void
  /** 增补完成（JD 匹配） */
  onEnriched?: (p: { gaps: any[] }) => void
  /** 失败 */
  onError?: (p: { error_code: string; error_message: string }) => void
}

/**
 * 打开一条 SSE 流：POST body 到 url，按 handlers 分发事件。
 *
 * @param url      API 路径（如 '/jd/match'，会拼到 VITE_STREAM_BASE_URL 后面）
 * @param body     请求体（POST，会被 JSON.stringify）
 * @param handlers 事件回调
 * @returns AbortController（调 .abort() 取消任务；取消时不触发 onError）
 */
export function openSseStream(
  url: string,
  body: unknown,
  handlers: SseHandlers,
): AbortController {
  const controller = new AbortController()

  void (async () => {
    // SSE 直连后端（VITE_STREAM_BASE_URL），绕开 vite proxy——proxy 不流式转发 text/event-stream。
    // 未配置时回退到普通 API base（走 proxy，流式可能不工作但至少不报错，便于降级）。
    const base = import.meta.env['VITE_STREAM_BASE_URL'] || import.meta.env.VITE_API_BASE_URL || ''
    const token = localStorage.getItem('token')
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    let resp: Response
    try {
      resp = await fetch(`${base}${url}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
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
      } catch {
        /* 非 JSON 错误体，保留默认文案 */
      }
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

/** 解析单个 SSE 事件块（event:/data: 行；注释行如 : keepalive 忽略） */
function parseSse(raw: string): { event: string; data: any } | null {
  let event = 'message'
  let dataStr = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataStr += line.slice(5).trim()
    // 以 : 开头的注释行（保活心跳）忽略
  }
  if (!dataStr) return null
  try {
    return { event, data: JSON.parse(dataStr) }
  } catch {
    return null
  }
}

/** 按 event 类型分发到 handlers 对应回调 */
function dispatch(evt: { event: string; data: any }, h: SseHandlers) {
  switch (evt.event) {
    case 'stage': h.onStage?.(evt.data); break
    case 'segment': h.onSegment?.(evt.data); break
    case 'token': h.onToken?.(evt.data); break
    case 'reasoning': h.onReasoning?.(evt.data); break
    case 'score': h.onScore?.(evt.data); break
    case 'done': h.onDone?.(evt.data); break
    case 'enriched': h.onEnriched?.(evt.data); break
    case 'error': h.onError?.(evt.data); break
    default: break
  }
}
