# resume-optimization Specification

## Purpose
TBD - created by archiving change add-resume-optimization. Update Purpose after archive.
## Requirements
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

系统 SHALL 提供可选的人机协同精修路径，以左右分栏的工作台形态呈现：左侧为简历成品的所见即所得预览与编辑区，右侧为 AI 对话区。用户 SHALL 能直接在简历预览中修改文字内容，也 SHALL 能通过自然语言对话向 AI 提出修改诉求，直到满意后导出定稿。精修会话 SHALL 跨多次请求，中间态由 checkpointer 持久化。

#### Scenario: 触发精修并进入工作台
- **WHEN** 用户在路径 A 产出上选择"精修"
- **THEN** 系统 SHALL 将模式切换为精修（refine）
- **AND** 系统 SHALL 呈现左右分栏工作台：左侧简历成品预览与编辑区，右侧 AI 对话区
- **AND** 系统 SHALL 在对话区给出操作指引开场白，说明手动编辑与对话改写两种方式

#### Scenario: 手动编辑简历成品
- **WHEN** 用户在左侧预览中直接修改文字内容
- **THEN** 系统 SHALL 允许用户就地编辑可见的文字
- **AND** 系统 SHALL 将编辑精确回写到 Markdown 真相源的对应片段

#### Scenario: 对话驱动的改写
- **WHEN** 用户以自然语言提出修改诉求
- **THEN** 系统 SHALL 根据诉求改写简历
- **AND** 系统 SHALL 返回一段自然语言说明本次改动
- **AND** 系统 SHALL 返回改写后的简历并在左侧刷新
- **AND** 系统 SHALL 通过 interrupt 暂停并等待用户的下一步输入

#### Scenario: 改写基于最新草稿
- **WHEN** 用户在手动编辑后发起对话改写
- **THEN** 系统 SHALL 先将手动编辑回写为最新草稿
- **AND** 系统 SHALL 基于含手动编辑的最新草稿执行改写
- **AND** 系统 SHALL NOT 在改写时冲掉用户尚未回写的手动编辑

#### Scenario: 改写过程展示思考
- **WHEN** 系统执行一轮精修改写
- **THEN** 系统 SHALL 在对话区增量展示 AI 的思考过程
- **AND** 思考过程 SHALL 与自然语言回复在视觉上区分

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
- **THEN** 系统 SHALL 通过 checkpointer 保存会话中间态（当前草稿、评估、对话历史、轮次）
- **AND** 系统 SHALL 仅在用户确认导出时将版本写入数据库，中间态不污染持久化简历列表

---

### Requirement: 简历导出（Markdown → HTML 主题 → A4 PDF）

系统 SHALL 将 Markdown 简历装配为带主题样式的 HTML，并 SHALL 在服务端将其渲染为 A4 格式的 PDF 以下载方式提供给用户，而非依赖客户端的打印对话框。

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

#### Scenario: 服务端 PDF 渲染下载
- **WHEN** 用户请求导出 PDF
- **THEN** 系统 SHALL 在服务端将简历渲染为符合 A4 尺寸的 PDF
- **AND** 系统 SHALL 以文件下载方式返回 PDF，而非打开客户端打印对话框
- **AND** 内容超出单页时 SHALL 自动分页
- **AND** PDF 默认文件名 SHALL 为"姓名-岗位"形式

#### Scenario: PDF 反映最新编辑
- **WHEN** 用户在精修中存在手动编辑后请求导出
- **THEN** 系统 SHALL 先将手动编辑回写为最新草稿
- **AND** 系统 SHALL 基于最新草稿装配并渲染 PDF
- **AND** 导出的 PDF SHALL 包含用户的手动编辑

#### Scenario: 排版质量检查
- **WHEN** 系统导出 PDF 前
- **THEN** 系统 SHALL 检查页数是否符合岗位层级预期（应届/初级 ≤2 页，资深 ≤3 页）
- **AND** 系统 SHALL 检查末页填充率（低于 30% 时提示精简）
- **AND** 系统 SHALL 检查行尾空白（过短的 bullet 提示合并或补全）

#### Scenario: 服务端渲染失败降级
- **WHEN** 服务端 PDF 渲染失败
- **THEN** 系统 SHALL 回退到客户端打印通道
- **AND** 系统 SHALL 提示用户当前为降级方式

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

系统 SHALL 返回统一的简历优化 API 响应格式；精修路径 SHALL 以流式方式增量推送改写过程与结构化结果。

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

