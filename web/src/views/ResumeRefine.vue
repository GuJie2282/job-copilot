<template>
  <!-- 精修工作台：左侧简历预览 + 右侧 AI 对话（左右分栏） -->
  <div class="page refine-page">
    <header class="page-head">
      <h1>精修简历</h1>
      <button class="btn-export" type="button" :disabled="exporting || !html" @click="exportPdf">
        {{ exporting ? '导出中…' : '📄 导出 PDF' }}
      </button>
    </header>

    <div v-if="finalizing" class="progress"><span class="spinner" /><p>定稿中…</p></div>

    <div class="workspace">
      <!-- 左侧：简历预览（AI 改写后整体刷新；手动编辑 Tasks 4 第二部分接入） -->
      <section class="pane pane-left">
        <div class="pane-head">
          <h3>简历预览</h3>
          <span v-if="round" class="round-tag">第 {{ round }} 轮</span>
        </div>
        <div class="pane-body">
          <ResumePreview v-if="html" ref="previewRef" :html="html" :refine="true" />
          <div v-else class="loading-box"><span class="spinner" /><p>加载简历…</p></div>
        </div>
      </section>

      <!-- 右侧：AI 对话 -->
      <section class="pane pane-right">
        <div class="pane-head"><h3>AI 对话</h3></div>
        <div class="pane-body">
          <RefineChat
            :messages="messages"
            :loading="streaming"
            :can-finalize="!!html"
            :round="round"
            @send="onSend"
            @finalize="onFinalize"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { refineResumeStream, finalizeResume, patchDraft } from '@/api/resume'
import ResumePreview from '@/components/ResumePreview.vue'
import RefineChat from '@/components/RefineChat.vue'

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

const route = useRoute()
const userStore = useUserStore()
const resumeId = route.params['resumeId'] as string

const html = ref('')
const resumeMd = ref('')
const round = ref(0)
const streaming = ref(false)
const finalizing = ref(false)
const exporting = ref(false)
const messages = ref<ChatMessage[]>([])
const previewRef = ref<{
  collectPatches: () => any[]
  partialUpdate: (oldMd: string, newMd: string, newHtml: string) => {
    ok: boolean
    reason?: string
    conflicts: number[]
  }
} | null>(null)

// flushEdits 不变量（Tasks 4.4）：发送对话 / 定稿前，先把左侧手动编辑回写到 Markdown 真相源，
// 保证 AI 改写基于「含手动编辑的最新草稿」、定稿/导出反映手改。
async function flushEdits() {
  const patches = previewRef.value?.collectPatches() || []
  if (!patches.length) return
  try {
    const res = await patchDraft(resumeId, { user_id: userStore.userId, patches })
    if (res.status === 'success' && res.data) {
      // 只更新真相源 MD；不刷新 html——iframe DOM 已是用户编辑后的状态，
      // 重渲染会闪屏 + 丢光标/IME（用户编辑的内容靠 partialUpdate 在 AI 改完时局部保留）
      if (res.data.resume_md) resumeMd.value = res.data.resume_md
      if ((res.data.warnings || []).length) {
        ElMessage.warning(`${res.data.warnings.length} 处编辑未能回写，可改用对话描述`)
      }
    }
  } catch {
    /* 回写失败不阻断对话（AI 改写仍可继续） */
  }
}

