# Spec: JD 匹配分析（jd-matching）

## ADDED Requirements

### Requirement: JD 输入与校验

系统 SHALL 接受用户粘贴的职位描述（JD）文本作为匹配输入，并在解析前进行基本校验。

#### Scenario: 粘贴完整 JD
- **WHEN** 用户粘贴一段完整的 JD 文本（≥ 200 字符）
- **THEN** 系统 SHALL 接受该输入
- **AND** 系统 SHALL 进入 JD 结构化解析流程

#### Scenario: JD 文本过短
- **WHEN** 用户粘贴的 JD 文本少于 200 字符
- **THEN** 系统 SHALL 检测到文本过短
- **AND** 系统 SHALL 提示"JD 内容过少，可能无法准确分析"
- **AND** 系统 SHALL 允许用户继续或补充内容

#### Scenario: 粘贴内容不是 JD
- **WHEN** 用户粘贴的文本缺少 JD 常见要素（如"职责""要求""任职""资格"等关键词）
- **THEN** 系统 SHALL 检测到内容可能不是 JD
- **AND** 系统 SHALL 提示"未识别到典型 JD 结构，请确认粘贴的是职位描述"
- **AND** 系统 SHALL 允许用户继续或重新粘贴

---

### Requirement: JD 结构化解析

系统 SHALL 调用 LLM 将 JD 文本解析为结构化的"要求画像"（job_profile），并按四类要求分类。

#### Scenario: 四类要求分类
- **WHEN** 系统解析一份 JD
- **THEN** 系统 SHALL 将提取的要求划分为以下四类：
  - **硬技能**：明确要求的技能、工具、年限、资质（如"熟练 Python""3 年以上经验""本科及以上"）
  - **软技能**：沟通、领导力、抗压等能力要求
  - **隐性偏好**：JD 未明说但有暗示的倾向（如"大厂背景优先""创业经历加分"）
  - **红线项**：硬性门槛（如"必须 985/211""接受出差""薪资面议"前提条件）

#### Scenario: 要求依据保留
- **WHEN** 系统提取出一条要求
- **THEN** 系统 SHALL 同时保留该要求在 JD 原文中的出处片段
- **AND** 系统 SHALL 为每条要求计算解析置信度（0.0-1.0）

#### Scenario: 区分必须项与加分项
- **WHEN** JD 中某条要求带有"必须""要求""任职资格"等强约束措辞
- **THEN** 系统 SHALL 将其标记为"必须项"（must_have）
- **WHEN** JD 中某条要求带有"优先""加分""nice to have"等措辞
- **THEN** 系统 SHALL 将其标记为"加分项"

#### Scenario: JD 解析输出约束
- **WHEN** 系统 LLM 解析 JD
- **THEN** 系统 SHALL 使用结构化输出约束（JSON Schema）保证格式稳定
- **AND** 当 LLM 输出不符合格式时，系统 SHALL 重试一次

---

### Requirement: 画像就绪性检查

系统 SHALL 在执行匹配前检查当前用户是否已有可用画像，画像缺失时引导用户先建立画像。

#### Scenario: 画像已就绪
- **WHEN** 用户发起 JD 匹配且已存在已保存的个人画像
- **THEN** 系统 SHALL 加载该画像
- **AND** 系统 SHALL 继续执行匹配流程

#### Scenario: 画像缺失
- **WHEN** 用户发起 JD 匹配但未建立画像
- **THEN** 系统 SHALL 中止匹配流程
- **AND** 系统 SHALL 返回明确的引导："请先建立个人画像后再进行 JD 匹配"
- **AND** 系统 SHALL 提供跳转到"建立画像"的入口

#### Scenario: 画像完整度不足
- **WHEN** 用户画像的关键字段（技能、工作经历）为空或置信度过低
- **THEN** 系统 SHALL 提示"画像信息不完整，匹配结果可能不准确"
- **AND** 系统 SHALL 允许用户补充画像后重试
- **AND** 系统 SHALL 在结果中标注受低置信度画像影响的得分项

---

### Requirement: 匹配度计算

系统 SHALL 采用混合式算法计算画像与 JD 的匹配度：对结构化要求做程序化逐项比对，对隐性要求用 LLM 做综合判断，最后加权汇总。

#### Scenario: 分维度评分
- **WHEN** 系统计算匹配度
- **THEN** 系统 SHALL 输出四个维度的独立得分（0-100）：
  - **技能匹配度**（硬技能要求的满足比例）
  - **经验匹配度**（工作年限、行业、项目相关度）
  - **学历匹配度**（学校层次、专业、学位是否满足）
  - **软技能匹配度**（软技能要求的覆盖情况）

