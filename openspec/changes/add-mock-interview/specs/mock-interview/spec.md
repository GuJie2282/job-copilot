# Spec: 模拟面试（mock-interview）

## ADDED Requirements

### Requirement: 面试会话创建与配置

系统 SHALL 允许用户创建一场模拟面试会话，并配置面试类型、档位、模式、人设等参数。JD（职位描述匹配结果）为可选项。

#### Scenario: 创建定向面试（关联 JD）
- **WHEN** 用户已建立画像且已有一份 JD 匹配结果，选择创建面试并关联该 JD
- **THEN** 系统 SHALL 基于画像与该 JD 的要求画像、差距清单生成定向面试
- **AND** 系统 SHALL 返回会话标识与第一道面试题

#### Scenario: 创建通用面试（无 JD）
- **WHEN** 用户已建立画像，创建面试时不关联任何 JD
- **THEN** 系统 SHALL 基于画像的求职目标岗位与画像强弱项生成通用面试
- **AND** 系统 SHALL 不因缺少 JD 而拒绝创建

#### Scenario: 选择面试类型
- **WHEN** 用户在创建会话时选择面试类型
- **THEN** 系统 SHALL 支持以下类型：行为面、技术面、案例面、动机面、全流程、压力面
- **AND** 当选择"全流程"时，系统 SHALL 按真实面试节奏混合多类型并排序

#### Scenario: 选择档位
- **WHEN** 用户选择面试档位
- **THEN** 系统 SHALL 提供语义化选项：简短、正常、深度、全程
- **AND** 系统 SHALL NOT 向用户展示具体时间分钟数
- **AND** 系统 SHALL 根据档位预生成"问答计划"（决定题量与每题深挖程度）

#### Scenario: 选择模式与人设
- **WHEN** 用户选择面试模式
- **THEN** 系统 SHALL 支持实战模式与教练模式，默认实战
- **WHEN** 用户选择或接受面试官人设
- **THEN** 系统 SHALL 按风格与角色两个维度装配人设

---

### Requirement: 画像就绪性检查

系统 SHALL 在创建面试会话前检查用户画像是否就绪，画像缺失或不完整时引导补充。

#### Scenario: 画像已就绪
- **WHEN** 用户创建面试且已存在包含工作或项目经历细节的画像
- **THEN** 系统 SHALL 加载画像快照进入会话状态
- **AND** 系统 SHALL 继续面试流程

#### Scenario: 画像缺失
- **WHEN** 用户创建面试但未建立画像
- **THEN** 系统 SHALL 中止创建
- **AND** 系统 SHALL 返回引导："请先建立个人画像后再进行模拟面试"
- **AND** 系统 SHALL 提供跳转到"建立画像"的入口

#### Scenario: 画像经历细节不足
- **WHEN** 用户画像存在但工作经历与项目经历的细节描述为空或过于简略
- **THEN** 系统 SHALL 提示"画像经历细节不足，面试可能无法个性化追问"
- **AND** 系统 SHALL 允许用户补充画像后重试，或继续进行通用面试

---

### Requirement: 个性化题库生成

系统 SHALL 基于用户画像、可选的 JD 匹配结果与面经库检索，生成结构化的个性化面试题库。每道题为"考查包"，包含主问题、追问地图与评判标尺。

#### Scenario: 考查包结构
- **WHEN** 系统生成一道面试题
- **THEN** 该题 SHALL 包含：题型、出题意图、主问题、个性化锚点（画像中的经历依据）
- **AND** 该题 SHALL 包含可挖掘点列表（用于支撑动态追问）
- **AND** 该题 SHALL 包含理想信号列表（用于评判回答与决定追问）
- **AND** 该题 SHALL 标注数据来源（真实面经 / AI 拟题 / 个人历史）

#### Scenario: 定向出题（有 JD）
- **WHEN** 面试关联了 JD 匹配结果
- **THEN** 系统 SHALL 优先围绕 JD 差距清单中的重点项出题
- **AND** 系统 SHALL 覆盖 JD 要求画像中的关键要求

#### Scenario: 通用出题（无 JD）
- **WHEN** 面试未关联 JD
- **THEN** 系统 SHALL 基于画像求职目标岗位与画像强弱项出题
- **AND** 系统 SHALL 对经历丰富领域深挖、对薄弱领域考察

