<template>
  <div class="work-list">
    <div class="section-header">
      <h4>工作经历</h4>
      <p class="hint">添加您的工作经验（可多个）</p>
    </div>

    <div
      v-for="(_, index) in works"
      :key="index"
      class="work-item"
    >
      <div class="item-header">
        <h5>工作经历 #{{ index + 1 }}</h5>
        <button
          v-if="works.length > 1"
          @click="removeWork(index)"
          class="remove-btn"
          type="button"
        >
          删除
        </button>
      </div>

      <div class="form-grid">
        <FormField
          label="公司名称"
          v-model="profileData.companies[index]"
          placeholder="例如：字节跳动"
        />
        <FormField
          label="职位"
          v-model="profileData.positions[index]"
          placeholder="例如：产品经理"
        />
        <FormField
          label="工作时间"
          v-model="profileData.durations[index]"
          placeholder="例如：2022-至今"
        />
      </div>
      <div class="work-description-field">
        <label>职责与成果详情</label>
        <textarea
          :value="profileData.work_descriptions?.[index] || ''"
          @input="setWorkDescription(index, ($event.target as HTMLTextAreaElement).value)"
          placeholder="例如：负责 XX 模块的需求分析与原型设计，推动评审通过率 95%…"
          rows="3"
        ></textarea>
      </div>
    </div>

    <button
      @click="addWork"
      class="add-btn"
      type="button"
    >
      + 添加工作经历
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

// 计算工作经历数量（取最长数组的长度）
const works = computed(() => {
  const maxLength = Math.max(
    profileData.value.companies?.length || 0,
    profileData.value.positions?.length || 0,
    profileData.value.durations?.length || 0,
    profileData.value.work_descriptions?.length || 0,
    1  // 至少显示一个
  )
  return Array.from({ length: maxLength }, (_, i) => i)
})

// 设置某段工作的详情（保证 work_descriptions 数组存在且长度足够，避免下标越界）
const setWorkDescription = (index: number, value: string) => {
  const p = profileData.value
  if (!p.work_descriptions) p.work_descriptions = []
  while (p.work_descriptions.length <= index) p.work_descriptions.push('')
  p.work_descriptions[index] = value
}

const addWork = () => {
  if (!profileData.value.companies) profileData.value.companies = []
  if (!profileData.value.positions) profileData.value.positions = []
  if (!profileData.value.durations) profileData.value.durations = []
  if (!profileData.value.work_descriptions) profileData.value.work_descriptions = []

  profileData.value.companies.push('')
  profileData.value.positions.push('')
  profileData.value.durations.push('')
  profileData.value.work_descriptions.push('')
}

const removeWork = (index: number) => {
  if (profileData.value.companies?.length > 1) {
    profileData.value.companies.splice(index, 1)
    profileData.value.positions?.splice(index, 1)
    profileData.value.durations?.splice(index, 1)
    profileData.value.work_descriptions?.splice(index, 1)
  }
}
</script>

<style scoped lang="scss">
.work-list {
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

.work-item {
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

/* 工作经历详情输入框（占满整行） */
.work-description-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.work-description-field label {
  font-weight: 600;
  color: $ink;
  font-size: 0.9rem;
}

.work-description-field textarea {
  padding: 0.75rem;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.5;
  resize: vertical;
}

.work-description-field textarea:focus {
  outline: none;
  border-color: $primary-color;
}
</style>
