<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">DEBRIEF</p>
      <h1>面试复盘</h1>
      <p class="sub">基于本场表现的结构化复盘：改进范例、失分卡壳、可执行的后续建议。</p>
    </header>

    <!-- 复盘生成中（NOT_FINISHED） -->
    <div v-if="generating" class="card state-center">
      <span class="spinner lg" />
      <p class="state-title">复盘生成中…</p>
      <p class="state-sub">详细复盘依赖 LLM，通常需要几秒。完成后点下方刷新。</p>
      <button class="btn-primary" type="button" :disabled="loading" @click="loadDebrief">
        {{ loading ? '加载中…' : '刷新复盘' }}
      </button>
    </div>

    <!-- 复盘内容 -->
    <template v-else-if="debrief">
      <!-- 总评 -->
      <section class="card score-card">
        <div class="overall">
          <div class="overall-score tnum" :style="{ color: scoreColor }">{{ avgScore ?? '-' }}</div>
          <div class="overall-hint">综合评分 / 100 · 共 {{ totalRounds || debrief.overview.total_rounds }} 轮</div>
        </div>
        <p v-if="debrief.overview.one_line_summary" class="one-line">{{ debrief.overview.one_line_summary }}</p>
      </section>

      <!-- 逐题改进范例（基于自身经历改写，非标准答案） -->
      <section v-if="reviewsWithAnswer.length" class="card">
        <h3 class="card-title">逐题改进范例 <span class="title-count tnum">（{{ reviewsWithAnswer.length }} 题）</span></h3>
        <p class="section-hint">改进版基于你【自身的经历】改写，培养反思而非背诵标准答案。</p>
        <div v-for="r in reviewsWithAnswer" :key="r.round" class="review-item">
          <div class="review-head">第 {{ r.round }} 题 <span v-if="r.question" class="review-q">{{ r.question }}</span></div>
          <div v-if="r.myAnswer" class="answer-block mine">
            <span class="block-label">你的回答</span>
            <p>{{ r.myAnswer }}</p>
          </div>
          <div v-if="r.better_version" class="answer-block better">
            <span class="block-label">改进版</span>
            <p>{{ r.better_version }}</p>
          </div>
          <p v-if="r.improvement_point" class="improvement-point">💡 {{ r.improvement_point }}</p>
        </div>
      </section>

      <!-- 失分 + 卡壳 -->
      <section v-if="debrief.inappropriate_answers.length || debrief.stuck_points.length" class="card">
        <h3 class="card-title">失分与卡壳</h3>
        <div v-if="debrief.inappropriate_answers.length" class="sub-section">
          <p class="sub-title">不合适的回答</p>
          <ul class="list">
            <li v-for="(s, i) in debrief.inappropriate_answers" :key="'a' + i">{{ s }}</li>
          </ul>
        </div>
        <div v-if="debrief.stuck_points.length" class="sub-section">
          <p class="sub-title">卡壳处</p>
          <ul class="list">
            <li v-for="(s, i) in debrief.stuck_points" :key="'s' + i">{{ s }}</li>
          </ul>
        </div>
      </section>

      <!-- 后续建议（可执行） -->
      <section v-if="debrief.next_steps.length" class="card">
        <h3 class="card-title">后续建议</h3>
        <ul class="list steps">
          <li v-for="(s, i) in debrief.next_steps" :key="'n' + i">{{ s }}</li>
        </ul>
      </section>

      <!-- 亮点 / 弱项 pill -->
      <section v-if="debrief.highlights.length || debrief.weaknesses.length" class="card">
        <h3 class="card-title">亮点与弱项</h3>
        <div class="pill-row">
          <span v-for="(h, i) in debrief.highlights" :key="'h' + i" class="pill pill-good">{{ h }}</span>
          <span v-for="(w, i) in debrief.weaknesses" :key="'w' + i" class="pill pill-warn">{{ w }}</span>
        </div>
      </section>

      <!-- 对话回放（折叠） -->
      <section class="card">
        <button class="btn-text toggle-btn" type="button" @click="showReplay = !showReplay">
          {{ showReplay ? '收起' : '展开' }}完整对话回放（{{ debrief.round_by_round.length }} 轮）
        </button>
        <div v-if="showReplay" class="replay">
          <div v-for="(t, i) in debrief.round_by_round" :key="i" class="replay-round">
            <p class="replay-q"><b>Q{{ t.round }}</b>（{{ actionLabel(t.action) }}{{ t.is_probe ? '·追问' : '' }}）{{ t.question }}</p>
            <p class="replay-a">{{ t.answer || '（未作答）' }}</p>
            <p v-if="t.evaluation && t.evaluation.score != null" class="replay-score tnum" :style="scoreStyle(t.evaluation.score)">
              本题 {{ t.evaluation.score }} 分
            </p>
          </div>
        </div>
      </section>

      <!-- 底部操作 -->
      <div class="actions">
        <button class="btn-primary" type="button" @click="router.push('/interview/setup')">再来一场</button>
        <button class="btn-text" type="button" @click="router.push('/interview/history')">查看历史</button>
      </div>
    </template>

    <!-- 加载中 -->
    <div v-else class="card state-center">
      <span class="spinner lg" />
      <p class="state-title">加载复盘…</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDebrief } from '@/api/interview'
