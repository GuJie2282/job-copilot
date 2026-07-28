# Spec Delta: 简历优化（resume-optimization）— 精修局部更新与并发

## ADDED Requirements

### Requirement: 精修局部更新与并发编辑

系统 SHALL 在精修一轮 AI 改写完成后，只局部更新被改动的简历原子，而非整体重渲染整个预览；用户在未被改动原子的手动编辑 SHALL 原地保留，使手动编辑与 AI 改写能以原子粒度并发进行。

#### Scenario: AI 改动局部下发
- **WHEN** 一轮精修改写完成，产出新简历
- **THEN** 系统 SHALL 识别本次改动的原子（与上一版的差异）
- **AND** 系统 SHALL 只更新被改动原子的预览
- **AND** 系统 SHALL NOT 整体重渲染整份简历预览

#### Scenario: 不同原子并发保留
- **WHEN** 用户在原子 A 有未保存的手动编辑，同时 AI 改写只涉及原子 B（A ≠ B）
- **THEN** 系统 SHALL 局部更新原子 B
- **AND** 系统 SHALL 保留原子 A 的手动编辑（不被覆盖）

#### Scenario: 同原子冲突提示
- **WHEN** 用户在原子 X 有未保存的手动编辑，且 AI 改写也涉及原子 X
- **THEN** 系统 SHALL 检测到冲突
- **AND** 系统 SHALL NOT 静默覆盖用户编辑
- **AND** 系统 SHALL 提示用户选择保留用户版本或采用 AI 版本

#### Scenario: 大改动回退整体刷新
- **WHEN** 一轮改写涉及的改动超过阈值（如大面积增删段落）
- **THEN** 系统 SHALL 回退为整体刷新整份预览（避免错乱）
- **AND** 系统 SHALL 在整体刷新前提示用户未保存的手动编辑

---

## MODIFIED Requirements

### Requirement: 人机协同精修（路径 B）

系统 SHALL 提供可选的人机协同精修路径，以左右分栏的工作台形态呈现：左侧为简历成品的所见即所得预览与编辑区，右侧为 AI 对话区。用户 SHALL 能直接在简历预览中修改文字内容，也 SHALL 能通过自然语言对话向 AI 提出修改诉求，直到满意后导出定稿。AI 改写完成后系统 SHALL 局部更新被改原子（不整体重渲染），使用户的手动编辑与 AI 改写能以原子粒度并发进行。精修会话 SHALL 跨多次请求，中间态由 checkpointer 持久化。

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

#### Scenario: 改写以局部更新呈现、并发不互冲
- **WHEN** 一轮改写完成且用户在另一原子有未保存的手动编辑
- **THEN** 系统 SHALL 只局部更新被改动的原子（不整体重渲染）
- **AND** 系统 SHALL 保留用户在未涉及原子的手动编辑
- **AND** 仅当定稿、导出或下一轮改写前，系统 SHALL 将累积的手动编辑回写为真相源

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
- **THEN** 系统 SHALL 先将所有未保存的手动编辑回写为真相源
- **AND** 系统 SHALL 执行格式校验
- **AND** 系统 SHALL 导出定稿 PDF
- **AND** 系统 SHALL 持久化为新版本，状态为 `finalized`

#### Scenario: 精修会话持久化
- **WHEN** 精修跨多次请求进行
- **THEN** 系统 SHALL 通过 checkpointer 保存会话中间态（当前草稿、评估、对话历史、轮次）
- **AND** 系统 SHALL 仅在用户确认导出时将版本写入数据库，中间态不污染持久化简历列表
