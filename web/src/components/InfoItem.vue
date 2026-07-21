<template>
  <div class="info-item">
    <label class="label">{{ label }}</label>
    <div class="value-wrapper">
      <span class="value" :title="value ?? undefined">{{ value || '未提取' }}</span>
      <ConfidenceBadge
        v-if="confidence"
        :score="confidence.score"
        :level="confidence.level"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import ConfidenceBadge from './ConfidenceBadge.vue'

defineProps<{
  label: string
  value: string | null
  confidence?: {
    score: number
    level: string
  }
}>()
</script>

<style scoped lang="scss">
.info-item {
  padding: 0.75rem;
  background: $bg-gray;
  border-radius: $radius-md;
}

.label {
  display: block;
  font-size: 0.85rem;
  color: $text-secondary;
  margin-bottom: 0.25rem;
  font-weight: 600;
}

.value-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.value {
  flex: 1;
  font-size: 1rem;
  color: $ink;
  word-break: break-all;
}

.value:not(:empty) {
  font-weight: 500;
}
</style>
