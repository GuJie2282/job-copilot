<template>
  <!--
    示例 JD 快捷填入（JD 匹配页 / 简历优化页共用）

    为什么做成共用组件：两页用的是同一批示例 JD，数据放一处改一处，
    避免「改了一页忘了另一页」。与 SampleSelector（示例简历）的思路一致。
  -->
  <div class="jd-samples">
    <span class="js-label">没有现成 JD？试试示例</span>

    <div class="js-chips">
      <button
        v-for="s in samples"
        :key="s.id"
        class="js-chip"
        :class="{ 'is-active': currentText === s.text }"
        :disabled="disabled"
        type="button"
        :title="`点击填入：${s.position}`"
        @click="pick(s)"
      >
        <span class="js-name">{{ s.name }}</span>
        <span class="js-tags">{{ s.tags.join(' · ') }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 示例 JD 选择器。
 *
 * 数据即「岗位名 + JD 原文」的一对：点击后把两者一起交给父组件，
 * 由父组件决定填到哪个输入框（JD 匹配页只填 JD，简历优化页还要顺带填目标岗位）。
 *
 * 为什么示例里放一份「Python 后端工程师」：它和产品经理画像差异明显，
 * 点进去能立刻看到 Gap 清单里成排的红线项——演示匹配能力时比"高度匹配"的样例更能说明问题。
 */
import { ref } from 'vue'

/** 一份示例 JD：岗位名 + 标签 + JD 原文（含岗位职责/任职要求，满足页面上「建议 ≥ 200 字符」的提示） */
interface JdSample {
  id: string
  name: string
  position: string
  tags: string[]
  text: string
}

const props = defineProps<{
  /** 当前输入框里的文本；与某份示例完全一致时该示例高亮（用于回显"正在用哪个示例"） */
  currentText?: string
  /** 生成中时禁用，避免示例把用户已输入的内容覆盖掉 */
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', payload: { position: string; text: string }): void
}>()

const samples = ref<JdSample[]>([
  {
    id: 'jd_ai_pm',
    name: 'AI 产品经理',
    position: 'AI 产品经理（大模型应用方向）',
    tags: ['大模型', 'B端', '本行推荐'],
    text: `岗位名称：AI 产品经理（大模型应用方向）
所属团队：智能应用部
工作地点：北京 / 上海

【岗位职责】
1. 负责大模型应用类产品（智能问答、文档理解、Agent 工作流）的需求调研、方案设计与落地推进；
2. 深入业务场景梳理用户任务链路，把模糊需求拆解为可验证的产品方案与验收标准；
3. 与算法、工程、设计紧密协作，定义 Prompt 策略、知识库检索方案与效果评估指标；
4. 建立产品效果评测体系，通过 A/B 测试与人工评测持续迭代模型效果与交互体验；
5. 跟踪大模型行业动态与竞品进展，输出分析报告，支撑产品路线图决策。

【任职要求】
1. 本科及以上学历，3 年以上产品经理经验，其中至少 1 年 AI / 大模型相关产品经验；
2. 理解 LLM 基本原理与常见应用范式（RAG、Function Calling、Agent 编排），能与算法同学对齐技术方案；
3. 具备优秀的需求抽象与结构化表达能力，能独立完成 PRD 撰写与评审；
4. 有数据分析能力，熟悉 SQL，能基于数据发现问题并驱动迭代；
5. 有 To B 产品经验，或有大模型应用从 0 到 1 落地经验者优先。

【加分项】
- 有 RAG / 知识库 / 智能客服类产品落地经验；
- 有从 0 到 1 的完整产品经历。`
  },
  {
    id: 'jd_b_pm',
    name: 'B 端产品经理',
    position: 'B 端产品经理（SaaS 方向）',
    tags: ['SaaS', '中台', '偏传统'],
    text: `岗位名称：B 端产品经理（SaaS 方向）
所属部门：企业服务事业部
工作地点：杭州

【岗位职责】
1. 负责企业级 SaaS 产品的模块规划与迭代，覆盖需求收集、方案设计、开发跟进与上线验收；
2. 对接客户与售前团队，深入一线理解业务流程，将客户诉求转化为通用产品能力；
3. 输出高质量 PRD、原型与流程图，组织需求评审并推动跨团队协作落地；
4. 关注产品核心指标（激活、留存、付费转化），通过数据与客户反馈持续优化；
5. 沉淀行业解决方案与产品文档，支持销售与实施团队规模化交付。

【任职要求】
1. 本科及以上学历，2 年以上 B 端产品经验，有完整模块从设计到上线的经历；
2. 具备较强的业务理解与抽象能力，能在个性化需求与产品通用性之间做出合理取舍；
3. 熟练使用 Axure / Figma 等原型工具，PRD 表达清晰严谨；
4. 具备良好的沟通协调能力，能推动研发、测试、实施多方达成一致；
5. 有数据分析意识，熟悉常用指标口径与埋点方案。

【加分项】
- 有 SaaS / 中台 / 行业解决方案经验；
- 有客户成功或售前支持经验，能直接面对客户。`
  },
  {
    id: 'jd_python_be',
    name: 'Python 后端工程师',
    position: 'Python 后端开发工程师',
    tags: ['技术岗', '对照用'],
    text: `岗位名称：Python 后端开发工程师
所属部门：平台研发中心
工作地点：深圳

【岗位职责】
1. 负责公司核心业务系统的后端设计与开发，保障服务稳定性与性能；
2. 参与系统架构设计，负责高并发场景下的接口性能优化与缓存设计；
3. 编写单元测试与接口文档，参与代码评审，持续改善代码质量；
4. 与产品、前端协作完成需求交付，参与线上问题排查与值班响应；
5. 参与 CI/CD 流程建设，推动研发效能提升。

【任职要求】
1. 本科及以上学历，计算机相关专业，3 年以上 Python 后端开发经验；
2. 精通 FastAPI / Django 等主流框架，熟悉 RESTful API 设计规范；
3. 熟悉 MySQL / PostgreSQL 与 Redis，具备 SQL 优化与索引设计能力；
4. 熟悉 Linux 环境与 Docker，了解 K8s 者优先；
5. 具备良好的编码习惯与工程素养，有大型分布式系统经验者优先。

【加分项】
- 有消息队列（Kafka / RabbitMQ）使用经验；
- 有开源项目贡献或技术博客输出。`
  }
])

/** 点击示例：把「岗位名 + JD 原文」一起抛给父组件填入输入框 */
function pick(s: JdSample): void {
  if (props.disabled) return
  emit('select', { position: s.position, text: s.text })
}
</script>

<style scoped lang="scss">
/* 与所在卡片的 label 同一行：左侧是字段名，右侧是示例入口 */
.jd-samples {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-sm;
  margin-left: auto;
}

.js-label {
  font-size: $font-size-xs;
  color: $text-secondary;
  white-space: nowrap;
}

.js-chips {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

/* 示例按钮：胶囊型，名字在上、标签在下 */
.js-chip {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: $spacing-xs $spacing-sm;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $bg-white;
  cursor: pointer;
  transition: all $transition-base ease;
  text-align: left;

  &:hover:not(:disabled) {
    border-color: $primary-color;
    background: $primary-lighter;
  }

  /* 已填入该示例：实心高亮，让用户知道当前输入来自哪个示例 */
  &.is-active {
    border-color: $primary-color;
    background: $primary-lighter;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
}

.js-name {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: $ink;
  line-height: 1.2;
}

.js-tags {
  font-size: $font-size-xs;
  color: $text-secondary;
  line-height: 1.2;
}

@media (max-width: $container-md) {
  /* 窄屏：示例整体换到 label 下方另起一行，避免把字段名挤变形 */
  .jd-samples {
    margin-left: 0;
    width: 100%;
  }
}
</style>
