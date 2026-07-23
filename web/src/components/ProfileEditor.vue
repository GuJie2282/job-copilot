<template>
  <div class="profile-editor">
    <div class="editor-header">
      <h3>编辑画像</h3>
      <p class="hint">您可以修正或补充画像信息</p>
    </div>

    <div class="editor-content">
      <!-- 基本信息 -->
      <section class="section">
        <h4>基本信息</h4>
        <div class="form-grid">
          <FormField
            label="姓名"
            v-model="editedProfile.name"
            :confidence="getConfidence('name')"
          />
          <FormField
            label="电话"
            v-model="editedProfile.phone"
            :confidence="getConfidence('phone')"
          />
          <FormField
            label="邮箱"
            v-model="editedProfile.email"
            :confidence="getConfidence('email')"
          />
          <FormField
            label="所在地"
            v-model="editedProfile.location"
            :confidence="getConfidence('location')"
          />
        </div>
      </section>

      <!-- 教育背景 -->
      <section class="section">
        <h4>教育背景</h4>
        <div
          v-for="(_, index) in educationList"
          :key="index"
          class="education-item"
        >
          <div class="item-header">
            <span class="item-number">教育经历 {{ index + 1 }}</span>
            <button
              v-if="educationList.length > 1"
              @click="removeEducation(index)"
              class="remove-btn"
              type="button"
            >
              删除
            </button>
          </div>
          <div class="form-grid">
            <FormField
              label="学校"
              v-model="editedProfile.schools[index]"
              :confidence="getConfidence(`schools[${index}]`)"
            />
            <FormField
              label="学历"
              v-model="editedProfile.degrees[index]"
              :confidence="getConfidence(`degrees[${index}]`)"
            />
            <FormField
              label="专业"
              v-model="editedProfile.majors[index]"
            />
            <FormField
              label="毕业年份"
              v-model="editedProfile.graduation_years[index]"
            />
          </div>
        </div>
        <button @click="addEducation" class="add-btn" type="button">
          + 添加教育经历
        </button>
      </section>

      <!-- 工作经历 -->
      <section class="section">
        <h4>工作经历</h4>
        <div
          v-for="(_, index) in workList"
          :key="index"
          class="work-item"
        >
          <div class="item-header">
            <span class="item-number">工作经历 {{ index + 1 }}</span>
            <button
              v-if="workList.length > 1"
              @click="removeWork(index)"
              class="remove-btn"
              type="button"
            >
              删除
            </button>
          </div>
          <div class="form-grid">
            <FormField
              label="公司"
              v-model="editedProfile.companies[index]"
              :confidence="getConfidence(`companies[${index}]`)"
            />
            <FormField
              label="职位"
              v-model="editedProfile.positions[index]"
            />
            <FormField
              label="时间"
              v-model="editedProfile.durations[index]"
            />
          </div>
          <div class="work-description-field">
            <label>职责与成果详情（保留原文细节）</label>
            <textarea
              v-model="editedProfile.work_descriptions[index]"
              placeholder="例如：负责 XX 模块的需求分析与原型设计，推动评审通过率 95%…"
              rows="3"
            ></textarea>
          </div>
        </div>
        <button @click="addWork" class="add-btn" type="button">
          + 添加工作经历
        </button>
      </section>

      <!-- 个人总结 -->
      <section class="section">
        <h4>个人总结</h4>
        <div class="skill-group">
          <textarea
            v-model="editedProfile.self_summary"
            placeholder="例如：3 年互联网产品经验，擅长从 0 到 1 搭建产品…"
            rows="3"
          ></textarea>
        </div>
      </section>

      <!-- 项目经验 -->
      <section class="section">
        <h4>项目经验</h4>
        <div
          v-for="(_, index) in projectList"
          :key="index"
          class="work-item"
        >
          <div class="item-header">
            <span class="item-number">项目经历 {{ index + 1 }}</span>
            <button
              v-if="projectList.length > 1"
              @click="removeProject(index)"
              class="remove-btn"
              type="button"
            >
              删除
            </button>
          </div>
          <div class="form-grid">
            <FormField
              label="项目名称"
              v-model="editedProfile.project_names[index]"
            />
            <FormField
              label="担任角色"
              v-model="editedProfile.project_roles[index]"
            />
          </div>
          <div class="work-description-field">
            <label>项目详情（保留原文细节）</label>
            <textarea
              v-model="editedProfile.project_descriptions[index]"
              placeholder="例如：项目背景、你的职责、核心成果数据…"
              rows="3"
            ></textarea>
          </div>
        </div>
        <button @click="addProject" class="add-btn" type="button">
          + 添加项目经历
        </button>
      </section>

      <!-- 技能 -->
      <section class="section">
        <h4>技能</h4>
        <div class="skills-section">
          <div class="skill-group">
            <label>技术技能（用逗号分隔）</label>
            <textarea
              v-model="technicalSkillsText"
              placeholder="例如：Python, Java, React"
              rows="2"
            ></textarea>
          </div>
          <div class="skill-group">
            <label>软技能（用逗号分隔）</label>
            <textarea
              v-model="softSkillsText"
              placeholder="例如：团队协作, 沟通能力"
              rows="2"
            ></textarea>
          </div>
          <div class="skill-group">
            <label>语言能力（用逗号分隔）</label>
            <textarea
              v-model="languagesText"
              placeholder="例如：英语, 日语"
              rows="2"
            ></textarea>
          </div>
        </div>
      </section>
    </div>

    <div class="actions">
      <button class="save-btn" @click="onSave" type="button">
        保存修改
      </button>
      <button class="cancel-btn" @click="onCancel" type="button">
        取消
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import FormField from './FormField.vue'

