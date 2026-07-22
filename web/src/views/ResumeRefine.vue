<template>
  <div class="page">
    <header class="page-head">
      <p class="eyebrow">REFINE</p>
      <h1>精修简历</h1>
      <p class="sub">按你的反馈逐轮改写，满意后定稿导出 PDF。每轮重新评估，看到简历变好。</p>
    </header>

    <!-- 加载 / 改写 / 定稿中 -->
    <div v-if="loading || submitting" class="progress">
      <span class="spinner" />
      <p>{{ progressMessage }}</p>
    </div>

    <template v-if="current">
      <!-- 当前评估 -->
      <section class="card">
        <h3 class="card-title">第 {{ current.round }} 轮评估</h3>
        <ResumeEvalReport :eval-report="current.eval_report" />
      </section>

      <!-- 待补充提示（画像追问） -->
      <div v-if="(current.pending_hints || []).length" class="notice notice-info">
        <b>待补充：</b>{{ (current.pending_hints || []).join('；') }}
        <span class="notice-hint">（在反馈里补充这些细节，会改得更好）</span>
      </div>

      <!-- 当前草稿（Markdown） -->
      <section class="card">
        <h3 class="card-title">当前草稿</h3>
        <pre class="md-pre">{{ current.resume_md }}</pre>
      </section>

      <!-- 反馈输入 -->
      <section class="card">
        <label class="field-label" for="feedback">反馈（要改什么）</label>
        <textarea
          id="feedback"
          v-model="feedback"
          class="feedback-input"
          rows="4"
          :disabled="submitting"
          placeholder="如：第二段经历补充量化数据；把 XX 项目前置；某处表述太空泛，换成具体做法…"
        />
        <div class="actions">
          <button
            class="btn-primary"
            type="button"
            :disabled="submitting || !feedback.trim()"
            @click="onRefine"
          >
            提交反馈，继续精修
          </button>
          <button
            class="btn-success"
            type="button"
            :disabled="submitting"
            @click="onFinalize"
          >
            满意，定稿
          </button>
        </div>
      </section>
    </template>

    <!-- 定稿结果 -->
    <section v-if="finalized" class="card finalize-card">
      <h3 class="card-title">
        定稿完成<span class="title-count tnum">（v{{ finalized.version }} · finalized）</span>
      </h3>
      <ResumePreview :html="finalized.html" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { refineResume, finalizeResume } from '@/api/resume'
import ResumeEvalReport from '@/components/ResumeEvalReport.vue'
import ResumePreview from '@/components/ResumePreview.vue'

const route = useRoute()
const userStore = useUserStore()
const resumeId = route.params['resumeId'] as string

const loading = ref(true)
const submitting = ref(false)
const progressMessage = ref('加载草稿…')
const current = ref<any>(null) // { resume_md, eval_report, round, pending_hints }
const feedback = ref('')
const finalized = ref<any>(null)

// 第一次：加载草稿 + 展示评估（无 feedback）
async function loadFirst() {
  loading.value = true
  progressMessage.value = '加载草稿…'
  try {
    const res = await refineResume(resumeId, { user_id: userStore.userId })
    if (res.status === 'success' && res.data) {
      current.value = res.data
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// 提交反馈：按反馈改写 + 重新评估
async function onRefine() {
  if (!feedback.value.trim()) return
  submitting.value = true
  progressMessage.value = '按反馈改写中…'
  try {
    const res = await refineResume(resumeId, {
      user_id: userStore.userId,
      feedback: feedback.value,
    })
    if (res.status === 'success' && res.data) {
      current.value = res.data
      feedback.value = ''
      ElMessage.success('已改写')
    } else {
      ElMessage.error(res.message || '改写失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '改写失败')
  } finally {
    submitting.value = false
  }
}

// 满意定稿：校验 + 导出 HTML + 落库 finalized
async function onFinalize() {
  submitting.value = true
  progressMessage.value = '定稿中…'
  try {
    const res = await finalizeResume(resumeId, { user_id: userStore.userId })
    if (res.status === 'success' && res.data) {
      finalized.value = res.data
      current.value = null
      ElMessage.success('定稿完成')
    } else {
      ElMessage.error(res.message || '定稿失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '定稿失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadFirst()
})
</script>

<style scoped lang="scss">
.page {
  max-width: 820px;
  margin: 0 auto;
  padding: $spacing-3xl $spacing-xl;
}

.page-head {
  margin-bottom: $spacing-2xl;

  .eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.15em;
    color: $accent-color;
    margin-bottom: $spacing-sm;
  }

  h1 {
    font-size: $font-size-3xl;
    margin-bottom: $spacing-sm;
  }

  .sub {
    color: $text-secondary;
    max-width: 60ch;
  }
}

.card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xl;
  margin-bottom: $spacing-lg;
}

.card-title {
  font-size: $font-size-lg;
  margin-bottom: $spacing-md;

  .title-count {
    font-weight: $font-weight-normal;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.notice {
  padding: $spacing-md $spacing-lg;
  border-radius: $radius-md;
  margin-bottom: $spacing-lg;
  font-size: $font-size-sm;
}

.notice-info {
  background: rgba($primary-color, 0.06);
  border: 1px solid rgba($primary-color, 0.2);
  color: $text-primary;

  .notice-hint {
    color: $text-secondary;
    font-size: $font-size-xs;
  }
}

.field-label {
  display: block;
  font-weight: $font-weight-medium;
  margin-bottom: $spacing-sm;
  color: $text-primary;
}

.feedback-input {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-md;
  font-size: $font-size-sm;
  line-height: $line-height-normal;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color $transition-base ease;

  &:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
  }
}

.actions {
  display: flex;
  gap: $spacing-md;
  margin-top: $spacing-md;
  flex-wrap: wrap;
}

.btn-primary,
.btn-success {
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-lg;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  transition: background $transition-base ease;

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

.progress {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
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

.md-pre {
  background: $bg-gray;
  border-radius: $radius-md;
  padding: $spacing-md;
  font-family: $font-mono;
  font-size: $font-size-xs;
  line-height: $line-height-normal;
  color: $text-primary;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow: auto;
  margin: 0;
}

.finalize-card {
  border-color: rgba($success, 0.3);
  background: rgba($success, 0.03);
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }
}
</style>