#### Scenario: 总分加权汇总
- **WHEN** 四个维度得分计算完成
- **THEN** 系统 SHALL 按预设权重加权汇总为总分（0-100）
- **AND** 红线项未满足时，系统 SHALL 对总分施加惩罚（红线为硬性门槛）

#### Scenario: 硬技能程序化比对
- **WHEN** 比对一条硬技能要求（如"熟练 Python"）
- **THEN** 系统 SHALL 在画像技能集中做匹配（含同义词、近义词归一）
- **AND** 系统 SHALL 输出"满足 / 部分满足 / 未满足"及匹配到的画像依据

#### Scenario: 隐性偏好 LLM 判断
- **WHEN** 比对一条隐性偏好（如"大厂背景优先"）
- **THEN** 系统 SHALL 调用 LLM 结合画像上下文做综合判断
- **AND** 系统 SHALL 输出该偏好的满足程度及判断理由

#### Scenario: 总分归一与等级
- **WHEN** 总分计算完成
- **THEN** 系统 SHALL 映射为匹配等级（如 ≥75 高度匹配 / 50-74 部分匹配 / <50 匹配度较低）

---

### Requirement: 匹配可解释性

系统 SHALL 为每个得分点提供可追溯的依据，使匹配结果可信、可解释。

#### Scenario: 得分点依据
- **WHEN** 系统输出某条要求的匹配结果
- **THEN** 系统 SHALL 同时给出 JD 原文出处与画像对应内容
- **AND** 系统 SHALL 说明该结果是"满足 / 部分满足 / 未满足"及判定理由

#### Scenario: 低置信度标注
- **WHEN** 某得分项依赖的画像字段置信度低于阈值
- **THEN** 系统 SHALL 标注该得分项为"待确认"
- **AND** 系统 SHALL 提示用户校验对应画像字段

#### Scenario: 红线项显式提示
- **WHEN** 存在未满足的红线项
- **THEN** 系统 SHALL 在报告中显眼位置单独列出
- **AND** 系统 SHALL 说明该红线项对录用可能性的影响

---

### Requirement: 差距分析（Gap 清单）

系统 SHALL 基于匹配结果生成结构化的差距清单（Gap），并按类型分类、附应对建议，作为简历优化模块的输入。

#### Scenario: Gap 四分类
- **WHEN** 系统生成 Gap 清单
- **THEN** 系统 SHALL 将每个 Gap 归入以下四类之一：
  - **硬技能差距**：缺少 JD 要求的硬技能或年限不足
  - **软技能表述弱**：画像具备该能力但描述空泛、缺数据化支撑
  - **隐性偏好缺位**：未体现 JD 暗示的偏好背景
  - **红线预警**：触及学历、年龄、资质等硬性门槛

#### Scenario: Gap 应对建议
- **WHEN** 系统输出一个 Gap
- **THEN** 系统 SHALL 附带可执行的应对建议（如"用 STAR 法则补充 XX 项目""挖掘可类比的高质量经历对冲"）
- **AND** 软技能类 Gap 的建议 SHALL 指向简历表述强化

#### Scenario: Gap 严重度排序
- **WHEN** 系统输出多个 Gap
- **THEN** 系统 SHALL 按严重度（红线 > 硬技能 > 隐性 > 软技能）排序
- **AND** 系统 SHALL 标注每个 Gap 的严重度等级

#### Scenario: 闭环接口契约
- **WHEN** 匹配流程结束
- **THEN** Gap 清单的结构 SHALL 可被简历优化模块直接消费
- **AND** 每个 Gap SHALL 包含足够字段（类型、要求、现状、建议、严重度）支撑后续改写

---

### Requirement: Gap 增补（lazy 加载）

系统 SHALL 将 Gap 的 LLM 增补内容（隐性偏好判断结果与应对建议）从主匹配流程中剥离，通过独立端点 lazy 加载，使用户能先拿到分数。

#### Scenario: 主请求返回 Gap 骨架
- **WHEN** 评分链（JD 解析 + 规则匹配）完成
- **THEN** 主请求 SHALL 返回规则可定的 Gap 骨架（硬技能 / 软技能 / 红线类，含现状与严重度）
- **AND** 隐性偏好类 Gap SHALL 以"分析中"占位，待增补回填

