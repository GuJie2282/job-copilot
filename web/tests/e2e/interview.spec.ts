/**
 * 模拟面试端到端（Playwright）
 * ================================
 *
 * 自动验证主链路：登录 → 配置 → 面试对话（多轮）→ 复盘渲染。
 * 用 short 档位（3 题）控制时长；画像就绪由测试账号保证（e2e@test.com，曾 seed 画像）。
 *
 * 运行前需起服务：
 *   后端：cd backend && ./.venv/Scripts/python.exe -m src.main   （8001）
 *   前端：cd web && npm run dev                                   （3000）
 * 然后：cd web && npx playwright test
 */
import { test, expect } from '@playwright/test'

const EMAIL = 'e2e@test.com'
const PASSWORD = 'Test1234!'

test('模拟面试完整流程：登录 → 配置 → 答题 → 复盘', async ({ page }) => {
  // ── 1. 登录 ──
  await page.goto('/login')
  await page.getByPlaceholder('you@example.com').fill(EMAIL)
  await page.getByPlaceholder('至少 6 位').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL(/\/(profile|jd-matcher|interview|)$/, { timeout: 15_000 })

  // ── 2. 配置面试（short 档位 + 实战模式）──
  await page.goto('/interview/setup')
  // 画像就绪性检查：若出现缺失引导，给出清晰失败信息
  const profileMissing = page.locator('.notice-warn')
  await expect(profileMissing).toBeHidden({ timeout: 10_000 })

  // 选「简短」档位（唯一含「简短」的卡片）
  await page.getByRole('button', { name: /简短/ }).click()
  await page.getByRole('button', { name: '开始面试' }).click()

  // ── 3. 进入面试间（出题 LLM 可能 5-15s）──
  await expect(page).toHaveURL(/\/interview\/room\//, { timeout: 120_000 })
  // 第一道题（面试官消息）出现
  await expect(page.locator('.msg.interviewer').first()).toBeVisible({ timeout: 30_000 })

  // ── 4. 答题循环：节奏由 LLM 自主（evolve-interview-pacing），轮数不固定 ──
  //    可能提前结束（<3 题）、可能连追；护栏 max_rounds = 题量×(1+5) = 18 轮上限。
  //    循环到跳复盘即止；上限 24 覆盖护栏天花板 + buffer。
  const answers = [
    '我在字节做 feed 推荐，用 A/B 测试优化召回策略，协调算法和工程团队，DAU 提升 15%。',
    '我用 SQL 做漏斗分析定位流失节点，针对性优化后转化率提升 12%，并复盘了流程。',
    '想做 PM 因为喜欢用数据解决问题，3 年内想成为能独立带产品线的高级 PM。',
    '那个项目我主导了策略设计，协调了算法和工程团队，自己负责数据验证。',
  ]
  for (let i = 0; i < 24; i++) {
    // 已跳复盘则结束（LLM 可能提前结束面试）
    if (page.url().includes('/debrief')) break

    const input = page.locator('.answer-input')
    await input.waitFor({ state: 'visible', timeout: 30_000 })
    await input.fill(answers[i % answers.length])
    // 等发送按钮可用（后端一轮 LLM 可能 30-60s：评估+节奏决策，放宽到 90s）
    const sendBtn = page.locator('.btn-send')
    await expect(sendBtn).toBeEnabled({ timeout: 90_000 })
    await sendBtn.click()

    // 等待下一题出现或跳复盘（评估+决策 LLM 5-10s）
    await page.waitForTimeout(6000)
  }

  // ── 5. 验证复盘渲染 ──
  await expect(page).toHaveURL(/\/interview\/debrief\//, { timeout: 120_000 })
  await expect(page.locator('.overall-score')).toBeVisible({ timeout: 30_000 })
  // 总评分是数字（- 或数字）
  await expect(page.locator('.overall-score')).not.toBeEmpty()
})