const props = defineProps<{
  profile: any
  confidence: any
}>()

const emit = defineEmits<{
  (e: 'save', profile: any): void
  (e: 'cancel'): void
}>()

// 深拷贝 profile（避免编辑时直接 mutate 父组件的 schools/companies 等数组）
const editedProfile = ref<any>(
  props.profile ? JSON.parse(JSON.stringify(props.profile)) : {}
)

// 规整详情数组：确保 work_descriptions 与 companies 等长，
// 避免 v-model 绑定 work_descriptions[index] 时下标越界（后端可能没返回该字段或长度不一致）
;(() => {
  const p = editedProfile.value
  // 规整工作详情数组：与 companies 等长，避免 v-model 绑 work_descriptions[index] 越界
  if (Array.isArray(p.companies)) {
    if (!Array.isArray(p.work_descriptions)) p.work_descriptions = []
    while (p.work_descriptions.length < p.companies.length) p.work_descriptions.push('')
    p.work_descriptions.length = p.companies.length
  }
  // 规整项目数组：project_roles / project_descriptions 与 project_names 等长
  if (Array.isArray(p.project_names)) {
    if (!Array.isArray(p.project_roles)) p.project_roles = []
    if (!Array.isArray(p.project_descriptions)) p.project_descriptions = []
    while (p.project_roles.length < p.project_names.length) p.project_roles.push('')
    while (p.project_descriptions.length < p.project_names.length) p.project_descriptions.push('')
    p.project_roles.length = p.project_names.length
    p.project_descriptions.length = p.project_names.length
  }
  // 个人总结兜底为字符串（避免 textarea v-model 绑 undefined 报错）
  if (p.self_summary == null) p.self_summary = ''
})()

// 技能列表转换
const technicalSkillsText = computed({
  get: () => editedProfile.value.technical_skills?.join(', ') || '',
  set: (value: string) => {
    editedProfile.value.technical_skills = value
      .split(',')
      .map(s => s.trim())
      .filter(s => s)
  }
})

const softSkillsText = computed({
  get: () => editedProfile.value.soft_skills?.join(', ') || '',
  set: (value: string) => {
    editedProfile.value.soft_skills = value
      .split(',')
      .map(s => s.trim())
      .filter(s => s)
  }
})

const languagesText = computed({
  get: () => editedProfile.value.languages?.join(', ') || '',
  set: (value: string) => {
    editedProfile.value.languages = value
      .split(',')
      .map(s => s.trim())
      .filter(s => s)
  }
})

// 教育列表
const educationList = computed(() => {
  const count = Math.max(
    editedProfile.value.schools?.length || 0,
    editedProfile.value.degrees?.length || 0
  )
  return Array.from({ length: count }, (_, i) => ({
    school: editedProfile.value.schools?.[i] || '',
    degree: editedProfile.value.degrees?.[i] || '',
    major: editedProfile.value.majors?.[i] || '',
    graduation_year: editedProfile.value.graduation_years?.[i] || ''
  }))
})

// 工作列表
const workList = computed(() => {
  const count = Math.max(
    editedProfile.value.companies?.length || 0,
    editedProfile.value.positions?.length || 0
  )
  return Array.from({ length: count }, (_, i) => ({
    company: editedProfile.value.companies?.[i] || '',
    position: editedProfile.value.positions?.[i] || '',
    duration: editedProfile.value.durations?.[i] || ''
  }))
})

// 项目列表（只需迭代次数，v-model 直接绑 editedProfile 的并行数组）
const projectList = computed(() => {
  const count = editedProfile.value.project_names?.length || 0
  return Array.from({ length: count }, (_, i) => i)
})

