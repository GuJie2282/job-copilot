<template>
  <div class="room">
    <!-- 顶部栏：面试官人设 + 进度 + 返回 -->
    <header class="room-header">
      <button class="btn-back" type="button" @click="goBack">←</button>
      <div class="avatar">AI</div>
      <div class="header-info">
        <div class="header-title">
          AI 面试官
          <span :class="['mode-tag', mode]">{{ mode === 'coach' ? '教练模式' : '实战模式' }}</span>
        </div>
        <div class="header-sub">
          <span v-if="typeLabel">{{ typeLabel }}</span>
          <span v-if="intensityLabel"> · {{ intensityLabel }}</span>
          <span v-if="currentRound"> · 第 {{ currentRound }} 题</span>
        </div>
      </div>
    </header>

    <!-- 主体：消息流 + coach 侧栏 -->
    <div class="room-body">
      <div ref="messagesEl" class="messages">
        <!-- 加载中 -->
        <div v-if="loading" class="state-center">
          <span class="spinner lg" />
          <p>正在进入面试…</p>
        </div>

        <!-- 消息流 -->
        <template v-else>
          <MessageBubble
            v-for="(m, i) in messages"
            :key="i"
            :role="m.role"
            :text="m.text"
            :is-probe="m.isProbe"
            :is-q-a="m.isQA"
          />
          <!-- 等待后端（评估/出题） -->
          <div v-if="submitting" class="typing">
            <span class="dots"><i /><i /><i /></span>
            <span>{{ progressMessage }}</span>
          </div>
        </template>
      </div>

      <!-- coach 侧栏（仅教练模式） -->
      <aside v-if="mode === 'coach'" class="coach-panel">
        <h4 class="coach-title">教练提示</h4>
        <div v-if="coachHint" class="coach-hint">{{ coachHint }}</div>
        <div v-else class="coach-empty">答完一题后，这里会给你一句改进建议。</div>
        <p class="coach-foot">实时提示不发给面试官，只给你看。</p>
      </aside>
    </div>

    <!-- 底部输入栏 -->
    <footer class="input-bar">
      <textarea
        ref="inputEl"
        v-model="answer"
        class="answer-input"
        placeholder="输入你的回答…（Ctrl/⌘ + Enter 发送）"
        :disabled="!currentQuestion"
        rows="2"
        @keydown="onKeydown"
      />
      <button
        class="btn-primary btn-send"
        type="button"
        :disabled="submitting || !answer.trim() || !currentQuestion"
        @click="onSend"
      >
        {{ submitting ? '发送中…' : '发送' }}
      </button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MessageBubble from '@/components/MessageBubble.vue'
import { getSession, submitAnswer } from '@/api/interview'
import { INTENSITY_LABELS } from '@/types/interview'
import type { Question, InterviewMode } from '@/types/interview'

const route = useRoute()
const router = useRouter()
const sessionId = String(route.params['sessionId'])

/** 本地消息模型（IM 流渲染用） */
interface ChatMessage {
  role: 'interviewer' | 'user'
  text: string
  isProbe?: boolean
  isQA?: boolean
}

const messages = ref<ChatMessage[]>([])
const currentQuestion = ref<Question | null>(null)
const mode = ref<InterviewMode>('real')
const interviewType = ref<string>('')
const intensity = ref<string>('')

const answer = ref('')
const loading = ref(true)
const submitting = ref(false)
const coachHint = ref<string>('')
const progressMessage = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
let progressTimer: ReturnType<typeof setInterval> | null = null

const typeLabel = computed(() => TYPE_LABELS[interviewType.value] || '')
const intensityLabel = computed(() => INTENSITY_LABELS[intensity.value as keyof typeof INTENSITY_LABELS] || '')
const currentRound = computed(() => currentQuestion.value?.round || 0)

const TYPE_LABELS: Record<string, string> = {
  full: '全程面试',
  behavioral: '行为面',
  technical: '技术面',
  case: '案例面',
  motivation: '动机面',
  stress: '压力面',
}

/** 把后端 transcript（已答轮次）+ pending_question（当前题）渲染成消息流 */
function renderFromDetail(detail: any) {
  mode.value = (detail.interview_mode as InterviewMode) || 'real'
  interviewType.value = detail.interview_type || ''
  intensity.value = detail.intensity || ''

  const list: ChatMessage[] = []
  for (const t of detail.transcript || []) {
    list.push({ role: 'interviewer', text: t.question, isProbe: t.is_probe, isQA: t.qid === 'qa' })
    if (t.answer) list.push({ role: 'user', text: t.answer })
  }
  // 当前待答题（interrupt 挂起的题，transcript 不含）
  const pending = detail.pending_question
  if (pending) {
    currentQuestion.value = pending
    list.push({ role: 'interviewer', text: pending.question, isProbe: pending.is_probe, isQA: pending.qid === 'qa' })
  } else {
    currentQuestion.value = null
  }
  messages.value = list
}

