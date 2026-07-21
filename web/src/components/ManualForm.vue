<template>
  <div class="manual-form">
    <div class="form-header">
      <h3>手动填写画像</h3>
      <p class="hint">分步骤填写个人信息，可以随时保存草稿</p>
    </div>

    <div class="form-content">
      <!-- 步骤指示器 -->
      <div class="steps-indicator">
        <div
          v-for="(_, index) in steps"
          :key="index"
          class="step-dot"
          :class="{ active: currentStep === index, completed: currentStep > index }"
        >
          {{ index + 1 }}
        </div>
      </div>

      <div class="step-title">
        <h4>{{ steps[currentStep]?.title }}</h4>
        <p>{{ steps[currentStep]?.description }}</p>
      </div>

      <!-- 步骤 1：基本信息 -->
      <div v-if="currentStep === 0" class="step-content">
        <div class="form-grid">
          <FormField
            label="姓名 *"
            v-model="profileData.name"
            placeholder="请输入您的姓名"
          />
          <FormField
            label="电话"
            v-model="profileData.phone"
            placeholder="请输入手机号码"
          />
          <FormField
            label="邮箱 *"
            v-model="profileData.email"
            placeholder="请输入邮箱地址"
          />
          <FormField
            label="所在地"
            v-model="profileData.location"
            placeholder="例如：北京、上海"
          />
        </div>
      </div>

      <!-- 步骤 2：教育背景 -->
      <div v-if="currentStep === 1" class="step-content">
        <EducationList v-model="profileData" />
      </div>

      <!-- 步骤 3：工作经历 -->
      <div v-if="currentStep === 2" class="step-content">
        <WorkList v-model="profileData" />
      </div>

      <!-- 步骤 4：技能 -->
      <div v-if="currentStep === 3" class="step-content">
        <SkillsSection v-model="profileData" />
      </div>

      <!-- 步骤 5：求职目标 -->
      <div v-if="currentStep === 4" class="step-content">
        <div class="form-grid">
          <FormField
            label="目标岗位"
            v-model="profileData.target_positions"
            placeholder="例如：产品经理、前端工程师"
          />
          <FormField
            label="目标公司"
            v-model="profileData.target_companies"
            placeholder="例如：字节跳动、阿里巴巴"
          />
          <FormField
            label="期望地点"
            v-model="profileData.location_preference"
            placeholder="例如：北京、上海、深圳"
          />
          <FormField
            label="期望薪资"
            v-model="profileData.salary_range"
            placeholder="例如：15-25K/月"
          />
          <FormField
            label="期望行业"
            v-model="profileData.industry"
            placeholder="例如：互联网、人工智能"
          />
        </div>
      </div>

      <!-- 导航按钮 -->
      <div class="navigation">
        <button
          v-if="currentStep > 0"
          class="prev-btn"
          @click="previousStep"
          type="button"
        >
          上一步
        </button>

        <button
          v-if="currentStep < steps.length - 1"
          class="next-btn"
          @click="nextStep"
          type="button"
        >
          下一步
        </button>

        <button
          v-if="currentStep === steps.length - 1"
          class="submit-btn"
          @click="submit"
          type="button"
        >
          完成填写
        </button>

        <button
          class="draft-btn"
          @click="saveDraft"
          type="button"
        >
          保存草稿
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import FormField from './FormField.vue'
import EducationList from './EducationList.vue'
import WorkList from './WorkList.vue'
import SkillsSection from './SkillsSection.vue'

const emit = defineEmits<{
  (e: 'submit', profile: any): void
  (e: 'saveDraft', profile: any): void
}>()

const currentStep = ref(0)

const steps = [
  { title: '基本信息', description: '填写您的基本联系方式' },
  { title: '教育背景', description: '添加您的教育经历' },
  { title: '工作经历', description: '添加您的工作经验' },
  { title: '技能与能力', description: '填写您的技能列表' },
  { title: '求职目标', description: '说明您的求职期望' }
]

const profileData = reactive({
  name: '',
  phone: '',
  email: '',
  location: '',
  schools: [''],
  degrees: [''],
  majors: [''],
  graduation_years: [''],
  companies: [''],
  positions: [''],
  durations: [''],
  technical_skills: '',
  soft_skills: '',
  languages: '',
  target_positions: '',
  target_companies: '',
  location_preference: '',
  salary_range: '',
  industry: ''
})

const nextStep = () => {
  // 验证当前步骤
  if (!validateCurrentStep()) return
  currentStep.value++
}

const previousStep = () => {
  currentStep.value--
}