#### Scenario: 精修流式响应（路径 B）
- **WHEN** 路径 B 执行一轮精修改写
- **THEN** 系统 SHALL 在改写期间增量下发思考过程事件
- **AND** 系统 SHALL 增量下发自然语言说明的内容片段
- **AND** 系统 SHALL 在改写完成时下发一个完成事件，携带改写后的简历、自然语言说明、当前评估与轮次
- **AND** 当改写失败时，系统 SHALL 下发错误事件并结束该流

#### Scenario: 手动编辑回写响应
- **WHEN** 用户提交在预览中的手动编辑
- **THEN** 响应 SHALL 包含回写后的最新草稿
- **AND** 响应 SHALL 包含基于最新草稿重新装配的预览
- **AND** 当存在未能回写的编辑项时，系统 SHALL 在响应中告警

#### Scenario: 错误响应
- **WHEN** 简历生成失败（画像缺失、Gap 缺失但未降级、LLM 失败）
- **THEN** 响应 SHALL 包含：
  - `status`: "error"
  - `error_code`: 错误类型（如 `PROFILE_MISSING`、`LLM_FAILED`、`GENERATE_FAILED`）
  - `error_message`: 用户友好的错误描述
  - `suggestions`: 引导下一步操作的数组

### Requirement: 简历真相源与所见即所得编辑回写

系统 SHALL 保证 Markdown 为简历的唯一真相源，预览所见的 HTML 永远为其派生渲染；用户在简历预览中的直接文字编辑 SHALL 精确回写到 Markdown 真相源的对应片段，而非重建整份内容。

#### Scenario: 单一真相源
- **WHEN** 系统呈现简历预览并允许编辑
- **THEN** 预览 SHALL 是 Markdown 真相源的派生渲染
- **AND** 系统 SHALL NOT 维护一份与 Markdown 并行、可被独立修改的 HTML 真相源

#### Scenario: 编辑精确局部回写
- **WHEN** 用户在预览中修改某一处文字
- **THEN** 系统 SHALL 仅将该处改动回写到 Markdown 中对应的片段
- **AND** 系统 SHALL NOT 因此重建或重排整份 Markdown

#### Scenario: 未编辑内容保持不变
- **WHEN** 一次编辑被回写
- **THEN** 用户未触及的字段与结构 SHALL 原样保留
- **AND** 系统 SHALL NOT 因回写导致未编辑字段丢失或变形

#### Scenario: 结构性改动由对话承担
- **WHEN** 用户希望进行超出文本替换的结构性改动（如增删整段经历、调整模块顺序）
- **THEN** 系统 SHALL 引导用户通过自然语言对话向 AI 提出该诉求
- **AND** 直接编辑 SHALL 仅承诺文本内容的替换

---

### Requirement: 精修改写的思考过程与结构化回复

系统 SHALL 在精修改写期间增量推送 AI 的思考过程，并将一次精修回复的自然语言说明与改写后的简历分别呈现，使思考、说明与简历三者在视觉上可区分。

#### Scenario: 精修展示思考过程
- **WHEN** 系统执行一轮精修改写
- **THEN** 系统 SHALL 在改写期间增量推送 AI 的思考过程
- **AND** 思考过程 SHALL 早于或伴随改写结果呈现
- **AND** 当底层模型未返回思考过程时，系统 SHALL 照常完成改写，不因缺思考而失败

#### Scenario: 回复含说明与改写简历
- **WHEN** 一轮精修改写完成
- **THEN** 系统 SHALL 给出一段自然语言说明，描述本次做了哪些改动
- **AND** 系统 SHALL 给出改写后的完整简历
- **AND** 自然语言说明与改写简历 SHALL 分别呈现

#### Scenario: 三层视觉区分
- **WHEN** 客户端展示一轮精修交互
- **THEN** 思考过程 SHALL 在视觉上弱化（如弱化色调、斜体）并支持折叠
- **AND** 自然语言说明 SHALL 以对话回复样式呈现
- **AND** 改写后的简历 SHALL 在预览区整体刷新，而非逐字打字机渲染

#### Scenario: 说明与简历切分的降级
- **WHEN** 模型回复未能将自然语言说明与改写简历清晰区分
- **THEN** 系统 SHALL 将回复内容作为自然语言说明呈现
- **AND** 简历 SHALL 沿用上一版本，不因切分失败而损坏
- **AND** 系统 SHALL 提示用户本次未生成新简历

---

