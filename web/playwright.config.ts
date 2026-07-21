import { defineConfig } from '@playwright/test'

/**
 * Playwright 配置
 * 超时放宽：模拟面试依赖 LLM，单轮出题/评估/复盘可能 5-15s，全程 3-5 分钟。
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,           // 串行：共享同一测试用户，避免并发互相干扰
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 300_000,               // 单测 5 分钟（LLM 慢）
  expect: { timeout: 30_000 },
  use: {
    baseURL: 'http://localhost:3000',
    channel: 'msedge',              // 用 Windows 自带 Edge（chromium 内核），免下载 chromium
    trace: 'on-first-retry',
    actionTimeout: 30_000,
  },
})