const validateCurrentStep = (): boolean => {
  // 步骤 1：基本信息
  if (currentStep.value === 0) {
    if (!profileData.name?.trim()) {
      alert('请填写姓名')
      return false
    }
    if (!profileData.email?.trim()) {
      alert('请填写邮箱')
      return false
    }
    // 简单的邮箱格式验证
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(profileData.email)) {
      alert('请填写正确的邮箱格式')
      return false
    }
  }

  // 步骤 2：教育背景（至少填写一个）
  if (currentStep.value === 1) {
    const hasEducation = profileData.schools?.some(s => s?.trim()) ||
                        profileData.degrees?.some(d => d?.trim())
    if (!hasEducation) {
      alert('请至少填写一项教育经历')
      return false
    }
  }

  // 步骤 3：工作经历（可选，但如果有至少填写一个）
  if (currentStep.value === 2) {
    const companies = profileData.companies?.filter(c => c?.trim())
    const positions = profileData.positions?.filter(p => p?.trim())
    if (companies.length > 0 && positions.length === 0) {
      alert('填写公司名称时请同时填写职位')
      return false
    }
  }

  // 步骤 4：技能（可选，不做强制验证）

  // 步骤 5：求职目标（可选，不做强制验证）

  return true
}

/**
 * 按行过滤并行数组：保证各数组长度一致。
 * 只有当一行的所有字段都为空时才丢弃该行，避免分别 filter 导致长度错位。
 * 例：schools=['清华','北大'], degrees=['本科',''] → 两行都保留，对齐返回。
 */
function filterParallelArrays(...arrays: string[][]): string[][] {
  const maxLen = Math.max(...arrays.map(a => a?.length || 0))
  const result: string[][] = arrays.map(() => [])
  for (let i = 0; i < maxLen; i++) {
    const row = arrays.map(a => a[i] ?? '')
    // 整行全空才丢弃；任一字段有值就保留整行（含空字段）
    if (row.some(v => v.trim())) {
      row.forEach((v, k) => result[k]?.push(v))
    }
  }
  return result
}

const submit = () => {
  if (!validateCurrentStep()) return

  // 教育背景：4 个并行数组按行过滤，保证长度一致
  const [schools, degrees, majors, graduation_years] = filterParallelArrays(
    profileData.schools,
    profileData.degrees,
    profileData.majors,
    profileData.graduation_years
  )

  // 工作经历：3 个并行数组按行过滤，保证长度一致
  const [companies, positions, durations] = filterParallelArrays(
    profileData.companies,
    profileData.positions,
    profileData.durations
  )

  // 转换为数组格式
  const formattedProfile = {
    ...profileData,
    schools,
    degrees,
    majors,
    graduation_years,
    companies,
    positions,
    durations,
    technical_skills: profileData.technical_skills
      .split(',')
      .map(s => s.trim())
      .filter(s => s),
    soft_skills: profileData.soft_skills
      .split(',')
      .map(s => s.trim())
      .filter(s => s),
    languages: profileData.languages
      .split(',')
      .map(s => s.trim())
      .filter(s => s)
  }

  emit('submit', formattedProfile)
}

const saveDraft = () => {
  emit('saveDraft', profileData)
}
</script>

<style scoped lang="scss">
.manual-form {
  margin: 2rem 0;
  padding: 2rem;
  background: white;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
}

.form-header {
  text-align: center;
  margin-bottom: 2rem;
}

.form-header h3 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.hint {
  color: $text-secondary;
  font-size: 0.9rem;
}

.steps-indicator {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.step-dot {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: $bg-gray;
  color: $text-secondary;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  transition: all $transition-slow ease;
}

.step-dot.active {
  background: $primary-color;
  color: white;
  transform: scale(1.1);
}

.step-dot.completed {
  background: $success;
  color: white;
}

.step-title {
  text-align: center;
  margin-bottom: 2rem;
}

.step-title h4 {
  margin: 0 0 0.5rem 0;
  color: $ink;
  font-size: 1.2rem;
}

.step-title p {
  margin: 0;
  color: $text-secondary;
}

.step-content {
  margin-bottom: 2rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.navigation {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.navigation button {
  padding: 1rem 2rem;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all $transition-slow ease;
}

.prev-btn {
  background: $text-disabled;
  color: white;
}

.prev-btn:hover {
  background: $text-secondary;
}

.next-btn {
  background: $primary-color;
  color: white;
}

.next-btn:hover {
  background: $primary-dark;
}

.submit-btn {
  background: $success;
  color: white;
}

.submit-btn:hover {
  background: $success;
  opacity: 0.9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($success, 0.3);
}

.draft-btn {
  background: $warning;
  color: white;
}

.draft-btn:hover {
  background: $accent-color;
}
</style>
