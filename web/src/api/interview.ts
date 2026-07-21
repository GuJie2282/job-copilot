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
 * timeout 90s：后端 session_setup 要出题（LLM）+ 可选 RAG 检索，通常 5-15s，留足余量。
 */
export async function createSession(data: CreateSessionRequest) {
  return await client.post('/interview/sessions', data, { timeout: 90000 })
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
