<template>
  <!-- 精修对话区：消息列表（用户右 / AI 左，AI 气泡含思考+回复+改写标记）+ 输入区 -->
  <div class="refine-chat">
    <div class="msg-list" v-auto-scroll>
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <!-- 用户消息（右） -->
        <div v-if="m.role === 'user'" class="bubble user-bubble">{{ m.text }}</div>

        <!-- AI 消息（左） -->
        <div v-else class="ai-msg">
          <!-- 思考过程：thinking 展开看流，applying/done 折叠；summary 显示阶段 + 动态点 -->
          <div v-if="m.reasoning" class="reasoning">
            <div class="reasoning-head" @click="m.reasoningOpen = !m.reasoningOpen">
              <template v-if="m.status === 'thinking'">🧠 AI 思考中<span class="dots"><i></i><i></i><i></i></span></template>
              <template v-else-if="m.status === 'applying'">✏️ 修改中<span class="dots"><i></i><i></i><i></i></span></template>
              <template v-else>🧠 AI 思考<span class="reasoning-toggle">{{ m.reasoningOpen ? '收起' : '展开' }}</span></template>
            </div>
            <pre v-if="m.pending || m.reasoningOpen">{{ (m.reasoning.split('<<<RESUME>>>')[0] ?? '').split('<<<REPLY>>>')[0]?.trim() }}{{ m.pending ? '▍' : '' }}</pre>
          </div>
          <!-- 回复正文 -->
          <div v-if="m.text" class="bubble ai-bubble">{{ m.text }}</div>
          <!-- 改写结果标记 -->
          <span v-if="m.resumed === true" class="chip chip-ok">📄 简历已更新（第 {{ m.round ?? '-' }} 轮 · 见左侧）</span>
          <span v-else-if="m.resumed === false && !m.pending && m.text" class="chip chip-warn">⚠️ 本次未改简历，沿用上一版</span>
          <!-- 无 reasoning details 时的阶段提示（初始等待 / 无思考的修改中） -->
          <span v-if="m.pending && !m.reasoning" class="typing">
            <template v-if="m.status === 'applying'">✏️ 修改中</template>
            <template v-else>🧠 AI 思考中</template>
            <span class="dots"><i></i><i></i><i></i></span>
          </span>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="composer">
      <textarea
        v-model="draft"
        class="input"
        rows="2"
        placeholder="告诉 AI 怎么改，如：第二段经历补量化数据；把 AI 项目前置…"
        @keydown.enter.exact.prevent="onSend"
      />
      <div class="composer-actions">
        <button class="btn-success" type="button" :disabled="loading || !canFinalize" @click="emit('finalize')">
          ✅ 满意定稿
        </button>
        <button class="btn-primary" type="button" :disabled="loading || !draft.trim()" @click="onSend">
          {{ loading ? '改写中…' : '发送（回车）' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// AI 气泡消息结构（reasoning 思考 / text 回复 / resumed 改写结果 / pending 流式中）
interface ChatMessage {
  role: 'user' | 'ai'
  text: string
  reasoning?: string
  resumed?: boolean
  pending?: boolean
  round?: number
  status?: 'thinking' | 'applying' | 'done'
  reasoningOpen?: boolean
}

const props = defineProps<{
  messages: ChatMessage[]
  loading: boolean
  canFinalize: boolean
  round: number
}>()

const emit = defineEmits<{
  send: [text: string]
  finalize: []
}>()

const draft = ref('')

function onSend() {
  const t = draft.value.trim()
  if (!t || props.loading) return
  emit('send', t)
  draft.value = ''
}
</script>

<style scoped lang="scss">
.refine-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-lg;
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.msg {
  display: flex;
  &.user { justify-content: flex-end; }
  &.ai { justify-content: flex-start; }
}

.bubble {
  max-width: 85%;
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-lg;
  font-size: $font-size-sm;
  line-height: 1.6;
  word-break: break-word;
}

.user-bubble {
  background: $primary-color;
  color: #fff;
  border-bottom-right-radius: $radius-sm;
}

.ai-bubble {
  background: $bg-gray;
  color: $text-primary;
  border-bottom-left-radius: $radius-sm;
  white-space: pre-wrap;
}

.ai-msg {
  max-width: 90%;
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  align-items: flex-start;
}

/* 思考过程：灰斜体、可折叠（与生成阶段思考区视觉一致，弱化色调区别于业务结果） */
.reasoning {
  width: 100%;
  .reasoning-head {
    cursor: pointer;
    color: $text-secondary;
    font-size: $font-size-xs;
    user-select: none;
  }
  .reasoning-toggle {
    margin-left: $spacing-xs;
    color: $text-disabled;
  }
  pre {
    margin-top: $spacing-xs;
    padding: $spacing-sm $spacing-md;
    background: rgba(0, 0, 0, 0.03);
    border-radius: $radius-md;
    color: $text-secondary;
    font-style: italic;
    font-size: $font-size-xs;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: $font-body;
  }
}

.chip {
  align-self: flex-start;
  font-size: $font-size-xs;
  padding: 2px $spacing-sm;
  border-radius: $radius-sm;
}
.chip-ok { background: rgba($success, 0.12); color: $success; }
.chip-warn { background: rgba($warning, 0.12); color: $warning; }

.typing {
  color: $text-secondary;
  font-size: $font-size-xs;
  font-style: italic;
  padding: $spacing-xs $spacing-sm;
}

/* 动态省略号（思考中/修改中：三个点错开跳动） */
.dots {
  display: inline-flex;
  gap: 3px;
  margin-left: 5px;
  vertical-align: middle;
}
.dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  animation: refine-dot 1.2s infinite ease-in-out;
}
.dots i:nth-child(2) { animation-delay: 0.2s; }
.dots i:nth-child(3) { animation-delay: 0.4s; }
@keyframes refine-dot {
  0%, 80%, 100% { opacity: 0.25; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.1); }
}

.composer {
  border-top: 1px solid $border-color;
  padding: $spacing-md;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.input {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  line-height: 1.5;
  resize: none;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color $transition-base ease;

  &:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
  }
  &:disabled { background: $bg-gray; }
}

.composer-actions {
  display: flex;
  gap: $spacing-sm;
  justify-content: flex-end;
}

.btn-primary, .btn-success {
  color: #fff;
  border: none;
  padding: $spacing-xs $spacing-lg;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;

  &:disabled {
    background: $bg-gray;
    color: $text-disabled;
    cursor: not-allowed;
  }
}
.btn-primary {
  background: $primary-color;
  &:hover:not(:disabled) { background: $primary-dark; }
}
.btn-success {
  background: $success;
  &:hover:not(:disabled) { filter: brightness(0.95); }
}
</style>
