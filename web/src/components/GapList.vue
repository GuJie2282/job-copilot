<template>
  <div class="gap-list">
    <div v-if="!gaps || gaps.length === 0" class="empty">
      没有明显差距，匹配度良好。
    </div>

    <div
      v-for="(g, i) in gaps"
      :key="i"
      class="gap-item"
      :style="{ borderLeftColor: sevColor(g.severity) }"
    >
      <div class="gap-head">
        <span class="sev-tag" :style="{ background: sevColor(g.severity) }">
          {{ sevLabel(g.severity) }}
        </span>
        <span class="type-tag">{{ typeLabel(g.type) }}</span>
        <span class="req">{{ g.requirement }}</span>
        <span v-if="g.need_confirm" class="confirm">待确认</span>
      </div>
      <div class="gap-body">
        <div class="row"><span class="k">现状：</span>{{ g.current_state || '画像中未体现' }}</div>
        <div class="row"><span class="k">建议：</span>{{ g.suggestion || '（正在生成建议…）' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Gap } from '@/types/jd'

defineProps<{ gaps?: Gap[] }>()

// 严重度配色：用 CSS 变量字符串，单一来源对齐设计 token（error / warning / primary / secondary）
const SEV_COLOR: Record<string, string> = {
  critical: 'var(--error)',
  high: 'var(--warning)',
  medium: 'var(--primary-color)',
  low: 'var(--text-secondary)'
}
const SEV_LABEL: Record<string, string> = {
  critical: '红线',
  high: '严重',
  medium: '中等',
  low: '轻微'
}
const TYPE_LABEL: Record<string, string> = {
  hard_skill: '硬技能差距',
  soft_skill: '软技能表述',
  implicit: '隐性偏好',
  redline: '红线预警'
}

function sevColor(s?: string) {
  return SEV_COLOR[s || ''] || 'var(--text-secondary)'
}
function sevLabel(s?: string) {
  return SEV_LABEL[s || ''] || s
}
function typeLabel(t?: string) {
  return TYPE_LABEL[t || ''] || t
}
</script>

<style scoped lang="scss">
.empty {
  color: $success;
  padding: $spacing-lg;
  text-align: center;
  font-size: $font-size-sm;
}

.gap-item {
  border-left: 3px solid $border-color;
  background: $bg-gray;
  padding: $spacing-md;
  margin-bottom: $spacing-sm;
  border-radius: $radius-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.gap-head {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;
  margin-bottom: $spacing-sm;
}

.sev-tag {
  font-size: $font-size-xs;
  padding: 1px 9px;
  border-radius: $radius-full;
  color: #fff;
  white-space: nowrap;
}

.type-tag {
  font-size: $font-size-xs;
  color: $text-secondary;
  background: $bg-white;
  border: 1px solid $border-color;
  padding: 1px 8px;
  border-radius: $radius-sm;
}

.req {
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.confirm {
  font-size: $font-size-xs;
  color: $warning;
  border: 1px solid $warning;
  border-radius: $radius-sm;
  padding: 0 5px;
}

.gap-body {
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: $line-height-relaxed;

  .row {
    margin: 2px 0;
  }

  .k {
    color: $text-disabled;
  }
}
</style>
