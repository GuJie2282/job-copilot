/**
 * 录音引擎 composable（add-voice-interview 阶段 2.1）
 * ================================================
 *
 * 封装浏览器 MediaRecorder，供 InterviewRoom 语音模式使用。
 * 职责：录音 start/pause/resume/stop + 麦克风权限 + 时长计时 + 上限保护 + 兼容性检测。
 *
 * 设计要点（对应 design.md 决策 6/7）：
 *  - 录音机式控制（非微信按住式）：自动开始、可暂停避噪、继续、手动结束
 *  - 暂停/继续间时长正确累计（pause 存已录秒数，resume 在此基础上续计）
 *  - 静默不自动断（用户决策 1a）；仅"达单段时长上限"时自动结束（5 分钟保护）
 *  - 产出 webm/opus Blob（浏览器 MediaRecorder 默认格式，后端 faster-whisper 经 PyAV 直读）
 *
 * 错误分类（供 UI 给不同降级提示，对应 design.md 决策 9）：
 *  - permission-denied  用户拒绝麦克风权限
 *  - no-device          无麦克风设备
 *  - unsupported        浏览器不支持 MediaRecorder
 *  - recorder-error     其他录音异常
 */
import { ref, onUnmounted } from 'vue'

export type RecorderStatus = 'idle' | 'recording' | 'paused' | 'unsupported'
export type RecorderError = 'permission-denied' | 'no-device' | 'unsupported' | 'recorder-error' | null

export interface UseRecorderOptions {
  /** 单段录音上限（秒），默认 300（5 分钟）。达上限自动结束。 */
  maxSeconds?: number
  /** 达上限自动结束时的回调（参数为录音 Blob），组件走与手动结束相同的转写提交流程 */
  onAutoStop?: (blob: Blob) => void
}

/** 检测当前环境是否支持 MediaRecorder（供组件提前判断是否降级文字） */
export function isRecorderSupported(): boolean {
  return typeof navigator !== 'undefined'
    && !!navigator.mediaDevices?.getUserMedia
    && typeof MediaRecorder !== 'undefined'
}

export function useRecorder(options: UseRecorderOptions = {}) {
  const maxSeconds = options.maxSeconds ?? 300
  const supported = isRecorderSupported()

  const status = ref<RecorderStatus>(supported ? 'idle' : 'unsupported')
  const error = ref<RecorderError>(null)
  const duration = ref(0) // 已录秒数（含暂停前累计）

  let mediaRecorder: MediaRecorder | null = null
  let stream: MediaStream | null = null
  let chunks: Blob[] = []
  let timer: ReturnType<typeof setInterval> | null = null
  let startAt = 0          // 当前(恢复后)段的开始时间戳
  let pausedElapsed = 0   // 暂停前已累计的秒数

  // ── 计时 ──
  function clearTimer() {
    if (timer) { clearInterval(timer); timer = null }
  }
  function tick() {
    duration.value = Math.floor((Date.now() - startAt) / 1000) + pausedElapsed
    if (duration.value >= maxSeconds) {
      clearTimer()
      // 达上限：走和手动结束一样的流程，组件在 onAutoStop 里转写提交
      stop().then((blob) => { if (blob) options.onAutoStop?.(blob) })
    }
  }
  function startTimer() {
    clearTimer()
    timer = setInterval(tick, 250)
  }

  // ── 选浏览器支持的音频格式（优先 webm/opus，后端 PyAV 直读）──
  function pickMime(): string | undefined {
    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']
    for (const m of candidates) {
      try {
        if (MediaRecorder.isTypeSupported(m)) return m
      } catch {
        // isTypeSupported 个别浏览器抛错，忽略继续尝试
      }
    }
    return undefined
  }

  // ── 开始录音 ──
  async function start(): Promise<boolean> {
    if (!supported) {
      status.value = 'unsupported'
      error.value = 'unsupported'
      return false
    }
    if (status.value === 'recording') return true

    // 申请麦克风权限
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e: any) {
      if (e?.name === 'NotAllowedError' || e?.name === 'SecurityError') {
        error.value = 'permission-denied'
      } else if (e?.name === 'NotFoundError' || e?.name === 'DevicesNotFoundError' || e?.name === 'OverconstrainedError') {
        error.value = 'no-device'
      } else {
        error.value = 'recorder-error'
      }
      status.value = 'idle'
      return false
    }

    chunks = []
    pausedElapsed = 0
    duration.value = 0
    const mime = pickMime()
    mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data)
    }
    mediaRecorder.start()
    status.value = 'recording'
    error.value = null
    startAt = Date.now()
    startTimer()
    return true
  }

  // ── 暂停（避噪思考，保留已录内容）──
  function pause() {
    if (status.value !== 'recording' || !mediaRecorder) return
    mediaRecorder.pause()
    status.value = 'paused'
    clearTimer()
    pausedElapsed = duration.value // 记下暂停前的累计秒数
  }

  // ── 继续 ──
  function resume() {
    if (status.value !== 'paused' || !mediaRecorder) return
    mediaRecorder.resume()
    status.value = 'recording'
    startAt = Date.now() // 在 pausedElapsed 基础上续计
    startTimer()
  }

  // ── 停止并返回录音 Blob ──
  function stop(): Promise<Blob | null> {
    return new Promise((resolve) => {
      if (!mediaRecorder) { resolve(null); return }
      clearTimer()
      const mr = mediaRecorder
      mr.onstop = () => {
        const blob = new Blob(chunks, { type: mr.mimeType || 'audio/webm' })
        cleanup()
        status.value = 'idle'
        resolve(blob)
      }
      if (mr.state !== 'inactive') {
        mr.stop()
      } else {
        cleanup()
        status.value = 'idle'
        resolve(null)
      }
    })
  }

  // ── 取消（不产出 Blob，用于放弃本次录音）──
  async function cancel() {
    clearTimer()
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.onstop = null
      try { mediaRecorder.stop() } catch { /* 忽略 */ }
    }
    cleanup()
    status.value = 'idle'
    duration.value = 0
  }

  function cleanup() {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop())
      stream = null
    }
    mediaRecorder = null
    chunks = []
  }

  // 组件卸载时释放资源（避免麦克风指示灯一直亮）
  onUnmounted(() => {
    clearTimer()
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      try { mediaRecorder.stop() } catch { /* 忽略 */ }
    }
    cleanup()
  })

  return { status, error, duration, isSupported: supported, start, pause, resume, stop, cancel }
}
