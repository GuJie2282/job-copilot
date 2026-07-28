<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">GENERATE</p>
      <h1>简历优化</h1>
      <p class="sub">基于你的画像 + 目标岗位，从零生成一份定制简历，经 6 维评估与格式校验，导出 A4 PDF。</p>
    </header>

    <!-- 画像缺失引导 -->
    <div v-if="profileMissing" class="notice notice-warn">
      <p>尚未建立个人画像，无法生成简历。</p>
      <button class="btn-primary" type="button" @click="goBuildProfile">去建立画像</button>
    </div>

    <!-- 生成输入 -->
    <section class="card">
      <label class="field-label" for="position">目标岗位</label>
      <input
        id="position"
        v-model="targetPosition"
        class="position-input"
        placeholder="如：AI 产品经理 / 后端工程师"
        :disabled="loading"
      />

      <!-- 两种方式切换 -->
      <div class="mode-tabs">
        <button
          type="button"
          class="mode-tab"
          :class="{ active: mode === 'paste' }"
          :disabled="loading"
          @click="mode = 'paste'"
        >粘贴岗位 JD（可选）</button>
        <button
          type="button"
          class="mode-tab"
          :class="{ active: mode === 'match' }"
          :disabled="loading"
          @click="switchToMatch"
        >关联 JD 匹配</button>
      </div>

      <!-- 方式 A：粘贴岗位 JD（可选） -->
      <div v-if="mode === 'paste'" class="mode-panel">
        <label class="field-label" for="jdtext">岗位 JD（可选，留空则通用生成）</label>
        <textarea
          id="jdtext"
          v-model="jdText"
          class="jd-textarea"
          rows="5"
          :disabled="loading"
          placeholder="粘贴目标岗位的 JD 原文，生成时会针对它定制；留空则仅基于画像通用生成"
        />
        <p class="mode-hint">留空 = 通用简历；填了 = 针对 JD 定制。</p>
      </div>

      <!-- 方式 B：关联 JD 匹配 -->
      <div v-else class="mode-panel">
        <label class="field-label" for="matchsel">选择已有的 JD 匹配</label>
        <div v-if="jdMatches.length === 0" class="match-empty">
          还没有匹配记录，去 <router-link to="/jd-matcher">做一次 JD 匹配</router-link> 后再来
        </div>
        <select
          v-else
          id="matchsel"
          v-model="selectedMatchId"
          class="match-select"
          :disabled="loading"
          @change="onSelectMatch"
        >
          <option :value="''">— 请选择 —</option>
          <option v-for="m in jdMatches" :key="m.id" :value="m.id">
            {{ m.position_title || '未知岗位' }} · {{ m.overall_score ?? '-' }} 分 · {{ formatTime(m.created_at) }}
          </option>
        </select>
        <p class="mode-hint">选中后，用该匹配的差距清单（Gap）做针对性生成，并自动填充岗位名。</p>
      </div>

      <div class="input-meta">
        <span class="meta-hint">生成约需 2-5 分钟（含评估迭代与导出）</span>
        <button
          class="btn-primary"
          type="button"
          :disabled="loading || !targetPosition.trim()"
          @click="onGenerate"
        >
          {{ loading ? '生成中…' : '生成简历' }}
        </button>
      </div>

      <!-- 分阶段进度 -->
      <div v-if="loading" class="progress">
        <span class="spinner" />
        <p>{{ progressMessage }}</p>
      </div>

      <!-- AI 思考过程（reasoning，glm-4.5 思考 token，灰色斜体可折叠） -->
      <details v-if="loading && reasoningText" style="margin-top: 0.75rem;">
        <summary style="cursor: pointer; color: #6b7280; font-size: 0.85rem;">🧠 AI 思考中…（可展开）</summary>
        <pre v-auto-scroll style="margin-top: 0.5rem; padding: 0.75rem; background: #f9fafb; border-radius: 6px; color: #6b7280; font-style: italic; font-size: 0.85rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; max-height: 300px; overflow-y: auto;">{{ reasoningText }}▍</pre>
      </details>
    </section>

    <!-- 生成结果 -->
    <div v-if="result" class="result">
      <!-- 结果顶部 CTA（双 CTA：看完评估即可精修，不用滚到 refine-card） -->
      <div v-if="result.refine_offered && result.resume_id" class="result-cta">
        <span class="rc-hint">简历已生成，想再打磨？进入精修按反馈逐轮改写</span>
        <button class="btn-primary" type="button" @click="goRefine(result.resume_id!)">进入精修 →</button>
      </div>
      <section class="card">
        <h3 class="card-title">
          质量评估<span v-if="result.version" class="title-count tnum">（v{{ result.version }} · draft）</span>
        </h3>
        <ResumeEvalReport :eval-report="result.eval_report" />
      </section>

      <section class="card">
        <h3 class="card-title">简历预览</h3>
        <ResumePreview :html="result.html" />
      </section>

      <section v-if="result.refine_offered && result.resume_id" class="card refine-card">
        <div>
          <h3 class="card-title">想再打磨？</h3>
          <p class="refine-hint">进入精修模式，按你的反馈逐轮改写，满意后定稿导出 PDF。</p>
        </div>
        <button class="btn-primary" type="button" @click="goRefine(result.resume_id!)">进入精修</button>
      </section>

      <section class="card">
        <div class="md-head">
          <h3 class="card-title">Markdown 原文</h3>
          <button class="btn-text" type="button" @click="copyMd">复制</button>
        </div>
        <pre class="md-pre">{{ result.content_md }}</pre>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { generateResumeStream } from '@/api/resume'
