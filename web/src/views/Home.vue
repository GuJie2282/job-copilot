<template>
  <div class="home">
    <main class="main">
      <!-- ========== HERO：eyebrow + 宋体巨字 + 动态论点 ========== -->
      <section class="hero">
        <p class="eyebrow">DASHBOARD</p>
        <h1>你好，{{ userStore.userName }}</h1>
        <p class="hero-thesis">{{ thesis }}</p>
      </section>

      <!-- 画像加载中 -->
      <div v-if="profileState === 'loading'" class="state-block">
        <span class="spinner" />
        <p>正在读取你的画像…</p>
      </div>

      <!-- 画像读取失败：错误 + 重试 -->
      <div v-else-if="profileState === 'error'" class="state-block">
        <p class="state-title">画像读取失败</p>
        <p class="state-sub">{{ profileError }}</p>
        <button class="btn-primary" type="button" @click="loadProfile">重试</button>
      </div>

      <!-- empty / ready：链路条 + 下一步 + 支撑数据 -->
      <template v-else>
        <!-- ========== SIGNATURE：求职链路条（编码真实进度） ========== -->
        <section class="track" aria-label="求职链路进度">
          <div
            v-for="s in stages"
            :key="s.no"
            class="track-node"
            :class="s.status"
            @click="go(s.to)"
          >
            <!-- 节点主体：圆点 + 文字 -->
            <div class="node-dot" />
            <div class="node-body">
              <span class="node-no tnum">{{ s.no }}</span>
              <span class="node-name">{{ s.name }}</span>
              <span class="node-meta">{{ s.meta }}</span>
            </div>
          </div>
        </section>

        <!-- ========== 下一步焦点（基于当前阶段） ========== -->
        <section class="next">
          <p class="section-label">下一步</p>
          <div class="next-card" @click="go(nextStep.to)">
            <div class="next-body">
              <h3>{{ nextStep.title }}</h3>
              <p>{{ nextStep.desc }}</p>
            </div>
            <button class="next-cta" type="button">
              {{ nextStep.cta }} <span class="arrow">→</span>
            </button>
          </div>
        </section>

        <!-- ========== 支撑数据：画像摘要 + 最近匹配（紧凑，ready 时显示） ========== -->
        <section v-if="profileState === 'ready'" class="support">
          <div class="sup-card">
            <p class="sup-eyebrow">个人画像</p>
            <div class="sup-stats">
              <span class="tnum"><b>{{ workCount }}</b> 工作</span>
              <span class="dot">·</span>
              <span class="tnum"><b>{{ skillCount }}</b> 技能</span>
              <span class="dot">·</span>
              <span class="tnum"><b>{{ eduCount }}</b> 教育</span>
            </div>
            <button class="sup-link" type="button" @click="go('/profile')">查看 / 完善 →</button>
          </div>

          <div class="sup-card">
            <p class="sup-eyebrow">最近匹配</p>
            <div v-if="recentMatches.length > 0" class="sup-matches">
              <span
                v-for="m in recentMatches.slice(0, 3)"
                :key="m.id"
                class="sup-match tnum"
                :style="{ color: scoreColor(m.overall_score) }"
                @click="go('/jd-matcher')"
              >
                {{ m.overall_score ?? '-' }}
              </span>
            </div>
            <p v-else class="sup-empty">还没有匹配记录</p>
            <button class="sup-link" type="button" @click="go('/jd-matcher')">查看全部 →</button>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getProfile } from '@/api/resume'
import { matchHistory } from '@/api/jd'

const router = useRouter()
const userStore = useUserStore()

// 画像状态：loading / ready / empty / error
const profileState = ref<'loading' | 'ready' | 'empty' | 'error'>('loading')
const profileError = ref('')
const profile = ref<any>(null)

// 最近匹配（最多取前几条做展示）
const recentMatches = ref<any[]>([])

