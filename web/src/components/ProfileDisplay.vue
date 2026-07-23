<template>
  <div class="profile-display">
    <div class="display-header">
      <h3>个人画像</h3>
      <div class="confidence-summary">
        高置信度: {{ highConfidenceCount }}/{{ totalCount }}
      </div>
    </div>

    <div class="profile-content">
      <!-- 基础信息 -->
      <section class="section">
        <h4>基本信息</h4>
        <div class="info-grid">
          <InfoItem
            label="姓名"
            :value="profile.name"
            :confidence="getConfidence('name')"
          />
          <InfoItem
            label="电话"
            :value="profile.phone"
            :confidence="getConfidence('phone')"
          />
          <InfoItem
            label="邮箱"
            :value="profile.email"
            :confidence="getConfidence('email')"
          />
          <InfoItem
            label="所在地"
            :value="profile.location"
            :confidence="getConfidence('location')"
          />
        </div>
      </section>

      <!-- 个人总结 -->
      <section v-if="profile.self_summary" class="section">
        <h4>个人总结</h4>
        <div class="summary-text">{{ profile.self_summary }}</div>
      </section>

      <!-- 教育背景 -->
      <section class="section">
        <h4>教育背景</h4>
        <div v-if="educationList.length > 0" class="list-items">
          <div
            v-for="(edu, index) in educationList"
            :key="index"
            class="list-item"
          >
            <div class="item-header">
              <span class="item-title">{{ edu.school }}</span>
              <ConfidenceBadge
                v-if="getConfidence(`schools[${index}]`)"
                :score="getConfidence(`schools[${index}]`)?.score || 0.5"
              />
            </div>
            <div class="item-details">
              {{ edu.degree }} · {{ edu.major }} · {{ edu.graduation_year }}
            </div>
          </div>
        </div>
        <div v-else class="empty-state">未提取到教育信息</div>
      </section>

      <!-- 工作经历 -->
      <section class="section">
        <h4>工作经历</h4>
        <div v-if="workList.length > 0" class="list-items">
          <div
            v-for="(work, index) in workList"
            :key="index"
            class="list-item"
          >
            <div class="item-header">
              <span class="item-title">{{ work.company }}</span>
              <ConfidenceBadge
                v-if="getConfidence(`companies[${index}]`)"
                :score="getConfidence(`companies[${index}]`)?.score || 0.5"
              />
            </div>
            <div class="item-details">
              {{ work.position }} · {{ work.duration }}
            </div>
            <div v-if="work.description" class="item-description">
              {{ work.description }}
            </div>
          </div>
        </div>
        <div v-else class="empty-state">未提取到工作信息</div>
      </section>

      <!-- 技能 -->
      <section class="section">
        <h4>技能</h4>
        <div class="skills-container">
          <div v-if="profile.technical_skills?.length" class="skill-group">
            <span class="skill-label">技术：</span>
            <span v-for="(skill, index) in profile.technical_skills" :key="index" class="skill-tag">
              {{ skill }}
            </span>
          </div>
          <div v-if="profile.soft_skills?.length" class="skill-group">
            <span class="skill-label">软技能：</span>
            <span v-for="(skill, index) in profile.soft_skills" :key="index" class="skill-tag">
              {{ skill }}
            </span>
          </div>
          <div v-if="profile.languages?.length" class="skill-group">
            <span class="skill-label">语言：</span>
            <span v-for="(lang, index) in profile.languages" :key="index" class="skill-tag">
              {{ lang }}
            </span>
          </div>
        </div>
      </section>

      <!-- 项目经验 -->
      <section v-if="projectList.length > 0" class="section">
        <h4>项目经验</h4>
        <div class="list-items">
          <div
            v-for="(project, index) in projectList"
            :key="index"
            class="list-item"
          >
            <div class="item-header">
              <span class="item-title">{{ project.name }}</span>
              <ConfidenceBadge
                v-if="getConfidence(`project_names[${index}]`)"
                :score="getConfidence(`project_names[${index}]`)?.score || 0.5"
              />
            </div>
            <div v-if="project.role" class="item-details">
              {{ project.role }}
            </div>
            <div v-if="project.description" class="item-description">
              {{ project.description }}
            </div>
          </div>
        </div>
      </section>

      <!-- 荣誉奖项 -->
      <section v-if="profile.achievements?.length" class="section">
        <h4>荣誉奖项</h4>
        <div class="achievements-list">
          <div v-for="(item, index) in profile.achievements" :key="index" class="achievement-item">
            · {{ item }}
          </div>
        </div>
      </section>
    </div>

    <div class="actions">
      <button class="edit-btn" @click="onEdit" type="button">
        编辑画像
      </button>
      <button class="save-btn" @click="onSave" type="button">
        保存画像
      </button>
      <button class="clear-btn" @click="onClear" type="button">
        清空画像
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import InfoItem from './InfoItem.vue'
import ConfidenceBadge from './ConfidenceBadge.vue'

