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
          <span v-if="inputMode === 'voice'" class="mode-tag voice">语音</span>
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
        <!-- 开局失败（后台出题异常） -->
        <div v-if="setupError" class="state-center">
          <span class="state-title">⚠ 面试开局失败</span>
          <span class="state-sub">生成题目时出错，请重新开始一场面试。</span>
          <button class="btn-primary" type="button" @click="retrySetup">重新开始</button>
        </div>

        <!-- 出题中（异步开局：后台正在生成第一题） -->
        <div v-else-if="setupPending" class="state-center">
          <span class="spinner lg" />
          <span class="state-title">面试官正在为你准备题目…</span>
          <span class="state-sub">通常需要 1 分钟左右，请稍候</span>
        </div>

        <!-- 加载中（初始进入） -->
        <div v-else-if="loading" class="state-center">
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
            :kind="m.kind"
            :duration="m.duration"
            :voice-status="m.voiceStatus"
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
      <!-- 文字模式（原有逻辑完全不变） -->
      <template v-if="inputMode === 'text'">
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
      </template>

      <!-- 语音模式：状态机指引栏（收音跟随面试状态） -->
      <div v-else class="voice-bar">
        <!-- idle：等面试官出题 -->
        <div v-if="voiceState === 'idle'" class="voice-hint">
          <span class="spinner sm" />
          <span>面试官正在准备问题…</span>
        </div>

        <!-- listening：收音中 -->
        <div v-else-if="voiceState === 'listening'" class="voice-row">
          <span class="voice-wave"><i /><i /><i /><i /><i /></span>
          <span class="voice-time">正在聆听 {{ formatDuration(recDuration) }}</span>
          <button class="btn-ghost" type="button" @click="onPause">⏸ 暂停</button>
          <button class="btn-primary btn-finish" type="button" @click="finishRecording">⏹ 说完了</button>
        </div>

        <!-- paused：已暂停 -->
        <div v-else-if="voiceState === 'paused'" class="voice-row">
          <span class="voice-wave paused"><i /><i /><i /><i /><i /></span>
          <span class="voice-time">已暂停 {{ formatDuration(recDuration) }}</span>
          <button class="btn-ghost" type="button" @click="onResume">▶ 继续</button>
          <button class="btn-primary btn-finish" type="button" @click="finishRecording">⏹ 说完了</button>
        </div>

        <!-- recognizing：识别中 -->
        <div v-else-if="voiceState === 'recognizing'" class="voice-hint">
          <span class="spinner sm" />
          <span>正在识别你的回答…</span>
        </div>

        <!-- submitting：评估中 -->
        <div v-else-if="voiceState === 'submitting'" class="voice-hint">
          <span class="spinner sm" />
          <span>面试官正在评估…</span>
        </div>

        <!-- failed：识别失败（2.3 基本版，3.x 完善语音条标红） -->
        <div v-else-if="voiceState === 'failed'" class="voice-row voice-failed">
          <span>⚠ {{ failedMessage }}</span>
          <button class="btn-ghost" type="button" @click="retryVoice">重新录制</button>
          <button class="btn-text" type="button" @click="switchToText">切文字</button>
        </div>

        <button v-if="voiceState !== 'failed'" class="btn-text btn-text-right" type="button" @click="switchToText">切换文字</button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MessageBubble from '@/components/MessageBubble.vue'
import { getSession, submitAnswer, transcribeVoice } from '@/api/interview'
import { useRecorder } from '@/composables/useRecorder'
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
  kind?: 'text' | 'voice'       // user 消息：文字气泡 / 语音条（3.x 起用语音条呈现）
  duration?: number             // voice 时长（秒）
  voiceStatus?: 'done' | 'failed' // voice 识别状态（3.x 起用）
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

// ── 异步开局：出题中轮询（add-async-interview-setup）──
const setupPending = ref(false)   // 后台出题中（status=setup_pending）
const setupError = ref(false)     // 开局失败（status=error 或轮询超时）
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollCount = 0
const POLL_INTERVAL = 3000
const POLL_MAX = 60  // 3s × 60 = 3 分钟轮询上限

// ── 语音模式状态（add-voice-interview）──
// inputMode：route.query.mode 优先（Setup 显式选），否则 localStorage 记忆，默认文字
const inputMode = ref<'text' | 'voice'>(
  route.query['mode'] === 'voice' ? 'voice'
    : (localStorage.getItem('interview_input_mode') === 'voice' ? 'voice' : 'text')
)
// voiceState：收音状态机——idle/listening/paused/recognizing/submitting/failed
type VoiceState = 'idle' | 'listening' | 'paused' | 'recognizing' | 'submitting' | 'failed'
const voiceState = ref<VoiceState>('idle')
const failedMessage = ref('识别失败')

