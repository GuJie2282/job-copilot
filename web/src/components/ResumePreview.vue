<template>
  <!-- 简历 HTML 预览（iframe 渲染 preview_shell 完整页，含 A4 分页 + 导出 PDF 工具条） -->
  <div class="resume-preview">
    <div v-if="html" class="preview-toolbar">
      <span class="hint">下方预览简历 A4 排版，点右上角「导出 PDF」可另存为 PDF</span>
      <button class="btn-primary" type="button" @click="printFrame">打印 / 导出 PDF</button>
    </div>
    <iframe
      v-if="html"
      ref="frameRef"
      class="preview-frame"
      :srcdoc="html"
      title="简历预览"
    />
    <div v-else class="empty">
      <p>HTML 预览尚未就绪。</p>
      <p class="empty-sub">后端导出（Phase 4）未产出 HTML 时，可先用上方的 Markdown 内容。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ html: string | null | undefined }>()

const frameRef = ref<HTMLIFrameElement | null>(null)

// 触发 iframe 内的打印（= 浏览器「另存为 PDF」）
function printFrame() {
  const frame = frameRef.value
  try {
    if (frame?.contentWindow) {
      frame.contentWindow.focus()
      frame.contentWindow.print()
    } else {
      window.print()
    }
  } catch (e) {
    // 跨域或渲染未完成时降级到当前页打印
    window.print()
  }
}
</script>

<style scoped lang="scss">
.resume-preview {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  flex-wrap: wrap;

  .hint {
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-xs $spacing-lg;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  transition: background $transition-base ease;

  &:hover {
    background: $primary-dark;
  }
}

.preview-frame {
  width: 100%;
  height: 80vh;
  min-height: 600px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: #fff;
}

.empty {
  text-align: center;
  padding: $spacing-2xl;
  color: $text-disabled;
  font-size: $font-size-sm;

  .empty-sub {
    font-size: $font-size-xs;
    margin-top: $spacing-sm;
  }
}
</style>
