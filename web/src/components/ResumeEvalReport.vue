<template>
  <!-- 6 维评估报告展示（被 ResumeOptimizer / ResumeRefine 复用） -->
  <div class="eval-report">
    <!-- 总分 -->
    <div class="eval-overall">
      <span class="score tnum" :style="{ color: scoreColor }">{{ evalReport?.overall_score ?? '-' }}</span>
      <div class="meta">
        <div class="label">/ 100 · {{ evalReport?.passed ? '通过' : '需改进' }}</div>
        <div class="sub">6 维加权评估</div>
      </div>
    </div>

    <!-- 六维度 -->
    <div v-if="evalReport?.dimensions" class="dims">
      <div v-for="(dim, key) in evalReport.dimensions" :key="key" class="dim">
        <div class="dim-name">{{ dimName(String(key)) }}</div>
        <div class="dim-bar">
          <div class="dim-bar-fill" :style="{ width: barWidth(dim.score), background: colorFor(dim.score) }" />
        </div>
        <div class="dim-score tnum" :style="{ color: colorFor(dim.score) }">{{ dim.score }}</div>
        <div class="dim-weight">权重 {{ Math.round(dim.weight * 100) }}%</div>
        <div class="dim-flag" :class="{ pass: dim.passed, fail: !dim.passed }">
          {{ dim.passed ? '✓' : '✗' }}
        </div>
      </div>
    </div>

    <!-- 改进优先级 -->
    <div v-if="priorities.length" class="priorities">
      <h4 class="block-title">改进优先级</h4>
      <ul>
        <li v-for="(p, i) in priorities" :key="i" :class="`prio prio-${p.priority}`">
          <span class="tag">{{ prioLabel(p.priority) }}</span>
          <span class="text">{{ p.suggestion }}</span>
        </li>
      </ul>
    </div>

    <!-- 格式校验 -->
    <div v-if="formatErrors.length" class="fmt-warn">
      <b>格式校验问题：</b>{{ formatErrors.join('；') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResumeEvalReport } from '@/types/resume'

const props = defineProps<{ evalReport: ResumeEvalReport | null | undefined }>()

const priorities = computed(() => props.evalReport?.feedback_priorities || [])
const formatErrors = computed(() => props.evalReport?.format_validation?.errors || [])
const scoreColor = computed(() => colorFor(props.evalReport?.overall_score))

// 分数 → 颜色（对齐设计 token：success / warning / error）
function colorFor(s?: number) {
  if ((s ?? 0) >= 75) return '#10b981'
  if ((s ?? 0) >= 50) return '#d97706'
  return '#ef4444'
}
function barWidth(s: number) {
  return `${Math.max(0, Math.min(100, s ?? 0))}%`
}

// 维度 key → 中文名
const DIM_NAMES: Record<string, string> = {
  basic_norm: '基础规范',
  jd_match: 'JD 匹配',
  quantification: '成果量化',
  structure: '结构清晰',
  differentiation: '差异化',
  language: '语言表达',
}
function dimName(key: string) {
  return DIM_NAMES[key] || key
}
function prioLabel(p: string) {
  return { high: '高', medium: '中', low: '低' }[p] || p
}
</script>

<style scoped lang="scss">
.eval-report {
  font-size: $font-size-sm;
}

.eval-overall {
  display: flex;
  align-items: baseline;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;

  .score {
    font-family: $font-heading;
    font-size: 48px;
    font-weight: $font-weight-bold;
    line-height: 1;
  }

  .label {
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }

  .sub {
    color: $text-secondary;
    font-size: $font-size-xs;
  }
}

.dims {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  margin-bottom: $spacing-lg;
}

.dim {
  display: grid;
  grid-template-columns: 80px 1fr 36px 64px 20px;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-xs;
}

.dim-name {
  color: $text-primary;
}

.dim-bar {
  height: 6px;
  background: $bg-gray;
  border-radius: 3px;
  overflow: hidden;
}

.dim-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.dim-score {
  text-align: right;
  font-weight: $font-weight-semibold;
}

.dim-weight {
  color: $text-disabled;
  font-size: 10px;
}

.dim-flag {
  text-align: center;
  font-weight: $font-weight-bold;

  &.pass { color: #10b981; }
  &.fail { color: #ef4444; }
}

.block-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  margin-bottom: $spacing-sm;
  color: $text-primary;
}

.priorities ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.prio {
  display: flex;
  align-items: baseline;
  gap: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-secondary;
  line-height: $line-height-normal;

  .tag {
    font-family: $font-mono;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: $radius-sm;
    flex-shrink: 0;

    @at-root .prio-high .tag { background: rgba(239, 68, 68, 0.12); color: #ef4444; }
    @at-root .prio-medium .tag { background: rgba(217, 119, 6, 0.12); color: #d97706; }
    @at-root .prio-low .tag { background: $bg-gray; color: $text-secondary; }
  }
}

.fmt-warn {
  margin-top: $spacing-md;
  padding: $spacing-sm $spacing-md;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: $radius-md;
  color: #ef4444;
  font-size: $font-size-xs;
}
</style>