// 真实计数（用户拍板：不算完成度，只显真实条数）
const workCount = computed(() => profile.value?.companies?.length ?? 0)
const eduCount = computed(() => profile.value?.schools?.length ?? 0)
const skillCount = computed(() => {
  const p = profile.value || {}
  return (
    (p.technical_skills?.length || 0) +
    (p.soft_skills?.length || 0) +
    (p.languages?.length || 0)
  )
})

// ===== 链路条 signature 的核心：四阶段 + 真实进度状态 =====
// status 三态：done(已完成·墨蓝实心) / active(当前·琥珀高亮) / todo(未达·灰虚线)
type StageStatus = 'done' | 'active' | 'todo'
type StageKey = 'profile' | 'match' | 'resume' | 'interview'

const stages = computed(() => {
  const hasProfile = profileState.value === 'ready' && !!profile.value
  const hasMatch = recentMatches.value.length > 0
  // NOTE: 简历优化 / 模拟面试 的历史 Home 暂未拉取，先以 todo 呈现；
  //       方向验证后推广时接入对应历史接口，让进度判定完整准确。
  const list: { no: string; key: StageKey; name: string; to: string; status: StageStatus; meta: string }[] = [
    {
      no: '01', key: 'profile', name: '建立画像', to: '/resume-parser',
      status: hasProfile ? 'done' : 'active',
      meta: hasProfile ? `${workCount.value}段经历` : '从这里开始',
    },
    {
      no: '02', key: 'match', name: 'JD 匹配', to: '/jd-matcher',
      status: hasMatch ? 'done' : (hasProfile ? 'active' : 'todo'),
      meta: hasMatch ? `最近 ${recentMatches.value[0]?.overall_score ?? '-'} 分` : (hasProfile ? '建议下一步' : '待解锁'),
    },
    { no: '03', key: 'resume', name: '简历优化', to: '/resume-optimizer', status: 'todo', meta: '待开始' },
    { no: '04', key: 'interview', name: '模拟面试', to: '/interview/setup', status: 'todo', meta: '待开始' },
  ]
  return list
})

// 当前阶段：优先 active，否则最后一个 done，否则第一站
const currentStage = computed(() => {
  const active = stages.value.find((s) => s.status === 'active')
  if (active) return active
  const done = [...stages.value].reverse().find((s) => s.status === 'done')
  return done ?? stages.value[0]
})

// HERO 论点：随当前阶段动态变化（让首屏说一句"有用的话"，而非标签）
const thesis = computed(() => {
  if (profileState.value === 'empty') return '先建立画像，AI 才能陪你走完求职全链路。'
  if (profileState.value === 'error') return '先把画像读出来，继续你的求职进度。'
  const stage = currentStage.value
  if (!stage) return '这是你的求职作战看板。'
  const map: Record<StageKey, string> = {
    profile: '画像还没建好，从这里开始你的求职链路。',
    match: '画像已成，下一站：匹配你的目标岗位。',
    resume: '目标已锁定，下一站：定向优化简历。',
    interview: '简历就绪，下一站：模拟面试实战演练。',
  }
  return map[stage.key] ?? '这是你的求职作战看板。'
})

// 下一步焦点卡：标题 / 描述 / CTA 文案，都随当前阶段
const nextStep = computed(() => {
  const s = currentStage.value
  if (!s) return { title: '', desc: '', cta: '', to: '/profile' }
  const cta: Record<StageKey, string> = {
    profile: '开始建立画像', match: '去匹配岗位', resume: '去优化简历', interview: '开始模拟面试',
  }
  const desc: Record<StageKey, string> = {
    profile: '上传简历或粘贴文本，AI 自动提取你的个人画像。',
    match: '粘贴目标岗位 JD，看匹配度与差距清单。',
    resume: '基于目标 JD，AI 定向优化简历的表达与亮点。',
    interview: 'AI 面试官真实场景演练，结束即复盘。',
  }
  return { title: s.name, desc: desc[s.key], cta: cta[s.key], to: s.to }
})

/** 进入路由 */
function go(to: string): void {
  router.push(to)
}