// 导出 PDF（服务端 Playwright 渲染，直接下载；渲染失败降级浏览器打印）
async function exportPdf() {
  exporting.value = true
  try {
    await flushEdits() // 导出前落手动编辑
    const base = import.meta.env['VITE_STREAM_BASE_URL'] || import.meta.env.VITE_API_BASE_URL || ''
    const token = localStorage.getItem('token')
    const resp = await fetch(
      `${base}/resume/${resumeId}/pdf?user_id=${encodeURIComponent(userStore.userId || '')}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    )
    const ct = resp.headers.get('content-type') || ''
    if (resp.ok && ct.includes('application/pdf')) {
      const blob = await resp.blob()
      const cd = resp.headers.get('content-disposition') || ''
      const m = cd.match(/filename\*=UTF-8''(.+)/)
      const filename = m && m[1] ? decodeURIComponent(m[1]) : '简历.pdf'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success('PDF 已下载')
    } else {
      const j = await resp.json().catch(() => ({}))
      ElMessage.warning(j?.message || 'PDF 渲染失败，请改用浏览器打印')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

// 开场白（操作指引：手动改 / 对话改 + 边界提示）
const WELCOME = `👋 欢迎来到精修工作台！两种改简历的方式：
· 对话改：在下方告诉我怎么改（如「第二段经历补量化数据」「把 AI 项目前置」），我改完会解释思路。
· 手动改：可直接编辑左侧简历的文字（逐步开放中）。
每轮你都能看到我的思考过程。满意了点「✅ 满意定稿」导出 PDF。`

onMounted(() => {
  messages.value = [{ role: 'ai', text: WELCOME }]
  loadFirst()
})

// 首次加载：拉当前草稿 + 预览（无 feedback）
function loadFirst() {
  streaming.value = true
  messages.value.push({ role: 'ai', text: '', pending: true })
  refineResumeStream(resumeId, { user_id: userStore.userId }, {
    onDone: (d) => {
      html.value = d.html || ''
      resumeMd.value = d.resume_md || ''
      round.value = d.round || 0
      streaming.value = false
      messages.value = messages.value.filter((m) => !m.pending) // 移除加载占位
    },
    onError: (e) => {
      streaming.value = false
      messages.value = messages.value.filter((m) => !m.pending)
      ElMessage.error(e.error_message || '加载失败')
    },
  })
}

// 用户发送反馈 → 对话改写
async function onSend(text: string) {
  await flushEdits() // 先落手动编辑，再让 AI 基于最新草稿改写
  messages.value.push({ role: 'user', text })
  messages.value.push({ role: 'ai', text: '', reasoning: '', pending: true, status: 'thinking' })
  streaming.value = true

  refineResumeStream(resumeId, { user_id: userStore.userId, feedback: text }, {
    onStage: (p) => {
      // 后端推 stage(applying) = 思考结束、进入「修改中」（简历生成阶段）
      const last = messages.value[messages.value.length - 1]
      if (last && p.node === 'applying') last.status = 'applying'
    },
    onReasoning: (p) => {
      const last = messages.value[messages.value.length - 1]
      if (!last) return
      last.reasoning = (last.reasoning || '') + p.delta
      // 核查完成、模型进入输出阶段（reasoning 里出现 <<<REPLY>>>/<<<RESUME>>>）→ 转「修改中」。
      // 此时 reasoning 流可能还在（AI 正在输出完整简历，前端截断不显示），但思考主体已完成。
      if (
        last.status === 'thinking' &&
        (last.reasoning.includes('<<<REPLY>>>') || last.reasoning.includes('<<<RESUME>>>'))
      ) {
        last.status = 'applying'
      }
    },
    onToken: (p) => {
      const last = messages.value[messages.value.length - 1]
      if (last) {
        last.text = (last.text || '') + p.delta
        last.status = 'applying' // reply 开始 = 思考结束，进入「修改中」
      }
    },
    onDone: (d) => {
      const last = messages.value[messages.value.length - 1]
      if (last) {
        last.pending = false
        last.status = 'done' // 修改完成
        last.resumed = d.resumed
        last.round = d.round // 记该消息自己的轮次（chip 显示，不随当前轮变）
        if (!last.text && d.reply) last.text = d.reply
      }
      // 简历更新：优先局部（只替换被改原子，保留 streaming 期间用户的其他编辑）；
      // bigChange / iframe 未就绪 → fallback 整体刷新 srcdoc
      if (d.resumed && d.html && d.resume_md) {
        const r = previewRef.value?.partialUpdate(resumeMd.value, d.resume_md, d.html)
        if (r?.ok) {
          if (r.conflicts.length) {
            ElMessage.warning(`${r.conflicts.length} 处你改过、AI 也改了，已保留你的版本`)
          }
        } else {
          html.value = d.html // bigChange 或 iframe 未就绪 → 整体刷新
        }
        resumeMd.value = d.resume_md
      } else if (d.html) {
        html.value = d.html
      }
      round.value = d.round || round.value
      streaming.value = false
      if (d.resumed) ElMessage.success('简历已更新')
    },
    onError: (e) => {
      const last = messages.value[messages.value.length - 1]
      if (last) {
        last.pending = false
        last.text = '❌ ' + (e.error_message || '改写失败')
      }
      streaming.value = false
    },
  })
}

// 满意定稿
async function onFinalize() {
  await flushEdits() // 定稿前落手动编辑
  finalizing.value = true
  try {
    const res = await finalizeResume(resumeId, { user_id: userStore.userId })
    if (res.status === 'success') {
      ElMessage.success('定稿完成，可在左侧导出 PDF')
    } else {
      ElMessage.error(res.message || '定稿失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '定稿失败')
  } finally {
    finalizing.value = false
  }
}
</script>

<style scoped lang="scss">
.refine-page {
  max-width: 1600px;                 // 加宽：给简历更多横向空间
  margin: 0 auto;
  padding: $spacing-sm $spacing-lg;   // 压缩垂直 padding（原 2xl/xl）
  height: calc(100vh - 64px);         // 减顶栏 64px（sticky 占流），刚好填满视口剩余，不溢出滚动
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  overflow: hidden;
}

.page-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;

  h1 {
    font-size: $font-size-lg;        // 标题缩小（原 2xl）
    margin: 0;
  }
  .btn-export {
    flex-shrink: 0;
    background: $primary-color;
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
}

.workspace {
  flex: 1;                            // 占满页头之外的剩余高度（取代 calc(100vh - 220px)）
  min-height: 0;
  display: grid;
  grid-template-columns: 1.6fr 1fr;  // 简历区加宽（原 1.4fr）
  gap: $spacing-md;
}

.pane {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.pane-head {
  padding: $spacing-sm $spacing-lg;
  border-bottom: 1px solid $border-color;
  display: flex;
  align-items: center;
  justify-content: space-between;

  h3 {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
  }
  .round-tag {
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.pane-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 左侧预览：让 ResumePreview 的 iframe 撑满 pane-body */
.pane-left .pane-body :deep(.resume-preview) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.pane-left .pane-body :deep(.preview-frame) {
  height: 100%;
  min-height: 0;
  flex: 1;
  border: none;
  border-top: 1px solid $border-color;
}

.loading-box {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.progress {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  color: $primary-color;
  font-size: $font-size-sm;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid $border-color;
  border-top-color: $primary-color;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: $container-md) {
  .workspace {
    grid-template-columns: 1fr;
    height: auto;
  }
  .pane {
    min-height: 420px;
  }
}
</style>