#### Scenario: 增补端点
- **WHEN** 前端以 result_id 调用 `POST /api/jd/{id}/enrich`
- **THEN** 系统 SHALL 并行执行隐性偏好判断与 Gap 建议生成（两段 LLM）
- **AND** 系统 SHALL 将结果 UPDATE 回同一条匹配记录
- **AND** 响应 SHALL 返回增补后的完整 Gap 清单

#### Scenario: 分数独立性
- **WHEN** 增补链的 LLM 调用失败或未完成
- **THEN** 总分与四维度得分 SHALL 仍然可用
- **AND** 总分 SHALL 仅依赖 JD 解析与规则匹配（技能 / 经验 / 学历 / 软技能 + 红线惩罚），不依赖隐性偏好判断与 Gap 建议

---

### Requirement: 匹配结果持久化

系统 SHALL 将每次 JD 匹配的结果持久化存储，支持用户回看历史匹配。

#### Scenario: 保存匹配结果
- **WHEN** 一次 JD 匹配完成
- **THEN** 系统 SHALL 将结果写入匹配结果存储
- **AND** 系统 SHALL 保留原始 JD 文本、解析出的要求画像、总分、分维度得分、Gap 清单与置信度

#### Scenario: 查询历史匹配
- **WHEN** 用户请求查看历史匹配记录
- **THEN** 系统 SHALL 按用户维度返回历史匹配列表
- **AND** 系统 SHALL 按时间倒序排列

#### Scenario: 结果可复算
- **WHEN** 用户回看某次历史匹配
- **THEN** 系统 SHALL 能展示该次的原始 JD、要求画像与 Gap 依据
- **AND** 系统 SHALL 不依赖外部状态即可还原分析过程

#### Scenario: 持久化时机（前移，支撑流式）
- **WHEN** 匹配计算完成、分数已得出
- **THEN** 系统 SHALL 立即将分数与规则 Gap 骨架写入匹配记录并生成 result_id
- **AND** result_id SHALL 在分数 SSE 事件中下发（供前端调用增补端点）
- **AND** 增补端点完成后 SHALL UPDATE 同一行（回填隐性判断与 Gap 建议）

---

### Requirement: 匹配报告输出

系统 SHALL 输出结构化的匹配报告供前端展示。

#### Scenario: 报告内容完整性
- **WHEN** 系统生成匹配报告
- **THEN** 报告 SHALL 包含：总分、匹配等级、四个维度得分、Gap 清单、红线项提示、各项依据与置信度

#### Scenario: 报告可读性
- **WHEN** 报告展示给用户
- **THEN** 系统 SHALL 以分维度形式呈现得分（支持雷达图等可视化数据）
- **AND** 系统 SHALL 将 Gap 清单分组展示并附建议

---

### Requirement: 流式匹配输出（SSE 阶段推送）

系统 SHALL 以 SSE（Server-Sent Events）流式输出 JD 匹配的阶段进度与结果，取代一次性同步返回，消除长请求超时。

#### Scenario: 阶段进度实时推送
- **WHEN** 匹配流程在节点间推进
- **THEN** 系统 SHALL 在每个节点完成后下发 SSE 事件（如 `event: stage`，携带阶段名与提示文案）
- **AND** 阶段 SHALL 覆盖：接收 JD / 质量检查 / 解析 JD / 加载画像 / 匹配计算

#### Scenario: 分数优先可见
- **WHEN** 匹配计算（match_calc）节点完成
- **THEN** 系统 SHALL 立即下发分数事件（总分 / 四维度 / level / result_id）
- **AND** 该下发 SHALL 早于 Gap 增补（隐性判断与建议）完成

#### Scenario: 连接保活
- **WHEN** 单个节点耗时较长（LLM 调用慢或重试）
- **THEN** 系统 SHALL 通过持续下发事件保持连接活跃
- **AND** 系统 SHALL 不因整体耗时触发客户端超时（取代原同步方案的 90 秒超时墙）

#### Scenario: 流式错误事件
- **WHEN** 流式过程中某节点失败（JD 无效 / 画像缺失 / LLM 失败）
- **THEN** 系统 SHALL 下发 `event: error`（携带 error_code 与友好文案）
- **AND** 系统 SHALL 随后正常关闭流

#### Scenario: 异步不阻塞
- **WHEN** 一个用户正在进行 JD 匹配
- **THEN** 系统 SHALL 不阻塞其他请求的处理（端点 SHALL 使用异步流式执行，不得在 async 端点中同步阻塞事件循环）

---

### Requirement: 错误处理与降级

系统 SHALL 在匹配各环节失败时提供友好的错误处理与降级方案。

