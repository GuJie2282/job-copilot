<template>
  <div class="education-list">
    <div class="section-header">
      <h4>教育背景</h4>
      <p class="hint">添加您的教育经历（可多个）</p>
    </div>

    <div
      v-for="(_, index) in educations"
      :key="index"
      class="education-item"
    >
      <div class="item-header">
        <h5>教育经历 #{{ index + 1 }}</h5>
        <button
          v-if="educations.length > 1"
          @click="removeEducation(index)"
          class="remove-btn"
          type="button"
        >
          删除
        </button>
      </div>

      <div class="form-grid">
        <FormField
          label="学校名称"
          v-model="profileData.schools[index]"
          placeholder="例如：清华大学"
        />
        <FormField
          label="学历"
          v-model="profileData.degrees[index]"
          placeholder="例如：本科、硕士、博士"
        />
        <FormField
          label="专业"
          v-model="profileData.majors[index]"
          placeholder="例如：计算机科学与技术"
        />
        <FormField
          label="毕业年份"
          v-model="profileData.graduation_years[index]"
          placeholder="例如：2022"
        />
      </div>
    </div>

    <button
      @click="addEducation"
      class="add-btn"
      type="button"
    >
      + 添加教育经历
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import FormField from './FormField.vue'

const props = defineProps<{
  modelValue: any
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void
}>()

const profileData = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 计算教育经历数量（取最长数组的长度）
const educations = computed(() => {
  const maxLength = Math.max(
    profileData.value.schools?.length || 0,
    profileData.value.degrees?.length || 0,
    profileData.value.majors?.length || 0,
    profileData.value.graduation_years?.length || 0,
    1  // 至少显示一个
  )
  return Array.from({ length: maxLength }, (_, i) => i)
})

const addEducation = () => {
  if (!profileData.value.schools) profileData.value.schools = []
  if (!profileData.value.degrees) profileData.value.degrees = []
  if (!profileData.value.majors) profileData.value.majors = []
  if (!profileData.value.graduation_years) profileData.value.graduation_years = []

  profileData.value.schools.push('')
  profileData.value.degrees.push('')
  profileData.value.majors.push('')
  profileData.value.graduation_years.push('')
}

const removeEducation = (index: number) => {
  if (profileData.value.schools?.length > 1) {
    profileData.value.schools.splice(index, 1)
    profileData.value.degrees?.splice(index, 1)
    profileData.value.majors?.splice(index, 1)
    profileData.value.graduation_years?.splice(index, 1)
  }
}
</script>

<style scoped lang="scss">
.education-list {
  margin-bottom: 2rem;
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-header h4 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.hint {
  color: $text-secondary;
  font-size: 0.85rem;
  margin: 0;
}

.education-item {
  background: $bg-gray;
  padding: 1.5rem;
  border-radius: $radius-md;
  margin-bottom: 1rem;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.item-header h5 {
  margin: 0;
  color: $ink;
}

.remove-btn {
  padding: 0.5rem 1rem;
  background: $error;
  color: white;
  border: none;
  border-radius: $radius-sm;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background $transition-slow ease;
}

.remove-btn:hover {
  background: $error;
  opacity: 0.9;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.add-btn {
  width: 100%;
  padding: 1rem;
  background: $primary-color;
  color: white;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all $transition-slow ease;
}

.add-btn:hover {
  background: $primary-dark;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($primary-color, 0.3);
}
</style>
