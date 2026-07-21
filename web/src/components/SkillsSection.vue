<template>
  <div class="skills-section">
    <div class="section-header">
      <h4>技能与能力</h4>
      <p class="hint">填写您的技能列表（用逗号分隔）</p>
    </div>

    <div class="skills-category">
      <label class="category-label">技术技能</label>
      <textarea
        v-model="profileData.technical_skills"
        class="skills-textarea"
        placeholder="例如：Python, Java, React, Vue, TensorFlow, SQL&#10;（用逗号或换行分隔）"
        rows="3"
      />
      <p class="help-text">编程语言、框架、工具等技术能力</p>
    </div>

    <div class="skills-category">
      <label class="category-label">软技能</label>
      <textarea
        v-model="profileData.soft_skills"
        class="skills-textarea"
        placeholder="例如：团队协作, 项目管理, 沟通能力, 问题解决&#10;（用逗号或换行分隔）"
        rows="3"
      />
      <p class="help-text">沟通、领导力、时间管理等软技能</p>
    </div>

    <div class="skills-category">
      <label class="category-label">语言能力</label>
      <textarea
        v-model="profileData.languages"
        class="skills-textarea"
        placeholder="例如：英语（流利）, 日语（N2）, 中文（母语）&#10;（用逗号或换行分隔）"
        rows="2"
      />
      <p class="help-text">外语能力及水平</p>
    </div>

    <div class="tips">
      <h5>填写建议</h5>
      <ul>
        <li>填写与求职目标相关的技能</li>
        <li>真实反映自己的能力水平</li>
        <li>优先填写硬技能（技术技能）</li>
        <li>用逗号或换行分隔多个技能</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

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
</script>

<style scoped lang="scss">
.skills-section {
  margin-bottom: 2rem;
}

.section-header {
  margin-bottom: 2rem;
  text-align: center;
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

.skills-category {
  margin-bottom: 2rem;
}

.category-label {
  display: block;
  font-size: 0.95rem;
  font-weight: 600;
  color: $ink;
  margin-bottom: 0.5rem;
}

.skills-textarea {
  width: 100%;
  padding: 1rem;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  transition: border-color $transition-slow ease;
}

.skills-textarea:focus {
  outline: none;
  border-color: $primary-color;
  box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
}

.help-text {
  color: $text-secondary;
  font-size: 0.85rem;
  margin: 0.5rem 0 0 0;
}

.tips {
  background: $primary-lighter;
  padding: 1.5rem;
  border-radius: $radius-md;
  border-left: 4px solid $primary-color;
}

.tips h5 {
  margin: 0 0 1rem 0;
  color: $ink;
}

.tips ul {
  margin: 0;
  padding-left: 1.5rem;
  color: $text-secondary;
  font-size: 0.9rem;
  line-height: 1.6;
}

.tips li {
  margin-bottom: 0.5rem;
}
</style>
