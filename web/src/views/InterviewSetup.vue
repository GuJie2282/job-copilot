<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">INTERVIEW</p>
      <h1>模拟面试</h1>
      <p class="sub">配置一场专属面试：AI 面试官会基于你的画像出题、追问，结束后给出复盘与改进建议。</p>
    </header>

    <!-- 画像缺失引导（抄 JdMatcher） -->
    <div v-if="profileMissing" class="notice notice-warn">
      <p>尚未建立个人画像，无法进行模拟面试。</p>
      <button class="btn-primary" type="button" @click="goBuildProfile">去建立画像</button>
    </div>

    <!-- 面试类型 -->
    <section class="card">
      <h3 class="card-title">面试类型</h3>
      <div class="option-grid">
        <button
          v-for="t in TYPES"
          :key="t.key"
          type="button"
          :class="['option-card', { active: selectedType === t.key }]"
          :disabled="isLoading"
          @click="selectedType = t.key"
        >
          <span class="opt-title">{{ t.label }}</span>
          <span class="opt-desc">{{ t.desc }}</span>
        </button>
      </div>
    </section>

    <!-- 时长档位（语义化，不显示分钟） -->
    <section class="card">
      <h3 class="card-title">时长档位</h3>
      <div class="option-grid">
        <button
          v-for="it in INTENSITIES"
          :key="it"
          type="button"
          :class="['option-card', { active: selectedIntensity === it }]"
          :disabled="isLoading"
          @click="selectedIntensity = it"
        >
          <span class="opt-title">{{ INTENSITY_LABELS[it] }}</span>
          <span class="opt-desc">{{ INTENSITY_SUBTITLES[it] }}</span>
        </button>
      </div>
    </section>

    <!-- 面试模式（实战 / 教练） -->
    <section class="card">
      <h3 class="card-title">面试模式</h3>
      <div class="option-grid option-grid-2">
        <button
          v-for="m in MODES"
          :key="m.key"
          type="button"
          :class="['option-card', { active: selectedMode === m.key }]"
          :disabled="isLoading"
          @click="selectedMode = m.key"
        >
          <span class="opt-title">{{ m.label }}</span>
          <span class="opt-desc">{{ m.desc }}</span>
        </button>
      </div>
    </section>

    <!-- 面试官风格（人设 tone） -->
    <section class="card">
      <h3 class="card-title">面试官风格</h3>
      <div class="option-grid option-grid-3">
        <button
          v-for="p in PERSONAS"
          :key="p.key"
          type="button"
          :class="['option-card', { active: selectedTone === p.key }]"
          :disabled="isLoading"
          @click="selectedTone = p.key"
        >
          <span class="opt-title">{{ p.label }}</span>
          <span class="opt-desc">{{ p.desc }}</span>
        </button>
      </div>
      <div class="role-row">
        <input v-model="company" class="role-input" placeholder="目标公司（可选，如 字节跳动）" :disabled="isLoading" />
        <input v-model="position" class="role-input" placeholder="目标职位（可选，如 高级产品经理）" :disabled="isLoading" />
      </div>
      <p class="field-hint">填入目标公司 / 职位，面试官人设会更贴合（不填则用通用面试官）。</p>
    </section>

    <!-- 关联 JD（可选） -->
    <section class="card">
      <h3 class="card-title">关联 JD <span class="title-optional">（可选）</span></h3>
      <select v-model="selectedJd" class="jd-select" :disabled="isLoading || jdHistory.length === 0">
        <option value="">通用面试（不关联 JD）</option>
        <option v-for="h in jdHistory" :key="h.id" :value="h.id">
          {{ h.position_title || '未知岗位' }} · {{ formatTime(h.created_at) }}
        </option>
      </select>
      <p class="field-hint">关联后，面试会围绕 JD 差距重点考查；不关联则按画像目标岗位通用出题。</p>
    </section>

    <!-- 提交 -->
    <div class="submit-bar">
      <div v-if="isLoading" class="progress">
        <span class="spinner" />
        <p>{{ progressMessage }}</p>
      </div>
      <button class="btn-primary btn-large" type="button" :disabled="isLoading" @click="onStart">
        {{ isLoading ? '准备中…' : '开始面试' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { createSession } from '@/api/interview'
import { matchHistory } from '@/api/jd'
import { INTENSITY_LABELS, INTENSITY_SUBTITLES } from '@/types/interview'
import type { InterviewType, Intensity, InterviewMode, Persona, CreateSessionRequest } from '@/types/interview'
import type { MatchHistoryItem } from '@/types/jd'

const router = useRouter()
const userStore = useUserStore()

// 配置项常量（前端自维护；后端响应不返回 label）
const TYPES: { key: InterviewType; label: string; desc: string }[] = [
  { key: 'full', label: '全程', desc: '混合各题型 · 完整流程' },
  { key: 'behavioral', label: '行为面', desc: '讲经历 · STAR + 数据化' },
  { key: 'technical', label: '技术 / 专业面', desc: '岗位专业深度' },
  { key: 'case', label: '案例面', desc: '情景分析 · 结构化思维' },
  { key: 'motivation', label: '动机面', desc: 'why 你 · why 我们' },
]
const INTENSITIES: Intensity[] = ['short', 'normal', 'deep', 'full']
const MODES: { key: InterviewMode; label: string; desc: string }[] = [
  { key: 'real', label: '实战模式', desc: '面试官只问只追，不实时评分（沉浸）' },
  { key: 'coach', label: '教练模式', desc: '每答完一题，侧栏给一句改进提示' },
]
const PERSONAS: { key: string; label: string; desc: string }[] = [
  { key: '专业', label: '专业', desc: '正式 · 聚焦数据' },
  { key: '严肃', label: '严肃', desc: '严谨 · 追问细节' },
  { key: '轻松', label: '轻松', desc: '随和 · 像聊天' },
  { key: '风趣', label: '风趣', desc: '幽默 · 爱比喻' },
  { key: '温和', label: '温和', desc: '鼓励 · 循循善诱' },
  { key: '压力', label: '压力', desc: '质疑 · 追问到底' },
]
// tone → 注入面试官 system prompt 的风格描述（后端追问消费此字段）
const TONE_STYLE_PROMPTS: Record<string, string> = {
  '专业': '语气正式、聚焦逻辑与数据、追问因果',
  '严肃': '语气严谨、一板一眼、追问细节',
  '轻松': '轻松、随和、像聊天、适度生活化',
  '风趣': '轻松、爱用比喻、适时幽默',
  '温和': '鼓励式、循循善诱、降低压力',
  '压力': '质疑、施压、追问到底、考察抗压能力',
}

// 选中状态（默认值对齐后端默认：full / normal / real）
const selectedType = ref<InterviewType>('full')
const selectedIntensity = ref<Intensity>('normal')
const selectedMode = ref<InterviewMode>('real')
const selectedTone = ref<string>('专业')
const company = ref('')
const position = ref('')
const selectedJd = ref('')

const isLoading = ref(false)
const profileMissing = ref(false)
const progressMessage = ref('')
const jdHistory = ref<MatchHistoryItem[]>([])
let progressTimer: ReturnType<typeof setInterval> | null = null

// 分阶段进度提示（前端基于时间模拟，后端 session_setup 出题 + RAG 检索可能 5-15s）
function startProgress() {
  const stages = ['正在加载你的画像…', '正在检索面经库…', '正在生成个性化题库…', '面试官就位中…']
  let i = 0
  progressMessage.value = stages[0] ?? '准备中…'
  progressTimer = setInterval(() => {
    i = (i + 1) % stages.length
    progressMessage.value = stages[i] ?? progressMessage.value
  }, 3500)
}
function stopProgress() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = null
}

async function onStart() {
  isLoading.value = true
  profileMissing.value = false
  startProgress()
  try {
    // 组装人设（4 字段，后端 prompts.get_followup_prompt 全消费）
    const persona: Persona = {
      tone: selectedTone.value,
      role: {
        company: company.value.trim() || undefined,
        position: position.value.trim() || undefined,
      },
      stress_mode: selectedTone.value === '压力',
      style_prompt: TONE_STYLE_PROMPTS[selectedTone.value] || '',
    }
    const payload: CreateSessionRequest = {
      user_id: userStore.userId,
      interview_type: selectedType.value,
      intensity: selectedIntensity.value,
      interview_mode: selectedMode.value,
      persona,
      jd_result_id: selectedJd.value || undefined,
    }
    const res: any = await createSession(payload)
    if (res.status === 'success' && res.data) {
      // detail_warning 非阻断：画像经历不足时后端给的软警告，toast 提示
      if (res.data.detail_warning) ElMessage.warning(res.data.detail_warning)
      ElMessage.success('面试开始')
      router.push('/interview/room/' + res.data.session_id)
    } else {
      const code = res.error_code || res.data?.error_code
      if (code === 'PROFILE_MISSING') {
        profileMissing.value = true
        ElMessage.warning('请先建立个人画像')
      } else {
        ElMessage.error(res.message || '创建面试失败')
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '创建面试失败，请稍后重试')
  } finally {
    stopProgress()
    isLoading.value = false
  }
}

function goBuildProfile() {
  router.push('/resume-parser')
}

async function loadJdHistory() {
  if (!userStore.userId) return
  try {
    const res: any = await matchHistory(userStore.userId)
    if (res.status === 'success' && res.data) {
      jdHistory.value = res.data.items || []
    }
  } catch {
    // 静默失败：JD 关联是可选项，拉不到不影响面试
  }
}

function formatTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 10)
}

