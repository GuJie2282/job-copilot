<template>
  <div class="page">
    <header class="page-head">
      <p class="eyebrow">HISTORY</p>
      <h1>面试历史</h1>
      <p class="sub">回看历次模拟面试。已结束的可看复盘，进行中的可继续答题。<router-link to="/interview/library" class="btn-text">面经库 →</router-link></p>
    </header>

    <!-- 加载中 -->
    <div v-if="loading" class="state-block"><span class="spinner" /></div>

    <!-- 空态 -->
    <div v-else-if="items.length === 0" class="empty-h">
      暂无面试记录，
      <router-link to="/interview/setup" class="link">开启第一场 →</router-link>
    </div>

    <template v-else>
      <!-- SIGNATURE：面试成长曲线（编码分数趋势 · 点高度=分数 · 色=档位） -->
      <section v-if="scoredItems.length > 0" class="track-card">
        <div class="track-summary">
          <span class="ts-item"><b class="tnum">{{ avgScore ?? '-' }}</b> 平均分</span>
          <span class="ts-item"><b class="tnum">{{ scoredItems.length }}</b> 场已评分</span>
          <span v-if="trend" class="ts-trend">{{ trend }}</span>
        </div>
        <svg class="track-svg" viewBox="0 0 600 140">
          <!-- 分档参考线：75(绿档界) / 50(琥珀档界) -->
          <line x1="40" y1="42.5" x2="560" y2="42.5" class="grid" />
          <line x1="40" y1="65" x2="560" y2="65" class="grid" />
          <text x="6" y="46" class="grid-label">75</text>
          <text x="6" y="69" class="grid-label">50</text>
          <!-- 折线 -->
          <polyline :points="linePoints" class="track-line" />
          <!-- 散点（可点进复盘/续面） -->
          <circle
            v-for="(p, i) in points"
            :key="i"
            :cx="p.x"
            :cy="p.y"
            :fill="p.color"
            r="5"
            class="track-dot"
            @click="open(p.item)"
          />
        </svg>
        <div class="track-axis">
          <span class="tnum">{{ formatTime(scoredItems[0]?.created_at) }}</span>
          <span class="axis-hint">最早 ← 　→ 最新</span>
        </div>
      </section>

      <!-- 历史会话列表（详情） -->
      <section class="card">
        <div class="history-head">
          <h3 class="card-title">历史会话 <span class="title-count tnum">（{{ items.length }}）</span></h3>
          <button class="btn-text" type="button" :disabled="loading" @click="load">刷新</button>
        </div>

        <div v-for="it in items" :key="it.id" class="history-item" @click="open(it)">
          <span class="h-score tnum" :style="{ color: colorFor(it.avg_score) }">{{ it.avg_score ?? '-' }}</span>
          <div class="h-mid">
            <span class="h-pos">{{ typeLabel(it.interview_type) }}<span v-if="it.intensity"> · {{ intensityLabel(it.intensity) }}</span></span>
            <span class="h-sub">{{ it.total_rounds ?? 0 }} 轮 · {{ statusLabel(it.status) }}</span>
          </div>
          <span class="h-time tnum">{{ formatTime(it.created_at) }}</span>
          <span class="h-arrow">{{ it.status === 'finished' ? '复盘' : '续面' }} →</span>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { listSessions } from '@/api/interview'
import { INTENSITY_LABELS } from '@/types/interview'
import type { SessionSummary } from '@/types/interview'

const router = useRouter()
const userStore = useUserStore()

const items = ref<SessionSummary[]>([])
const loading = ref(false)

const TYPE_LABELS: Record<string, string> = {
  full: '全程面试', behavioral: '行为面', technical: '技术面',
  case: '案例面', motivation: '动机面', stress: '压力面',
}

function typeLabel(t?: string | null) {
  return (t && TYPE_LABELS[t]) || '模拟面试'
}
function intensityLabel(i?: string | null) {
  return (i && INTENSITY_LABELS[i as keyof typeof INTENSITY_LABELS]) || ''
}
function statusLabel(s: string) {
  return { interviewing: '进行中', paused: '已暂停', finished: '已结束', error: '异常' }[s] || s
}

function colorFor(s?: number | null) {
  if ((s ?? 0) >= 75) return '#10b981'
  if ((s ?? 0) >= 50) return '#d97706'
  if (s == null) return '#94a3b8'
  return '#ef4444'
}

function formatTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

function open(it: SessionSummary) {
  if (it.status === 'finished') {
    router.push('/interview/debrief/' + it.id)
  } else {
    router.push('/interview/room/' + it.id)
  }
}

// ===== SIGNATURE 数据：面试成长曲线 =====
// 只画「已评分」的面试（avg_score 非空），未评分的不进曲线（仍在下方列表）
const scoredItems = computed(() => items.value.filter((it) => it.avg_score != null))

// SVG 坐标系：viewBox 600x140，绘图区 x∈[40,560] y∈[20,110]（高分在上）
const W = 600, PADX = 40, PADY = 20, PLOTH = 90