/** 读取画像 */
async function loadProfile(): Promise<void> {
  profileState.value = 'loading'
  profileError.value = ''
  try {
    const res = await getProfile(userStore.userId)
    if (res.status === 'success' && res.data) {
      if (res.data.profile) {
        profile.value = res.data.profile
        profileState.value = 'ready'
      } else {
        profileState.value = 'empty'
      }
    } else {
      profileState.value = 'error'
      profileError.value = res.message || '读取失败，请稍后重试'
    }
  } catch (e: any) {
    profileState.value = 'error'
    profileError.value = e?.message || '网络异常，请检查连接'
  }
}

/** 读取最近匹配（静默失败：失败则匹配卡显示空态，不阻断页面） */
async function loadMatches(): Promise<void> {
  if (!userStore.userId) return
  try {
    const res = await matchHistory(userStore.userId)
    if (res.status === 'success' && res.data) {
      recentMatches.value = (res.data.items || []).slice(0, 5)
    }
  } catch {
    recentMatches.value = []
  }
}

/** 匹配度配色（对齐 token：$success / $warning / $error） */
function scoreColor(s?: number): string {
  if ((s ?? 0) >= 75) return '#10b981'
  if ((s ?? 0) >= 50) return '#d97706'
  return '#ef4444'
}

onMounted(() => {
  loadProfile()
  loadMatches()
})
</script>

<style scoped lang="scss">
.home {
  // 顶栏 AppTopBar 是 sticky、占文档流 65px（64 高 + 1 边框）。
  // 若这里仍写 min-height:100vh，总高 = 65 + 100vh ＞ 视口 → 底部空背景 + 能滚动。
  // 减去顶栏高度，内容少时刚好铺满、不多出；内容多时自然滚动。
  min-height: calc(100vh - 65px);
  background: $bg-light;
}

.main {
  max-width: 1040px;
  margin: 0 auto;
  padding: $spacing-3xl $spacing-xl $spacing-2xl;
}

/* ========== HERO ========== */
.hero {
  margin-bottom: $spacing-2xl;

  .eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.18em;
    color: $accent-color;
    margin-bottom: $spacing-md;
  }

  h1 {
    font-size: $font-size-4xl;       // 宋体巨字，hero 冲击
    color: $ink;
    margin-bottom: $spacing-sm;
    letter-spacing: -0.01em;
  }

  .hero-thesis {
    color: $text-secondary;
    font-size: $font-size-lg;
    max-width: 46ch;
  }
}

/* ========== SIGNATURE：求职链路条 ========== */
.track {
  display: flex;
  align-items: flex-start;
  margin-bottom: $spacing-2xl;
  padding: $spacing-xl $spacing-md 0;
}

.track-node {
  flex: 1;
  position: relative;
  text-align: center;
  cursor: pointer;
  padding-top: 22px;                 // 给圆点 + 连线留位

  // 连线：本节点左半段（从上一节点中心到本节点中心）
  &::before {
    content: '';
    position: absolute;
    top: 9px;                        // 圆点垂直中心
    right: 50%;
    width: 100%;
    height: 2px;
    transform: translateX(0.5px);
  }
  &:first-child::before {
    display: none;                   // 首节点无左线
  }

  // 三态连线 + 圆点配色
  &.done::before { background: $ink; }
  &.active::before { background: $accent-color; }
  &.todo::before {
    background: transparent;
    border-top: 2px dashed $border-color;
    height: 0;
    top: 10px;
  }
}

.node-dot {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 18px;
  height: 18px;
  border-radius: 50%;
  z-index: 1;
  transition: all $transition-base ease;

  .done & {
    background: $ink;
  }

  .active & {
    background: $accent-color;
    box-shadow: 0 0 0 5px rgba($accent-color, 0.18);   // 琥珀光环
    animation: pulse 2.4s ease-in-out infinite;
  }

  .todo & {
    background: $bg-white;
    border: 2px solid $border-color;
  }

  // hover：节点轻微放大，提示可点
  .track-node:hover & {
    transform: translateX(-50%) scale(1.18);
  }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 5px rgba($accent-color, 0.18); }
  50% { box-shadow: 0 0 0 9px rgba($accent-color, 0.08); }
}

