<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">PROFILE</p>
      <h1>简历解析</h1>
      <p class="sub">上传简历或粘贴文本，AI 自动提取你的个人画像。</p>
    </header>

    <!-- 编辑模式：覆盖默认流程，只显示编辑器 -->
    <ProfileEditor
      v-if="isEditing && parseResult?.profile"
      :profile="parseResult.profile"
      :confidence="parseResult.confidence"
      @save="onProfileSave"
      @cancel="onProfileEditCancel"
    />

    <!-- 默认流程：输入 → 预览 → 展示 → 后续引导 -->
    <template v-else>
      <!-- 输入方式选择 -->
      <InputSelector
        v-model="inputMethod"
        @change="onInputMethodChange"
      />

      <!-- 文件上传 -->
      <FileUpload
        v-if="inputMethod === 'file'"
        :loading="isLoading"
        @upload="onFileUpload"
        @sample="onSampleText"
      />

      <!-- 文本输入 -->
      <TextInput
        v-if="inputMethod === 'text'"
        :loading="isLoading"
        @submit="onTextSubmit"
      />

      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading">
        <span class="spinner" />
        <p>{{ loadingMessage }}</p>
      </div>

      <!-- 解析结果 -->
      <div v-if="parseResult && !isLoading" class="result">
        <TextPreview
          :text="parseResult.text"
          :quality-score="parseResult.quality_score"
          :warnings="parseResult.warnings"
          @reupload="onReupload"
        />

        <ProfileDisplay
          v-if="showProfile"
          :profile="parseResult.profile"
          :confidence="parseResult.confidence"
          @edit="onProfileEdit"
          @save="onSave"
          @clear="onClear"
        />

        <NextStepsCard
          v-if="showProfile"
          @navigate="onNavigate"
          @edit="onProfileEdit"
        />
      </div>

      <!-- 错误提示 -->
      <ErrorHandler
        v-if="error"
        :error="error"
        @close="error = null"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

// 导入组件
import InputSelector from '@/components/InputSelector.vue'
import FileUpload from '@/components/FileUpload.vue'
import TextInput from '@/components/TextInput.vue'
import TextPreview from '@/components/TextPreview.vue'
import ProfileDisplay from '@/components/ProfileDisplay.vue'
import ProfileEditor from '@/components/ProfileEditor.vue'
import NextStepsCard from '@/components/NextStepsCard.vue'
import ErrorHandler from '@/components/ErrorHandler.vue'

// 导入 API
import * as resumeApi from '@/api/resume'

// 路由
const router = useRouter()

// 状态
const userStore = useUserStore()

const inputMethod = ref<'file' | 'text'>('file')
const isLoading = ref(false)
const loadingMessage = ref('')
const parseResult = ref<any>(null)
const showProfile = ref(false)
const error = ref<any>(null)

// 编辑模式开关（为 true 时覆盖默认流程，只渲染编辑器）
const isEditing = ref(false)

// 输入方式变更
const onInputMethodChange = (method: 'file' | 'text') => {
  inputMethod.value = method
  parseResult.value = null
  showProfile.value = false
  error.value = null
}

// 文件上传处理
const onFileUpload = async (file: File) => {
  isLoading.value = true
  loadingMessage.value = '正在上传并解析简历...'
  error.value = null

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userStore.userId || '')

    const response = await resumeApi.parseFile(formData)

    if (response.status === 'success' || response.status === 'warning') {
      parseResult.value = {
        text: response.data?.text || '',
        quality_score: response.quality_score || 0,
        warnings: response.warnings || [],
        profile: response.profile || null,
        confidence: response.confidence || null
      }
      // 解析成功后直接展示画像（后端已一次性返回 profile），无需用户手动点"提取画像"；
      // 用户可在画像上直接点"编辑"修改。
      showProfile.value = true
    } else {
      error.value = {
        type: 'error',
        message: response.message || '解析失败，请重试'
      }
    }
  } catch (err: any) {
    error.value = {
      type: 'error',
      message: err.message || '上传失败，请检查网络连接'
    }
  } finally {
    isLoading.value = false
  }
}

