/**
 * 简历解析 API
 */

import client from './client'

/**
 * 解析文件
 */
export async function parseFile(formData: FormData) {
  // ⚠️ 不要手动设置 Content-Type：axios 传 FormData 时会自动加上带 boundary 的请求头，
  //    手动设置反而会丢失 boundary，导致后端无法解析 multipart 请求体（文件上传失败）。
  // ⚠️ timeout 放宽到 180 秒：文件解析要走 LLM 提取画像，长简历 + 详情字段提取 glm-4-flash
  //    可能要 60-120 秒，后端 LLM 超时设的 120s，前端要比后端略大并留余量，
  //    否则会在后端还在跑时就超时断开，让用户误以为功能坏了。
  const response = await client.post('/resume/parse-file', formData, {
    timeout: 180000
  })
  return response
}

/**
 * 解析文本
 */
export async function parseText(data: {
  text: string
  user_id?: string
}) {
  const response = await client.post('/resume/parse-text', data, {
    timeout: 180000  // 同 parseFile：文本解析也要走 LLM 提取，耗时较长
  })
  return response
}

/**
 * LLM 提取
 */
export async function extractProfile(data: {
  text: string
  quality_score: number
  is_retry: boolean
}) {
  const response = await client.post('/resume/extract', data, {
    timeout: 180000  // 同 parseFile：LLM 提取耗时较长
  })
  return response
}

/**
 * 更新画像
 */
export async function updateProfile(data: {
  user_id?: string
  profile: any
}) {
  const response = await client.post('/resume/update-profile', data)
  return response
}

/**
 * 获取画像
 */
export async function getProfile(userId?: string) {
  const response = await client.get('/resume/profile', {
    params: { user_id: userId }
  })
  return response
}

/**
 * 导出画像
 */
export async function exportProfile(userId?: string, format: 'json' | 'markdown' = 'json') {
  const response = await client.get('/resume/export-profile', {
    params: {
      user_id: userId,
      format
    }
  })
  return response
}

/**
 * 删除画像
 */
export async function deleteProfile(userId?: string) {
  const response = await client.delete('/resume/profile', {
    params: { user_id: userId }
  })
  return response
}

/**
 * 获取示例简历
 */
export async function getSampleResumes() {
  const response = await client.get('/resume/sample-resumes')
  return response
}

/**
 * 健康检查
 */
export async function healthCheck() {
  const response = await client.get('/resume/health')
  return response
}