// 尊重「减少动态」偏好
@media (prefers-reduced-motion: reduce) {
  .node-dot .active &,
  .active .node-dot { animation: none; }
}

.node-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 $spacing-xs;

  .node-no {
    font-family: $font-mono;
    font-size: $font-size-xs;
    color: $text-disabled;
    letter-spacing: 0.08em;
  }

  .node-name {
    font-family: $font-heading;
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: $ink;
  }

  .node-meta {
    font-family: $font-mono;
    font-size: $font-size-xs;
    color: $text-secondary;
  }

  .todo & .node-name { color: $text-disabled; }
  .active & .node-name { color: $accent-color; }
}

/* ========== 下一步焦点 ========== */
.next {
  margin-bottom: $spacing-2xl;
}

.section-label {
  font-family: $font-mono;
  font-size: $font-size-xs;
  letter-spacing: 0.14em;
  color: $text-secondary;
  margin-bottom: $spacing-md;
}

.next-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-lg;
  background: $bg-white;
  border: 1px solid $border-color;
  border-left: 3px solid $accent-color;    // 琥珀焦点条
  border-radius: $radius-lg;
  padding: $spacing-lg $spacing-xl;
  cursor: pointer;
  transition: all $transition-base ease;

  &:hover {
    border-left-color: $accent-light;
    box-shadow: $shadow-md;
    transform: translateX(2px);
  }
}

.next-body {
  h3 {
    font-size: $font-size-lg;
    color: $ink;
    margin-bottom: $spacing-xs;
  }

  p {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.next-cta {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-lg;
  border-radius: $radius-md;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  white-space: nowrap;
  cursor: pointer;
  transition: background $transition-base ease;

  .arrow {
    transition: transform $transition-base ease;
  }

  .next-card:hover & {
    background: $primary-dark;

    .arrow {
      transform: translateX(3px);
    }
  }
}

/* ========== 支撑数据（紧凑横排） ========== */
.support {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-lg;
}

.sup-card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-lg $spacing-xl;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.sup-eyebrow {
  font-family: $font-mono;
  font-size: $font-size-xs;
  letter-spacing: 0.12em;
  color: $text-secondary;
}

.sup-stats {
  display: flex;
  align-items: baseline;
  gap: $spacing-sm;
  font-size: $font-size-sm;
  color: $text-secondary;

  b {
    font-family: $font-heading;
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: $ink;
    margin-right: 2px;
  }

  .dot {
    color: $border-color;
  }
}

.sup-matches {
  display: flex;
  gap: $spacing-md;

  .sup-match {
    font-family: $font-heading;
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    cursor: pointer;
  }
}

.sup-empty {
  font-size: $font-size-sm;
  color: $text-disabled;
}

.sup-link {
  align-self: flex-start;
  background: none;
  border: none;
  color: $primary-color;
  font-size: $font-size-sm;
  cursor: pointer;
  padding: 0;
  margin-top: $spacing-xs;

  &:hover {
    color: $primary-dark;
  }
}

/* ========== 状态块（加载 / 错误） ========== */
.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: $spacing-md;
  padding: $spacing-3xl $spacing-xl;
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  color: $text-secondary;
}

.state-title {
  font-family: $font-heading;
  font-size: $font-size-xl;
  color: $ink;
}

.state-sub {
  font-size: $font-size-sm;
  max-width: 40ch;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid $border-color;
  border-top-color: $primary-color;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-xl;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;

  &:hover { background: $primary-dark; }
}

/* ========== 响应式 ========== */
@media (max-width: $container-md) {
  .main {
    padding: $spacing-2xl $spacing-lg $spacing-xl;
  }

  .hero h1 {
    font-size: $font-size-3xl;
  }

  // 窄屏：链路条只留编号 + 名，meta 换行更紧凑
  .node-meta {
    font-size: 10px;
  }

  .next-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .support {
    grid-template-columns: 1fr;
  }
}
</style>
