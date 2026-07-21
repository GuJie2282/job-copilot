<template>
  <div class="page">
    <header class="page-head">
      <p class="eyebrow">HISTORY</p>
      <h1>面试历史</h1>
      <p class="sub">回看历次模拟面试。已结束的可看复盘，进行中的可继续答题。<router-link to="/interview/library" class="btn-text">面经库 →</router-link></p>
    </header>

    <section class="card">
      <div class="history-head">
        <h3 class="card-title">历史会话 <span class="title-count tnum">（{{ items.length }}）</span></h3>
        <button class="btn-text" type="button" :disabled="loading" @click="load">刷新</button>
      </div>

      <div v-if="loading" class="state-block"><span class="spinner" /></div>

      <div v-else-if="items.length === 0" class="empty-h">
        暂无面试记录，
        <router-link to="/interview/setup" class="link">开启第一场 →</router-link>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

  .history-item {
    flex-wrap: wrap;
  }
}
</style>
