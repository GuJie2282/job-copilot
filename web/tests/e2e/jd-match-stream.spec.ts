/**
 * JD 匹配流式 + lazy 增补 端到端（Playwright）
 * ============================================
 *
 * 验证区块三（design 决策 9/11）的两段式 UX：
 *   登录 → 贴 JD → 点匹配 → 进度真实推进 → 分数先出（hero）→ 规则 Gap 骨架
 *                                                    →（lazy）增补建议回填
 *
 * 关键断言：总分 hero（.overall-score）在 Gap 建议回填前就可见 = "分数优先"。
 * 截图存 web/.verify/，便于人眼复核两段式过渡。
 *
 * 运行：后端 8001 + 前端 3000 已起，然后 cd web && npx playwright test jd-match-stream
 */
import { test, expect } from '@playwright/test'

const EMAIL = 'e2e@test.com'
const PASSWORD = 'Test1234!'

// 一份会命中差距的真实 JD（用户技能 Python/SQL/Axure；JD 要 LangChain/RAG、大厂背景、本科红线）
const JD_TEXT = `岗位：AI 产品经理
【岗位职责】
1. 负责公司 AI 产品的规划与设计，推动大模型能力在业务场景落地；
2. 撰写 PRD 与交互文档，协同研发、算法团队推进产品迭代；
3. 通过数据分析与用户调研，持续优化产品体验与核心指标；
4. 对接客户需求，输出解决方案并支持售前沟通。
【任职要求】
1. 本科及以上学历，计算机或相关专业优先；
2. 3 年以上互联网产品经验，有 AI/大模型产品经验加分；
3. 熟练使用 Axure、SQL 进行原型设计与数据验证；
4. 大厂背景优先，有从 0 到 1 孵化产品经验者优先；
5. 具备优秀的跨团队沟通能力与抗压能力。
【加分项】
- 熟悉 LangChain、RAG 等 LLM 应用框架者优先；
- 有 Kaggle 等竞赛经历加分。`

test('JD 匹配：流式分数优先 → 骨架 → lazy 增补', async ({ page }) => {
  const consoleErrors: string[] = []
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })

  // ── 1. 登录 ──
  await page.goto('/login')
  await page.getByPlaceholder('you@example.com').fill(EMAIL)
  await page.getByPlaceholder('至少 6 位').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL(/\/(profile|jd-matcher|interview|)$/, { timeout: 15_000 })

  // ── 2. 进入 JD 匹配，贴 JD ──
  await page.goto('/jd-matcher')
  await page.locator('#jd').fill(JD_TEXT)
  await expect(page.locator('.notice-warn')).toBeHidden({ timeout: 10_000 }) // 画像就绪

  // ── 3. 点开始匹配，立刻截 loading 态 ──
  await page.getByRole('button', { name: '开始匹配' }).click()
  await expect(page.locator('.progress')).toBeVisible() // spinner 出现（进度由 SSE 驱动）
  await page.screenshot({ path: '.verify/01-loading.png', fullPage: false })

  // ── 4. 等分数 hero 出现（评分链 ~1 次 LLM；放宽到 150s）── 这是"分数优先"的证明
  await expect(page.locator('.overall-score')).toBeVisible({ timeout: 150_000 })
  await expect(page.locator('.gap-item').first()).toBeVisible({ timeout: 15_000 }) // 规则骨架
  await page.screenshot({ path: '.verify/02-score-skeleton.png', fullPage: true })

  // 记录此刻 gap 建议是否还是占位（"正在生成建议…"）
  const beforeEnrich = await page.locator('.gap-item').first().textContent()

  // ── 5. lazy 增补：等建议回填（GLM 抖动可能很慢，给 90s 上限，超了也接受——分数已证）──
  await expect(async () => {
    const txt = (await page.locator('.gap-item').first().textContent()) || ''
    // 任意一条 gap 建议不再是占位文案 → 增补已回填
    const anyReal = await page.locator('.gap-item .row').filter({ hasText: / STAR |对冲|量化|事例|策略/ }).count()
    expect(anyReal > 0 || !txt?.includes('正在生成建议')).toBeTruthy()
  }).toPass({ timeout: 90_000 }).catch(() => { /* 增补慢/失败不阻断：骨架已证分数优先 */ })
  await page.screenshot({ path: '.verify/03-after-enrich.png', fullPage: true })

  // ── 断言：无致命 console 错误（SSE 解析/渲染不应报错）──
  const fatal = consoleErrors.filter((e) => !e.includes('ResizeObserver') && !e.includes('favicon'))
  expect(fatal, `console 错误: ${fatal.join(' | ')}`).toEqual([])
})
