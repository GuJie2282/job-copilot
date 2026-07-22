<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">MATCH</p>
      <h1>JD 匹配</h1>
      <p class="sub">粘贴目标岗位 JD，AI 解析要求并与你的画像比对，给出匹配度与差距清单。</p>
    </header>

    <!-- 画像缺失引导 -->
    <div v-if="profileMissing" class="notice notice-warn">
      <p>尚未建立个人画像，无法进行 JD 匹配。</p>
      <button class="btn-primary" type="button" @click="goBuildProfile">去建立画像</button>
    </div>

    <!-- JD 输入 -->
    <section class="card">
      <label class="field-label" for="jd">职位描述（JD）</label>
      <textarea
        id="jd"
        v-model="jdText"
        class="jd-input"
        placeholder="粘贴完整的 JD，建议包含「岗位职责」与「任职要求」…"
        :disabled="isLoading"
        rows="8"
      />
      <div class="input-meta">
        <span class="meta-count tnum">{{ jdText.length }} 字符（建议 ≥ 200）</span>
        <button
          class="btn-primary"
          type="button"
          :disabled="isLoading || !jdText.trim()"
          @click="onMatch"
        >
          {{ isLoading ? '分析中…' : '开始匹配' }}
        </button>
      </div>

      <!-- 分阶段进度提示（前端基于时间模拟，后端同步返回） -->
      <div v-if="isLoading" class="progress">
        <span class="spinner" />
        <p>{{ progressMessage }}</p>
      </div>
    </section>

    <!-- 匹配结果 -->
    <div v-if="result" class="result">
      <!-- 总分 + 维度雷达图 -->
      <section class="card score-card">
        <div class="overall">
          <div class="overall-score tnum" :style="{ color: scoreColor }">{{ result.overall_score ?? '-' }}</div>
          <div class="overall-level">{{ result.level }}</div>
          <div class="overall-hint">总分 / 100</div>
        </div>
        <ScoreRadar
          :skill="result.dimension_scores?.skill"
          :experience="result.dimension_scores?.experience"
          :education="result.dimension_scores?.education"
          :soft-skill="result.dimension_scores?.soft_skill"
        />
      </section>

      <!-- 红线预警 -->
      <div v-if="result.redline_hit" class="redline-alert">
        存在未满足的红线项（硬性门槛），可能严重影响录用，详见下方差距清单。
      </div>

      <!-- Gap 清单 -->
      <section class="card">
        <div class="gap-head">
          <h3 class="card-title">
            差距清单<span class="title-count tnum">（{{ (result.gaps || []).length }} 项，按严重度排序）</span>
          </h3>
          <button class="btn-primary" type="button" @click="goGenerate">据此生成简历</button>
        </div>
        <GapList :gaps="result.gaps" />
      </section>

      <!-- JD 要求画像概要 -->
      <section v-if="result.job_profile" class="card">
        <h3 class="card-title">JD 要求画像 · {{ result.job_profile.position_title || '岗位' }}</h3>
        <div class="req-grid">
          <div><b>硬技能：</b>{{ joinReqs(result.job_profile.hard_skills) }}</div>
          <div><b>软技能：</b>{{ joinReqs(result.job_profile.soft_skills) }}</div>
          <div><b>隐性偏好：</b>{{ joinReqs(result.job_profile.implicit_preferences) }}</div>
          <div><b>红线项：</b>{{ joinReqs(result.job_profile.red_lines) }}</div>
        </div>
      </section>
    </div>

    <!-- 历史匹配 -->
    <section class="card">
      <div class="history-head">
        <h3 class="card-title">历史匹配</h3>
        <button class="btn-text" type="button" :disabled="historyLoading" @click="loadHistory">刷新</button>
      </div>
      <div v-if="history.length === 0" class="empty-h">暂无历史匹配</div>
      <div v-for="h in history" :key="h.id" class="history-item">
        <span class="h-score tnum" :style="{ color: histColor(h.overall_score) }">{{ h.overall_score ?? '-' }}</span>
        <span class="h-pos">{{ h.position_title || '未知岗位' }}</span>
        <span class="h-time tnum">{{ formatTime(h.created_at) }}</span>
        <button class="btn-text" type="button" @click="viewDetail(h.id)">详情</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { matchJd, matchHistory, matchDetail } from '@/api/jd'
import type { MatchResult, MatchHistoryItem } from '@/types/jd'
import ScoreRadar from '@/components/ScoreRadar.vue'
import GapList from '@/components/GapList.vue'

const router = useRouter()
const userStore = useUserStore()

const jdText = ref('')
const isLoading = ref(false)
const progressMessage = ref('')
const result = ref<MatchResult | null>(null)
const profileMissing = ref(false)
const history = ref<MatchHistoryItem[]>([])
const historyLoading = ref(false)
let progressTimer: ReturnType<typeof setInterval> | null = null

// 分数配色：对齐设计 token（success / warning / error）
function colorFor(s?: number) {
  if ((s ?? 0) >= 75) return '#10b981' // $success
  if ((s ?? 0) >= 50) return '#d97706' // $warning
  return '#ef4444'                      // $error
}
const scoreColor = computed(() => colorFor(result.value?.overall_score))
function histColor(s?: number) {
  return colorFor(s)
}

function joinReqs(arr?: { requirement?: string }[]) {
  if (!arr || arr.length === 0) return '—'
  return arr.map((a) => a.requirement || '').filter(Boolean).join('、') || '—'
}