const props = defineProps<{
  profile: any
  confidence: any
}>()

const emit = defineEmits<{
  (e: 'edit', profile: any): void
  (e: 'save'): void
  (e: 'clear'): void
}>()

const educationList = computed(() => {
  if (!props.profile?.schools) return []
  const count = Math.min(props.profile.schools.length, props.profile.degrees?.length || 0)
  const list = []
  for (let i = 0; i < count; i++) {
    list.push({
      school: props.profile.schools[i],
      degree: props.profile.degrees?.[i],
      major: props.profile.majors?.[i],
      graduation_year: props.profile.graduation_years?.[i]
    })
  }
  return list
})

const workList = computed(() => {
  if (!props.profile?.companies) return []
  const count = Math.min(props.profile.companies.length, props.profile.positions?.length || 0)
  const list = []
  for (let i = 0; i < count; i++) {
    const company = props.profile.companies[i]
    // 跳过 LLM 误填的空项（字符串 "null"/"None"）
    if (!company || company === 'null' || company === 'None') continue
    list.push({
      company,
      position: props.profile.positions?.[i],
      duration: props.profile.durations?.[i],
      description: props.profile.work_descriptions?.[i]
    })
  }
  return list
})

// 项目列表（扁平数组按同序拼成对象）
// 注意：LLM 偶尔会把缺失项填成字符串 "null"/"None" 并多塞一个空项目，这里过滤掉
const projectList = computed(() => {
  if (!props.profile?.project_names) return []
  const list = []
  for (let i = 0; i < props.profile.project_names.length; i++) {
    const name = props.profile.project_names[i]
    if (!name || name === 'null' || name === 'None') continue
    list.push({
      name,
      role: props.profile.project_roles?.[i],
      description: props.profile.project_descriptions?.[i]
    })
  }
  return list
})

const getConfidence = (field: string) => {
  return props.confidence?.[field]
}

const highConfidenceCount = computed(() => {
  if (!props.confidence) return 0
  return Object.values(props.confidence).filter((c: any) => c.score >= 0.8).length
})

const totalCount = computed(() => {
  return props.confidence ? Object.keys(props.confidence).length : 0
})

const onEdit = () => {
  emit('edit', props.profile)
}

const onSave = () => {
  emit('save')
}

const onClear = () => {
  emit('clear')
}
</script>

<style scoped lang="scss">
.profile-display {
  margin: 2rem 0;
  padding: 2rem;
  background: white;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
}

.display-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.display-header h3 {
  margin: 0;
  color: $ink;
}

.confidence-summary {
  padding: 0.5rem 1rem;
  background: $success-light;
  color: $success;
  border-radius: $radius-full;
  font-size: 0.9rem;
  font-weight: 600;
}

.section {
  margin-bottom: 2rem;
}

.section h4 {
  margin: 0 0 1rem 0;
  color: $ink;
  font-size: 1.1rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.list-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.list-item {
  padding: 1rem;
  background: $bg-gray;
  border-radius: $radius-md;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.item-title {
  font-weight: 600;
  color: $ink;
}

.item-details {
  color: $text-secondary;
  font-size: 0.9rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: $text-disabled;
  font-style: italic;
}

/* 经历/项目的详情描述（多行，保留原文换行） */
.item-description {
  margin-top: 0.5rem;
  color: $ink-soft;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-line;
  word-break: break-word;
}

/* 个人总结 */
.summary-text {
  padding: 1rem;
  background: $bg-gray;
  border-radius: $radius-md;
  color: $ink-soft;
  font-size: 0.95rem;
  line-height: 1.7;
  white-space: pre-line;
}

/* 荣誉奖项 */
.achievements-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.achievement-item {
  padding: 0.5rem 0.75rem;
  background: $warning-light;
  color: $warning;
  border-radius: $radius-sm;
  font-size: 0.9rem;
}

.skills-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.skill-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.skill-label {
  font-weight: 600;
  color: $ink;
  margin-right: 0.5rem;
}

.skill-tag {
  padding: 0.4rem 0.8rem;
  background: $primary-lighter;
  color: $primary-color;
  border-radius: $radius-full;
  font-size: 0.9rem;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.actions button {
  flex: 1;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all $transition-slow ease;
}

.edit-btn {
  background: $primary-color;
  color: white;
}

.edit-btn:hover {
  background: $primary-dark;
}

.save-btn {
  background: $success;
  color: white;
}

.save-btn:hover {
  background: $success;
  opacity: 0.9;
}

.clear-btn {
  background: rgba($error, 0.1);
  color: $error;
}

.clear-btn:hover {
  background: $error;
  color: white;
}
</style>
