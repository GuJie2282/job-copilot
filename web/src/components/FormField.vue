<template>
  <div class="form-field">
    <label class="field-label">{{ label }}</label>
    <input
      v-model="innerValue"
      type="text"
      :placeholder="placeholder"
      class="field-input"
      :disabled="disabled"
    />
    <ConfidenceBadge
      v-if="confidence && showConfidence"
      :score="confidence.score"
      :level="confidence.level"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ConfidenceBadge from './ConfidenceBadge.vue'

const props = defineProps<{
  label: string
  modelValue: string
  confidence?: {
    score: number
    level: string
  }
  placeholder?: string
  disabled?: boolean
  showConfidence?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const innerValue = computed({
  get: () => props.modelValue || '',
  set: (value: string) => emit('update:modelValue', value)
})
</script>

<style scoped lang="scss">
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: $text-secondary;
}

.field-input {
  padding: 0.75rem;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  font-size: 1rem;
  font-family: inherit;
  transition: border-color $transition-slow ease;
}

.field-input:focus {
  outline: none;
  border-color: $primary-color;
}

.field-input:disabled {
  background: $bg-gray;
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
