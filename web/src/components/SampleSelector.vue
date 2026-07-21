<template>
  <div class="sample-selector">
    <h4>没有简历？试试示例</h4>
    <p class="hint">点击示例简历快速体验功能</p>

    <div class="samples">
      <button
        v-for="sample in samples"
        :key="sample.id"
        class="sample-card"
        @click="selectSample(sample)"
        type="button"
      >
        <div class="info">
          <h5>{{ sample.name }}</h5>
          <p>{{ sample.description }}</p>
          <div class="tags">
            <span
              v-for="(tag, index) in sample.tags"
              :key="index"
              class="tag"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'select', sampleText: string): void
}>()

const samples = ref([
  {
    id: 'sample_1',
    name: '产品经理简历',
    description: '高质量简历，结构清晰',
    tags: ['产品经理', '完整', '推荐'],
    text: `张三
电话：13800138000
邮箱：zhangsan@example.com

教育背景
清华大学 计算机科学与技术 本科 2018-2022
GPA: 3.8/4.0

工作经历
ABC科技公司 产品经理 2022.07-至今
- 负责核心产品的规划和管理
- 协调跨部门团队，推动产品迭代
- 用户增长30%，日活跃用户达到100万

技能
- 产品设计：Axure, Figma, Sketch
- 数据分析：SQL, Python, Tableau
- 项目管理：Agile, Scrum, JIRA
- 语言能力：英语流利（雅思7.5）

项目经验
移动端APP改版项目 2023.01-2023.06
- 主导产品改版，提升用户体验
- 通过A/B测试优化核心流程
- 用户留存率提升25%

求职目标
- 期望职位：高级产品经理、产品总监
- 期望城市：北京、上海、深圳
- 期望薪资：30-50K/月
- 期望行业：互联网、人工智能`
  },
  {
    id: 'sample_2',
    name: '技术负责人简历',
    description: '复杂技术栈，多个项目',
    tags: ['技术', '开发', '复杂'],
    text: `李四
电话：13900139000
邮箱：lisi@example.com

教育背景
北京大学 软件工程 硕士 2016-2019
浙江大学 计算机科学 本科 2012-2016

工作经历
XYZ互联网公司 技术负责人 2019.08-至今
- 负责技术架构设计和团队管理
- 主导核心系统重构，性能提升3倍
- 管理技术团队15人

技能
- 编程语言：Java, Python, Go, JavaScript
- 框架：Spring Boot, Django, Gin, React
- 数据库：MySQL, MongoDB, Redis
- 云服务：AWS, 阿里云, Docker, K8s

项目经验
微服务架构改造 2022.01-2022.12
- 设计并实施微服务拆分方案
- 提升系统可用性至99.95%
- 降低运维成本40%

求职目标
- 期望职位：技术总监、CTO
- 期望城市：杭州、北京
- 期望薪资：50-80K/月
- 期望行业：互联网、金融科技`
  },
  {
    id: 'sample_3',
    name: '应届生简历',
    description: '简短简历，适合参考',
    tags: ['应届生', '简短', '实习'],
    text: `王五
电话：13700137000
邮箱：wangwu@example.com

教育背景
上海交通大学 软件工程 本科 2020-2024
GPA: 3.6/4.0

实习经历
DEF科技公司 前端开发实习生 2023.07-2023.12
- 协助开发公司官网
- 参与组件库建设

技能
- 编程语言：JavaScript, HTML, CSS
- 框架：Vue.js, React
- 工具：Git, Webpack, VS Code

项目经验
个人博客系统 2023.01-2023.03
- 使用Vue3开发个人博客
- 实现文章发布和评论功能

求职目标
- 期望职位：前端开发工程师
- 期望城市：上海、杭州
- 期望薪资：10-15K/月`
  }
])

const selectSample = (sample: any) => {
  emit('select', sample.text)
}
</script>

<style scoped lang="scss">
.sample-selector {
  margin: 2rem 0;
  text-align: center;
}

.sample-selector h4 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.hint {
  color: $text-secondary;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.samples {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.sample-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
  border: 2px solid $border-color;
  border-radius: $radius-lg;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.sample-card:hover {
  border-color: $primary-color;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba($primary-color, 0.15);
}

.info {
  flex: 1;
}

.info h5 {
  margin: 0 0 0.5rem 0;
  color: $ink;
}

.info p {
  margin: 0 0 0.75rem 0;
  color: $text-secondary;
  font-size: 0.9rem;
  line-height: 1.4;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  padding: 0.25rem 0.75rem;
  background: $primary-lighter;
  color: $primary-color;
  border-radius: $radius-lg;
  font-size: 0.8rem;
  font-weight: 600;
}
</style>