#### Scenario: 面经库增强出题
- **WHEN** 系统生成题库
- **THEN** 系统 SHALL 检索公司面经库获取目标岗位的真实高频题以增强真实感
- **AND** 系统 SHALL 检索个人面经库避免与近期练过的题重复，并优先复练历史弱项

#### Scenario: 问答计划预生成
- **WHEN** 题库生成完成
- **THEN** 系统 SHALL 根据所选档位生成"问答计划"，明确本场面试的题量、每题深挖上限与是否含反问环节
- **AND** 问答计划 SHALL 决定面试的结束时机

---

### Requirement: 多轮面试对话

系统 SHALL 通过状态机的中断与恢复机制支持跨多个请求的长程面试对话，并完整记录对话流水。

#### Scenario: 单轮交互
- **WHEN** 面试官提出一个问题
- **THEN** 系统 SHALL 暂停状态机并等待用户回答
- **AND** 系统 SHALL 在用户提交回答后恢复状态机继续处理

#### Scenario: 对话流水记录
- **WHEN** 每一轮问答完成
- **THEN** 系统 SHALL 将该轮的问题、回答、评估结果追加到会话的对话流水（transcript）
- **AND** transcript SHALL 作为追问、评分、复盘与面经沉淀的统一数据来源

#### Scenario: 画像快照隔离
- **WHEN** 面试会话开始
- **THEN** 系统 SHALL 拷贝当前画像快照进入会话状态
- **AND** 面试进行中用户对原始画像的修改 SHALL NOT 影响正在进行的会话

---

### Requirement: 动态追问

系统 SHALL 基于用户回答与预埋的评判标尺决定是否追问、追问什么，且每题追问次数受控。

#### Scenario: 追问必要性判定
- **WHEN** 系统评估一轮回答
- **THEN** 系统 SHALL 将回答与会话该题的理想信号列表比对（信号差检测）
- **AND** 若回答命中全部理想信号，系统 SHALL 判定为已充分并切换下一题
- **AND** 若回答缺少信号且存在对应可挖掘点，系统 SHALL 沿该方向追问

#### Scenario: 追问按图索骥
- **WHEN** 系统决定追问
- **THEN** 系统 SHALL 基于出题时预埋的可挖掘点生成追问
- **AND** 系统 SHALL NOT 依赖临场自由发挥决定追问内容

#### Scenario: 追问次数上限
- **WHEN** 单道题的追问次数达到 3 次
- **THEN** 系统 SHALL 强制切换到下一题
- **AND** 当该题可挖掘点已全部耗尽时，系统 SHALL 切换下一题

#### Scenario: 回答空洞兜底
- **WHEN** 用户回答空洞或跑题
- **THEN** 系统 SHALL 追问引导具体化（如"能具体讲讲吗？"）
- **AND** 该兜底追问 SHALL 计入追问次数上限

---

### Requirement: 换题与结束

系统 SHALL 按预设问答计划推进面试，在适当时机切换题目、进入反问环节或结束面试。

#### Scenario: 切换下一题
- **WHEN** 当前题已充分回答或追问到终点，且问答计划仍有未问题目
- **THEN** 系统 SHALL 切换到下一题

#### Scenario: 进入反问环节
- **WHEN** 问答计划接近完成（剩余题目不足）且计划包含反问环节
- **THEN** 系统 SHALL 进入反问环节，由用户向面试官提问
- **AND** 系统 SHALL 评估用户提问的质量并计入综合评分

#### Scenario: 面试结束
- **WHEN** 问答计划全部执行完成
- **THEN** 系统 SHALL 结束面试
- **AND** 系统 SHALL NOT 依赖墙钟时间决定结束
- **AND** 系统 SHALL 进入复盘环节

#### Scenario: 用户主动结束
- **WHEN** 用户在面试过程中主动选择结束
- **THEN** 系统 SHALL 基于已有对话流水生成复盘
- **AND** 系统 SHALL 在复盘中标注本次面试为提前结束

---

### Requirement: 面试官人设

系统 SHALL 提供可配置的面试官人设，由风格与角色两个正交维度组成，压力面作为风格叠加而非独立题型。

#### Scenario: 风格选择
- **WHEN** 用户配置人设风格
- **THEN** 系统 SHALL 支持多种风格（如严肃、轻松、风趣、温和、压力）
- **AND** 所选风格 SHALL 影响面试官的开场白、提问口吻与追问语气

