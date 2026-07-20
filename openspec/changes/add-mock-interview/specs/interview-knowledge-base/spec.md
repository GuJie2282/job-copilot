# Spec: 面试知识库（interview-knowledge-base）

## ADDED Requirements

### Requirement: 个人面经库写入

系统 SHALL 在每次面试复盘后，将结构化的面经条目沉淀到该用户的个人面经库。

#### Scenario: 复盘后自动沉淀
- **WHEN** 一场面试复盘完成
- **THEN** 系统 SHALL 从复盘报告中提取结构化面经条目写入个人面经库
- **AND** 每条目 SHALL 包含：岗位、公司、题型、问题、用户回答、评分、改进范例、发生时间

#### Scenario: 沉淀的完整性
- **WHEN** 系统写入面经条目
- **THEN** 条目 SHALL 保留足够的细节以支撑后续检索与对比
- **AND** 系统 SHALL 记录该条目来源为"个人历史"

#### Scenario: 提前结束的面试
- **WHEN** 一场面试被用户提前结束
- **THEN** 系统 SHALL 仍基于已有对话流水沉淀面经条目
- **AND** 系统 SHALL 标注该场面试为提前结束

---

### Requirement: 个人面经库检索

系统 SHALL 支持按语义与关键词检索用户本人的历史面经，服务于出题与复盘对比。

#### Scenario: 出题时避免重复与复练弱项
- **WHEN** 系统为新面试生成题库
- **THEN** 系统 SHALL 检索用户近期练过的题目以避免重复
- **AND** 系统 SHALL 优先将历史评分较低考查点的相关题纳入本轮以支持复练

#### Scenario: 复盘时成长对比
- **WHEN** 系统生成复盘报告
- **THEN** 系统 SHALL 检索同考查点的历史面经
- **AND** 报告 SHALL 展示本次与历史表现的成长对比

#### Scenario: 跨岗位检索
- **WHEN** 用户检索个人面经
- **THEN** 系统 SHALL 支持按岗位、公司、题型维度筛选
- **AND** 系统 SHALL 按相关性返回结果

---

### Requirement: 公司面经库冷启动

系统 SHALL 通过混合策略完成公司/岗位面经库的冷启动，兼顾质量、覆盖与合规。

#### Scenario: 精选种子打底
- **WHEN** 系统初始化公司面经库
- **THEN** 系统 SHALL 预置人工精选的高频真题种子集
- **AND** 种子集 SHALL 覆盖若干热门岗位（如产品、运营、技术等）
- **AND** 种子条目 SHALL 标注来源为"精选"

#### Scenario: LLM 扩充长尾
- **WHEN** 某岗位面经数量不足
- **THEN** 系统 SHALL 基于精选种子与公开信息生成补充题目填补长尾
- **AND** 生成的条目 SHALL 标注来源为"AI 拟题"

#### Scenario: UGC 逐渐替换
- **WHEN** 用户主动贡献真实面经
- **THEN** 系统 SHALL 接收并标注来源为"用户贡献"
- **AND** 随 UGC 积累，系统 SHALL 逐步以真实面经替换生成数据

#### Scenario: 合规边界
- **WHEN** 系统获取面经数据
- **THEN** 系统 SHALL NOT 通过爬取第三方平台获取面经
- **AND** 系统 SHALL 仅采用精选录入、生成与用户自愿贡献三种来源

---

### Requirement: 公司面经库检索

系统 SHALL 支持按目标公司与岗位检索真实面经，增强模拟面试的真实感。

#### Scenario: 出题时真实感增强
- **WHEN** 系统为关联特定公司或岗位的面试生成题库
- **THEN** 系统 SHALL 检索该公司/岗位的真实高频面经
- **AND** 检索结果 SHALL 用于增强题库的真实感

#### Scenario: 检索优先级
- **WHEN** 系统从公司面经库检索
- **THEN** 系统 SHALL 按来源优先级排序：精选 > 用户贡献 > AI 拟题
- **AND** 当高质量来源不足时，系统 SHALL 补充较低优先级来源并标注

