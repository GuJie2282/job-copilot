/**
 * 语音模式端到端（Playwright）—— add-voice-interview task 4.2.1 / 4.3
 * ================================================
 * 验证「语音模式 → 麦克风未授权 → 自动降级文字」降级链路。
 *
 * 用 route mock 接管 createSession + getSession，避开后端出题 LLM 的时序卡点
 * （智谱偶发慢；与语音功能无关），聚焦验证前端语音流转 + 降级。
 *
 * 流程：登录(真) → Setup 选「语音回答」→ 开始 → createSession(mock) →
 *       进 room → getSession(mock 返回首题) → pending_question 就绪 →
 *       watch 触发 recStart → getUserMedia(Playwright 默认拒绝) →
 *       handleRecorderError → 降级文字输入。
 *
 * 运行：后端 8001 + 前端 3000 已起。cd web && npx playwright test voice
 */
import { test, expect } from '@playwright/test'

const EMAIL = 'e2e@test.com'
const PASSWORD = 'Test1234!'
const SID = 'voice-e2e-1'

test('语音模式：麦克风未授权 → 自动降级文字输入', async ({ page }) => {
  // ── mock createSession（避开出题 LLM 时序卡点）──
  await page.route('**/api/interview/sessions', async (route) => {
    if (route.request().method() !== 'POST') return route.continue()
    await route.fulfill({
      status: 200,
      json: { status: 'success', message: 'ok', data: { session_id: SID } },
    })
  })
  // ── mock getSession（room 加载拿首题，触发 watch → 收音）──
  await page.route(`**/api/interview/sessions/${SID}`, async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        status: 'success',
        data: {
          status: 'interviewing',
          interview_mode: 'real',
          interview_type: 'full',
          intensity: 'short',
          transcript: [],
          pending_question: {
            qid: 'q1',
            round: 1,
            question: '请先做一个简单的自我介绍。',
            is_probe: false,
          },
        },
      },
    })
  })

  // ── 1. 登录（真后端 auth，快）──
  await page.goto('/login')
  await page.getByPlaceholder('you@example.com').fill(EMAIL)
  await page.getByPlaceholder('至少 6 位').fill(PASSWORD)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL(/\/(profile|jd-matcher|interview|)$/, { timeout: 15_000 })

  // ── 2. 配置：选「语音回答」+ 开始 ──
  await page.goto('/interview/setup')
  await expect(page.locator('.notice-warn')).toBeHidden({ timeout: 10_000 })
  await page.getByRole('button', { name: /语音回答/ }).click()
  await page.getByRole('button', { name: '开始面试' }).click()

  // ── 3. 进入面试间（createSession mocked，立即跳转）──
  await expect(page).toHaveURL(new RegExp(`/interview/room/${SID}`), { timeout: 15_000 })
  // 首题（mocked pending_question）渲染
  await expect(page.locator('.msg.interviewer').first()).toBeVisible({ timeout: 15_000 })

  // ── 4. 降级验证（语音模式独有路径）──
  // voice 模式：pending_question 就绪 → watch 触发 recStart → getUserMedia。
  // Playwright headless 默认无麦克风权限 → getUserMedia 拒绝 → handleRecorderError → 降级文字。
  await expect(page.locator('.answer-input')).toBeVisible({ timeout: 30_000 })
  await expect(page.locator('.voice-bar')).toBeHidden({ timeout: 10_000 })
})
