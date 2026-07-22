# Spec: 简历优化（resume-optimization）

## ADDED Requirements

### Requirement: 简历生成输入与就绪性检查

系统 SHALL 接受「用户画像 + 目标岗位」作为简历生成的输入，并可选关联一次 JD 匹配结果以获取差距清单（Gap）。系统 SHALL 在生成前检查画像与 Gap 的就绪性，缺失时给出明确引导。

#### Scenario: 画像与 Gap 均就绪
- **WHEN** 用户发起简历生成，且已存在个人画像并关联了一份含 Gap 的 JD 匹配结果
- **THEN** 系统 SHALL 加载画像与 Gap 清单
- **AND** 系统 SHALL 拷贝画像与 Gap 作为本次生成的快照（保证生成过程中不被并发修改影响）
- **AND** 系统 SHALL 进入简历生成流程

#### Scenario: 画像缺失
- **WHEN** 用户发起简历生成但未建立个人画像
- **THEN** 系统 SHALL 中止生成流程
- **AND** 系统 SHALL 返回明确的引导："请先建立个人画像后再生成简历"
- **AND** 系统 SHALL 提供跳转到"建立画像"的入口

#### Scenario: 未关联 Gap（无 JD 匹配结果）
- **WHEN** 用户发起简历生成但未关联 JD 匹配结果，或匹配结果无 Gap
- **THEN** 系统 SHALL 降级为"通用简历生成"（仅基于画像，不针对特定 Gap 做改写）
- **AND** 系统 SHALL 提示用户"未检测到岗位差距，已生成通用版本，建议先做 JD 匹配以获得针对性简历"

#### Scenario: 画像完整度不足
- **WHEN** 用户画像的关键字段（工作经历、项目、技能）为空或置信度过低
- **THEN** 系统 SHALL 提示"画像信息不完整，生成结果可能单薄"
- **AND** 系统 SHALL 允许用户补充画像后重试，或继续生成

---

### Requirement: 画像与差距驱动的简历生成

系统 SHALL 基于用户画像，针对目标岗位从零生成一份结构化的 Markdown 简历。当存在 Gap 清单时，系统 SHALL 按 Gap 类型应用对应的改写策略，使简历内容针对该岗位定向优化。系统 SHALL 仅从画像生成，不接收用户的旧简历作为优化底稿。

#### Scenario: Gap 驱动的针对性生成
- **WHEN** 系统在有关联 Gap 清单的情况下生成简历
- **THEN** 系统 SHALL 按 Gap 类型应用改写策略：
  - **硬技能差距** → 强化相关项目经历 + 转移焦点（放大相邻可迁移技能）
  - **软技能表述弱** → STAR 改写 + 数据化
  - **隐性偏好缺位** → 挖掘可类比经历对冲
  - **红线预警** → 策略性呈现 + 预警（不造假）
- **AND** 系统 SHALL 在评估报告中标注哪些简历内容对应哪条 Gap 的改写（可追溯）

#### Scenario: 生成内容忠实于画像
- **WHEN** 系统生成简历
- **THEN** 系统 SHALL 仅使用画像中存在的信息组织简历
- **AND** 系统 SHALL 不编造画像中没有的经历、项目或量化数字
- **AND** 当某模块因画像信息不足无法充实内容时，系统 SHALL 标注"待补充"而非填充虚构内容

#### Scenario: 表述规则
- **WHEN** 系统生成简历正文
- **THEN** 经历描述 SHALL 遵循 STAR 结构并以强动词开头
- **AND** 涉及公司内部项目名称的内容 SHALL 脱敏（用业务功能或规模描述替代，如"核心交易链路"，不使用"某"式占位）
- **AND** 表述 SHALL 平实具体，不解释领域常识，不使用空泛套话（如"吃苦耐劳"）

#### Scenario: 简历结构规范
- **WHEN** 系统输出 Markdown 简历
- **THEN** 简历 SHALL 以 `# self-intro` 作为首个一级标题模块（含 name/role/contact/education 等键值）
- **AND** 简历 SHALL 包含教育背景模块（含毕业年份）
- **AND** 经历条目 SHALL 使用 `## 机构 | 角色` 形式，含 `date:` 与 bullet 要点
- **AND** 标题层级 SHALL 只使用 `#` 与 `##`

