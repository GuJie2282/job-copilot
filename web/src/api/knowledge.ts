/**
 * 面经库 API
 *
 * 对应后端 /api/knowledge/*：
 * - GET    /personal            个人库列表/搜索（有 q 语义，无 q 分页）
 * - GET    /personal/weakness   历史低分题
 * - DELETE /personal/{id}       删单条（user_id 校验）
 * - DELETE /personal            清空全部
 * - GET    /company             公司库搜索
 * - GET    /company/facets      公司/岗位聚合
 * - POST   /company/ugc         UGC 贡献
 */
import client from './client'

/** 个人库列表/搜索 */
export async function listPersonal(params: {
  user_id: string
  q?: string
  position?: string
  company?: string
  category?: string
  offset?: number
  limit?: number
}) {
  return await client.get('/knowledge/personal', { params })
}

/** 历史低分题（复练弱项） */
export async function listWeakness(userId: string, limit = 5) {
  return await client.get('/knowledge/personal/weakness', { params: { user_id: userId, limit } })
}

/** 删除单条个人面经 */
export async function deletePersonalOne(id: string, userId: string) {
  return await client.delete(`/knowledge/personal/${id}`, { params: { user_id: userId } })
}

/** 清空个人面经库 */
export async function deletePersonalAll(userId: string) {
  return await client.delete('/knowledge/personal', { params: { user_id: userId } })
}

/** 公司库搜索 */
export async function searchCompany(params: {
  q?: string
  company?: string
  position?: string
  top_k?: number
}) {
  return await client.get('/knowledge/company', { params })
}

/** 公司库 facets（公司/岗位聚合） */
export async function companyFacets() {
  return await client.get('/knowledge/company/facets')
}

/** UGC 贡献面经 */
export async function contributeUgc(data: {
  user_id: string
  company?: string
  position?: string
  category?: string
  question: string
  context?: string
}) {
  return await client.post('/knowledge/company/ugc', data)
}