#### Scenario: 角色配置
- **WHEN** 配置人设角色
- **THEN** 系统 SHALL 按公司、职位、资深度装配角色背景
- **AND** 角色背景 SHALL 影响提问的专业方向与深度

#### Scenario: 压力面叠加
- **WHEN** 用户选择压力面
- **THEN** 系统 SHALL 在所选题型基础上叠加挑战性人设（质疑、施压）
- **AND** 压力面 SHALL NOT 替换原有题型，而是作为风格层叠加

#### Scenario: 预置人设组合
- **WHEN** 用户不自行配置人设
- **THEN** 系统 SHALL 提供若干预置人设组合（如特定公司 + 职位 + 风格）供选择

---

### Requirement: 实战与教练双模式

系统 SHALL 提供实战与教练两种模式，分别满足沉浸体验与即时学习的诉求。

#### Scenario: 实战模式
- **WHEN** 用户选择实战模式
- **THEN** 面试过程中系统 SHALL NOT 向用户展示实时评分或评价
- **AND** 系统 SHALL 仅在面试结束后输出完整复盘

#### Scenario: 教练模式
- **WHEN** 用户选择教练模式
- **THEN** 每轮回答后系统 SHALL 在侧边区域提供一句改进提示
- **AND** 改进提示 SHALL NOT 打断面试官的提问节奏

#### Scenario: 模式默认值
- **WHEN** 用户未显式选择模式
- **THEN** 系统 SHALL 默认采用实战模式

---

### Requirement: 面试复盘报告

系统 SHALL 在面试结束后输出结构化复盘报告，包含逐题回顾、改进范例、卡壳分析与可执行的后续建议。

#### Scenario: 复盘内容完整性
- **WHEN** 系统生成复盘报告
- **THEN** 报告 SHALL 包含：综合总评、分维度能力评估、逐题回顾
- **AND** 每题回顾 SHALL 包含原问题、用户回答、评估与改进范例

#### Scenario: 改进范例基于自身回答
- **WHEN** 系统为某题生成改进范例
- **THEN** 系统 SHALL 基于该用户自己的回答生成个性化改进版
- **AND** 系统 SHALL NOT 从题库检索通用标准答案作为范例

#### Scenario: 失分与卡壳分析
- **WHEN** 系统分析失分点
- **THEN** 报告 SHALL 列出不合适的回答（跑题、空洞、负面、造假感）
- **AND** 报告 SHALL 标注卡壳处（信号缺失、追问未答出、回答过短或含糊）

#### Scenario: 可执行的后续建议
- **WHEN** 系统给出后续面试建议
- **THEN** 建议 SHALL 落到具体动作（如"准备 3 个 STAR 故事覆盖某方向"）
- **AND** 建议 SHALL NOT 使用"加强某能力"式空泛表述

#### Scenario: 成长对比
- **WHEN** 用户历史面经库存在同考查点的历史记录
- **THEN** 报告 SHALL 提供本次与历史表现的对比，展示成长曲线

---

### Requirement: 会话持久化与续面

系统 SHALL 持久化面试会话状态，支持跨请求续面与抗中断恢复。

#### Scenario: 跨请求保持状态
- **WHEN** 一场面试跨越多个 HTTP 请求
- **THEN** 系统 SHALL 在每轮交互后持久化会话状态（进度、对话流水、累积评分）
- **AND** 下一轮请求 SHALL 能恢复到上次状态继续

#### Scenario: 续面
- **WHEN** 用户中断后重新进入一场进行中的面试
- **THEN** 系统 SHALL 展示已有对话流水
- **AND** 系统 SHALL 从中断处继续面试

#### Scenario: 抗重启
- **WHEN** 后端进程在面试进行中重启
- **THEN** 系统 SHALL NOT 丢失进行中的会话状态
- **AND** 用户 SHALL 能在重启后继续未完成的面试

#### Scenario: 会话生命周期
- **WHEN** 面试会话处于不同阶段
- **THEN** 系统 SHALL 维护会话状态：配置中、面试中、已暂停、已完成
- **AND** 已完成的会话 SHALL 可回看复盘但不可继续答题

---

### Requirement: 会话式 API

系统 SHALL 提供会话式 API 支持长程面试交互，答题端点采用多态响应。

#### Scenario: 创建会话
- **WHEN** 客户端请求创建面试会话（含配置参数）
- **THEN** 响应 SHALL 包含会话标识与第一道题
- **AND** 响应状态 SHALL 标记为等待回答

