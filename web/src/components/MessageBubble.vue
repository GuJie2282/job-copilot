<template>
  <div :class="['msg', role]">
    <!-- 面试官头像（用户消息不显示，靠右对齐即可） -->
    <div v-if="role === 'interviewer'" class="avatar">AI</div>
    <div class="bubble-wrap">
      <!-- 追问角标：同一题的深挖 -->
      <span v-if="isProbe" class="probe-tag">追问</span>
      <!-- 反问环节标记 -->
      <span v-else-if="isQA" class="qa-tag">反问环节</span>

      <!-- 语音条（用户语音回答 · add-voice-interview 决策 8：沉浸呈现 + 点击回看） -->
      <div
        v-if="role === 'user' && kind === 'voice'"
        :class="['voice-bubble', { failed: voiceStatus === 'failed', expanded: voiceExpanded }]"
        :title="voiceExpanded ? '点击收起' : '点击查看识别文字'"
        @click="toggleVoice"
      >
        <span class="voice-icon">{{ voiceStatus === 'failed' ? '⚠' : (voiceExpanded ? '⏸' : '▶') }}</span>
        <span class="voice-bars"><i v-for="n in 8" :key="n" :style="{ height: barHeight(n) }" /></span>
        <span class="voice-dur">{{ formatDuration(duration || 0) }}</span>
        <!-- 展开后显示识别文字（可回看，不进消息流；失败时显示失败提示） -->
        <div v-if="voiceExpanded" class="voice-text">
          {{ voiceStatus === 'failed' ? '识别失败，请在下方重试或切换文字' : text }}
        </div>
      </div>

      <!-- 文字气泡（默认） -->
      <div v-else class="bubble">{{ text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * IM 聊天气泡：面试官消息靠左（带头像），用户回答靠右。
 * - isProbe：同一题的追问（显示「追问」角标）
 * - isQA：进入反问环节（qid === 'qa'）
 * - kind='voice'：用户语音回答 → 以语音条呈现（不显示文字保沉浸），
 *   点击展开识别文字（可回看）；voiceStatus='failed' 时标红。
 */
import { ref } from 'vue'

defineProps<{
  role: 'interviewer' | 'user'
  text: string
  isProbe?: boolean
  isQA?: boolean
  kind?: 'text' | 'voice'
  duration?: number
  voiceStatus?: 'done' | 'failed'
}>()

const voiceExpanded = ref(false)
function toggleVoice() {
  voiceExpanded.value = !voiceExpanded.value
}
function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}
// 固定波形高度（避免每次渲染抖动；8 条柱状模拟语音波形）
const BAR_HEIGHTS = [6, 12, 8, 16, 10, 14, 7, 11]
function barHeight(n: number): string {
  return BAR_HEIGHTS[(n - 1) % BAR_HEIGHTS.length] + 'px'
}
</script>

<style scoped lang="scss">
.msg {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;

  /* 用户消息靠右 */
  &.user {
    flex-direction: row-reverse;

    .bubble {
      background: $primary-color;
      color: #fff;
      border-bottom-right-radius: $radius-sm;
    }
  }

  /* 面试官消息靠左 */
  &.interviewer {
    .bubble {
      background: $bg-gray;
      color: $text-primary;
      border-bottom-left-radius: $radius-sm;
    }
  }
}

.avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: $primary-color;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-size-xs;
  font-weight: $font-weight-bold;
}

.bubble-wrap {
  max-width: 75%;
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.user .bubble-wrap {
  align-items: flex-end;
}

.bubble {
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-lg;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  word-break: break-word;
  white-space: pre-wrap;
}

/* 语音条（用户语音回答） */
.voice-bubble {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-lg;
  background: $primary-color;
  color: #fff;
  cursor: pointer;
  user-select: none;
  min-width: 150px;
  border-bottom-right-radius: $radius-sm;
  transition: background $transition-base ease, transform $transition-base ease;

  &:hover {
    background: $primary-dark;
    transform: translateY(-1px);
  }

  &.failed {
    background: $error;
    &:hover { background: darken($error, 5%); }
  }

  .voice-icon {
    font-size: $font-size-xs;
    flex-shrink: 0;
  }

  .voice-bars {
    display: flex;
    align-items: center;
    gap: 2px;
    flex: 1;
    min-width: 60px;

    i {
      width: 3px;
      background: rgba(255, 255, 255, 0.75);
      border-radius: 2px;
      display: inline-block;
    }
  }

  .voice-dur {
    font-size: $font-size-xs;
    opacity: 0.9;
    flex-shrink: 0;
  }

  .voice-text {
    flex-basis: 100%;
    margin-top: $spacing-xs;
    padding-top: $spacing-xs;
    border-top: 1px solid rgba(255, 255, 255, 0.3);
    font-size: $font-size-xs;
    line-height: $line-height-normal;
    white-space: pre-wrap;
    word-break: break-word;
    color: rgba(255, 255, 255, 0.95);
    animation: voice-text-in 0.2s ease;
  }
}

/* 识别文字展开淡入 */
@keyframes voice-text-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.probe-tag,
.qa-tag {
  align-self: flex-start;
  font-size: $font-size-xs;
  padding: 2px $spacing-sm;
  border-radius: $radius-full;
  font-weight: $font-weight-medium;
}

.probe-tag {
  background: $accent-color;
  color: #fff;
}

.qa-tag {
  background: $success-light;
  color: $success;
}

.user .probe-tag,
.user .qa-tag {
  align-self: flex-end;
}

@media (max-width: $container-md) {
  .bubble-wrap {
    max-width: 85%;
  }

  .voice-bubble {
    min-width: 120px;
  }
}
</style>
