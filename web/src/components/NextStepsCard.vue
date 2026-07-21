<template>
  <div class="next-steps-card">
    <div class="card-header">
      <p class="eyebrow">NEXT</p>
      <h3>解析完成，接下来你可以</h3>
    </div>

    <div class="cards">
      <button
        v-for="card in cards"
        :key="card.id"
        class="step-card"
        :class="{ recommended: card.recommended }"
        type="button"
        @click="navigate(card.route)"
      >
        <div class="card-content">
          <h4>{{ card.title }}</h4>
          <p>{{ card.description }}</p>
        </div>
        <span class="card-arrow">→</span>
        <span v-if="card.recommended" class="recommended-badge">推荐</span>
      </button>
    </div>

    <div class="manual-option">
      <span class="or">或者</span>
      <button class="manual-btn" type="button" @click="editProfile">编辑 / 完善画像</button>
    </div>
  </div>
</template>

<script setup lang="ts">
const cards = [
  {
    id: 'jd_match',
    title: 'JD 匹配',
    description: '将你的画像与职位描述比对，查看契合度',
    route: '/jd-matcher',
    recommended: true
  },
  {
    id: 'resume_optimize',
    title: '简历优化',
    description: '基于画像优化简历，提升竞争力',
    route: '/resume-optimize',
    recommended: false
  },
  {
    id: 'mock_interview',
    title: '模拟面试',
    description: 'AI 模拟真实面试场景，练习并复盘',
    route: '/interview/setup',
    recommended: false
  }
]

const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'navigate', route: string): void
}>()

// 不直接 router.push：未实现的路由（简历优化 / 模拟面试）交由父组件决定如何提示，
// 避免跳转到不存在的路由触发控制台 warning 且用户无反馈
const navigate = (route: string) => {
  emit('navigate', route)
}

const editProfile = () => {
  emit('edit')
}
</script>

<style scoped lang="scss">
// 原「紫渐变 + 毛玻璃 + 金色」风格已弃用，改为克制的白底卡片，与全站统一
.next-steps-card {
  margin-top: $spacing-xl;
  padding: $spacing-xl;
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.card-header {
  margin-bottom: $spacing-lg;

  .eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.15em;
    color: $accent-color;
    margin-bottom: $spacing-xs;
  }

  h3 {
    font-size: $font-size-xl;
  }
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

.step-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  background: $bg-light;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  cursor: pointer;
  transition: all $transition-base ease;
  text-align: left;

  &:hover {
    background: $primary-lighter;
    border-color: $primary-color;
    transform: translateY(-2px);
  }

  &.recommended {
    background: $bg-white;
    border-color: $accent-color;
  }
}

.card-content {
  flex: 1;

  h4 {
    font-size: $font-size-base;
    margin-bottom: $spacing-xs;
    color: $ink;
  }

  p {
    font-size: $font-size-xs;
    color: $text-secondary;
    line-height: $line-height-normal;
    margin: 0;
  }
}

.card-arrow {
  color: $text-disabled;
  font-size: $font-size-lg;
}

.recommended-badge {
  position: absolute;
  top: $spacing-xs;
  right: $spacing-xs;
  padding: 1px 8px;
  background: $accent-color;
  color: #fff;
  border-radius: $radius-full;
  font-size: $font-size-xs;
  font-weight: $font-weight-semibold;
}

.manual-option {
  text-align: center;
  padding-top: $spacing-md;
  border-top: 1px solid $border-light;

  .or {
    display: block;
    color: $text-disabled;
    font-size: $font-size-xs;
    margin-bottom: $spacing-sm;
  }
}

.manual-btn {
  padding: $spacing-sm $spacing-xl;
  background: transparent;
  color: $primary-color;
  border: 1px solid $primary-color;
  border-radius: $radius-md;
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all $transition-base ease;

  &:hover {
    background: $primary-color;
    color: #fff;
  }
}
</style>
