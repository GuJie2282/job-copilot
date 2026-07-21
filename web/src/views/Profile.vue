<template>
  <div class="page">
    <!-- 页头 -->
    <header class="page-head">
      <p class="eyebrow">PROFILE</p>
      <h1>我的画像</h1>
      <p class="sub">查看与编辑你已保存的个人画像，它是 JD 匹配的基础。</p>
    </header>

    <!-- 加载中 -->
    <div v-if="loadState === 'loading'" class="state-block">
      <span class="spinner" />
      <p>正在读取画像…</p>
    </div>

    <!-- 无画像：引导去建立 -->
    <div v-else-if="loadState === 'empty'" class="state-block">
      <p class="state-title">还没有画像</p>
      <p class="state-sub">先上传简历或粘贴文本，AI 会帮你建立画像。</p>
      <button class="btn-primary" type="button" @click="goBuild">开始建立画像 →</button>
    </div>

    <!-- 读取失败：提示重试 -->
    <div v-else-if="loadState === 'error'" class="state-block">
      <p class="state-title">读取画像失败</p>
      <p class="state-sub">{{ errorMsg }}</p>
      <button class="btn-primary" type="button" @click="loadProfile">重试</button>
    </div>

    <!-- 有画像：展示 / 编辑（复用现有组件，零新展示逻辑） -->
    <template v-else>
      <ProfileEditor
        v-if="isEditing"
        :profile="profile"
        :confidence="confidence"
        @save="onEditorSave"
        @cancel="onEditorCancel"
      />
      <ProfileDisplay
        v-else
        :profile="profile"
        :confidence="confidence"
        @edit="onEdit"
        @save="onSave"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getProfile, updateProfile } from '@/api/resume'
import ProfileDisplay from '@/components/ProfileDisplay.vue'
import ProfileEditor from '@/components/ProfileEditor.vue'

const router = useRouter()
const userStore = useUserStore()

// 加载状态：loading 读取中 / ready 有画像 / empty 无画像 / error 读取失败
const loadState = ref<'loading' | 'ready' | 'empty' | 'error'>('loading')
const errorMsg = ref('')

// 画像数据（对应后端响应 data: { profile, confidence }）
const profileData = ref<any>(null)
const profile = computed(() => profileData.value?.profile ?? null)
const confidence = computed(() => profileData.value?.confidence ?? null)

// 编辑模式：true 渲染 ProfileEditor，false 渲染 ProfileDisplay
const isEditing = ref(false)

/** 读取画像 */
async function loadProfile(): Promise<void> {
  loadState.value = 'loading'
  errorMsg.value = ''
  try {
    const res = await getProfile(userStore.userId)
    if (res.status === 'success' && res.data) {
      if (res.data.profile) {
        profileData.value = res.data
        loadState.value = 'ready'
      } else {
        // data.profile 为 null → 用户尚未建立画像
        loadState.value = 'empty'
      }
    } else {
      loadState.value = 'error'
      errorMsg.value = res.message || '读取失败，请稍后重试'
    }
  } catch (e: any) {
    loadState.value = 'error'
    errorMsg.value = e?.message || '网络异常，请检查连接'
  }
}

/** 进入编辑（ProfileDisplay 的「编辑画像」触发） */
function onEdit(): void {
  isEditing.value = true
}

/** 编辑器取消：回到展示态（ProfileEditor 内部已深拷贝，取消即丢弃改动） */
function onEditorCancel(): void {
  isEditing.value = false
}

/** 编辑器保存：持久化 → 成功回展示态；失败保留编辑态不丢数据 */
async function onEditorSave(editedProfile: any): Promise<void> {
  try {
    await updateProfile({ user_id: userStore.userId, profile: editedProfile })
    // 本地更新，展示态即时反映最新值
    profileData.value = { ...profileData.value, profile: editedProfile }
    isEditing.value = false
    ElMessage.success('画像已保存')
  } catch {
    // 不切回展示态 → ProfileEditor 保持挂载，用户编辑不丢失
    ElMessage.warning('保存失败，请稍后重试')
  }
}

/** 直接「保存画像」（ProfileDisplay 的保存按钮：持久化当前画像，幂等 upsert） */
async function onSave(): Promise<void> {
  if (!profile.value) return
  try {
    await updateProfile({ user_id: userStore.userId, profile: profile.value })
    ElMessage.success('画像已保存')
  } catch {
    ElMessage.warning('保存失败，请稍后重试')
  }
}

/** 去建立画像 */
function goBuild(): void {
  router.push('/resume-parser')
}

onMounted(() => {
  loadProfile()
})
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

/* 状态块（加载 / 空 / 错误共用） */
.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: $spacing-md;
  padding: $spacing-3xl $spacing-xl;
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  color: $text-secondary;
}

.state-title {
  font-family: $font-heading;
  font-size: $font-size-xl;
  color: $ink;
}

.state-sub {
  font-size: $font-size-sm;
  color: $text-secondary;
  max-width: 40ch;
}

/* 加载 spinner */
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

/* 主按钮 */
.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-xl;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  transition: background $transition-base ease;

  &:hover {
    background: $primary-dark;
  }
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