import { matchHistory } from '@/api/jd'
import type { MatchHistoryItem } from '@/types/jd'
import ResumeEvalReport from '@/components/ResumeEvalReport.vue'
import ResumePreview from '@/components/ResumePreview.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const targetPosition = ref('')
const jdText = ref('')
const mode = ref<'paste' | 'match'>('paste') // 方式 A 粘贴 / 方式 B 关联匹配
const jdMatches = ref<MatchHistoryItem[]>([])
const selectedMatchId = ref<string>('')
const jdResultId = ref<string | undefined>(undefined)

const loading = ref(false)
const progressMessage = ref('')
const reasoningText = ref('')  // AI 思考过程（reasoning，思考区展示）
const profileMissing = ref(false)
const result = ref<any>(null)
// 进度由 SSE onStage 真实驱动（取代旧的定时器模拟）

function formatTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

async function loadMatches() {
  if (!userStore.userId) return
  try {
    const res = await matchHistory(userStore.userId)
    if (res.status === 'success' && res.data) {
      jdMatches.value = res.data.items || []
    }
  } catch {
    // 静默失败
  }
}

function switchToMatch() {
  mode.value = 'match'
  if (jdMatches.value.length === 0) loadMatches()
}

function onSelectMatch() {
  if (!selectedMatchId.value) {
    jdResultId.value = undefined
    return
  }
  jdResultId.value = selectedMatchId.value
  // 自动填充岗位名（若用户未手写）
  const m = jdMatches.value.find((x) => x.id === selectedMatchId.value)
  if (m?.position_title && !targetPosition.value.trim()) {
    targetPosition.value = m.position_title
  }
}

function onGenerate() {
  if (!targetPosition.value.trim()) {
    ElMessage.warning('请填写目标岗位')
    return
  }
  loading.value = true
  profileMissing.value = false
  result.value = null
  progressMessage.value = '准备画像与岗位…'
  reasoningText.value = ''  // 思考区重置

  // 按方式组装请求：方式 B 用 jd_result_id；方式 A 用 jd_text（可选）
  const payload: {
    target_position: string
    user_id?: string
    jd_result_id?: string
    jd_text?: string
  } = {
    target_position: targetPosition.value,
    user_id: userStore.userId,
  }
  if (mode.value === 'match' && jdResultId.value) {
    payload.jd_result_id = jdResultId.value
  } else if (mode.value === 'paste' && jdText.value.trim()) {
    payload.jd_text = jdText.value.trim()
  }

  // 流式生成：onStage 真实进度 + onReasoning 思考过程 + onDone 定稿 + onError
  // （去掉 content 打字机——简历最终由 done 一次性给出）
  generateResumeStream(payload, {
    onStage: (p) => { progressMessage.value = p.message },
    onReasoning: (p) => { reasoningText.value += p.delta },
    onDone: (d) => {
      result.value = d
      loading.value = false
      progressMessage.value = ''
      reasoningText.value = ''  // 定稿后清思考区（result 区显示简历）
      ElMessage.success('简历生成完成')
    },
    onError: (e) => {
      loading.value = false
      progressMessage.value = ''
      reasoningText.value = ''
      if (e.error_code === 'PROFILE_MISSING') {
        profileMissing.value = true
        ElMessage.warning('请先建立个人画像')
      } else {
        ElMessage.error(e.error_message || '生成失败')
      }
    },
  })
}

