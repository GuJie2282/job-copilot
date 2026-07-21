<template>
  <div class="file-upload">
    <div
      class="upload-area"
      :class="{ dragging: isDragging, 'has-file': selectedFile }"
      @drop.prevent="onDrop"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @click="selectFile"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx"
        @change="onFileChange"
        style="display: none"
      />

      <div v-if="!selectedFile" class="upload-prompt">
        <div class="icon">↑</div>
        <h3>点击或拖拽文件到此处</h3>
        <p>支持 PDF 和 Word 文档（.docx），最大 10MB</p>
        <button class="browse-btn" type="button">浏览文件</button>
      </div>

      <div v-else class="file-info">
        <div class="info">
          <h4>{{ selectedFile.name }}</h4>
          <p>{{ formatFileSize(selectedFile.size) }}</p>
        </div>
        <button class="remove-btn" @click.stop="removeFile" type="button">
          删除
        </button>
      </div>
    </div>

    <div v-if="selectedFile" class="actions">
      <button
        class="upload-btn"
        :disabled="loading"
        @click="upload"
        type="button"
      >
        {{ loading ? '上传中...' : '开始解析' }}
      </button>
    </div>

    <SampleSelector v-if="!selectedFile" @select="onSampleSelect" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SampleSelector from './SampleSelector.vue'

// loading 由父组件控制，避免子组件状态与父组件不同步导致按钮永久卡死
const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'upload', file: File): void
  (e: 'sample', text: string): void
}>()

const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)

const selectFile = () => {
  fileInput.value?.click()
}

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    validateAndSelectFile(target.files[0])
  }
}

const onDrop = (e: DragEvent) => {
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
    validateAndSelectFile(e.dataTransfer.files[0])
  }
}

const onDragOver = () => {
  isDragging.value = true
}

const onDragLeave = () => {
  isDragging.value = false
}

const validateAndSelectFile = (file: File) => {
  // 检查文件类型
  const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
  const fileName = file.name.toLowerCase()
  const validExtension = fileName.endsWith('.pdf') || fileName.endsWith('.docx')

  if (!validTypes.includes(file.type) && !validExtension) {
    alert('不支持的文件格式。请上传 PDF 或 Word 文档（.docx）。')
    return
  }

  // 检查文件大小（10MB）
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    alert('文件过大（最大 10MB）。文件过大可能是扫描件，建议使用可搜索的 PDF。')
    return
  }

  selectedFile.value = file
}

const removeFile = () => {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const upload = () => {
  if (!selectedFile.value || props.loading) return
  // 直接 emit 文件，loading 状态交给父组件统一管理
  emit('upload', selectedFile.value)
}

const onSampleSelect = (sampleText: string) => {
  // 示例是纯文本，交给父组件切换到文本解析通道
  // （不能伪装成 .txt 文件上传——后端 parse-file 只接受 pdf/docx，会被拒绝）
  emit('sample', sampleText)
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}
</script>

<style scoped lang="scss">
.file-upload {
  margin: 2rem 0;
}

.upload-area {
  border: 2px dashed $border-color;
  border-radius: $radius-lg;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.upload-area:hover {
  border-color: $primary-color;
  background: $bg-gray;
}

.upload-area.dragging {
  border-color: $primary-color;
  background: $primary-lighter;
}

.upload-area.has-file {
  border-style: solid;
  border-color: $success;
  background: $success-light;
}

.upload-prompt .icon {
  font-size: 3rem;
  font-weight: $font-weight-bold;
  color: $primary-color;
  margin-bottom: 1rem;
}

.upload-prompt h3 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.upload-prompt p {
  color: $text-secondary;
  margin-bottom: 1.5rem;
}

.browse-btn {
  padding: 0.75rem 2rem;
  background: $primary-color;
  color: white;
  border: none;
  border-radius: $radius-sm;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s ease;
}

.browse-btn:hover {
  background: $primary-dark;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
}

.file-info .info {
  flex: 1;
  text-align: left;
}

.file-info h4 {
  margin: 0 0 0.25rem 0;
  color: $ink;
}

.file-info p {
  margin: 0;
  color: $text-secondary;
  font-size: 0.9rem;
}

.remove-btn {
  padding: 0.25rem 0.75rem;
  border: none;
  background: $error;
  color: white;
  border-radius: $radius-sm;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.3s ease;
}

.remove-btn:hover {
  background: $error;
}

.actions {
  margin-top: 1.5rem;
  text-align: center;
}

.upload-btn {
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

.upload-btn:hover:not(:disabled) {
  background: $success;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($success, 0.3);
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