---

### Requirement: 简历质量评估（6 维 LLM 评估）

系统 SHALL 对生成的简历执行 6 维度 LLM 内容评估，输出各维度得分、通过/不通过判定与可执行的改进建议，作为自动迭代与人工精修的依据。评估 SHALL 只评估与建议，不直接改写简历。

#### Scenario: 六维度评估
- **WHEN** 系统评估一份生成的简历
- **THEN** 系统 SHALL 从以下六个维度逐项检查，每个检查项标记为"通过 / 不通过 / 部分通过"：
  - **基础规范**（权重 15%）：联系方式齐全、self-intro 完整、时间线无断层、脱敏合规
  - **JD 匹配**（权重 25%）：关键词命中、能力对齐（技能重叠 ≥60%）、相关经历前置
  - **成果量化**（权重 25%）：STAR 完整、至少 1 个可验证数字、强动词开头、无职责罗列
  - **结构清晰**（权重 10%）：模块顺序合理、层级正确、无冗余、每段 3-5 条 bullet
  - **差异化**（权重 15%）：独特亮点、加分项、层级适配
  - **语言表达**（权重 10%）：简洁无套话、客观具体、主语明确

#### Scenario: 评估输出结构
- **WHEN** 一次评估完成
- **THEN** 系统 SHALL 输出各维度得分与加权总分（0-100）
- **AND** 系统 SHALL 输出"通过项 / 需迭代项"汇总
- **AND** 系统 SHALL 输出按优先级排序的改进列表（高/中/低），每项含具体可执行建议

#### Scenario: 评估稳定性约束
- **WHEN** 系统 LLM 评估简历
- **THEN** 系统 SHALL 使用结构化输出约束（JSON Schema）保证评估结果格式稳定
- **AND** 当 LLM 输出不符合格式时，系统 SHALL 重试一次

#### Scenario: 量化可信度把关
- **WHEN** 评估"成果量化"维度
- **THEN** 系统 SHALL 检查量化数字是否合理可解释、来源是否可追溯（来自画像）
- **AND** 对无法追溯或明显编造的数字，系统 SHALL 标记为"不通过"

---

### Requirement: 简历格式校验（脚本硬规则）

系统 SHALL 对生成的 Markdown 简历与装配后的 HTML 产物执行确定性格式校验，拦截必须修复的硬错误。格式校验 SHALL 与 LLM 内容评估独立，作为第二层质量门。

#### Scenario: Markdown 格式硬规则
- **WHEN** 系统校验生成的 Markdown 简历
- **THEN** 系统 SHALL 检测并报告以下错误（必须修复）：
  - 无任何一级标题，或首个一级标题不是 `# self-intro`
  - self-intro 缺必填字段 `name:`
  - 缺少教育信息或教育背景缺毕业年份
  - `date:` 行格式错误（应为 `YYYY.MM — YYYY.MM|至今`）
  - 出现空的标题
- **AND** 系统 SHALL 对以下情况给出警告：出现 `###`+ 深标题、空模块、self-intro 未知字段、avatar 路径不存在

#### Scenario: HTML 产物硬规则
- **WHEN** 系统校验装配后的 HTML 产物
- **THEN** 系统 SHALL 检测并报告以下错误：
  - 存在未填充的 `{{占位符}}`
  - 缺少 Header（姓名区）
- **AND** 系统 SHALL 对缺少章节标题或缺 `<style>` 给出警告

#### Scenario: 校验阻断导出
- **WHEN** 格式校验存在错误（ERROR）
- **THEN** 系统 SHALL 阻止导出
- **AND** 系统 SHALL 返回生成/装配节点修复，错误清零后才继续

---

### Requirement: 自动迭代生成（路径 A）

