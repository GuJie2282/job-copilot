<template>
  <!-- 简历 HTML 预览（iframe 渲染 preview_shell 完整页，含 A4 分页 + 导出 PDF 工具条）。
       refine 模式（精修）：进入可编辑态，父页通过 collectPatches() 采集手动编辑回写。 -->
  <div class="resume-preview">
    <div v-if="html && !refine" class="preview-toolbar">
      <span class="hint">下方预览简历 A4 排版，点右上角「导出 PDF」可另存为 PDF</span>
      <button class="btn-primary" type="button" @click="printFrame">打印 / 导出 PDF</button>
    </div>
    <div v-else-if="html && refine" class="preview-toolbar refine-toolbar">
      <span class="hint">✏️ 可直接点击简历文字编辑；改动会在你发送对话或定稿时自动保存</span>
    </div>
    <iframe
      v-if="html"
      ref="frameRef"
      class="preview-frame"
      :srcdoc="html"
      title="简历预览"
      @load="onFrameLoad"
    />
    <div v-else class="empty">
      <p>HTML 预览尚未就绪。</p>
      <p class="empty-sub">后端导出（Phase 4）未产出 HTML 时，可先用上方的 Markdown 内容。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { diffResumeLines } from '@/utils/resumeDiff'

const props = defineProps<{ html: string | null | undefined; refine?: boolean }>()

const frameRef = ref<HTMLIFrameElement | null>(null)

// iframe 加载完成：精修模式下进入编辑态（采集锚点 patch 用）
function onFrameLoad() {
  if (props.refine) {
    try {
      ;(frameRef.value?.contentWindow as any)?.__setRefineMode?.(true)
    } catch {
      /* 跨域或未就绪时忽略 */
    }
  }
}

// 采集当前手动编辑的 patches（供父页 flushEdits 调用，回写到 Markdown 真相源）
function collectPatches(): any[] {
  try {
    return (frameRef.value?.contentWindow as any)?.__collectPatches?.() || []
  } catch {
    return []
  }
}

// 触发 iframe 内的打印（= 浏览器「另存为 PDF」；精修导出 Tasks 5 改服务端渲染）
function printFrame() {
  const frame = frameRef.value
  try {
    if (frame?.contentWindow) {
      frame.contentWindow.focus()
      frame.contentWindow.print()
    } else {
      window.print()
    }
  } catch {
    window.print()
  }
}

// 局部更新（evolve-refine-partial-update）：AI 改完后只替换被改原子，不整体刷新 iframe。
// 返回 ok=true 表示局部更新成功；ok=false 调用方应 fallback 整体刷新；conflicts 为同原子冲突行号。
function partialUpdate(oldMd: string, newMd: string, newHtml: string): {
  ok: boolean
  reason?: string
  conflicts: number[]
} {
  const win = frameRef.value?.contentWindow as any
  const doc = frameRef.value?.contentDocument
  if (!win || !doc) return { ok: false, conflicts: [], reason: 'iframe 未就绪' }

  const diff = diffResumeLines(oldMd, newMd)
  if (diff.bigChange) return { ok: false, conflicts: [], reason: diff.reason }

  // 解析新 html，按 data-md-line 建索引 {line → 新原子[]}
  const newDoc = new DOMParser().parseFromString(newHtml, 'text/html')
  const newByLine = new Map<number, Element[]>()
  newDoc.querySelectorAll('[data-md-line]').forEach((el) => {
    const ln = parseInt(el.getAttribute('data-md-line') || '', 10)
    if (!isNaN(ln)) {
      if (!newByLine.has(ln)) newByLine.set(ln, [])
      newByLine.get(ln)!.push(el)
    }
  })

  const initialTexts: Record<string, string> = win.__initialTexts || {}
  const conflicts: number[] = []
  let replaced = 0

  diff.changedLines.forEach((line) => {
    const newAtoms = newByLine.get(line)
    if (!newAtoms?.length) return // 新 html 无该行可编辑原子（如 stack-row），跳过
    // 只替换 #scaler（显示的、用户编辑所在）；#source 是隐藏装配源不动。
    // 注：d.html 的 #scaler 为空（分页 JS 在浏览器跑，后端只填 #source），故新原子取自 newDoc #source。
    const oldAtoms = Array.from(doc.querySelectorAll(`#scaler [data-md-line="${line}"]`))
    if (!oldAtoms.length) return

    // 冲突检测：iframe 该原子当前值 vs 基线（用户是否编辑过该原子）。
    // stack-row 的 raw textContent 含编辑按钮(×/+)，用 __readStack 签名对比；其他用 textContent。
    const conflict = oldAtoms.some((el) => {
      const field = el.getAttribute('data-md-field') || ''
      const base = initialTexts[`${line}|${field}`]
      if (base === undefined) return false
      if (el.classList.contains('stack-row')) {
        const s = win.__readStack?.(el)
        return s ? `${s.cat}||${s.chips.join('·')}` !== base : false
      }
      return (el.textContent?.trim() || '') !== base
    })
    if (conflict) { conflicts.push(line); return } // 冲突：不静默覆盖，记录给调用方提示

    // 局部替换（按顺序对位）
    oldAtoms.forEach((el, i) => {
      const rep = newAtoms[i]
      if (rep) {
        el.replaceWith(doc.importNode(rep, true))
        replaced++
      }
    })
  })

  if (replaced > 0) {
    win.__reflow?.() // 重排分页（替换后原子高度可能变）
    win.__refineRehook?.() // 重挂编辑态：新替换的 stack-row 需重新加 chip-del/add 按钮 + contenteditable
    win.__recordInitial?.() // 重记基线（新原子文本为新基线，避免下次冲突误判）
  }

  return { ok: true, conflicts }
}

defineExpose({ collectPatches, partialUpdate })
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

.refine-toolbar {
  justify-content: flex-start;
  background: rgba($primary-color, 0.04);
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