import type { DebriefReport, RoundAction } from '@/types/interview'

const route = useRoute()
const router = useRouter()
const sessionId = String(route.params['sessionId'])

const debrief = ref<DebriefReport | null>(null)
const avgScore = ref<number | null>(null)
const totalRounds = ref<number>(0)
const loading = ref(false)
const generating = ref(false)
const showReplay = ref(false)

// 逐题改进：把 round_reviews 与 round_by_round 按 round 关联（带上你的原回答）
const reviewsWithAnswer = computed(() => {
  const d = debrief.value
  if (!d) return []
  const byRound = new Map(d.round_by_round.map((t) => [t.round, t]))
  return d.round_reviews.map((r) => ({
    round: r.round,
    question: byRound.get(r.round)?.question || '',
    myAnswer: byRound.get(r.round)?.answer || '',
    better_version: r.better_version,
    improvement_point: r.improvement_point,
  }))
})

const scoreColor = computed(() => colorFor(avgScore.value ?? undefined))

// 分数配色：对齐设计 token（success / warning / error）
function colorFor(s?: number) {
  if ((s ?? 0) >= 75) return '#10b981'
  if ((s ?? 0) >= 50) return '#d97706'
  return '#ef4444'
}

function scoreStyle(score: number) {
  return { color: colorFor(score) }
}

function actionLabel(a: RoundAction) {
  return { probe: '追问', next: '换题', enter_qa: '反问', end: '结束' }[a] || a
}

