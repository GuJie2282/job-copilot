<template>
  <div class="input-selector">
    <div class="selector-header">
      <h3>选择输入方式</h3>
      <p class="hint">选择最适合你的方式上传简历</p>
    </div>

    <div class="options">
      <button
        class="option-card"
        :class="{ active: modelValue === 'file' }"
        @click="select('file')"
      >
        <div class="content">
          <h4>上传文件</h4>
          <p>支持 PDF 和 Word 文档</p>
        </div>
        <div class="check" v-if="modelValue === 'file'"></div>
      </button>

      <button
        class="option-card"
        :class="{ active: modelValue === 'text' }"
        @click="select('text')"
      >
        <div class="content">
          <h4>粘贴文本</h4>
          <p>直接复制粘贴简历内容</p>
        </div>
        <div class="check" v-if="modelValue === 'text'"></div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: 'file' | 'text'
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: 'file' | 'text'): void
  (e: 'change', value: 'file' | 'text'): void
}>()

const select = (value: 'file' | 'text') => {
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped lang="scss">
.input-selector {
  margin-bottom: 2rem;
}

.selector-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.selector-header h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  color: $ink;
}

.hint {
  color: $text-secondary;
  font-size: 0.9rem;
}

.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  max-width: 800px;
  margin: 0 auto;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border: 2px solid $border-color;
  border-radius: $radius-lg;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.option-card:hover {
  border-color: $primary-color;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($primary-color, 0.15);
}

.option-card.active {
  border-color: $primary-color;
  background: $primary-lighter;
}

.content {
  flex: 1;
  text-align: left;
}

.content h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  color: $ink;
}

.content p {
  margin: 0;
  font-size: 0.85rem;
  color: $text-secondary;
}

// 选中态：右上角实心圆点指示
.check {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 12px;
  height: 12px;
  background: $primary-color;
  border-radius: 50%;
}
</style>
