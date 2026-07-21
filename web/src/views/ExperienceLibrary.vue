<template>
  <div class="page">
    <header class="page-head">
      <p class="eyebrow">LIBRARY</p>
      <h1>面经库</h1>
      <p class="sub">个人面经（你的私有沉淀）+ 公司面经（全局真题）。越练越懂你，竞品抄不走。<router-link to="/interview/history" class="btn-text">面试历史 →</router-link></p>
    </header>

    <!-- Tab 切换 -->
    <div class="tabs">
      <button :class="['tab', { active: tab === 'personal' }]" type="button" @click="switchTab('personal')">个人面经库</button>
      <button :class="['tab', { active: tab === 'company' }]" type="button" @click="switchTab('company')">公司面经库</button>
    </div>

    <!-- 个人库 -->
    <template v-if="tab === 'personal'">
      <section class="card">
        <div class="toolbar">
          <input v-model="pQuery" class="search-input" placeholder="语义搜索你的历史面经（如：团队推动、数据结果）" @keyup.enter="loadPersonal" />
          <select v-model="pCategory" class="filter-select" @change="loadPersonal">
            <option value="">全部题型</option>
            <option v-for="c in CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</option>
          </select>
          <button class="btn-primary" type="button" :disabled="pLoading" @click="loadPersonal">搜索</button>
          <button v-if="personal.length" class="btn-text danger" type="button" @click="confirmClear">清空全部</button>
        </div>
      </section>

      <div v-if="pLoading" class="card state-center"><span class="spinner" /></div>

      <section v-else-if="personal.length" class="card">
        <div v-for="ep in personal" :key="ep.id" class="ep-item">
          <div class="ep-head">
            <span class="ep-cat">{{ categoryLabel(ep.category) }}</span>
            <span v-if="ep.position" class="ep-pos">{{ ep.position }}</span>
            <span class="ep-score tnum" :style="{ color: colorFor(ep.score) }">{{ ep.score ?? '-' }}</span>
            <span class="ep-time tnum">{{ formatTime(ep.happened_at) }}</span>
            <button class="btn-text danger" type="button" @click="confirmDelete(ep)">删除</button>
          </div>
          <p class="ep-q">{{ ep.question }}</p>
          <details v-if="ep.my_answer || ep.better_version" class="ep-detail">
            <summary>查看回答与改进范例</summary>
            <p v-if="ep.my_answer" class="ep-ans"><b>你的回答：</b>{{ ep.my_answer }}</p>
            <p v-if="ep.better_version" class="ep-better"><b>改进版：</b>{{ ep.better_version }}</p>
          </details>
        </div>
      </section>

      <div v-else class="card empty">
        <p>还没有个人面经。</p>
        <p class="empty-sub">完成一场模拟面试后，系统会自动把每道题沉淀到这里，供你回看与复练。</p>
        <router-link to="/interview/setup" class="btn-primary">去开启一场面试</router-link>
      </div>
    </template>

    <!-- 公司库 -->
    <template v-else>
      <section class="card">
        <div class="toolbar">
          <input v-model="cQuery" class="search-input" placeholder="搜索公司面经（如：产品 DAU 下滑）" @keyup.enter="loadCompany" />
          <button class="btn-primary" type="button" :disabled="cLoading" @click="loadCompany">搜索</button>
          <button class="btn-text" type="button" @click="showContribute = true">＋ 贡献面经</button>
        </div>

        <div class="company-layout">
          <!-- 岗位 facets -->
          <aside class="facets">
            <p class="facet-title">按岗位筛选</p>
            <button
              type="button"
              :class="['facet-item', { active: !cPosition }]"
              @click="setPosition('')"
            >全部</button>
            <button
              v-for="p in facets.positions"
              :key="p"
              type="button"
              :class="['facet-item', { active: cPosition === p }]"
              @click="setPosition(p)"
            >{{ p }}</button>
          </aside>

          <!-- 真题列表 -->
          <div class="company-list">
            <div v-if="cLoading" class="state-center"><span class="spinner" /></div>
            <div v-else-if="company.length === 0" class="empty-inline">暂无面经</div>
            <div v-for="cq in company" :key="cq.id" class="cq-item">
              <div class="cq-head">
                <span :class="['src-tag', sourceClass(cq.source)]">{{ SOURCE_LABELS[cq.source] || cq.source }}</span>
                <span v-if="cq.position" class="cq-pos">{{ cq.position }}</span>
              </div>
              <p class="cq-q">{{ cq.question }}</p>
              <p v-if="cq.context" class="cq-ctx">考查：{{ cq.context }}</p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- 贡献面经 modal（自写，保持手写风格） -->
    <div v-if="showContribute" class="modal-mask" @click.self="showContribute = false">
      <div class="modal">
        <h3 class="modal-title">贡献面经</h3>
        <p class="modal-sub">分享你遇到的真实面试题。脱敏后进入公司库，供大家参考（不暴露你的身份）。</p>
        <div class="modal-form">
          <input v-model="ugc.position" class="modal-input" placeholder="岗位（如 产品经理）" />
          <input v-model="ugc.company" class="modal-input" placeholder="公司（可选）" />
          <select v-model="ugc.category" class="modal-input">
            <option value="">选择题型（可选）</option>
            <option v-for="c in CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</option>
          </select>
          <textarea v-model="ugc.question" class="modal-input" rows="3" placeholder="面经问题（你被问过的真题）"></textarea>
          <input v-model="ugc.context" class="modal-input" placeholder="考察点（可选）" />
        </div>
        <div class="modal-actions">
          <button class="btn-text" type="button" @click="showContribute = false">取消</button>
          <button class="btn-primary" type="button" :disabled="ugcLoading || ugc.question.trim().length < 5" @click="submitUgc">
            {{ ugcLoading ? '提交中…' : '提交贡献' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import {
  listPersonal, deletePersonalOne, deletePersonalAll,
  searchCompany, companyFacets, contributeUgc,
} from '@/api/knowledge'
import { SOURCE_LABELS, sourceClass } from '@/types/knowledge'
import type { PersonalEpisode, CompanyQuestion, CompanyFacets } from '@/types/knowledge'

const userStore = useUserStore()

const CATEGORIES = [
  { key: 'behavioral', label: '行为面' },
  { key: 'technical', label: '技术/专业面' },
  { key: 'case', label: '案例面' },
  { key: 'motivation', label: '动机面' },
]
function categoryLabel(c?: string | null) {
  return (c && CATEGORIES.find((x) => x.key === c)?.label) || '未分类'
}
function colorFor(s?: number | null) {
  if (s == null) return '#94a3b8'
  if (s >= 75) return '#10b981'
  if (s >= 50) return '#d97706'
  return '#ef4444'
}
function formatTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 10)
}