系统 SHALL 提供默认的自动迭代生成路径：基于画像与 Gap 生成简历草稿，评估不通过时自动带反馈迭代，直到通过或达到轮次上限，最终导出并持久化为草稿版本。

#### Scenario: 自动迭代循环
- **WHEN** 路径 A 执行生成
- **THEN** 系统 SHALL 按以下顺序执行：生成草稿 → 6 维评估 → 判定
- **AND** 当评估存在不通过项且未达轮次上限时，系统 SHALL 携带评估反馈回到生成节点改写
- **AND** 每轮迭代 SHALL 至少修复 1 个不通过项

#### Scenario: 迭代收敛与上限
- **WHEN** 所有维度均通过
- **THEN** 系统 SHALL 结束迭代并进入格式校验与导出
- **WHEN** 达到最大轮次（默认 3）仍有不通过项
- **THEN** 系统 SHALL 结束迭代
- **AND** 系统 SHALL 在交付结果中标注"仍需改进项"
- **AND** 系统 SHALL 不无限循环

#### Scenario: 路径 A 产出
- **WHEN** 路径 A 完成（评估通过或达上限）且格式校验通过
- **THEN** 系统 SHALL 装配 HTML 并就绪 PDF（前端打印模式）
- **AND** 系统 SHALL 持久化该简历，状态为 `draft`，版本号为该岗位下的首个版本
- **AND** 系统 SHALL 返回 HTML/PDF、评估报告与简历标识
- **AND** 系统 SHALL 标记"已提供精修入口"，允许用户选择进入路径 B

---

### Requirement: 人机协同精修（路径 B）

系统 SHALL 提供可选的人机协同精修路径：用户在路径 A 产出的基础上触发精修，通过多轮反馈与画像追问迭代改进简历，直到用户确认满意后导出定稿。精修会话 SHALL 跨多次请求，中间态由 checkpointer 持久化。

#### Scenario: 触发精修
- **WHEN** 用户在路径 A 产出上选择"精修"
- **THEN** 系统 SHALL 将模式切换为精修（refine）
- **AND** 系统 SHALL 展示当前草稿、评估报告与反馈输入入口

#### Scenario: 反馈驱动的改写
- **WHEN** 用户提交精修反馈（如"这个项目多写点""换强调方向"）
- **THEN** 系统 SHALL 根据反馈改写简历草稿
- **AND** 系统 SHALL 对改写后的简历重新执行 6 维评估
- **AND** 系统 SHALL 通过 interrupt 暂停并等待用户的下一步反馈

#### Scenario: 画像追问挖亮点
- **WHEN** 精修过程中发现某 Gap 需要画像中不具备的素材（如某个项目的执行细节）
- **THEN** 系统 SHALL 主动 interrupt 向用户追问（如"你当时具体是怎么做这件事的？"）
- **AND** 系统 SHALL 将用户回答的素材融入简历改写
- **AND** 系统 SHALL 提示用户是否将新素材同步回画像

#### Scenario: 满意定稿
- **WHEN** 用户表示对当前版本满意
- **THEN** 系统 SHALL 执行格式校验
- **AND** 系统 SHALL 导出定稿 PDF
- **AND** 系统 SHALL 持久化为新版本，状态为 `finalized`

#### Scenario: 精修会话持久化
- **WHEN** 精修跨多次请求进行
- **THEN** 系统 SHALL 通过 checkpointer 保存会话中间态（当前草稿、评估、反馈历史、轮次）
- **AND** 系统 SHALL 仅在用户确认导出时将版本写入数据库，中间态不污染持久化简历列表

---

### Requirement: 简历导出（Markdown → HTML 主题 → A4 PDF）

系统 SHALL 将 Markdown 简历装配为带主题样式的 HTML，并支持导出为 A4 格式的 PDF。

#### Scenario: 主题选择
- **WHEN** 系统导出简历
- **THEN** 系统 SHALL 根据目标岗位特征选择主题，或使用用户指定主题
- **AND** 当岗位无明确主题倾向时，系统 SHALL 使用默认主题