async function loadDebrief() {
  loading.value = true
  generating.value = false
  try {
    const res: any = await getDebrief(sessionId)
    if (res.status === 'success' && res.data) {
      debrief.value = res.data.debrief
      avgScore.value = res.data.avg_score
      totalRounds.value = res.data.total_rounds || 0
      generating.value = false
    } else if (res.error_code === 'NOT_FINISHED') {
      generating.value = true
    } else {
      ElMessage.error(res.message || '加载复盘失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载复盘失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDebrief()
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
  margin-bottom: $spacing-lg;
}

.card-title {
  font-size: $font-size-lg;
  margin-bottom: $spacing-sm;

  .title-count {
    font-family: $font-body;
    font-weight: $font-weight-normal;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.section-hint {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-bottom: $spacing-md;
}

.state-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
  text-align: center;

  .state-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
  }

  .state-sub {
    font-size: $font-size-sm;
    color: $text-secondary;
    max-width: 40ch;
  }
}

/* 总评 */
.score-card {
  display: flex;
  align-items: center;
  gap: $spacing-xl;
  flex-wrap: wrap;
}

.overall-score {
  font-family: $font-heading;
  font-size: 64px;
  font-weight: $font-weight-bold;
  line-height: 1;
}

.overall-hint {
  color: $text-secondary;
  font-size: $font-size-xs;
  margin-top: $spacing-xs;
}

.one-line {
  flex: 1;
  min-width: 260px;
  color: $text-primary;
  line-height: $line-height-relaxed;
  border-left: 3px solid $primary-color;
  padding-left: $spacing-md;
}

/* 逐题改进 */
.review-item {
  border-top: 1px solid $border-light;
  padding: $spacing-md 0;

  &:first-child {
    border-top: none;
    padding-top: 0;
  }
}

.review-head {
  font-weight: $font-weight-semibold;
  font-size: $font-size-sm;
  margin-bottom: $spacing-sm;
}

.review-q {
  font-weight: $font-weight-normal;
  color: $text-secondary;
  margin-left: $spacing-sm;
}

.answer-block {
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-md;
  margin-bottom: $spacing-sm;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;

  .block-label {
    display: block;
    font-size: $font-size-xs;
    font-weight: $font-weight-semibold;
    margin-bottom: $spacing-xs;
  }

  p {
    white-space: pre-wrap;
  }

  &.mine {
    background: $bg-gray;
    color: $text-primary;
  }

  &.better {
    background: $success-light;
    color: $text-primary;

    .block-label {
      color: $success;
    }
  }
}

.improvement-point {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-top: $spacing-xs;
}

/* 失分/卡壳/建议 列表 */
.sub-section {
  margin-top: $spacing-sm;
}

.sub-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: $text-primary;
  margin-bottom: $spacing-sm;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    position: relative;
    padding-left: $spacing-lg;
    margin-bottom: $spacing-sm;
    font-size: $font-size-sm;
    line-height: $line-height-relaxed;
    color: $text-primary;

    &::before {
      content: '•';
      position: absolute;
      left: $spacing-xs;
      color: $primary-color;
      font-weight: $font-weight-bold;
    }
  }

  &.steps li::before {
    content: '✓';
    color: $success;
  }
}

/* pill */
.pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
}

.pill {
  font-size: $font-size-xs;
  padding: $spacing-xs $spacing-md;
  border-radius: $radius-full;
  line-height: $line-height-normal;
}

.pill-good {
  background: $success-light;
  color: $success;
}

.pill-warn {
  background: $warning-light;
  color: $warning;
}

/* 对话回放 */
.toggle-btn {
  background: none;
  border: none;
  color: $primary-color;
  cursor: pointer;
  font-size: $font-size-sm;
  padding: 0;

  &:hover {
    color: $primary-dark;
  }
}

.replay {
  margin-top: $spacing-md;
}

.replay-round {
  border-left: 2px solid $border-color;
  padding: $spacing-sm 0 $spacing-sm $spacing-md;
  margin-bottom: $spacing-md;
}

.replay-q {
  font-size: $font-size-sm;
  color: $text-primary;
  margin-bottom: $spacing-xs;

  b {
    color: $primary-color;
  }
}

.replay-a {
  font-size: $font-size-sm;
  color: $text-secondary;
  white-space: pre-wrap;
  margin-bottom: $spacing-xs;
}

.replay-score {
  font-size: $font-size-xs;
  font-weight: $font-weight-semibold;
}

/* 底部操作 */
.actions {
  display: flex;
  gap: $spacing-md;
  justify-content: center;
  margin-top: $spacing-xl;
}

.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-lg;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  transition: background $transition-base ease;

  &:hover:not(:disabled) {
    background: $primary-dark;
  }

  &:disabled {
    background: $bg-gray;
    cursor: not-allowed;
  }
}

.btn-text {
  background: none;
  border: none;
  color: $primary-color;
  cursor: pointer;
  font-size: $font-size-sm;
  padding: $spacing-sm $spacing-lg;

  &:hover {
    color: $primary-dark;
  }
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid $border-color;
  border-top-color: $primary-color;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;

  &.lg {
    width: 32px;
    height: 32px;
    border-width: 3px;
  }
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

  .overall-score {
    font-size: 48px;
  }
}
</style>
