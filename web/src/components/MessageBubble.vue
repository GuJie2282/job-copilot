<template>
  <div :class="['msg', role]">
    <!-- 面试官头像（用户消息不显示，靠右对齐即可） -->
    <div v-if="role === 'interviewer'" class="avatar">AI</div>
    <div class="bubble-wrap">
      <!-- 追问角标：同一题的深挖 -->
      <span v-if="isProbe" class="probe-tag">追问</span>
      <!-- 反问环节标记 -->
      <span v-else-if="isQA" class="qa-tag">反问环节</span>
      <div class="bubble">{{ text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * IM 聊天气泡：面试官消息靠左（带头像），用户回答靠右。
 * - isProbe：同一题的追问（显示「追问」角标）
 * - isQA：进入反问环节（qid === 'qa'）
 */
defineProps<{
  role: 'interviewer' | 'user'
  text: string
  isProbe?: boolean
  isQA?: boolean
}>()
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
}
</style>
