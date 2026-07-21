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
 * 提交 JD 执行匹配
 *
 * timeout 放宽到 90 秒：后端要串行跑 3 类 LLM 调用
 * （JD 结构化解析 + 隐性偏好判断 + Gap 建议生成），通常 15-30 秒。
 */
export async function matchJd(data: { jd_text: string; user_id?: string }) {
  return await client.post('/jd/match', data, { timeout: 90000 })
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
