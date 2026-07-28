/**
 * v-auto-scroll：贴底才跟随的自动滚动（思考打字机区用，evolve-resume-refine）。
 *
 * 用 MutationObserver 监听容器内容变化（文本追加 / 子节点增删），内容增长时：
 * - 用户当前贴底 → 自动滚到底，保证看到最新内容；
 * - 用户向上翻阅 → 不打断（pinned=false）；
 * - 用户滚回底部 → pinned 恢复 true，后续继续跟随。
 *
 * 全局注册（main.ts），各思考打字机容器（精修消息列表 / 生成 / 解析 / JD 的思考 pre）
 * 只需加 `v-auto-scroll`，无需改各自 script。
 *
 * 挂到可滚动容器（overflow:auto 的 pre / 消息列表）。
 */
import type { Directive } from 'vue'

const THRESHOLD = 40 // 距底 < 40px 视为贴底（容忍像素/亚像素误差）

interface AutoScrollState {
  onScroll: () => void
  mo: MutationObserver
  pinned: boolean
}

export const vAutoScroll: Directive<HTMLElement> = {
  mounted(el) {
    const state: AutoScrollState = {
      pinned: true,
      onScroll: () => {
        state.pinned = el.scrollHeight - el.scrollTop - el.clientHeight < THRESHOLD
      },
      mo: new MutationObserver(() => {
        if (state.pinned) el.scrollTop = el.scrollHeight
      }),
    }
    el.addEventListener('scroll', state.onScroll, { passive: true })
    // subtree + characterData：捕获 pre 文本追加、子节点增删
    state.mo.observe(el, { childList: true, subtree: true, characterData: true })
    ;(el as unknown as { _autoScroll?: AutoScrollState })._autoScroll = state
  },
  unmounted(el) {
    const s = (el as unknown as { _autoScroll?: AutoScrollState })._autoScroll
    if (s) {
      el.removeEventListener('scroll', s.onScroll)
      s.mo.disconnect()
    }
  },
}