// 录音引擎（onAutoStop：达 5 分钟上限自动结束，走与手动结束相同的转写提交流程）
const recorder = useRecorder({
  maxSeconds: 300,
  onAutoStop: (blob: Blob) => handleRecordedBlob(blob, recorder.duration.value),
})
const { status: recStatus, error: recError, duration: recDuration, start: recStart, pause: recPause, resume: recResume, stop: recStop, cancel: recCancel } = recorder

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
  setupError.value = false
  try {
    await fetchSession()
  } catch (e: any) {
    setupError.value = true
    ElMessage.error(e?.message || '加载面试失败')
  } finally {
    loading.value = false
  }
}

/** 拉一次会话状态并按 status 分支：finished→复盘 / error→失败态 / setup_pending→出题中轮询 / interviewing→渲染 */
async function fetchSession() {
  const res: any = await getSession(sessionId)
  if (res.status !== 'success' || !res.data) {
    setupError.value = true
    ElMessage.error(res.message || '加载面试失败')
    return
  }
  const st = res.data.status
  if (st === 'finished') {
    router.replace('/interview/debrief/' + sessionId)
    return
  }
  if (st === 'error') {
    setupError.value = true
    stopPolling()
    return
  }
  renderFromDetail(res.data)
  // setup_pending 且无第一题 → 后台还在出题，显示出题中态并轮询
  if (st === 'setup_pending' && !res.data.pending_question) {
    setupPending.value = true
    startPolling()
  } else {
    setupPending.value = false
    stopPolling()
  }
}

/** 出题中轮询：每 3s 拉一次，第一题就绪 / 失败 / 达 3min 上限则停 */
function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    pollCount++
    if (pollCount > POLL_MAX) {
      stopPolling()
      setupError.value = true
      return
    }
    await fetchSession()
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  pollCount = 0
}

/** 开局失败 → 回设置页重新开始 */
function retrySetup() {
  stopPolling()
  router.push('/interview/setup')
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

/**
 * 提交回答的核心逻辑（文字/语音共用，零侵入：语音识别结果以文本接入）。
 * 文字模式传 kind:'text'；语音模式传 kind:'voice' + duration（3.x 起语音条呈现）。
 */
async function sendAnswer(text: string, opts: { kind?: 'text' | 'voice'; duration?: number } = {}) {
  if (!text || !currentQuestion.value || submitting.value) return
  // user 消息立即入列（2.3：语音消息也带 text，MessageBubble 暂按文字渲染；3.x 改语音条）
  messages.value.push({
    role: 'user',
    text,
    kind: opts.kind ?? 'text',
    duration: opts.duration,
    voiceStatus: opts.kind === 'voice' ? 'done' : undefined,
  })
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

// 文字模式发送
async function onSend() {
  const text = answer.value.trim()
  if (!text || !currentQuestion.value || submitting.value) return
  answer.value = ''
  await sendAnswer(text, { kind: 'text' })
}

// Ctrl/⌘ + Enter 发送；普通 Enter 换行（长回答友好）
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    onSend()
  }
}

// ── 语音模式：录音控制 ──
function onPause() {
  recPause()
  voiceState.value = 'paused'
}
function onResume() {
  recResume()
  voiceState.value = 'listening'
}

/** 用户点"说完了"：停止录音 → 识别 → 提交 */
async function finishRecording() {
  if (voiceState.value !== 'listening' && voiceState.value !== 'paused') return
  const seconds = recDuration.value
  const blob = await recStop()
  voiceState.value = 'idle' // 临时态，handleRecordedBlob 会推进
  if (!blob || blob.size === 0) {
    failedMessage.value = '未录到内容，请重新回答'
    voiceState.value = 'failed'
    return
  }
  await handleRecordedBlob(blob, seconds)
}

/** 拿到录音 Blob → 转写 → 接入 sendAnswer（与手动结束共用，onAutoStop 也走这里） */
async function handleRecordedBlob(blob: Blob, seconds: number) {
  voiceState.value = 'recognizing'
  try {
    const res: any = await transcribeVoice(blob)
    if (res.status === 'success' && res.data?.text) {
      voiceState.value = 'submitting'
      await sendAnswer(res.data.text, { kind: 'voice', duration: seconds })
      // sendAnswer 完成后 submitting 置 false，watch 会触发下一轮 listening
      return
    }
    // 失败：按 error_code 给提示
    const code = res?.data?.error_code
    failedMessage.value = transcribeErrorMsg(code)
    voiceState.value = 'failed'
  } catch (e: any) {
    failedMessage.value = '语音识别失败，可重试或切文字'
    voiceState.value = 'failed'
  }
}

function transcribeErrorMsg(code?: string): string {
  switch (code) {
    case 'EMPTY_AUDIO':
    case 'NO_CONTENT':
      return '未识别到内容，请重新回答'
    case 'DECODE_FAILED':
      return '音频格式异常，请重新录制'
    case 'TRANSCRIBE_ERROR':
      return '识别失败，可重试或切文字'
    default:
      return '识别失败，可重试或切文字'
  }
}

/** 识别失败后重新录制 */
async function retryVoice() {
  voiceState.value = 'listening'
  const ok = await recStart()
  if (!ok) handleRecorderError(recError.value)
}