// Tab
const tab = ref<'personal' | 'company'>('personal')
function switchTab(t: 'personal' | 'company') {
  tab.value = t
  if (t === 'company' && company.value.length === 0) loadCompany()
}

// 个人库
const personal = ref<PersonalEpisode[]>([])
const pQuery = ref('')
const pCategory = ref('')
const pLoading = ref(false)

async function loadPersonal() {
  if (!userStore.userId) return
  pLoading.value = true
  try {
    const res: any = await listPersonal({
      user_id: userStore.userId,
      q: pQuery.value,
      category: pCategory.value || undefined,
      limit: 30,
    })
    if (res.status === 'success' && res.data) {
      personal.value = res.data.items || []
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    pLoading.value = false
  }
}

async function confirmDelete(ep: PersonalEpisode) {
  try {
    await ElMessageBox.confirm(`确定删除这道面经？`, '删除确认', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    const res: any = await deletePersonalOne(ep.id, userStore.userId)
    if (res.status === 'success') {
      ElMessage.success('已删除')
      personal.value = personal.value.filter((x) => x.id !== ep.id)
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    // 取消
  }
}

async function confirmClear() {
  try {
    await ElMessageBox.confirm('确定清空全部个人面经？此操作不可恢复。', '清空确认', {
      confirmButtonText: '清空全部', cancelButtonText: '取消', type: 'error',
    })
    const res: any = await deletePersonalAll(userStore.userId)
    if (res.status === 'success') {
      ElMessage.success(res.message)
      personal.value = []
    }
  } catch (e) {
    // 取消
  }
}

// 公司库
const company = ref<CompanyQuestion[]>([])
const facets = ref<CompanyFacets>({ companies: [], positions: [] })
const cQuery = ref('')
const cPosition = ref('')
const cLoading = ref(false)

async function loadFacets() {
  try {
    const res: any = await companyFacets()
    if (res.status === 'success' && res.data) {
      facets.value = res.data
    }
  } catch {
    // 静默
  }
}

async function loadCompany() {
  cLoading.value = true
  try {
    const res: any = await searchCompany({
      q: cQuery.value,
      position: cPosition.value || undefined,
      top_k: 30,
    })
    if (res.status === 'success' && res.data) {
      company.value = res.data.items || []
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    cLoading.value = false
  }
}

function setPosition(p: string) {
  cPosition.value = p
  loadCompany()
}

// UGC 贡献
const showContribute = ref(false)
const ugcLoading = ref(false)
const ugc = reactive({ position: '', company: '', category: '', question: '', context: '' })

async function submitUgc() {
  if (ugc.question.trim().length < 5) {
    ElMessage.warning('请补充完整的面经问题')
    return
  }
  ugcLoading.value = true
  try {
    const res: any = await contributeUgc({
      user_id: userStore.userId,
      position: ugc.position || undefined,
      company: ugc.company || undefined,
      category: ugc.category || undefined,
      question: ugc.question,
      context: ugc.context || undefined,
    })
    if (res.status === 'success') {
      ElMessage.success('感谢贡献！面经已收录')
      showContribute.value = false
      ugc.question = ''
      ugc.context = ''
      loadFacets()
      loadCompany()
    } else {
      ElMessage.error(res.message || '贡献失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '贡献失败')
  } finally {
    ugcLoading.value = false
  }
}

onMounted(() => {
  loadPersonal()
  loadFacets()
  loadCompany()
})
</script>

<style scoped lang="scss">
.page {
  max-width: 920px;
  margin: 0 auto;
  padding: $spacing-3xl $spacing-xl;
}

.page-head {
  margin-bottom: $spacing-xl;

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

/* Tab */
.tabs {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-lg;
  border-bottom: 1px solid $border-color;
}

.tab {
  background: none;
  border: none;
  padding: $spacing-sm $spacing-lg;
  cursor: pointer;
  font-size: $font-size-sm;
  color: $text-secondary;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;

  &:hover {
    color: $ink;
  }

  &.active {
    color: $primary-color;
    border-bottom-color: $primary-color;
    font-weight: $font-weight-semibold;
  }
}

.card {
  background: $bg-white;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xl;
  margin-bottom: $spacing-lg;
}

/* 工具栏 */
.toolbar {
  display: flex;
  gap: $spacing-sm;
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 200px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  font-family: $font-body;

  &:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
  }
}

.filter-select {
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  background: $bg-white;
  cursor: pointer;
}

/* 个人库条目 */
.ep-item {
  border-bottom: 1px solid $border-light;
  padding: $spacing-md 0;

  &:first-child {
    padding-top: 0;
  }

  &:last-child {
    border-bottom: none;
  }
}

.ep-head {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-xs;
  font-size: $font-size-xs;
}

.ep-cat {
  background: $primary-lighter;
  color: $primary-color;
  padding: 2px $spacing-sm;
  border-radius: $radius-full;
  font-weight: $font-weight-medium;
}

.ep-pos {
  color: $text-secondary;
}

.ep-score {
  font-weight: $font-weight-bold;
  margin-left: auto;
}

.ep-time {
  color: $text-disabled;
}

.ep-q {
  font-size: $font-size-sm;
  color: $text-primary;
  line-height: $line-height-relaxed;
}

.ep-detail {
  margin-top: $spacing-sm;
  font-size: $font-size-sm;

  summary {
    cursor: pointer;
    color: $primary-color;
    font-size: $font-size-xs;
  }

  p {
    margin-top: $spacing-xs;
    color: $text-secondary;
    line-height: $line-height-relaxed;
  }

  .ep-better {
    color: $text-primary;
    background: $success-light;
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
  }
}

/* 公司库布局 */
.company-layout {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: $spacing-lg;
  margin-top: $spacing-md;
}

.facets {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.facet-title {
  font-size: $font-size-xs;
  color: $text-secondary;
  font-weight: $font-weight-semibold;
  margin-bottom: $spacing-xs;
}

.facet-item {
  background: none;
  border: 1px solid transparent;
  border-radius: $radius-md;
  padding: $spacing-xs $spacing-md;
  cursor: pointer;
  font-size: $font-size-sm;
  color: $text-secondary;
  text-align: left;

  &:hover {
    background: $bg-gray;
  }

  &.active {
    background: $primary-lighter;
    color: $primary-color;
    font-weight: $font-weight-medium;
  }
}

.cq-item {
  border-bottom: 1px solid $border-light;
  padding: $spacing-md 0;

  &:first-child {
    padding-top: 0;
  }

  &:last-child {
    border-bottom: none;
  }
}

.cq-head {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-xs;
}

.src-tag {
  font-size: $font-size-xs;
  padding: 2px $spacing-sm;
  border-radius: $radius-full;
  font-weight: $font-weight-medium;

  &.src-curated {
    background: $success-light;
    color: $success;
  }

  &.src-ugc {
    background: $primary-lighter;
    color: $primary-color;
  }

  &.src-llm {
    background: $bg-gray;
    color: $text-secondary;
  }
}

.cq-pos {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.cq-q {
  font-size: $font-size-sm;
  color: $text-primary;
  line-height: $line-height-relaxed;
}

.cq-ctx {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: $spacing-xs;
}

/* 空态 */
.empty {
  text-align: center;
  padding: $spacing-2xl;
  color: $text-secondary;

  .empty-sub {
    font-size: $font-size-xs;
    margin: $spacing-sm 0 $spacing-md;
  }

  .btn-primary {
    text-decoration: none;
    display: inline-block;
  }
}

.empty-inline {
  color: $text-disabled;
  font-size: $font-size-sm;
  padding: $spacing-lg;
  text-align: center;
}

.state-center {
  display: flex;
  justify-content: center;
}

/* 按钮 */
.btn-primary {
  background: $primary-color;
  color: #fff;
  border: none;
  padding: $spacing-sm $spacing-lg;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;

  &:hover:not(:disabled) {
    background: $primary-dark;
  }

  &:disabled {
    background: $bg-gray;
    color: $text-disabled;
    cursor: not-allowed;
  }
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

  &.danger {
    color: $error;

    &:hover {
      color: darken($error, 10%);
    }
  }
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid $border-color;
  border-top-color: $primary-color;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 贡献 modal */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: $spacing-lg;
}

.modal {
  background: $bg-white;
  border-radius: $radius-lg;
  padding: $spacing-xl;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-title {
  font-size: $font-size-lg;
  margin-bottom: $spacing-xs;
}

.modal-sub {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-bottom: $spacing-md;
  line-height: $line-height-relaxed;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
}

.modal-input {
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  font-family: $font-body;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: $primary-color;
  }
}

textarea.modal-input {
  resize: vertical;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-sm;
}

@media (max-width: $container-md) {
  .page {
    padding: $spacing-2xl $spacing-lg;
  }

  .company-layout {
    grid-template-columns: 1fr;
  }

  .facets {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
