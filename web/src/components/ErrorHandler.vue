<template>
  <div v-if="error" class="error-handler" :class="`error-${error.type}`">
    <div class="error-content">
      <div class="icon">{{ getIcon() }}</div>
      <div class="message">
        <h4>{{ getTitle() }}</h4>
        <p>{{ error.message }}</p>
      </div>
      <button class="close-btn" @click="onClose" type="button">关闭</button>
    </div>

    <div v-if="error.type === 'error'" class="suggestions">
      <h5>建议：</h5>
      <ul>
        <li v-for="(suggestion, index) in suggestions" :key="index">
          {{ suggestion }}
        </li>
      </ul>
    </div>

    <div v-if="error.type === 'warning'" class="actions">
      <button class="retry-btn" @click="onRetry" type="button">
        重试
      </button>
      <button class="fallback-btn" @click="onFallback" type="button">
        使用其他方式
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  error: {
    type: 'error' | 'warning' | 'info'
    message: string
    suggestions?: string[]
  } | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'retry'): void
  (e: 'fallback'): void
}>()

const suggestions = computed(() => {
  return props.error?.suggestions || [
    '检查文件格式是否正确（PDF 或 Word）',
    '确保文件未加密且不是扫描件',
    '尝试复制粘贴文本内容',
    '使用手动填写方式'
  ]
})

const getIcon = () => {
  if (!props.error) return ''
  switch (props.error.type) {
    case 'error': return ''
    case 'warning': return ''
    case 'info': return ''
    default: return ''
  }
}

const getTitle = () => {
  if (!props.error) return ''
  switch (props.error.type) {
    case 'error': return '解析失败'
    case 'warning': return '警告'
    case 'info': return '提示'
    default: return '注意'
  }
}

const onClose = () => {
  emit('close')
}

const onRetry = () => {
  emit('retry')
}

const onFallback = () => {
  emit('fallback')
}
</script>

<style scoped lang="scss">
.error-handler {
  margin: 2rem 0;
  padding: 1.5rem;
  border-radius: $radius-lg;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.error-error {
  background: $error-light;
  border: 1px solid $error-light;
}

.error-warning {
  background: $warning-light;
  border: 1px solid $warning;
}

.error-info {
  background: $primary-lighter;
  border: 1px solid $primary-lighter;
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.message {
  flex: 1;
}

.message h4 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.message p {
  margin: 0;
  color: $text-secondary;
  line-height: 1.5;
}

.close-btn {
  padding: 0.25rem 0.75rem;
  border: none;
  background: transparent;
  color: $text-secondary;
  border-radius: $radius-sm;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

.suggestions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.suggestions h5 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.suggestions ul {
  margin: 0;
  padding-left: 1.5rem;
}

.suggestions li {
  margin-bottom: 0.5rem;
  color: $text-secondary;
  line-height: 1.5;
}

.actions {
  margin-top: 1rem;
  display: flex;
  gap: 1rem;
}

.actions button {
  flex: 1;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.retry-btn {
  background: $primary-color;
  color: white;
}

.retry-btn:hover {
  background: $primary-dark;
}

.fallback-btn {
  background: $text-secondary;
  color: white;
}

.fallback-btn:hover {
  background: $text-secondary;
}
</style>