#### Scenario: LLM 解析或判断失败
- **WHEN** JD 解析或隐性判断的 LLM 调用失败（API 错误、超时、格式异常）
- **THEN** 系统 SHALL 按指数退避重试
- **AND** 重试耗尽后 SHALL 返回友好错误并保留用户已输入的 JD

#### Scenario: JD 质量过低
- **WHEN** JD 文本质量分过低（结构混乱、信息过少）
- **THEN** 系统 SHALL 提示"JD 内容不完整，分析结果仅供参考"
- **AND** 系统 SHALL 允许用户补充 JD 后重新分析

#### Scenario: 画像与 JD 均就绪但匹配异常
- **WHEN** 匹配计算过程中出现未预期异常
- **THEN** 系统 SHALL 捕获异常并返回统一错误响应
- **AND** 系统 SHALL 不向用户暴露技术细节

---

### Requirement: API 响应格式

系统 SHALL 对 JD 匹配的 match 端点返回 SSE 事件流，对 Gap 增补端点返回统一 JSON。

#### Scenario: match 端点 SSE 事件流
- **WHEN** 前端 POST `/api/jd/match`
- **THEN** 响应 SHALL 为 `text/event-stream`，由以下事件组成：
  - `event: stage` — 阶段进度（阶段名 + 提示文案）
  - `event: score` — 分数（overall_score / dimension_scores / level / result_id）
  - `event: done` — 主链结束（携带规则 Gap 骨架与 job_profile）
  - `event: error` — 失败（error_code + error_message）

#### Scenario: enrich 端点 JSON 响应
- **WHEN** 前端 POST `/api/jd/{id}/enrich` 成功
- **THEN** 响应 SHALL 为 JSON，包含：
  - `status`: "success"
  - `gaps`: 增补后的完整 Gap 清单（含隐性判断结果与应对建议）

#### Scenario: 错误响应
- **WHEN** JD 匹配失败（画像缺失、JD 无效、LLM 失败）
- **THEN** 系统 SHALL 通过 `event: error` 下发
- **AND** 事件 SHALL 携带 `error_code`（如 `PROFILE_MISSING`、`JD_INVALID`、`LLM_FAILED`）与用户友好的 `error_message`

---

## MODIFIED Requirements

（此能力为新增，不修改已有 Requirements）

---

## REMOVED Requirements

（此变更不删除任何 Requirements）

---

## 数据结构定义

### job_profile（要求画像）

```json
{
  "hard_skills": [
    {
      "requirement": "熟练 Python",
      "must_have": true,
      "evidence": "JD 原文片段",
      "confidence": 0.95
    }
  ],
  "soft_skills": [
    { "requirement": "跨团队沟通能力", "must_have": false, "evidence": "...", "confidence": 0.8 }
  ],
  "implicit_preferences": [
    { "requirement": "大厂背景优先", "evidence": "...", "confidence": 0.6 }
  ],
  "red_lines": [
    { "requirement": "本科 985/211", "evidence": "...", "confidence": 0.9 }
  ]
}
```

### match_result（匹配结果）

```json
{
  "overall_score": 75,
  "level": "高度匹配",
  "dimension_scores": {
    "skill": 80,
    "experience": 70,
    "education": 65,
    "soft_skill": 85
  },
  "matched_items": [
    {
      "requirement": "熟练 Python",
      "status": "satisfied",
      "jd_evidence": "...",
      "profile_evidence": "画像中的技能项",
      "confidence": 0.95
    }
  ]
}
```

### gap（差距项）

```json
{
  "type": "hard_skill | soft_skill | implicit | redline",
  "requirement": "数据分析经验",
  "current_state": "画像中无相关项目",
  "suggestion": "用 STAR 法则补充 XX 项目，强调量化成果",
  "severity": "high | medium | low"
}
```

---

## 边界条件

### 输入边界
- JD 文本长度：200 - 20000 字符（超出截断或提示）
- JD 文本编码：UTF-8

### 输出边界
- 各项得分范围：0 - 100
- 置信度范围：0.0 - 1.0
- Gap 数量：按严重度排序，默认返回全部

### 性能边界
- JD 结构化解析：< 10 秒
- 评分链（JD 解析 + 规则四维度 + 红线，不含隐性判断/Gap 建议）：< 30 秒（目标约 10 秒；SSE 流式中分数优先可见）
- 增补链（隐性偏好判断 + Gap 建议生成，lazy 端点、两段 LLM 并行）：另约 20-30 秒（不阻塞，用户已见分数）
