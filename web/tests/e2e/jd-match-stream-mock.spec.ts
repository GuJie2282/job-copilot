/**
 * JD 匹配流式前端（mock 后端，确定性）
 * ===================================
 *
 * 后端 SSE 机制已由 API 层（httpx 实测 stage/score/done）证明；本 spec 用 Playwright
 * route 把 /api/jd/match（SSE）与 /api/jd/{id}/enrich mock 成预制响应，**脱离 GLM 抖动**
 * 确定性验证前端的：SSE 手写解析 → 分数先出（hero）→ 规则骨架（隐性"分析中"）→ enrich 回填。
 *
 * 运行：cd web && npx playwright test jd-match-stream-mock
 */
import { test, expect, type Route } from '@playwright/test'

const EMAIL = 'e2e@test.com'
const PASSWORD = 'Test1234!'

const JD_TEXT = '岗位：AI 产品经理\n【岗位职责】\n1. 负责 AI 产品规划。\n【任职要求】\n1. 本科及以上；\n2. 熟练 Axure、SQL；\n3. 熟悉 LangChain、RAG 者优先；\n4. 大厂背景优先。'

// 预制 SSE 流：3 个 stage → score（分数先出）→ done（规则骨架，隐性"分析中"）
const SSE_BODY = [
  'event: stage\ndata: {"message":"正在解析 JD 要求…","node":"jd_parsing"}',
  'event: stage\ndata: {"message":"正在加载你的画像…","node":"profile_load"}',
  'event: stage\ndata: {"message":"正在比对匹配度…","node":"match_calc"}',
  'event: score\ndata: {"overall_score":68,"level":"部分匹配","dimension_scores":{"skill":60,"experience":70,"education":90,"soft_skill":50},"redline_hit":false,"result_id":"mock-res-1"}',
  'event: done\ndata: {"result_id":"mock-res-1","job_profile":{"position_title":"AI 产品经理","hard_skills":[{"requirement":"熟悉 LangChain、RAG"}],"soft_skills":[],"implicit_preferences":[{"requirement":"大厂背景"}],"red_lines":[]},"gaps":[{"type":"hard_skill","requirement":"熟悉 LangChain、RAG","current_state":"画像中未体现","status":"missing","severity":"high","suggestion":"用 STAR 法则补充相关项目经历，强调量化成果。"},{"type":"implicit","requirement":"大厂背景","current_state":"分析中…","status":"分析中","severity":"medium","suggestion":null}]}',
].join('\n\n') + '\n\n'

// enrich 回填：隐性 gap 状态从"分析中"→"missing"，补上建议
const ENRICH_BODY = {
  status: 'success',
  message: '增补完成',
  data: {
    gaps: [
      { type: 'hard_skill', requirement: '熟悉 LangChain、RAG', current_state: '画像中未体现', status: 'missing', severity: 'high', suggestion: '用 STAR 法则补充你做过的 RAG 检索增强项目，强调召回率提升 20%。' },
      { type: 'implicit', requirement: '大厂背景', current_state: '无大厂经历，但有高复杂度项目可类比对冲。', status: 'missing', severity: 'medium', suggestion: '挖掘高影响力项目对冲——突出你独立从 0 到 1 的经历。' },
    ],
  },
}

test('JD 匹配前端：SSE 解析 → 分数优先 → 骨架 → enrich 回填（mock）', async ({ page }) => {
  // mock SSE match 端点（直连 8001 或走 proxy 都用 **/ 兜住）
  await page.route('**/api/jd/match', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: { 'cache-control': 'no-cache' },
      body: SSE_BODY,
    })
  })
  // mock enrich 端点（延迟 1.5s，好让测试捕捉到骨架态→回填态的过渡）
  await page.route('**/api/jd/*/enrich', async (route: Route) => {
    await new Promise((r) => setTimeout(r, 1500))
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ENRICH_BODY) })
  })

  await page.goto('/login')
  await page.getByPlaceholder('you@example.com').fill(EMAIL)
  await page.getByPlaceholder('至少 6 位').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL(/\/(profile|jd-matcher|interview|)$/, { timeout: 15_000 })

  await page.goto('/jd-matcher')
  await page.locator('#jd').fill(JD_TEXT)
  await page.getByRole('button', { name: '开始匹配' }).click()

  // ── 分数 hero 先出 ──
  await expect(page.locator('.overall-score')).toHaveText('68', { timeout: 15_000 })
  await expect(page.locator('.overall-level')).toHaveText('部分匹配')
  await page.screenshot({ path: '.verify/mock-01-score.png', fullPage: false })

  // ── 规则骨架：隐性 gap 显示"分析中"（done 事件带骨架）──
  await expect(page.locator('.gap-item')).toHaveCount(2, { timeout: 10_000 })
  const implicitRow = page.locator('.gap-item', { hasText: '大厂背景' })
  await expect(implicitRow).toContainText('分析中')
  await expect(implicitRow).toContainText('正在生成建议') // suggestion=null 的占位
  await page.screenshot({ path: '.verify/mock-02-skeleton.png', fullPage: true })

  // ── enrich 回填：隐性状态脱离"分析中"、建议不再是占位 ──
  await expect(implicitRow).not.toContainText('分析中', { timeout: 15_000 })
  await expect(implicitRow).not.toContainText('正在生成建议')
  await expect(implicitRow).toContainText('对冲')
  await page.screenshot({ path: '.verify/mock-03-enriched.png', fullPage: true })
})
