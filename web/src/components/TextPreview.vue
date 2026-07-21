<template>
  <div class="text-preview">
    <div class="preview-header">
      <h3>文本预览</h3>
      <div class="quality-badge" :class="getQualityClass()">
        {{ getQualityLabel() }}
      </div>
    </div>

    <div v-if="warnings.length > 0" class="warnings">
      <div v-for="(warning, index) in warnings" :key="index" class="warning-item">
        {{ warning }}
      </div>
    </div>

    <div class="text-content">
      <pre>{{ text }}</pre>
    </div>

    <div class="actions">
      <button class="edit-btn" @click="onEdit" type="button">
        编辑文本
      </button>
      <button class="reupload-btn" @click="onReupload" type="button">
        重新上传
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  text: string
  qualityScore: number
  warnings: string[]
}>()

const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'reupload'): void
}>()

const getQualityLabel = () => {
  if (props.qualityScore >= 0.8) return '高质量'
  if (props.qualityScore >= 0.6) return '中等质量'
  return '低质量'
}

const getQualityClass = () => {
  if (props.qualityScore >= 0.8) return 'high'
  if (props.qualityScore >= 0.6) return 'medium'
  return 'low'
}

const onEdit = () => {
  emit('edit')
}

const onReupload = () => {
  emit('reupload')
}
</script>

<style scoped lang="scss">
.text-preview {
  margin: 2rem 0;
  padding: 2rem;
  background: white;
  border-radius: $radius-lg;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.preview-header h3 {
  margin: 0;
  color: $ink;
}

.quality-badge {
  padding: 0.5rem 1rem;
  border-radius: $radius-full;
  font-size: 0.9rem;
  font-weight: 600;
}

.quality-badge.high {
  background: $success-light;
  color: $success;
}

.quality-badge.medium {
  background: $warning-light;
  color: $warning;
}

.quality-badge.low {
  background: $error-light;
  color: $error;
}

.warnings {
  margin-bottom: 1.5rem;
}

.warning-item {
  padding: 0.75rem 1rem;
  background: $warning-light;
  border-left: 4px solid $warning;
  margin-bottom: 0.5rem;
  border-radius: $radius-sm;
  font-size: 0.9rem;
  color: $warning;
}

.text-content {
  margin-bottom: 1.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.text-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  padding: 1rem;
  background: $bg-gray;
  border-radius: $radius-md;
  font-size: 0.9rem;
  line-height: 1.6;
  color: $ink;
}

.actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.actions button {
  flex: 1;
  min-width: 150px;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.confirm-btn {
  background: $success;
  color: white;
}

.confirm-btn:hover {
  background: $success;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($success, 0.3);
}

.edit-btn {
  background: $primary-color;
  color: white;
}

.edit-btn:hover {
  background: $primary-dark;
}

.reupload-btn {
  background: $text-secondary;
  color: white;
}

.reupload-btn:hover {
  background: $text-secondary;
}
</style>
