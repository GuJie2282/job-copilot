<template>
  <div class="text-input">
    <div class="input-header">
      <h3>粘贴简历文本</h3>
      <p class="hint">将简历内容复制粘贴到下方文本框中</p>
    </div>

    <div class="textarea-wrapper">
      <textarea
        v-model="text"
        placeholder="在此粘贴简历文本...
最少 50 字符，建议使用完整的简历内容"
        :disabled="loading"
        @input="onInput"
      ></textarea>
      <div class="char-count" :class="{ warning: isTextTooShort }">
        {{ text.length }} 字符
        <span v-if="isTextTooShort">（至少需要 50 字符）</span>
      </div>
    </div>

    <div class="actions">
      <button
        class="submit-btn"
        :disabled="!canSubmit || loading"
        @click="submit"
        type="button"
      >
        {{ loading ? '解析中...' : '开始解析' }}
      </button>

      <button
        class="clear-btn"
        :disabled="loading"
        @click="clear"
        type="button"
      >
        清空
      </button>
    </div>

    <div v-if="text" class="tips">
      <h4>提示</h4>
      <ul>
        <li>确保包含完整的个人信息、教育背景、工作经历</li>
        <li>文本质量越高，解析准确度越高</li>
        <li>可以包含项目经验、技能等信息</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// loading 由父组件控制，避免子组件状态与父组件不同步导致按钮永久卡死
const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', text: string): void
}>()

const text = ref('')
const MIN_LENGTH = 50

const onInput = () => {
  // 可以添加实时验证
}

const isTextTooShort = computed(() => {
  return text.value.length > 0 && text.value.length < MIN_LENGTH
})

const canSubmit = computed(() => {
  return text.value.length >= MIN_LENGTH && !props.loading
})

const submit = () => {
  if (!canSubmit.value) return
  // 直接 emit 文本，loading 状态交给父组件统一管理
  emit('submit', text.value)
}

const clear = () => {
  text.value = ''
}
</script>

<style scoped lang="scss">
.text-input {
  margin: 2rem 0;
}

.input-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.input-header h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  color: $ink;
}

.hint {
  color: $text-secondary;
  font-size: 0.9rem;
}

.textarea-wrapper {
  position: relative;
  margin-bottom: 1rem;
}

textarea {
  width: 100%;
  min-height: 300px;
  padding: 1rem;
  border: 2px solid $border-color;
  border-radius: $radius-lg;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.3s ease;
}

textarea:focus {
  outline: none;
  border-color: $primary-color;
}

textarea:disabled {
  background: $bg-gray;
  cursor: not-allowed;
}

.char-count {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  font-size: 0.85rem;
  color: $text-secondary;
}

.char-count.warning {
  color: $error;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin: 1.5rem 0;
}

.submit-btn {
  padding: 1rem 3rem;
  background: $success;
  color: white;
  border: none;
  border-radius: $radius-md;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.submit-btn:hover:not(:disabled) {
  background: $success;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($success, 0.3);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.clear-btn {
  padding: 1rem 2rem;
  background: $text-secondary;
  color: white;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s ease;
}

.clear-btn:hover:not(:disabled) {
  background: $text-secondary;
}

.clear-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tips {
  margin-top: 2rem;
  padding: 1.5rem;
  background: $bg-gray;
  border-radius: $radius-md;
}

.tips h4 {
  margin: 0 0 1rem 0;
  color: $ink;
}

.tips ul {
  margin: 0;
  padding-left: 1.5rem;
}

.tips li {
  margin-bottom: 0.5rem;
  color: $text-secondary;
  line-height: 1.5;
}
</style>