const getConfidence = (field: string) => {
  return props.confidence?.[field]
}

const addEducation = () => {
  if (!editedProfile.value.schools) {
    editedProfile.value.schools = []
    editedProfile.value.degrees = []
    editedProfile.value.majors = []
    editedProfile.value.graduation_years = []
  }
  editedProfile.value.schools.push('')
  editedProfile.value.degrees.push('')
  editedProfile.value.majors.push('')
  editedProfile.value.graduation_years.push('')
}

const removeEducation = (index: number) => {
  editedProfile.value.schools?.splice(index, 1)
  editedProfile.value.degrees?.splice(index, 1)
  editedProfile.value.majors?.splice(index, 1)
  editedProfile.value.graduation_years?.splice(index, 1)
}

const addWork = () => {
  if (!editedProfile.value.companies) {
    editedProfile.value.companies = []
    editedProfile.value.positions = []
    editedProfile.value.durations = []
    editedProfile.value.work_descriptions = []
  }
  editedProfile.value.companies.push('')
  editedProfile.value.positions.push('')
  editedProfile.value.durations.push('')
  editedProfile.value.work_descriptions.push('')
}

const removeWork = (index: number) => {
  editedProfile.value.companies?.splice(index, 1)
  editedProfile.value.positions?.splice(index, 1)
  editedProfile.value.durations?.splice(index, 1)
  editedProfile.value.work_descriptions?.splice(index, 1)
}

const addProject = () => {
  if (!editedProfile.value.project_names) {
    editedProfile.value.project_names = []
    editedProfile.value.project_roles = []
    editedProfile.value.project_descriptions = []
  }
  editedProfile.value.project_names.push('')
  editedProfile.value.project_roles.push('')
  editedProfile.value.project_descriptions.push('')
}

const removeProject = (index: number) => {
  editedProfile.value.project_names?.splice(index, 1)
  editedProfile.value.project_roles?.splice(index, 1)
  editedProfile.value.project_descriptions?.splice(index, 1)
}

const onSave = () => {
  emit('save', editedProfile.value)
}

const onCancel = () => {
  emit('cancel')
}
</script>

<style scoped lang="scss">
.profile-editor {
  margin: 2rem 0;
  padding: 2rem;
  background: white;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
}

.editor-header {
  text-align: center;
  margin-bottom: 2rem;
}

.editor-header h3 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.hint {
  color: $text-secondary;
  font-size: 0.9rem;
}

.section {
  margin-bottom: 2rem;
}

.section h4 {
  margin: 0 0 1rem 0;
  color: $ink;
  font-size: 1.1rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.education-item,
.work-item {
  padding: 1.5rem;
  background: $bg-gray;
  border-radius: $radius-md;
  margin-bottom: 1rem;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.item-number {
  font-weight: 600;
  color: $ink;
}

.remove-btn {
  padding: 0.4rem 0.8rem;
  background: $error;
  color: white;
  border: none;
  border-radius: $radius-sm;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background $transition-slow ease;
}

.remove-btn:hover {
  background: $error;
  opacity: 0.9;
}

.add-btn {
  width: 100%;
  padding: 0.75rem;
  background: $primary-color;
  color: white;
  border: none;
  border-radius: $radius-md;
  font-size: 1rem;
  cursor: pointer;
  transition: background $transition-slow ease;
}

.add-btn:hover {
  background: $primary-dark;
}

/* 工作经历详情输入框（占满整行，区别于上面的三列网格） */
.work-description-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.work-description-field label {
  font-weight: 600;
  color: $ink;
  font-size: 0.9rem;
}

.work-description-field textarea {
  padding: 0.75rem;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.5;
  resize: vertical;
}

.work-description-field textarea:focus {
  outline: none;
  border-color: $primary-color;
}

.skills-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.skill-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skill-group label {
  font-weight: 600;
  color: $ink;
  font-size: 0.9rem;
}

.skill-group textarea {
  padding: 0.75rem;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  font-family: inherit;
  font-size: 0.9rem;
  resize: vertical;
}

.skill-group textarea:focus {
  outline: none;
  border-color: $primary-color;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.actions button {
  flex: 1;
  padding: 1rem;
  border: none;
  border-radius: $radius-md;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all $transition-slow ease;
}

.save-btn {
  background: $success;
  color: white;
}

.save-btn:hover {
  background: $success;
  opacity: 0.9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($success, 0.3);
}

.cancel-btn {
  background: $text-disabled;
  color: white;
}

.cancel-btn:hover {
  background: $text-secondary;
}
</style>
