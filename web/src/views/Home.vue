<template>
  <div class="home">
    <main class="main">
      <!-- 欢迎区 -->
      <section class="welcome">
        <p class="eyebrow">DASHBOARD</p>
        <h1>你好，{{ userStore.userName }}</h1>
        <p class="welcome-sub">这是你的求职作战看板。</p>
      </section>

      <!-- 画像加载中 -->
      <div v-if="profileState === 'loading'" class="state-block">
        <span class="spinner" />
        <p>正在读取你的画像…</p>
      </div>

      <!-- 画像读取失败：错误 + 重试（不阻断下方链路） -->
      <div v-else-if="profileState === 'error'" class="state-block">
        <p class="state-title">画像读取失败</p>
        <p class="state-sub">{{ profileError }}</p>
        <button class="btn-primary" type="button" @click="loadProfile">重试</button>
      </div>

      <!-- 新用户：无画像 → 大 CTA -->
      <div v-else-if="profileState === 'empty'" class="onboard">
        <p class="onboard-eyebrow">开始你的求职清单</p>
        <h2 class="onboard-title">先建立画像，AI 才能帮你匹配岗位、优化简历。</h2>
        <button class="cta" type="button" @click="go('/resume-parser')">
          开始建立画像 →
        </button>
      </div>

      <!-- 有画像：作战看板（画像摘要 + 最近匹配） -->
      <div v-else class="board">
        <!-- 画像摘要卡：只显真实计数，不算完成度 -->
        <section class="card">
          <div class="card-head">
            <p class="card-eyebrow">个人画像</p>
            <button class="link" type="button" @click="go('/profile')">查看 / 完善 →</button>
          </div>
          <div class="stats">
            <div class="stat">
              <span class="stat-num tnum">{{ workCount }}</span>
              <span class="stat-label">工作经历</span>
            </div>
            <div class="stat">
              <span class="stat-num tnum">{{ skillCount }}</span>
              <span class="stat-label">技能项</span>
            </div>
            <div class="stat">
              <span class="stat-num tnum">{{ eduCount }}</span>
              <span class="stat-label">教育经历</span>
            </div>
          </div>
        </section>

        <!-- 最近匹配卡 -->
        <section class="card">
          <div class="card-head">
            <p class="card-eyebrow">最近匹配</p>
            <button class="link" type="button" @click="go('/jd-matcher')">查看全部 →</button>
          </div>
          <div v-if="recentMatches.length > 0" class="match-list">
            <div
              v-for="m in recentMatches"
              :key="m.id"
              class="match-item"
              @click="go('/jd-matcher')"
            >
              <span class="m-score tnum" :style="{ color: scoreColor(m.overall_score) }">
                {{ m.overall_score ?? '-' }}
              </span>
              <span class="m-pos">{{ m.position_title || '未知岗位' }}</span>
              <span class="m-time tnum">{{ formatTime(m.created_at) }}</span>
            </div>
          </div>
          <div v-else class="match-empty">
            <p>还没有匹配记录</p>
            <button class="btn-primary sm" type="button" @click="go('/jd-matcher')">去匹配岗位</button>
          </div>
        </section>
      </div>

      <!-- 下一步链路（加载中/空状态时不显示，避免与 CTA 重复） -->
      <section v-if="profileState === 'ready' || profileState === 'error'" class="flow-wrap">
        <p class="section-label">下一步</p>
        <div class="flow">
          <div
            v-for="step in steps"
            :key="step.id"
            class="flow-item"
            :class="{ 'is-open': step.open, 'is-soon': !step.open }"
            @click="step.open && go(step.to)"
          >
            <div class="flow-no tnum">{{ step.no }}</div>
            <div class="flow-body">
              <h3>{{ step.title }}</h3>
              <p>{{ step.desc }}</p>
            </div>
            <div class="flow-cta">
              <span v-if="step.open" class="cta-open">进入 →</span>
              <span v-else class="cta-soon">即将开放</span>
            </div>
          </div>
        </div>
      </section>
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

// 最近匹配（最多 5 条）
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

// 求职四步链路：01/02 已实现，03/04 灰显（编号是真实求职顺序，故保留）
const steps = [
  { id: 1, no: '01', title: '建立画像', desc: '上传简历或粘贴文本，AI 自动提取你的个人画像。', open: true, to: '/resume-parser' },
  { id: 2, no: '02', title: 'JD 匹配', desc: '粘贴目标岗位，AI 解析要求并给出匹配度与差距清单。', open: true, to: '/jd-matcher' },
  { id: 3, no: '03', title: '简历优化', desc: '基于目标 JD，AI 定向优化简历的表达与亮点。', open: false, to: '' },
  { id: 4, no: '04', title: '模拟面试', desc: 'AI 扮演面试官，真实场景练习并复盘。', open: true, to: '/interview/setup' }
]

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
  if ((s ?? 0) >= 75) return '#10b981' // $success
  if ((s ?? 0) >= 50) return '#d97706' // $warning
  return '#ef4444'                      // $error
}

/** 时间格式化（复用 JdMatcher 同款） */
function formatTime(t?: string | null): string {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  loadProfile()
  loadMatches()
})
</script>