const points = computed(() => {
  const arr = scoredItems.value
  const n = arr.length
  if (n === 0) return [] as { x: number; y: number; score: number; color: string; item: SessionSummary }[]
  return arr.map((it, i) => {
    const x = n === 1 ? W / 2 : PADX + (i / (n - 1)) * (W - 2 * PADX)
    const score = it.avg_score ?? 0
    const y = PADY + (1 - score / 100) * PLOTH   // 分数越高 y 越小（越靠上）
    return { x, y, score, color: colorFor(it.avg_score), item: it }
  })
})

// 折线 points 字符串（"x,y x,y ..."）
const linePoints = computed(() => points.value.map((p) => `${p.x},${p.y}`).join(' '))

// 平均分（已评分的）
const avgScore = computed(() => {
  const arr = scoredItems.value
  if (!arr.length) return null
  return Math.round(arr.reduce((s, it) => s + (it.avg_score ?? 0), 0) / arr.length)
})

// 趋势：最后一场 vs 第一场的分差
const trend = computed(() => {
  const arr = points.value
  if (arr.length < 2) return ''
  const d = (arr[arr.length - 1].score ?? 0) - (arr[0].score ?? 0)
  if (d > 2) return '↗ 上升'
  if (d < -2) return '↘ 下降'
  return '→ 平稳'
})

async function load() {
  if (!userStore.userId) return
  loading.value = true
  try {
    const res: any = await listSessions(userStore.userId)
    if (res.status === 'success' && res.data) {
      items.value = res.data.items || []
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载历史失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped lang="scss">
.page {
  max-width: 820px;
  margin: 0 auto;
  padding: $spacing-3xl $spacing-xl;
  // 减顶栏 65px，避免底部空白溢出
  min-height: calc(100vh - 65px);
}

.page-head {
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

  .sub {
    color: $text-secondary;
    max-width: 60ch;
  }
}

/* ===== SIGNATURE：面试成长曲线 ===== */
.track-card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-left: 3px solid $accent-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-lg $spacing-xl;
  margin-bottom: $spacing-lg;
}

.track-summary {
  display: flex;
  align-items: baseline;
  gap: $spacing-lg;
  margin-bottom: $spacing-sm;

  .ts-item {
    font-size: $font-size-sm;
    color: $text-secondary;

    b {
      font-family: $font-heading;
      font-size: $font-size-xl;
      font-weight: $font-weight-bold;
      color: $ink;
      margin-right: 2px;
    }
  }

  .ts-trend {
    margin-left: auto;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $primary-color;
  }
}

.track-svg {
  width: 100%;
  height: auto;
  display: block;
}

.grid {
  stroke: $border-color;
  stroke-width: 1;
  stroke-dasharray: 3 4;
}

.grid-label {
  font-family: $font-mono;
  font-size: 9px;
  fill: $text-disabled;
}

.track-line {
  fill: none;
  stroke: $primary-color;
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.track-dot {
  stroke: $bg-white;
  stroke-width: 2;
  cursor: pointer;
  transition: r $transition-base ease;

  &:hover {
    r: 7;
  }
}

.track-axis {
  display: flex;
  justify-content: space-between;
  margin-top: $spacing-xs;
  font-size: $font-size-xs;
  color: $text-disabled;

  .axis-hint {
    color: $text-disabled;
  }
}

/* 历史列表（详情） */
.card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xl;
}

.card-title {
  font-size: $font-size-lg;

  .title-count {
    font-family: $font-body;
    font-weight: $font-weight-normal;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.history-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
}

.empty-h {
  text-align: center;
  padding: $spacing-2xl;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.link {
  color: $primary-color;
  text-decoration: none;

  &:hover {
    color: $primary-dark;
  }
}

.state-block {
  display: flex;
  justify-content: center;
  padding: $spacing-xl;
}

.history-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md 0;
  border-bottom: 1px solid $border-light;
  cursor: pointer;
  font-size: $font-size-sm;
  transition: background $transition-base ease;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: $bg-light;
  }
}

.h-score {
  font-weight: $font-weight-bold;
  min-width: 36px;
  font-size: $font-size-base;
  text-align: center;
}

.h-mid {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.h-pos {
  color: $text-primary;
  font-weight: $font-weight-medium;
}

.h-sub {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.h-time {
  color: $text-disabled;
  font-size: $font-size-xs;
}

.h-arrow {
  color: $primary-color;
  font-size: $font-size-xs;
  white-space: nowrap;
}

.btn-text {
  background: none;
  border: none;
  color: $primary-color;
  cursor: pointer;
  font-size: $font-size-sm;
  padding: $spacing-xs $spacing-sm;

  &:hover {
    color: $primary-dark;
  }

  &:disabled {
    color: $text-disabled;
    cursor: not-allowed;
  }
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid $border-color;
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

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }

  .page-head h1 {
    font-size: $font-size-2xl;
  }

  .history-item {
    flex-wrap: wrap;
  }

  .track-summary {
    flex-wrap: wrap;
    gap: $spacing-md;

    .ts-trend {
      margin-left: 0;
    }
  }
}
</style>
