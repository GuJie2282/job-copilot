# Spec Delta: 简历优化（resume-optimization）— 精修工作台化

## ADDED Requirements

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

## MODIFIED Requirements

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
