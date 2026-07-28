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

      <!-- 教育背景（嵌套对象数组：每个 edu 的字段绑在同一对象） -->
      <section class="section">
        <h4>教育背景</h4>
        <div
          v-for="(edu, index) in editedProfile.education"
          :key="index"
          class="education-item"
        >
          <div class="item-header">
            <span class="item-number">教育经历 {{ index + 1 }}</span>
            <button
              v-if="editedProfile.education.length > 1"
              @click="removeEducation(index)"
              class="remove-btn"
              type="button"
            >
              删除
            </button>
          </div>
          <div class="form-grid">
            <FormField label="学校" v-model="edu.school" :confidence="getConfidence(`education[${index}].school`)" />
            <FormField label="学历" v-model="edu.degree" :confidence="getConfidence(`education[${index}].degree`)" />
            <FormField label="专业" v-model="edu.major" />
            <FormField label="毕业年份" v-model="edu.graduation_year" />
          </div>
        </div>
        <button @click="addEducation" class="add-btn" type="button">
          + 添加教育经历
        </button>
      </section>

      <!-- 工作经历（嵌套对象数组） -->
      <section class="section">
        <h4>工作经历</h4>
        <div
          v-for="(work, index) in editedProfile.work_experience"
          :key="index"
          class="work-item"
        >
          <div class="item-header">
            <span class="item-number">工作经历 {{ index + 1 }}</span>
            <button
              v-if="editedProfile.work_experience.length > 1"
              @click="removeWork(index)"
              class="remove-btn"
              type="button"
            >
              删除
            </button>
          </div>
          <div class="form-grid">
            <FormField label="公司" v-model="work.company" :confidence="getConfidence(`work_experience[${index}].company`)" />
            <FormField label="职位" v-model="work.position" />
            <FormField label="时间" v-model="work.duration" />
          </div>
          <div class="work-description-field">
            <label>职责与成果详情（保留原文细节）</label>
            <textarea
              v-model="work.description"
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

      <!-- 项目经验（嵌套对象数组） -->
      <section class="section">
        <h4>项目经验</h4>
        <div
          v-for="(project, index) in editedProfile.projects"
          :key="index"
          class="work-item"
        >
          <div class="item-header">
            <span class="item-number">项目经历 {{ index + 1 }}</span>
            <button
              v-if="editedProfile.projects.length > 1"
              @click="removeProject(index)"
              class="remove-btn"
              type="button"
            >
              删除
            </button>
          </div>
          <div class="form-grid">
            <FormField label="项目名称" v-model="project.name" />
            <FormField label="担任角色" v-model="project.role" />
          </div>
          <div class="work-description-field">
            <label>项目详情（保留原文细节）</label>
            <textarea
              v-model="project.description"
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

// 规整嵌套数组：兼容旧扁平结构（转嵌套）+ 兜底空数组，确保模板 v-for 安全
;(() => {
  const p = editedProfile.value
  // 旧扁平 → 嵌套（兼容历史画像）
  if (!Array.isArray(p.education) && Array.isArray(p.schools)) {
    const n = Math.max(p.schools.length, p.degrees?.length || 0)
    p.education = Array.from({ length: n }, (_, i) => ({
      school: p.schools[i] || '',
      degree: p.degrees?.[i] || '',
      major: p.majors?.[i] || '',
      graduation_year: p.graduation_years?.[i] || '',
    }))
  }
  if (!Array.isArray(p.work_experience) && Array.isArray(p.companies)) {
    p.work_experience = p.companies.map((c: any, i: number) => ({
      company: c || '',
      position: p.positions?.[i] || '',
      duration: p.durations?.[i] || '',
      description: p.work_descriptions?.[i] || '',
    }))
  }
  if (!Array.isArray(p.projects) && Array.isArray(p.project_names)) {
    p.projects = p.project_names.map((nm: any, i: number) => ({
      name: nm || '',
      role: p.project_roles?.[i] || '',
      description: p.project_descriptions?.[i] || '',
    }))
  }
  // 兜底：三个嵌套数组必须存在（空画像/新画像）
  if (!Array.isArray(p.education)) p.education = []
  if (!Array.isArray(p.work_experience)) p.work_experience = []
  if (!Array.isArray(p.projects)) p.projects = []
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

// 教育/工作/项目：模板直接 v-for editedProfile 的嵌套对象数组（不再需要 computed 拼装）

const getConfidence = (field: string) => {
  return props.confidence?.[field]
}

// 增删：直接操作嵌套对象数组
const addEducation = () => {
  editedProfile.value.education.push({ school: '', degree: '', major: '', graduation_year: '' })
}
const removeEducation = (index: number) => {
  editedProfile.value.education.splice(index, 1)
}

const addWork = () => {
  editedProfile.value.work_experience.push({ company: '', position: '', duration: '', description: '' })
}
const removeWork = (index: number) => {
  editedProfile.value.work_experience.splice(index, 1)
}

const addProject = () => {
  editedProfile.value.projects.push({ name: '', role: '', description: '' })
}
const removeProject = (index: number) => {
  editedProfile.value.projects.splice(index, 1)
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
