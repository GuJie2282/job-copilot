<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">GENERATE</p>
      <h1>简历优化</h1>
      <p class="sub">基于你的画像 + 目标岗位差距，从零生成一份定制简历，经 6 维评估与格式校验，导出 A4 PDF。</p>
    </header>

    <!-- 画像缺失引导（6.2.4） -->
    <div v-if="profileMissing" class="notice notice-warn">
      <p>尚未建立个人画像，无法生成简历。</p>
      <button class="btn-primary" type="button" @click="goBuildProfile">去建立画像</button>
    </div>

    <!-- 生成输入（6.2.1） -->
    <section class="card">
      <label class="field-label" for="position">目标岗位</label>
      <input
        id="position"
        v-model="targetPosition"
        class="position-input"
        placeholder="如：AI 产品经理 / 后端工程师"
        :disabled="loading"
      />

      <!-- 关联的 JD 匹配（6.2.2：从 JD 匹配跳转带入） -->
      <div v-if="jdResultId" class="linked-jd">
        <span class="link-tag">已关联 JD 匹配</span>
        <span class="link-hint">将读取该匹配的差距清单（Gap）做针对性生成</span>
      </div>
      <div v-else class="linked-jd hint-no-gap">
        <span class="link-tag muted">未关联 JD 匹配</span>
        <span class="link-hint">将生成通用简历。建议先做 <router-link to="/jd-matcher">JD 匹配</router-link> 获得针对性差距</span>
      </div>

      <div class="input-meta">
        <span class="meta-hint">生成约需 30-60 秒（含评估迭代与导出）</span>
        <button
          class="btn-primary"
          type="button"
          :disabled="loading || !targetPosition.trim()"
          @click="onGenerate"
        >
          {{ loading ? '生成中…' : '生成简历' }}
        </button>
      </div>

      <!-- 分阶段进度提示（6.2.3） -->
      <div v-if="loading" class="progress">
        <span class="spinner" />
        <p>{{ progressMessage }}</p>
      </div>
    </section>

    <!-- 生成结果 -->
    <div v-if="result" class="result">
      <!-- 评估报告 -->
      <section class="card">
        <h3 class="card-title">
          质量评估<span v-if="result.version" class="title-count tnum">（v{{ result.version }} · draft）</span>
        </h3>
        <ResumeEvalReport :eval-report="result.eval_report" />
      </section>

      <!-- HTML 预览（6.3.1 复用） -->
      <section class="card">
        <h3 class="card-title">简历预览</h3>
        <ResumePreview :html="result.html" />
      </section>

      <!-- 精修入口（路径 B） -->
      <section v-if="result.refine_offered && result.resume_id" class="card refine-card">
        <div>
          <h3 class="card-title">想再打磨？</h3>
          <p class="refine-hint">进入精修模式，按你的反馈逐轮改写，满意后定稿导出 PDF。</p>
        </div>
        <button class="btn-primary" type="button" @click="goRefine(result.resume_id!)">进入精修</button>
      </section>

      <!-- Markdown 原文（可复制） -->
      <section class="card">
        <div class="md-head">
          <h3 class="card-title">Markdown 原文</h3>
          <button class="btn-text" type="button" @click="copyMd">复制</button>
        </div>
        <pre class="md-pre">{{ result.content_md }}</pre>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { generateResume } from '@/api/resume'
import ResumeEvalReport from '@/components/ResumeEvalReport.vue'
import ResumePreview from '@/components/ResumePreview.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const targetPosition = ref('')
const jdResultId = ref<string | undefined>(undefined)
const loading = ref(false)
const progressMessage = ref('')
const profileMissing = ref(false)
const result = ref<any>(null)
let progressTimer: ReturnType<typeof setInterval> | null = null