// 分阶段进度提示（前端基于时间模拟，后端同步返回）
function startProgress() {
  const stages = ['正在校验 JD…', '正在解析 JD 要求…', '正在加载你的画像…', '正在比对匹配度…', '正在生成差距分析…', '即将完成…']
  let i = 0
  progressMessage.value = stages[0] ?? '分析中…'
  progressTimer = setInterval(() => {
    i = (i + 1) % stages.length
    progressMessage.value = stages[i] ?? progressMessage.value
  }, 3500)
}
function stopProgress() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = null
}

async function onMatch() {
  if (jdText.value.trim().length < 50) {
    ElMessage.warning('JD 内容过少，请粘贴更完整的职位描述')
    return
  }
  isLoading.value = true
  profileMissing.value = false
  result.value = null
  startProgress()
  try {
    const res = await matchJd({ jd_text: jdText.value, user_id: userStore.userId })
    if (res.status === 'success' && res.data) {
      result.value = res.data
      ElMessage.success('匹配完成')
      loadHistory()  // 刷新历史
    } else {
      const code = (res as any).error_code || (res.data as any)?.error_code
      if (code === 'PROFILE_MISSING') {
        profileMissing.value = true
        ElMessage.warning('请先建立个人画像')
      } else {
        ElMessage.error(res.message || '匹配失败')
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '匹配失败，请稍后重试')
  } finally {
    stopProgress()
    isLoading.value = false
  }
}

function goBuildProfile() {
  router.push('/resume-parser')
}

async function loadHistory() {
  if (!userStore.userId) return
  historyLoading.value = true
  try {
    const res = await matchHistory(userStore.userId)
    if (res.status === 'success' && res.data) {
      history.value = res.data.items || []
    }
  } catch {
    // 静默失败
  } finally {
    historyLoading.value = false
  }
}

async function viewDetail(id: string) {
  try {
    const res = await matchDetail(id)
    if (res.status === 'success' && res.data) {
      result.value = res.data
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  } catch {
    ElMessage.error('加载详情失败')
  }
}

// 跳转到简历优化，带入本次匹配的 result_id + 岗位（供针对性生成）
function goGenerate() {
  const r = result.value
  if (!r?.result_id) {
    ElMessage.warning('请先完成匹配')
    return
  }
  const position = r.job_profile?.position_title || ''
  router.push({ path: '/resume-optimizer', query: { jd_result_id: r.result_id, position } })
}

function formatTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  loadHistory()
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
  margin-bottom: $spacing-md;

  .title-count {
    font-family: $font-body;
    font-weight: $font-weight-normal;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

/* 画像缺失引导 */
.notice {
  padding: $spacing-md $spacing-lg;
  border-radius: $radius-md;
  margin-bottom: $spacing-lg;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  flex-wrap: wrap;
}

.notice-warn {
  background: $warning-light;
  border: 1px solid $warning;
  color: $warning;

  p {
    color: inherit;
  }
}

/* JD 输入 */
.field-label {
  display: block;
  font-weight: $font-weight-medium;
  margin-bottom: $spacing-sm;
  color: $text-primary;
}

.jd-input {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-md;
  font-size: $font-size-sm;
  font-family: $font-body;
  line-height: $line-height-normal;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color $transition-base ease;

  &:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
  }

  &:disabled {
    background: $bg-gray;
  }
}

.input-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: $spacing-md;
  gap: $spacing-md;
  flex-wrap: wrap;
}

.meta-count {
  color: $text-secondary;
  font-size: $font-size-xs;
}

/* 通用按钮 */
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
    color: $text-disabled;
    cursor: not-allowed;
  }
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
}

/* 进度 */
.progress {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  margin-top: $spacing-md;
  color: $primary-color;
  font-size: $font-size-sm;
}

.spinner {
  width: 16px;
  height: 16px;
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

/* 结果区 */
.result {
  margin-top: $spacing-xl;
}

.score-card {
  display: flex;
  align-items: center;
  gap: $spacing-2xl;
  flex-wrap: wrap;
  justify-content: center;
}

.overall {
  text-align: center;
}

.overall-score {
  font-family: $font-heading;
  font-size: 72px;
  font-weight: $font-weight-bold;
  line-height: 1;
}

.overall-level {
  color: $ink;
  margin-top: $spacing-sm;
  font-weight: $font-weight-semibold;
  font-size: $font-size-lg;
}

.overall-hint {
  color: $text-secondary;
  font-size: $font-size-xs;
  margin-top: $spacing-xs;
}

.redline-alert {
  background: $error-light;
  border: 1px solid $error;
  color: $error;
  padding: $spacing-md $spacing-lg;
  border-radius: $radius-md;
  margin-bottom: $spacing-lg;
  font-weight: $font-weight-medium;
  font-size: $font-size-sm;
}

.req-grid {
  display: grid;
  gap: $spacing-sm;
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: $line-height-relaxed;

  b {
    color: $text-primary;
    font-weight: $font-weight-semibold;
  }
}

/* 历史匹配 */
.history-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;

  .card-title {
    margin-bottom: 0;
  }
}

.empty-h {
  color: $text-disabled;
  padding: $spacing-md;
  font-size: $font-size-sm;
}

.history-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm 0;
  border-bottom: 1px solid $border-light;
  font-size: $font-size-sm;

  &:last-child {
    border-bottom: none;
  }
}

.h-score {
  font-weight: $font-weight-bold;
  min-width: 36px;
  font-size: $font-size-base;
}

.h-pos {
  flex: 1;
  color: $text-primary;
}

.h-time {
  color: $text-disabled;
  font-size: $font-size-xs;
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }

  .page-head h1 {
    font-size: $font-size-2xl;
  }

  .overall-score {
    font-size: 56px;
  }

  .score-card {
    gap: $spacing-lg;
  }
}
</style>