// 文本提交处理
const onTextSubmit = async (text: string) => {
  isLoading.value = true
  loadingMessage.value = '正在解析文本...'
  error.value = null

  try {
    const response = await resumeApi.parseText({
      text,
      user_id: userStore.userId || ''
    })

    if (response.status === 'success' || response.status === 'warning') {
      parseResult.value = {
        text: text,
        quality_score: response.quality_score || 0,
        warnings: response.warnings || [],
        profile: response.profile || null,
        confidence: response.confidence || null
      }
      showProfile.value = true
    } else {
      error.value = {
        type: 'error',
        message: response.message || '解析失败，请重试'
      }
    }
  } catch (err: any) {
    error.value = {
      type: 'error',
      message: err.message || '解析失败，请检查网络连接'
    }
  } finally {
    isLoading.value = false
  }
}

// 示例简历：切换到文本模式并直接解析示例文本
// （示例是纯文本，必须走文本解析通道；之前伪装成 .txt 文件会被后端拒绝）
const onSampleText = async (text: string) => {
  inputMethod.value = 'text'
  await onTextSubmit(text)
}

// 重新上传
const onReupload = () => {
  parseResult.value = null
  showProfile.value = false
  error.value = null
}

// 进入画像编辑模式（由 ProfileDisplay 的"编辑"或 NextStepsCard 的"编辑/完善"触发）
const onProfileEdit = () => {
  isEditing.value = true
}

// 保存编辑后的画像
const onProfileSave = async (editedProfile: any) => {
  // 先本地更新，保证界面即时响应
  parseResult.value.profile = editedProfile
  isEditing.value = false

  // 调用后端持久化（MVP 阶段后端返回成功但未真正落库）
  try {
    await resumeApi.updateProfile({
      user_id: userStore.userId || '',
      profile: editedProfile
    })
    ElMessage.success('画像已保存')
  } catch (err: any) {
    // 持久化失败不影响本地编辑结果，仅提示
    ElMessage.warning('画像已本地更新，但保存到服务器失败')
  }
}

// 取消编辑
const onProfileEditCancel = () => {
  isEditing.value = false
}

// 保存画像（由 ProfileDisplay 的"保存画像"触发）—— 持久化到数据库，供后续 JD 匹配读取
const onSave = async () => {
  if (!parseResult.value?.profile) return
  try {
    await resumeApi.updateProfile({
      user_id: userStore.userId || '',
      profile: parseResult.value.profile
    })
    ElMessage.success('画像已保存，可用于 JD 匹配')
  } catch (err: any) {
    ElMessage.warning('保存到服务器失败，请稍后重试')
  }
}

// 清空画像（由 ProfileDisplay 的"清空画像"触发）—— 二次确认后删除数据库画像并重置页面
const onClear = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空当前画像吗？将同时删除已保存的画像数据，此操作不可撤销。',
      '清空画像',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return // 用户点了取消
  }

  try {
    await resumeApi.deleteProfile(userStore.userId || '')
    ElMessage.success('画像已清空')
  } catch (err: any) {
    ElMessage.warning('删除服务器画像失败，但本地已清空')
  }

  // 重置到初始状态（回到上传/粘贴入口）
  parseResult.value = null
  showProfile.value = false
  isEditing.value = false
  error.value = null
}

// 后续功能导航（由 NextStepsCard 触发）
const onNavigate = async (route: string) => {
  // JD 匹配：已实现，跳转前先保存画像（JD 匹配依赖持久化的画像）
  if (route === '/jd-matcher') {
    if (parseResult.value?.profile) {
      try {
        await resumeApi.updateProfile({
          user_id: userStore.userId || '',
          profile: parseResult.value.profile
        })
      } catch {
        // 保存失败不阻断跳转，JD 匹配页会提示无画像
      }
    }
    router.push('/jd-matcher')
    return
  }
  // 简历优化 / 模拟面试：尚未实现，给出明确提示
  const names: Record<string, string> = {
    '/resume-optimize': '简历优化',
    '/mock-interview': '模拟面试'
  }
  ElMessage.info(`${names[route] || '该功能'}正在开发中，敬请期待`)
}
</script>

<style scoped lang="scss">
.page {
  max-width: 1000px;
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
  }
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-2xl;
  color: $primary-color;
  font-size: $font-size-sm;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid $border-color;
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
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }

  .page-head h1 {
    font-size: $font-size-2xl;
  }
}
</style>