#### Scenario: HTML 装配
- **WHEN** 系统装配 HTML
- **THEN** 系统 SHALL 将 `# self-intro` 渲染为 Header 组件（姓名/方向/教育/联系方式/照片）
- **AND** 系统 SHALL 将每个 `# 模块` 渲染为章节标题 + 模块正文
- **AND** 系统 SHALL 将 `## 机构 | 角色` 渲染为经历条目，bullet 拆为独立原子
- **AND** 系统 SHALL 套用预览壳（含 A4 自动分页）

#### Scenario: A4 PDF 导出
- **WHEN** 用户请求导出 PDF
- **THEN** 系统 SHALL 产出符合 A4 尺寸的 PDF
- **AND** 内容超出单页时 SHALL 自动分页
- **AND** PDF 默认文件名 SHALL 为"姓名-岗位"形式

#### Scenario: 排版质量检查
- **WHEN** 系统导出 PDF 前
- **THEN** 系统 SHALL 检查页数是否符合岗位层级预期（应届/初级 ≤2 页，资深 ≤3 页）
- **AND** 系统 SHALL 检查末页填充率（低于 30% 时提示精简）
- **AND** 系统 SHALL 检查行尾空白（过短的 bullet 提示合并或补全）

---

### Requirement: 简历持久化与版本管理

系统 SHALL 将生成的简历持久化存储，按用户与目标岗位维度维护，每份简历支持多版本。

#### Scenario: 保存简历
- **WHEN** 一次简历生成（路径 A）或定稿（路径 B）完成
- **THEN** 系统 SHALL 将简历写入持久化存储
- **AND** 系统 SHALL 保留目标岗位、关联的匹配结果、Markdown 全文、HTML、评估报告、综合评分、状态、主题与版本号

#### Scenario: 按岗位多份
- **WHEN** 用户为不同目标岗位分别生成简历
- **THEN** 系统 SHALL 按岗位分别存储，互不覆盖
- **AND** 系统 SHALL 支持按岗位分组查询用户的简历列表

#### Scenario: 按版本多次
- **WHEN** 用户对同一岗位的简历进行精修并定稿
- **THEN** 系统 SHALL 保留历史版本，新增版本号自增
- **AND** 系统 SHALL 支持查看指定版本的简历内容与评估报告

#### Scenario: 简历状态
- **WHEN** 简历处于不同阶段
- **THEN** 系统 SHALL 标注状态为以下之一：
  - `draft`：路径 A 自动生成的草稿
  - `finalized`：经精修定稿的版本

#### Scenario: 历史回看
- **WHEN** 用户请求查看简历历史
- **THEN** 系统 SHALL 按用户维度返回简历列表
- **AND** 系统 SHALL 按岗位分组、按版本与时间组织
- **AND** 系统 SHALL 支持下载指定版本的 PDF

---

### Requirement: 错误处理与降级

系统 SHALL 在简历生成各环节失败时提供友好的错误处理与降级方案。

#### Scenario: LLM 生成失败
- **WHEN** 简历生成的 LLM 调用失败（API 错误、超时、格式异常）
- **THEN** 系统 SHALL 按指数退避重试
- **AND** 重试耗尽后 SHALL 返回友好错误并保留已输入的岗位与关联信息

#### Scenario: 评估 LLM 失败
- **WHEN** 6 维评估的 LLM 调用失败
- **THEN** 系统 SHALL 降级为"仅格式校验通过即交付"
- **AND** 系统 SHALL 在评估报告中标注"自动评估未完成，请人工复核"

#### Scenario: 画像与 Gap 均就绪但生成异常
- **WHEN** 生成过程中出现未预期异常
- **THEN** 系统 SHALL 捕获异常并返回统一错误响应
- **AND** 系统 SHALL 不向用户暴露技术细节

---

### Requirement: API 响应格式

系统 SHALL 返回统一的简历优化 API 响应格式。