<style scoped lang="scss">
.home {
  min-height: 100vh;
  background: $bg-light;
}

.main {
  max-width: 1040px;
  margin: 0 auto;
  padding: $spacing-3xl $spacing-xl;
}

/* 欢迎区 */
.welcome {
  margin-bottom: $spacing-2xl;

  .eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.15em;
    color: $accent-color;
    margin-bottom: $spacing-sm;
  }

  h1 {
    font-size: $font-size-3xl;
    margin-bottom: $spacing-sm;
  }

  .welcome-sub {
    color: $text-secondary;
  }
}

/* 状态块（加载 / 错误） */
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
  margin-bottom: $spacing-2xl;
}

.state-title {
  font-family: $font-heading;
  font-size: $font-size-xl;
  color: $ink;
}

.state-sub {
  font-size: $font-size-sm;
  color: $text-secondary;
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
  to {
    transform: rotate(360deg);
  }
}

/* 新用户引导：大 CTA */
.onboard {
  padding: $spacing-3xl $spacing-2xl;
  background: $bg-white;
  border: 1px solid $border-color;
  border-left: 3px solid $accent-color;
  border-radius: $radius-lg;
  margin-bottom: $spacing-2xl;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: $spacing-md;

  .onboard-eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.15em;
    color: $accent-color;
  }

  .onboard-title {
    font-family: $font-heading;
    font-size: $font-size-2xl;
    color: $ink;
    line-height: 1.4;
    max-width: 36ch;
  }
}

.cta {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-md $spacing-2xl;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  transition: background $transition-base ease;

  &:hover {
    background: $primary-dark;
  }
}

/* 看板：两列 */
.board {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-lg;
  margin-bottom: $spacing-3xl;
}

.card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xl;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;

  .card-eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.12em;
    color: $text-secondary;
  }
}

.link {
  background: none;
  border: none;
  color: $primary-color;
  font-size: $font-size-sm;
  cursor: pointer;
  padding: 0;

  &:hover {
    color: $primary-dark;
  }
}

/* 画像计数 */
.stats {
  display: flex;
  gap: $spacing-xl;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.stat-num {
  font-family: $font-heading;
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  color: $ink;
  line-height: 1;
}

.stat-label {
  font-size: $font-size-xs;
  color: $text-secondary;
}

/* 最近匹配列表 */
.match-list {
  display: flex;
  flex-direction: column;
}

.match-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm 0;
  border-bottom: 1px solid $border-light;
  cursor: pointer;
  font-size: $font-size-sm;

  &:last-child {
    border-bottom: none;
  }

  &:hover .m-pos {
    color: $primary-color;
  }
}

.m-score {
  font-weight: $font-weight-bold;
  min-width: 36px;
  font-size: $font-size-base;
}

.m-pos {
  flex: 1;
  color: $text-primary;
  transition: color $transition-base ease;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-time {
  color: $text-disabled;
  font-size: $font-size-xs;
}

.match-empty {
  text-align: center;
  padding: $spacing-lg 0;
  color: $text-secondary;
  font-size: $font-size-sm;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-md;
}

/* 按钮 */
.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-xl;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  transition: background $transition-base ease;

  &:hover {
    background: $primary-dark;
  }

  &.sm {
    padding: $spacing-xs $spacing-lg;
  }
}

/* 下一步链路 */
.section-label {
  font-family: $font-mono;
  font-size: $font-size-xs;
  letter-spacing: 0.12em;
  color: $text-secondary;
  margin-bottom: $spacing-md;
}

.flow {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.flow-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: $spacing-lg;
  padding: $spacing-lg $spacing-xl;
  background: $bg-white;
  border: 1px solid $border-color;
  border-left: 3px solid transparent;
  border-radius: $radius-lg;
  transition: all $transition-base ease;

  &.is-open {
    cursor: pointer;

    &:hover {
      border-left-color: $primary-color;
      transform: translateX(4px);
      box-shadow: $shadow-md;
    }
  }

  &.is-soon {
    background: $bg-gray;

    .flow-no {
      color: $text-disabled;
    }
  }
}

.flow-no {
  font-family: $font-heading;
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: $accent-color;
  min-width: 44px;
}

.flow-body {
  h3 {
    font-size: $font-size-lg;
    margin-bottom: $spacing-xs;
  }

  p {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.flow-cta {
  .cta-open {
    color: $primary-color;
    font-weight: $font-weight-medium;
    font-size: $font-size-sm;
    white-space: nowrap;
  }

  .cta-soon {
    color: $text-disabled;
    font-size: $font-size-xs;
    border: 1px solid $border-color;
    padding: 2px 10px;
    border-radius: $radius-full;
    white-space: nowrap;
  }
}

/* 响应式 */
@media (max-width: $container-md) {
  .main {
    padding: $spacing-2xl $spacing-lg;
  }

  .welcome h1 {
    font-size: $font-size-2xl;
  }

  .board {
    grid-template-columns: 1fr;
  }

  .stats {
    gap: $spacing-lg;
  }

  .flow-item {
    padding: $spacing-md;
    gap: $spacing-md;
  }
}
</style>