// 分阶段进度（前端基于时间模拟，后端同步返回）
function startProgress() {
  const stages = ['准备画像与差距…', '生成简历草稿…', '6 维评估中…', '迭代改进中…', '装配 HTML…', '即将完成…']
  let i = 0
  progressMessage.value = stages[0] ?? '生成中…'
  progressTimer = setInterval(() => {
    i = (i + 1) % stages.length
    progressMessage.value = stages[i] ?? progressMessage.value
  }, 5000)
}
function stopProgress() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = null
}

async function onGenerate() {
  if (!targetPosition.value.trim()) {
    ElMessage.warning('请填写目标岗位')
    return
  }
  loading.value = true
  profileMissing.value = false
  result.value = null
  startProgress()
  try {
    const res = await generateResume({
      target_position: targetPosition.value,
      jd_result_id: jdResultId.value,
      user_id: userStore.userId,
    })
    if (res.status === 'success' && res.data) {
      result.value = res.data
      ElMessage.success('简历生成完成')
    } else {
      const code = (res as any).error_code || (res.data as any)?.error_code
      if (code === 'PROFILE_MISSING') {
        profileMissing.value = true
        ElMessage.warning('请先建立个人画像')
      } else {
        ElMessage.error(res.message || '生成失败')
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败，请稍后重试')
  } finally {
    stopProgress()
    loading.value = false
  }
}

function goBuildProfile() {
  router.push('/resume-parser')
}

function goRefine(resumeId: string) {
  router.push(`/resume-refine/${resumeId}`)
}

async function copyMd() {
  if (!result.value?.content_md) return
  try {
    await navigator.clipboard.writeText(result.value.content_md)
    ElMessage.success('已复制 Markdown')
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

onMounted(() => {
  // 从 JD 匹配跳转带入：jd_result_id + position（6.2.2）
  jdResultId.value = (route.query['jd_result_id'] as string) || undefined
  targetPosition.value = (route.query['position'] as string) || ''
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  flex-wrap: wrap;
}

.notice-warn {
  background: $warning-light;
  border: 1px solid $warning;
  color: $warning;
}

.field-label {
  display: block;
  font-weight: $font-weight-medium;
  margin-bottom: $spacing-sm;
  color: $text-primary;
}

.position-input {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  box-sizing: border-box;
  transition: border-color $transition-base ease;

  &:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
  }

  &:disabled {
    background: $bg-gray;
  }
}

.linked-jd {
  margin-top: $spacing-sm;
  font-size: $font-size-xs;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;

  .link-tag {
    font-family: $font-mono;
    padding: 2px 8px;
    border-radius: $radius-sm;
    background: rgba($success, 0.12);
    color: $success;

    &.muted {
      background: $bg-gray;
      color: $text-secondary;
    }
  }

  .link-hint {
    color: $text-secondary;
  }

  &.hint-no-gap a {
    color: $primary-color;
  }
}

.input-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: $spacing-md;
  gap: $spacing-md;
  flex-wrap: wrap;
}

.meta-hint {
  color: $text-secondary;
  font-size: $font-size-xs;
}

.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-lg;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  transition: background $transition-base ease;

  &:hover:not(:disabled) {
    background: $primary-dark;
  }

  &:disabled {
    background: $bg-gray;
    color: $text-disabled;
    cursor: not-allowed;
  }
}

.btn-text {
  background: none;
  border: none;
  color: $primary-color;
  cursor: pointer;
  font-size: $font-size-sm;
  padding: $spacing-xs $spacing-sm;

  &:hover {
    color: $primary-dark;
  }
}

.progress {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  margin-top: $spacing-md;
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
  to {
    transform: rotate(360deg);
  }
}

.result {
  margin-top: $spacing-xl;
}

.refine-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  flex-wrap: wrap;
  background: rgba($primary-color, 0.04);
  border-color: rgba($primary-color, 0.2);

  .refine-hint {
    color: $text-secondary;
    font-size: $font-size-sm;
    margin-top: $spacing-xs;
  }
}

.md-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-sm;

  .card-title {
    margin-bottom: 0;
  }
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

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }
}
</style>