function goBuildProfile() {
  router.push('/resume-parser')
}

function goRefine(resumeId: string) {
  router.push(`/resume-refine/${resumeId}`)
}

async function copyMd() {
  if (!result.value?.content_md) return
  try {
    await navigator.clipboard.writeText(result.value.content_md)
    ElMessage.success('已复制 Markdown')
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

onMounted(() => {
  // 从 JD 匹配跳转带入：jd_result_id + position → 自动切到「关联匹配」模式
  const qJd = (route.query['jd_result_id'] as string) || ''
  const qPos = (route.query['position'] as string) || ''
  if (qJd) {
    mode.value = 'match'
    selectedMatchId.value = qJd
    jdResultId.value = qJd
    targetPosition.value = qPos
    loadMatches()
  } else {
    targetPosition.value = qPos
  }
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
    font-weight: $font-weight-normal;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

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
}

.field-label {
  display: block;
  font-weight: $font-weight-medium;
  margin-bottom: $spacing-sm;
  color: $text-primary;
}

.position-input {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
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

/* 两种方式切换 */
.mode-tabs {
  display: flex;
  gap: $spacing-xs;
  margin-top: $spacing-md;
  margin-bottom: $spacing-md;
  border-bottom: 1px solid $border-light;
}

.mode-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: $spacing-sm $spacing-md;
  cursor: pointer;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: all $transition-base ease;

  &:hover:not(:disabled) {
    color: $primary-color;
  }

  &.active {
    color: $primary-color;
    border-bottom-color: $primary-color;
    font-weight: $font-weight-medium;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
}

.mode-panel {
  margin-bottom: $spacing-sm;
}

.jd-textarea {
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

.match-select {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  background: $bg-white;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: $primary-color;
  }
}

.match-empty {
  padding: $spacing-md;
  background: $bg-gray;
  border-radius: $radius-md;
  font-size: $font-size-sm;
  color: $text-secondary;

  a {
    color: $primary-color;
  }
}

.mode-hint {
  margin-top: $spacing-xs;
  font-size: $font-size-xs;
  color: $text-disabled;
}

.input-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: $spacing-md;
  gap: $spacing-md;
  flex-wrap: wrap;
}

.meta-hint {
  color: $text-secondary;
  font-size: $font-size-xs;
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

.result {
  margin-top: $spacing-xl;
}

.refine-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  flex-wrap: wrap;
  background: rgba($primary-color, 0.04);
  border-color: rgba($primary-color, 0.2);

  .refine-hint {
    color: $text-secondary;
    font-size: $font-size-sm;
    margin-top: $spacing-xs;
  }
}

.md-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-sm;

  .card-title {
    margin-bottom: 0;
  }
}

.md-pre {
  background: $bg-gray;
  border-radius: $radius-md;
  padding: $spacing-md;
  font-family: $font-mono;
  font-size: $font-size-xs;
  line-height: $line-height-normal;
  color: $text-primary;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow: auto;
  margin: 0;
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }
}
/* 结果顶部 CTA（双 CTA：看完评估即可精修，不用滚到 refine-card） */
.result-cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-lg;
  background: $bg-white;
  border: 1px solid $border-color;
  border-left: 3px solid $accent-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-md $spacing-xl;
  margin-bottom: $spacing-lg;
  flex-wrap: wrap;

  .rc-hint {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}
</style>