/** 麦克风不可用 → 降级文字（design.md 决策 9） */
function handleRecorderError(err: any) {
  inputMode.value = 'text'
  localStorage.setItem('interview_input_mode', 'text')
  const msgMap: Record<string, string> = {
    'permission-denied': '未获得麦克风权限，已切换文字输入',
    'no-device': '未检测到麦克风，已切换文字输入',
    'unsupported': '当前浏览器不支持语音输入，已切换文字',
    'recorder-error': '录音启动失败，已切换文字输入',
  }
  ElMessage.warning(msgMap[err as string] || '录音不可用，已切换文字输入')
}

/** 切换回文字模式 */
async function switchToText() {
  if (recStatus.value === 'recording' || recStatus.value === 'paused') {
    await recCancel()
  }
  inputMode.value = 'text'
  localStorage.setItem('interview_input_mode', 'text')
  voiceState.value = 'idle'
}

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function goBack() {
  router.push('/interview/setup')
}

/**
 * 收音跟随面试状态（design.md 决策 5）：
 *  - submitting 中：确保收音停（评估期间不应有录音残留）
 *  - 非 submitting 且当前题就绪：自动进入 listening（收音 ON）
 *  - 无题（面试官准备中）：idle
 * voiceState 处于 listening/paused 时不打断（用户主动控制中）；
 * 处于 recognizing/submitting/failed 时由对应流程自管理，不自动推进。
 */
watch([currentQuestion, submitting], async () => {
  if (inputMode.value !== 'voice') return
  // 评估中：停掉任何残留录音
  if (submitting.value) {
    if (recStatus.value === 'recording' || recStatus.value === 'paused') {
      await recCancel()
    }
    return
  }
  // 非提交态
  if (currentQuestion.value) {
    // 轮到用户：若不在 listening/paused（避免打断用户），自动开始收音
    if (voiceState.value !== 'listening' && voiceState.value !== 'paused' && voiceState.value !== 'failed') {
      voiceState.value = 'listening'
      const ok = await recStart()
      if (!ok) handleRecorderError(recError.value)
    }
  } else {
    // 无题：空闲
    if (voiceState.value !== 'idle') voiceState.value = 'idle'
  }
})

// 消息变化时自动滚到底
watch(() => messages.value.length, () => {
  nextTick(() => {
    messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })
  })
})

onMounted(() => {
  loadSession()
})

onBeforeUnmount(() => {
  stopPolling()
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

  &.voice {
    background: $warning-light;
    color: $warning;
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

.state-title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $ink;
}

.state-sub {
  font-size: $font-size-sm;
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

/* 语音模式指引栏 */
.voice-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: $spacing-md;
  min-height: 56px;
}

.voice-hint {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  color: $text-secondary;
  font-size: $font-size-sm;
  flex: 1;
}

.voice-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex: 1;
}

.voice-time {
  font-size: $font-size-sm;
  color: $text-primary;
  font-weight: $font-weight-medium;
  min-width: 110px;
}

.rec-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e53935;
  animation: rec-pulse 1.2s infinite;
  flex-shrink: 0;
}

@keyframes rec-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

/* 录音波形：listening 时柱条跳动（让用户「看到」在录），paused 时静止变灰 */
.voice-wave {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  height: 22px;
  margin-right: $spacing-xs;
  flex-shrink: 0;

  i {
    width: 3px;
    background: $primary-color;
    border-radius: 2px;
    transform-origin: center;
    animation: voice-wave 1s infinite ease-in-out;
  }
  i:nth-child(1) { height: 8px; animation-delay: 0s; }
  i:nth-child(2) { height: 16px; animation-delay: 0.15s; }
  i:nth-child(3) { height: 12px; animation-delay: 0.3s; }
  i:nth-child(4) { height: 18px; animation-delay: 0.45s; }
  i:nth-child(5) { height: 10px; animation-delay: 0.6s; }

  &.paused i {
    animation-play-state: paused;
    background: $text-disabled;
  }
}

@keyframes voice-wave {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

.btn-finish {
  margin-left: auto;
}

.btn-ghost {
  background: $bg-white;
  color: $text-primary;
  border: 1px solid $border-color;
  padding: $spacing-xs $spacing-md;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  transition: border-color $transition-base ease;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
  }
}

.btn-text {
  background: none;
  border: none;
  color: $text-secondary;
  cursor: pointer;
  font-size: $font-size-xs;
  padding: $spacing-xs $spacing-sm;

  &:hover {
    color: $primary-color;
  }
}

.btn-text-right {
  margin-left: auto;
}

.voice-failed {
  color: #e53935;
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
  flex-shrink: 0;

  &.lg {
    width: 32px;
    height: 32px;
    border-width: 3px;
  }

  &.sm {
    width: 14px;
    height: 14px;
    border-width: 2px;
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

  /* 语音控件窄屏适配：按钮缩小、时间不占定宽 */
  .voice-bar {
    flex-wrap: wrap;
    gap: $spacing-sm;
  }

  .voice-time {
    min-width: auto;
  }

  .btn-ghost,
  .btn-finish {
    padding: $spacing-xs $spacing-sm;
    font-size: $font-size-xs;
  }
}
</style>
