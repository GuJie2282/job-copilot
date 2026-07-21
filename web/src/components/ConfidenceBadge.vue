<template>
  <div
    class="confidence-badge tnum"
    :class="badgeClass"
    :title="`置信度：${scorePercent}`"
  >
    {{ scorePercent }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  score: number
  level?: string
}>()

const scorePercent = computed(() => {
  return Math.round(props.score * 100) + '%'
})

const badgeClass = computed(() => {
  if (props.score >= 0.8) return 'high'
  if (props.score >= 0.6) return 'medium'
  return 'low'
})
</script>

<style scoped lang="scss">
// 置信度三态：对齐设计 token 的 success / warning / error 体系
.confidence-badge {
  display: inline-block;
  padding: $spacing-xs $spacing-md;
  border-radius: $radius-full;
  font-size: $font-size-xs;
  font-weight: $font-weight-bold;
  white-space: nowrap;

  &.high {
    background: $success-light;
    color: $success;
  }

  &.medium {
    background: $warning-light;
    color: $warning;
  }

  &.low {
    background: $error-light;
    color: $error;
  }
}
</style>
