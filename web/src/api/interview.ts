/**
 * 模拟面试 API
 *
 * 对应后端 /api/interview/*：
 * - POST /sessions               创建会话（session_setup 出题，LLM 慢）
 * - POST /sessions/:id/answer    提交回答（多态响应：继续 / 结束）
 * - GET  /sessions/:id           查状态 + transcript（续面用）
 * - GET  /sessions/:id/debrief   获取复盘报告
 * - GET  /sessions?user_id=      历史会话列表（后端写死 50 条上限）
 *
 * 与 jd.ts 一致：不绑定严格响应泛型（client 响应拦截器已剥壳返回后端响应体），
 * 调用方按 res.status === 'success' && res.data 访问。
 */
import client from './client'
import type { CreateSessionRequest } from '@/types/interview'

/**
 * 创建面试会话。
 * timeout 180s：后端 session_setup 出题走 strong 档（glm-4.5），实测单次 ~62s + RAG 检索，
 * 总耗时常 70-85s，偶发逼近/超过原 90s 超时导致「请求失败」。放宽到 180s 覆盖单次出题 + 余量。
 * 根治方案：出题降档 strong→fast（见 evolve-interview-pacing 之外的优化，待定）。
 */
export async function createSession(data: CreateSessionRequest) {
  return await client.post('/interview/sessions', data, { timeout: 180000 })
}

/**
 * 提交回答（多态响应：interviewing 继续 / finished 结束）。
 * timeout 60s：evaluator 信号差检测 + 可能的追问生成。
 */
export async function submitAnswer(sessionId: string, answer: string) {
  return await client.post(`/interview/sessions/${sessionId}/answer`, { answer }, { timeout: 60000 })
}

/** 查会话状态 + transcript（续面 / 查看进度） */
export async function getSession(sessionId: string) {
  return await client.get(`/interview/sessions/${sessionId}`)
}

/** 获取复盘报告（timeout 30s：详细复盘 LLM 可能稍慢） */
export async function getDebrief(sessionId: string) {
  return await client.get(`/interview/sessions/${sessionId}/debrief`, { timeout: 30000 })
}

/** 历史会话列表（按用户，时间倒序） */
export async function listSessions(userId: string) {
  return await client.get('/interview/sessions', { params: { user_id: userId } })
}

/**
 * 语音转文本（add-voice-interview：语音回答模式）。
 * 上传录音 Blob → 后端 faster-whisper 转写 → 返回文本。
 * 前端拿到文本后，以 answer 调 submitAnswer，与文字模式汇合（零侵入）。
 *
 * timeout 30s：后端 small 模型 CPU 转写 15-30s 录音约 4-8s，留足余量。
 *
 * 响应是后端 ApiResponse：成功 {status:'success', data:{text}}，
 * 失败 {status:'error', data:{error_code}}（error_code 供前端区分降级提示）。
 */
export async function transcribeVoice(blob: Blob) {
  const form = new FormData()
  // 文件名仅辅助后端取扩展名，faster-whisper 经 PyAV 按内容识别格式
  form.append('file', blob, 'answer.webm')
  return await client.post('/interview/voice/transcribe', form, { timeout: 30000 })
}
