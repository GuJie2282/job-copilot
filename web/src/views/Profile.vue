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

    <!-- 有画像：身份卡 signature + 展示/编辑 -->
    <template v-else>
      <!-- SIGNATURE：职业身份卡（编码"你是谁、做什么、擅长什么、画像多可靠"） -->
      <section v-if="!isEditing" class="identity-card">
        <label class="id-avatar" :class="{ uploading: avatarUploading }" :title="profile?.avatar_url ? '点击更换头像' : '点击上传头像'">
          <img v-if="profile?.avatar_url" :src="profile.avatar_url" alt="头像" />
          <span v-else>{{ initials }}</span>
          <input type="file" accept="image/jpeg,image/png" hidden @change="onAvatarChange" />
        </label>
        <div class="id-main">
          <div class="id-name-row">
            <h2 class="id-name">{{ profile?.name || '求职者' }}</h2>
            <span v-if="workCount" class="id-role tnum">{{ workCount }} 段经历</span>
          </div>
          <p v-if="latestPosition" class="id-position">{{ latestPosition }}</p>
          <div v-if="topSkills.length" class="id-skills">
            <span v-for="s in topSkills" :key="s" class="id-skill">{{ s }}</span>
          </div>
        </div>
        <div class="id-health">
          <template v-if="totalConfCount > 0">
            <span class="id-health-num tnum">{{ highConfCount }}<small>/{{ totalConfCount }}</small></span>
            <span class="id-health-label">高置信</span>
          </template>
          <span v-else class="id-health-ready">画像已就绪</span>
        </div>
      </section>

      <!-- 展示 / 编辑（复用现有组件） -->
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
import { ref, computed, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getProfile, updateProfile, deleteProfile, uploadAvatar } from '@/api/resume'
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

// ===== SIGNATURE 数据：职业身份卡 =====
// 首字母（姓名取首字，无则用品牌字"求"）
const initials = computed(() => {
  const n = profile.value?.name || ''
  return n ? n.charAt(0).toUpperCase() : '求'
})

// 最近一段职位 @ 公司（work_experience 嵌套数组取首项）
const latestPosition = computed(() => {
  const w = profile.value?.work_experience?.[0]
  if (!w) return ''
  const pos = w.position
  const comp = w.company
  if (pos && comp) return `${pos} @ ${comp}`
  return pos || comp || ''
})

// 工作经历段数（work_experience 数组长度）
const workCount = computed(() => profile.value?.work_experience?.length ?? 0)

// 核心技能标签（技术技能取前 4）
const topSkills = computed(() => (profile.value?.technical_skills || []).slice(0, 4))

// 画像健康度：高置信字段数 / 总字段数（复用 ProfileDisplay 的算法）
const highConfCount = computed(() => {
  if (!confidence.value) return 0
  return Object.values(confidence.value).filter((c: any) => c?.score >= 0.8).length
})
const totalConfCount = computed(() => (confidence.value ? Object.keys(confidence.value).length : 0))

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

/** 上传/更换头像（add-resume-avatar）：点头像触发文件选择 → 上传 → 回显。
 *  前端预校验 ≤2MB；后端再校验类型/魔数。上传中头像半透明 + 禁用态。 */
const avatarUploading = ref(false)
async function onAvatarChange(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('头像过大（≤ 2MB），请压缩后再上传')
    input.value = ''
    return
  }
  avatarUploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await uploadAvatar(userStore.userId, fd)
    if (res.status === 'success' && res.data?.avatar_url) {
      profileData.value = {
        ...profileData.value,
        profile: { ...(profile.value || {}), avatar_url: res.data.avatar_url },
      }
      ElMessage.success('头像已更新')
    } else {
      ElMessage.error(res.message || '头像上传失败')
    }
  } catch (err: any) {
    ElMessage.error(err?.message || '头像上传失败')
  } finally {
    avatarUploading.value = false
    input.value = ''  // 重置，允许重复选同一文件
  }
}

/** 清空画像（ProfileDisplay 的「清空画像」触发）—— 二次确认后删除画像并回到「无画像」态 */
async function onClear(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '确定要清空当前画像吗？将同时删除已保存的画像数据，此操作不可撤销。',
      '清空画像',
      { confirmButtonText: '确定清空', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户点了取消
  }
  try {
    await deleteProfile(userStore.userId)
    ElMessage.success('画像已清空')
    // 重置本地状态：回到「无画像」引导态
    profileData.value = null
    loadState.value = 'empty'
    isEditing.value = false
  } catch {
    ElMessage.warning('删除服务器画像失败，请稍后重试')
  }
}

// 通过 provide 把清空函数注入 ProfileDisplay 子组件（子组件 inject 后直接调用）
provide('clearProfile', onClear)

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
  // 减顶栏 65px，避免底部空白溢出（与 Home/JdMatcher 同款修复）
  min-height: calc(100vh - 65px);
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

/* ===== SIGNATURE：职业身份卡 ===== */
.identity-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: $spacing-xl;
  background: $bg-white;
  border: 1px solid $border-color;
  border-left: 3px solid $accent-color;  // 琥珀签名条（和 Home 的 next-card 同语言）
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-lg $spacing-xl;
  margin-bottom: $spacing-xl;
}

.id-avatar {
  width: 56px;
  height: 56px;
  border-radius: $radius-full;
  background: $primary-color;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: $font-heading;
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  cursor: pointer;        // 点头像上传/更换
  overflow: hidden;       // 图片按圆形裁剪
  position: relative;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &.uploading {
    opacity: 0.6;
    cursor: progress;
  }
}

.id-main {
  min-width: 0;
}

.id-name-row {
  display: flex;
  align-items: baseline;
  gap: $spacing-md;
  margin-bottom: $spacing-xs;
}

.id-name {
  font-size: $font-size-xl;
  color: $ink;
  margin: 0;
}

.id-role {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.id-position {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
}

.id-skills {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
}

.id-skill {
  padding: $spacing-xs $spacing-sm;
  background: $primary-lighter;
  color: $primary-color;
  border-radius: $radius-full;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
}

.id-health {
  text-align: center;
  padding-left: $spacing-lg;
  border-left: 1px solid $border-color;
}

.id-health-num {
  display: block;
  font-family: $font-heading;
  font-size: $font-size-xl;
  font-weight: $font-weight-bold;
  color: $ink;
  line-height: 1;

  small {
    font-size: $font-size-xs;
    color: $text-disabled;
    font-weight: $font-weight-normal;
  }
}

.id-health-label {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: $spacing-xs;
  display: block;
}

// confidence 数据缺失时的就绪态（避免显示 0/0）
.id-health-ready {
  font-size: $font-size-xs;
  color: $success;
  font-weight: $font-weight-medium;
  padding: $spacing-xs $spacing-sm;
  background: $success-light;
  border-radius: $radius-full;
  white-space: nowrap;
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

  // 窄屏：身份卡转单列（头像→主体→健康度 纵排）
  .identity-card {
    grid-template-columns: 1fr;
    gap: $spacing-md;
    justify-items: center;
    text-align: center;

    .id-name-row {
      justify-content: center;
    }

    .id-skills {
      justify-content: center;
    }

    .id-health {
      border-left: none;
      border-top: 1px solid $border-color;
      padding-left: 0;
      padding-top: $spacing-md;
    }
  }
}
</style>
