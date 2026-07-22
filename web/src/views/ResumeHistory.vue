<template>
  <div class="page">
    <header class="page-head">
      <p class="eyebrow">HISTORY</p>
      <h1>简历历史</h1>
      <p class="sub">按岗位分组，支持精修与回看。草稿可继续精修，定稿可导出 PDF。</p>
    </header>

    <section class="card">
      <div class="head-row">
        <h3 class="card-title">我的简历</h3>
        <button class="btn-text" type="button" :disabled="loading" @click="load">刷新</button>
      </div>

      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="positions.length === 0" class="empty">
        暂无简历，去 <router-link to="/resume-optimizer">生成一份</router-link>
      </div>

      <div v-for="pos in positions" :key="pos.name" class="pos-group">
        <h4 class="pos-title">
          {{ pos.name }}<span class="cnt tnum">（{{ pos.versions.length }} 份）</span>
        </h4>
        <div v-for="v in pos.versions" :key="v.id" class="ver-item">
          <span class="ver-tag" :class="v.status">{{ statusLabel(v.status) }} v{{ v.version }}</span>
          <span class="ver-score tnum" :class="{ na: v.eval_score == null }">{{ v.eval_score ?? '—' }}</span>
          <span class="ver-time tnum">{{ formatTime(v.created_at) }}</span>
          <button class="btn-text" type="button" @click="goRefine(v.id)">精修</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { listResumes } from '@/api/resume'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
// 后端返回 {items: {岗位: [版本...]}}
const grouped = ref<Record<string, any[]>>({})

// 转成数组便于模板遍历
const positions = computed(() =>
  Object.entries(grouped.value).map(([name, versions]) => ({ name, versions }))
)

async function load() {
  if (!userStore.userId) return
  loading.value = true
  try {
    const res = await listResumes(userStore.userId)
    if (res.status === 'success' && res.data) {
      grouped.value = res.data.items || {}
    }
  } catch (e: any) {
    ElMessage.error('加载历史失败')
  } finally {
    loading.value = false
  }
}

function goRefine(id: string) {
  router.push(`/resume-refine/${id}`)
}

function statusLabel(s?: string) {
  return ({ draft: '草稿', finalized: '定稿', refining: '精修中' } as Record<string, string>)[s || ''] || s || ''
}

function formatTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

onMounted(() => {
  load()
})
</script>

<style scoped lang="scss">
.page {
  max-width: 820px;
  margin: 0 auto;
  padding: $spacing-3xl $spacing-xl;
}

.page-head {
  margin-bottom: $spacing-2xl;

  .eyebrow {
    font-family: $font-mono;
    font-size: $font-size-xs;
    letter-spacing: 0.15em;
    color: $accent-color;
    margin-bottom: $spacing-sm;
  }

  h1 {
    font-size: $font-size-3xl;
    margin-bottom: $spacing-sm;
  }

  .sub {
    color: $text-secondary;
    max-width: 60ch;
  }
}

.card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xl;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;

  .card-title {
    margin-bottom: 0;
  }
}

.card-title {
  font-size: $font-size-lg;
}

.empty {
  color: $text-disabled;
  padding: $spacing-md;
  font-size: $font-size-sm;

  a {
    color: $primary-color;
  }
}

.pos-group {
  border-top: 1px solid $border-light;
  padding-top: $spacing-md;
  margin-top: $spacing-md;

  &:first-of-type {
    border-top: none;
    padding-top: 0;
    margin-top: 0;
  }
}

.pos-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  margin-bottom: $spacing-sm;

  .cnt {
    font-weight: $font-weight-normal;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.ver-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-xs 0;
  font-size: $font-size-sm;
}

.ver-tag {
  font-family: $font-mono;
  font-size: $font-size-xs;
  padding: 2px 8px;
  border-radius: $radius-sm;

  &.draft {
    background: $bg-gray;
    color: $text-secondary;
  }
  &.finalized {
    background: rgba($success, 0.12);
    color: $success;
  }
  &.refining {
    background: rgba($primary-color, 0.12);
    color: $primary-color;
  }
}

.ver-score {
  font-weight: $font-weight-semibold;
  min-width: 28px;

  &.na {
    color: $text-disabled;
    font-weight: $font-weight-normal;
  }
}

.ver-time {
  flex: 1;
  color: $text-disabled;
  font-size: $font-size-xs;
}

.btn-text {
  background: none;
  border: none;
  color: $primary-color;
  cursor: pointer;
  font-size: $font-size-sm;
  padding: $spacing-xs $spacing-sm;

  &:hover {
    color: $primary-dark;
  }

  &:disabled {
    color: $text-disabled;
    cursor: not-allowed;
  }
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }
}
</style>