---

### Requirement: 数据来源治理与透明度

系统 SHALL 为每条面经数据标注来源，并向用户透明展示，不假装生成数据为真实面经。

#### Scenario: 来源标签
- **WHEN** 系统存储任意面经条目
- **THEN** 该条目 SHALL 携带来源标签：精选 / 用户贡献 / AI 拟题 / 个人历史

#### Scenario: 对用户透明
- **WHEN** 面试题或面经展示给用户
- **THEN** 系统 SHALL 明确标注其来源（如"基于真实面经整理"或"AI 拟题"）
- **AND** 系统 SHALL NOT 将 AI 生成的题目伪装为真实面经

#### Scenario: 检索结果可追溯
- **WHEN** 系统基于检索结果出题或对比
- **THEN** 系统 SHALL 保留每条结果与最终输出（题目、对比）的对应关系
- **AND** 用户 SHALL 能查看某题依据了哪些面经来源

---

### Requirement: 混合检索

系统 SHALL 采用关键词与语义相结合的混合检索方式，保证面经检索的召回稳定性。

#### Scenario: 语义检索为主
- **WHEN** 系统按语义相似度检索面经
- **THEN** 系统 SHALL 使用向量嵌入计算语义相关性

#### Scenario: 关键词兜底
- **WHEN** 面经查询包含明确的专业术语或岗位关键词
- **THEN** 系统 SHALL 结合关键词匹配检索
- **AND** 混合检索 SHALL 提升专业术语场景下的召回率

#### Scenario: 检索结果排序
- **WHEN** 系统返回检索结果
- **THEN** 系统 SHALL 综合语义相关性、关键词匹配度与来源优先级排序

---

### Requirement: 隐私与隔离

系统 SHALL 保证个人面经库的用户隔离，个人面经不被其他用户访问。

#### Scenario: 个人库隔离
- **WHEN** 系统检索或写入个人面经库
- **THEN** 系统 SHALL 严格按用户维度隔离
- **AND** 系统 SHALL NOT 允许某用户访问另一用户的个人面经

#### Scenario: 公司库共享
- **WHEN** 系统检索公司面经库
- **THEN** 公司库 SHALL 为全局共享
- **AND** 用户贡献进入公司库的内容 SHALL 经脱敏处理，不暴露贡献者私人信息

#### Scenario: 数据可删除
- **WHEN** 用户请求删除其个人面经数据
- **THEN** 系统 SHALL 支持删除该用户的全部个人面经
- **AND** 删除 SHALL NOT 影响公司库中的共享数据（已脱敏）

---

## 数据结构定义

### PersonalEpisode（个人面经条目）

```json
{
  "id": "string",
  "user_id": "string",
  "position": "岗位",
  "company": "公司（可为空）",
  "category": "behavioral | technical | case | motivation",
  "question": "面试问题",
  "my_answer": "用户当时的回答",
  "score": 75,
  "better_version": "改进范例",
  "happened_at": "时间戳",
  "source": "personal",
  "session_id": "关联的面试会话"
}
```

### CompanyQuestion（公司面经条目）

```json
{
  "id": "string",
  "company": "公司",
  "position": "岗位",
  "category": "题型",
  "question": "面经问题",
  "context": "问题背景/考察点（可选）",
  "source": "curated | ugc | llm_generated",
  "created_at": "时间戳"
}
```

---

## 边界条件

### 数据规模边界
- 个人面经库：随用户使用自然增长，无硬性上限
- 公司面经库冷启动种子：每个热门岗位 10-20 条精选起步
- 单次检索返回：默认 Top-K（如 5），可配置

### 检索边界
- 检索响应时间：< 3 秒
- 向量嵌入维度与模型：实现细节，见 design.md
- 混合检索权重：可配置，按样本校准

### 隐私边界
- 个人面经：仅本人可访问
- 用户贡献至公司库的内容：必须脱敏，不可反向追溯到贡献者