async function loadSession() {
  loading.value = true
  try {
    const res: any = await getSession(sessionId)
    if (res.status === 'success' && res.data) {
      // finished 会话 GET detail 拿不到完整 transcript → 直接看复盘
      if (res.data.status === 'finished') {
        router.replace('/interview/debrief/' + sessionId)
        return
      }
      renderFromDetail(res.data)
    } else {
      ElMessage.error(res.message || '加载面试失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载面试失败')
  } finally {
    loading.value = false
  }
}

// 评估/出题等待进度（前端基于时间模拟，单轮 LLM 可能 5-10s）
function startProgress() {
  const stages = ['正在评估你的回答…', '面试官正在思考…', '正在准备下一个问题…']
  let i = 0
  progressMessage.value = stages[0] ?? '处理中…'
  progressTimer = setInterval(() => {
    i = (i + 1) % stages.length
    progressMessage.value = stages[i] ?? progressMessage.value
  }, 3500)
}
function stopProgress() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = null
}

async function onSend() {
  const text = answer.value.trim()
  if (!text || !currentQuestion.value || submitting.value) return

  // 用户消息立即入列（不等后端，体验顺滑）
  messages.value.push({ role: 'user', text })
  answer.value = ''
  submitting.value = true
  startProgress()
  try {
    const res: any = await submitAnswer(sessionId, text)
    if (res.status === 'success' && res.data) {
      const data = res.data
      if (data.interview_status === 'interviewing') {
        // coach 模式：展示上一轮 weakness 作为提示
        if (mode.value === 'coach' && data.coach_hint) {
          coachHint.value = data.coach_hint
        }
        if (data.next_question) {
          currentQuestion.value = data.next_question
          messages.value.push({
            role: 'interviewer',
            text: data.next_question.question,
            isProbe: data.next_question.is_probe,
            isQA: data.next_question.qid === 'qa',
          })
        } else {
          currentQuestion.value = null
        }
      } else if (data.interview_status === 'finished') {
        currentQuestion.value = null
        ElMessage.success('面试结束，正在生成复盘…')
        router.push('/interview/debrief/' + sessionId)
      }
    } else {
      ElMessage.error(res.message || '提交失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '提交失败，请重试')
  } finally {
    stopProgress()
    submitting.value = false
  }
}

// Ctrl/⌘ + Enter 发送；普通 Enter 换行（长回答友好）
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    onSend()
  }
}

function goBack() {
  router.push('/interview/setup')
}

// 消息变化时自动滚到底
watch(() => messages.value.length, () => {
  nextTick(() => {
    messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })
  })
})

onMounted(() => {
  loadSession()
})
</script>

<style scoped lang="scss">
.room {
  height: calc(100vh - 64px);  /* 减去 AppTopBar 高度 */
  display: flex;
  flex-direction: column;
  max-width: 1040px;
  margin: 0 auto;
}

/* 顶部栏 */
.room-header {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-color;
  background: $bg-white;
}

.btn-back {
  background: none;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  width: 32px;
  height: 32px;
  cursor: pointer;
  color: $text-secondary;
  font-size: $font-size-base;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
  }
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: $primary-color;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-size-sm;
  font-weight: $font-weight-bold;
  flex-shrink: 0;
}

.header-info {
  flex: 1;
}

.header-title {
  font-weight: $font-weight-semibold;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.mode-tag {
  font-size: $font-size-xs;
  padding: 2px $spacing-sm;
  border-radius: $radius-full;
  font-weight: $font-weight-medium;

  &.coach {
    background: $success-light;
    color: $success;
  }

  &.real {
    background: $primary-lighter;
    color: $primary-color;
  }
}

.header-sub {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 2px;
}

/* 主体 */
.room-body {
  flex: 1;
  display: flex;
  gap: $spacing-lg;
  overflow: hidden;
  padding: $spacing-lg;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-md;
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.state-center {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-md;
  color: $text-secondary;
}

/* 打字/等待指示器 */
.typing {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  color: $text-secondary;
  font-size: $font-size-xs;
  margin-top: $spacing-sm;
}

.dots {
  display: inline-flex;
  gap: 4px;

  i {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: $primary-color;
    animation: blink 1.4s infinite both;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

/* coach 侧栏 */
.coach-panel {
  width: 260px;
  flex-shrink: 0;
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-md;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.coach-title {
  font-size: $font-size-sm;
  color: $text-secondary;
  font-weight: $font-weight-semibold;
}

.coach-hint {
  background: $warning-light;
  border-left: 3px solid $warning;
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-sm;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  color: $text-primary;
  flex: 1;
}

.coach-empty {
  color: $text-disabled;
  font-size: $font-size-xs;
  flex: 1;
}

.coach-foot {
  font-size: $font-size-xs;
  color: $text-disabled;
}

/* 底部输入栏 */
.input-bar {
  display: flex;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-color;
  background: $bg-white;
}

.answer-input {
  flex: 1;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  font-family: $font-body;
  line-height: $line-height-normal;
  resize: none;
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

.btn-send {
  align-self: stretch;
  padding: $spacing-sm $spacing-xl;
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
  .room-body {
    flex-direction: column;
    padding: $spacing-sm;
  }

  .coach-panel {
    width: auto;
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;

    .coach-hint {
      flex: initial;
    }
  }
}
</style>
