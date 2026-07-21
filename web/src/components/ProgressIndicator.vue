<template>
  <div class="progress-indicator">
    <div class="progress-header">
      <h4>{{ currentStep.title }}</h4>
      <p class="progress-percent">{{ Math.round(progress) }}%</p>
    </div>

    <div class="progress-bar-container">
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: progress + '%' }"
        ></div>
      </div>
    </div>

    <div class="steps-list">
      <div
        v-for="(step, index) in steps"
        :key="index"
        class="step-item"
        :class="getStepClass(index)"
      >
        <div class="step-icon">
          <span v-if="getStepStatus(index) === 'completed'">{{ index + 1 }}</span>
          <span v-else-if="getStepStatus(index) === 'active'">{{ index + 1 }}</span>
          <span v-else>{{ index + 1 }}</span>
        </div>
        <div class="step-content">
          <h5>{{ step.title }}</h5>
          <p>{{ step.description }}</p>
        </div>
      </div>
    </div>

    <div v-if="(estimatedTime ?? 0) > 0" class="estimated-time">
      预计剩余时间：{{ estimatedTime }} 秒
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  currentStep: {
    title: string
    description: string
  }
  progress: number
  estimatedTime?: number
}>()

const steps = [
  {
    title: '上传文件',
    description: '正在上传简历文件'
  },
  {
    title: '解析文本',
    description: '正在提取文件内容'
  },
  {
    title: '质量检测',
    description: '正在检测文本质量'
  },
  {
    title: '提取画像',
    description: 'AI 正在提取个人画像'
  },
  {
    title: '计算置信度',
    description: '正在计算字段置信度'
  },
  {
    title: '完成',
    description: '解析完成！'
  }
]

const getStepStatus = (index: number) => {
  if (props.progress >= 100 && index === steps.length - 1) return 'completed'
  if (props.progress >= (index + 1) * (100 / steps.length)) return 'completed'
  if (props.progress >= index * (100 / steps.length)) return 'active'
  return 'pending'
}

const getStepClass = (index: number) => {
  return getStepStatus(index)
}
</script>

<style scoped lang="scss">
.progress-indicator {
  margin: 2rem 0;
  padding: 2rem;
  background: white;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.progress-header h4 {
  margin: 0;
  color: $ink;
}

.progress-percent {
  font-size: 1.5rem;
  font-weight: 700;
  color: $primary-color;
}

.progress-bar-container {
  margin-bottom: 2rem;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: $bg-gray;
  border-radius: $radius-sm;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: $primary-color;
  border-radius: $radius-sm;
  transition: width 0.5s ease;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.step-item {
  display: flex;
  gap: 1rem;
  opacity: 0.6;
  transition: opacity $transition-slow ease;
}

.step-item.active {
  opacity: 1;
}

.step-item.completed {
  opacity: 1;
}

.step-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: $bg-gray;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  font-weight: 700;
  color: $text-secondary;
  flex-shrink: 0;
  transition: all $transition-slow ease;
}

.step-item.active .step-icon {
  background: $primary-color;
  color: white;
}

.step-item.completed .step-icon {
  background: $success;
  color: white;
}

.step-content {
  flex: 1;
}

.step-content h5 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  color: $ink;
}

.step-content p {
  margin: 0;
  font-size: 0.85rem;
  color: $text-secondary;
}

.estimated-time {
  margin-top: 2rem;
  padding: 1rem;
  background: $bg-gray;
  border-radius: $radius-md;
  text-align: center;
  color: $text-secondary;
  font-size: 0.9rem;
}
</style>