#### Scenario: 提交回答（面试继续）
- **WHEN** 客户端提交一轮回答且面试未结束
- **THEN** 响应 SHALL 包含状态为"等待回答"、当前轮次、下一题内容
- **AND** 当处于教练模式时，响应 SHALL 包含上一轮的改进提示

#### Scenario: 提交回答（面试结束）
- **WHEN** 客户端提交一轮回答且问答计划已执行完
- **THEN** 响应 SHALL 包含状态为"已结束"、总轮次、复盘标识
- **AND** 客户端 SHALL 据此跳转至复盘

#### Scenario: 查询与历史
- **WHEN** 客户端请求会话详情
- **THEN** 响应 SHALL 包含会话状态与对话流水
- **WHEN** 客户端请求历史会话
- **THEN** 响应 SHALL 按用户维度返回历史会话列表，按时间倒序

---

### Requirement: 错误处理与降级

系统 SHALL 在面试各环节失败时提供友好处理与降级方案。

#### Scenario: LLM 调用失败
- **WHEN** 出题、评估或复盘的 LLM 调用失败
- **THEN** 系统 SHALL 按指数退避重试
- **AND** 重试耗尽后 SHALL 返回友好错误并保留已有会话进度

#### Scenario: 面经库检索失败
- **WHEN** 面经库检索失败或返回空
- **THEN** 系统 SHALL 降级为不依赖检索的出题
- **AND** 系统 SHALL NOT 因检索失败中断面试

#### Scenario: 会话状态异常
- **WHEN** 续面时会话状态损坏或缺失
- **THEN** 系统 SHALL 提示会话无法恢复
- **AND** 系统 SHALL 引导用户重新开始一场面试

---

## 数据结构定义

### QuestionPackage（考查包）

```json
{
  "qid": "string",
  "category": "behavioral | technical | case | motivation",
  "intent": "出题意图",
  "stem": "主问题文本",
  "anchor": "画像中的经历依据",
  "jd_ref": "关联的 JD 要求（无 JD 时为 null）",
  "probing_points": ["可挖掘点，追问弹药"],
  "ideal_signals": ["好回答应体现的信号，评判标尺"],
  "estimated_minutes": 4,
  "rag_source": "company_lib | llm_gen | personal"
}
```

### InterviewSession（面试会话）

```json
{
  "session_id": "string",
  "user_id": "string",
  "status": "setup | interviewing | paused | finished",
  "interview_type": "behavioral | technical | case | motivation | full | stress",
  "intensity": "short | normal | deep | full",
  "mode": "real | coach",
  "persona": { "tone": "...", "role": {...}, "stress_mode": false },
  "jd_result_id": "string | null",
  "profile_snapshot": { "画像快照" },
  "question_plan": { "题量": 6, "probing_limit": 2, "has_qa_session": true },
  "question_bank": [QuestionPackage],
  "transcript": [
    { "round": 1, "question": "...", "answer": "...", "evaluation": {...}, "action": "probe|next|end" }
  ],
  "running_scores": { "communication": 0, "logic": 0, "expertise": 0, "resilience": 0, "fit": 0 },
  "highlights": [], "weaknesses": [],
  "debrief_id": "string | null"
}
```

### DebriefReport（复盘报告）

```json
{
  "overview": { "radar": {...}, "level": "...", "one_line_summary": "..." },
  "round_by_round": [
    { "question": "...", "your_answer": "...", "evaluation": {...}, "better_version": "改进范例" }
  ],
  "weaknesses": { "inappropriate_answers": [], "stuck_points": [] },
  "next_steps": ["可执行建议"],
  "growth_comparison": { "本次 vs 历史" }
}
```

---

## 边界条件

### 输入边界
- 面试配置参数：类型、档位、模式、人设四选一组合
- 单轮回答长度：建议 10-5000 字符（过短视为卡壳信号，过长截断）
- 关联 JD：可选，必须为当前用户已有的 JD 匹配结果

### 输出边界
- 单场面试题量：由档位决定（简短 3-4 / 正常 5-7 / 深度 7-10 / 全程含完整流程）
- 单题追问次数：最多 3 次
- 能力评分范围：0-100
- transcript 完整保留所有轮次

### 性能边界
- 出题阶段（含检索）：< 15 秒
- 单轮评估 + 决策：< 10 秒
- 复盘生成：< 20 秒