#### Scenario: 生成成功响应（路径 A）
- **WHEN** 路径 A 简历生成成功
- **THEN** 响应 SHALL 包含：
  - `status`: "success" | "warning"
  - `resume_id`: 持久化简历标识
  - `version`: 版本号
  - `content_md`: Markdown 简历全文
  - `html`: 渲染后的 HTML（用于预览/打印 PDF）
  - `eval_report`: 6 维评估报告（维度得分、总分、通过项、改进优先级）
  - `refine_offered`: 是否提供精修入口（布尔）

#### Scenario: 精修响应（路径 B，interrupt）
- **WHEN** 路径 B 一轮精修完成且等待用户下一步
- **THEN** 响应 SHALL 包含：
  - `status`: "awaiting_feedback"
  - `content_md`: 当前草稿
  - `eval_report`: 当前评估
  - `round`: 当前轮次
  - `pending_questions`: 系统追问用户的问题（可空）

#### Scenario: 错误响应
- **WHEN** 简历生成失败（画像缺失、Gap 缺失但未降级、LLM 失败）
- **THEN** 响应 SHALL 包含：
  - `status`: "error"
  - `error_code`: 错误类型（如 `PROFILE_MISSING`、`LLM_FAILED`、`GENERATE_FAILED`）
  - `error_message`: 用户友好的错误描述
  - `suggestions`: 引导下一步操作的数组

---

## MODIFIED Requirements

（此能力为新增，不修改已有 Requirements）

---

## REMOVED Requirements

（此变更不删除任何 Requirements）

---

## 数据结构定义

### resume_eval（6 维评估报告）

```json
{
  "overall_score": 82,
  "passed": false,
  "dimensions": {
    "basic_norm": {"score": 90, "weight": 0.15, "passed": true, "items": [{"check": "联系方式", "result": "pass"}]},
    "jd_match": {"score": 75, "weight": 0.25, "passed": false, "items": [...]},
    "quantification": {"score": 70, "weight": 0.25, "passed": false, "items": [...]},
    "structure": {"score": 85, "weight": 0.10, "passed": true, "items": [...]},
    "differentiation": {"score": 80, "weight": 0.15, "passed": true, "items": [...]},
    "language": {"score": 88, "weight": 0.10, "passed": true, "items": [...]}
  },
  "feedback_priorities": [
    {"priority": "high", "suggestion": "为第二段经历补充量化指标"},
    {"priority": "medium", "suggestion": "将 XX 项目前置以突出岗位相关"}
  ]
}
```

### resume 记录（持久化）

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "target_position": "AI 产品经理",
  "jd_result_id": "uuid（可空）",
  "version": 1,
  "status": "draft",
  "theme": "tech-dense",
  "content_md": "# self-intro\n...",
  "html": "<style>...</style>...",
  "eval_report_json": { ... },
  "eval_score": 82,
  "created_at": "...",
  "updated_at": "..."
}
```

### gaps_snapshot（输入，来自 JD 匹配）

```json
[
  {
    "type": "hard_skill | soft_skill | implicit | redline",
    "requirement": "数据分析经验",
    "current_state": "画像中无相关项目",
    "suggestion": "用 STAR 法则补充 XX 项目，强调量化成果",
    "severity": "high | medium | low | critical"
  }
]
```

---

## 边界条件

### 输入边界
- 目标岗位文本：1 - 100 字符
- 画像：必须含 `name`，工作/项目/技能至少一项非空
- Gap 清单：可空（降级为通用生成）；非空时每条含 type/requirement/severity
- 关联匹配结果：可空

### 输出边界
- Markdown 简历长度：建议 800 - 3000 字符
- 评估各项得分范围：0 - 100
- 评估综合分范围：0 - 100
- PDF 页数：应届/初级 ≤ 2 页，资深 ≤ 3 页

### 性能边界
- 简历生成（单次 LLM）：< 15 秒
- 6 维评估（单次 LLM）：< 15 秒
- 路径 A 端到端（生成 + 评估 + ≤3 轮迭代 + 导出）：< 60 秒
- 路径 B 单轮精修（改写 + 评估）：< 30 秒

### 迭代边界
- 路径 A 自动迭代上限：3 轮（可配置）
- 路径 B 精修轮次：由用户决定，单会话建议 ≤ 10 轮
