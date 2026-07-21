<template>
  <div class="score-radar">
    <svg :viewBox="`0 0 ${size} ${size}`" class="radar-svg">
      <!-- 同心网格 -->
      <circle v-for="r in rings" :key="r" class="grid" :cx="c" :cy="c" :r="r" />
      <!-- 四条轴线 -->
      <line v-for="(p, i) in axesEnd" :key="'a' + i" class="grid" :x1="c" :y1="c" :x2="p.x" :y2="p.y" />
      <!-- 数据多边形 -->
      <polygon class="data-poly" :points="dataPointsStr" />
      <!-- 数据点 -->
      <circle v-for="(p, i) in dataPoints" :key="'d' + i" class="data-dot" :cx="p.x" :cy="p.y" r="3.5" />
      <!-- 维度标签 + 分数 -->
      <template v-for="(lbl, i) in labels" :key="'l' + i">
        <text :x="labelPos(i).x" :y="labelPos(i).y" text-anchor="middle" class="axis-label">{{ lbl.text }}</text>
        <text :x="labelPos(i).x" :y="labelPos(i).y + 16" text-anchor="middle" class="axis-score tnum">{{ lbl.score ?? '-' }}</text>
      </template>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  skill?: number
  experience?: number
  education?: number
  softSkill?: number
}>()

const size = 280
const c = size / 2
const R = 95                 // 最大半径
const rings = [R * 0.25, R * 0.5, R * 0.75, R]

// 四个维度：上=技能、右=经验、下=学历、左=软技能
const labels = computed(() => [
  { text: '技能', score: props.skill },
  { text: '经验', score: props.experience },
  { text: '学历', score: props.education },
  { text: '软技能', score: props.softSkill }
])

function axisDir(i: number) {
  const angle = -Math.PI / 2 + (i * Math.PI) / 2  // 从正上方开始顺时针
  return { x: Math.cos(angle), y: Math.sin(angle) }
}

function pointFor(i: number, score?: number) {
  const s = (score ?? 0) / 100
  const d = axisDir(i)
  return { x: c + d.x * R * s, y: c + d.y * R * s }
}

const axesEnd = computed(() => [0, 1, 2, 3].map((i) => pointFor(i, 100)))
const dataPoints = computed(() => [0, 1, 2, 3].map((i) => pointFor(i, labels.value[i]?.score)))
const dataPointsStr = computed(() => dataPoints.value.map((p) => `${p.x},${p.y}`).join(' '))

function labelPos(i: number) {
  const d = axisDir(i)
  return { x: c + d.x * (R + 24), y: c + d.y * (R + 24) }
}
</script>

<style scoped lang="scss">
// 配色全部走设计 token（$primary-color / $ink / $text-secondary / $border-color）
.score-radar {
  display: flex;
  justify-content: center;
}

.radar-svg {
  width: 280px;
  height: 280px;
}

.grid {
  fill: none;
  stroke: $border-color;
  stroke-width: 1;
}

.data-poly {
  fill: $primary-color;
  fill-opacity: 0.25;
  stroke: $primary-color;
  stroke-width: 2;
}

.data-dot {
  fill: $primary-color;
}

.axis-label {
  font-family: $font-body;
  font-size: 13px;
  fill: $ink;
  font-weight: $font-weight-semibold;
}

.axis-score {
  font-family: $font-body;
  font-size: 12px;
  fill: $text-secondary;
}
</style>