onMounted(() => {
  loadJdHistory()
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

  .title-optional {
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

  p {
    color: inherit;
  }
}

.notice-warn {
  background: $warning-light;
  border: 1px solid $warning;
  color: $warning;
}

/* 选项卡片网格 */
.option-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: $spacing-md;
}

.option-grid-2 {
  grid-template-columns: repeat(2, 1fr);
}

.option-grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.option-card {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  padding: $spacing-md;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $bg-white;
  cursor: pointer;
  text-align: left;
  transition: all $transition-base ease;

  &:hover:not(:disabled) {
    border-color: $primary-color;
  }

  &.active {
    border-color: $primary-color;
    background: $primary-lighter;
    box-shadow: 0 0 0 1px $primary-color inset;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .opt-title {
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }

  .opt-desc {
    font-size: $font-size-xs;
    color: $text-secondary;
    line-height: $line-height-normal;
  }
}

/* 公司 / 职位输入 */
.role-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-md;
  margin-top: $spacing-md;
}

.role-input {
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  font-family: $font-body;
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

.field-hint {
  margin-top: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-secondary;
}

/* JD 下拉 */
.jd-select {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  font-family: $font-body;
  background: $bg-white;
  box-sizing: border-box;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: $primary-color;
  }

  &:disabled {
    background: $bg-gray;
    cursor: not-allowed;
  }
}

/* 提交栏 */
.submit-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-md;
  margin-top: $spacing-xl;
}

.progress {
  display: flex;
  align-items: center;
  gap: $spacing-md;
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

.btn-large {
  padding: $spacing-md $spacing-2xl;
  font-size: $font-size-base;
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }

  .page-head h1 {
    font-size: $font-size-2xl;
  }

  .role-row,
  .option-grid-2,
  .option-grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>
