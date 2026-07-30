# Design: 面试官人设贯穿出题 + 去反问

## 背景

persona 当前只在 evaluator 的 next_probe_followup 生效（追问措辞）。出题（generate_question_bank）不知道人设，新题 stem 通用口吻。用户选"压力面"但题目语气平淡。

## 决策

### 决策 1：出题吃 persona，stem 按人设口吻生成

- `generate_question_bank` 加 `persona` 参数；`session_setup` 传 `state["persona"]`。
- `get_question_generation_prompt` 加 persona 段：tone/role/stress → 指引 stem 口吻：
  - 压力面（stress）：题目带质疑、施压、追问到底的语气
  - 轻松面：口语、亲切、像聊天
  - 严肃面：专业、克制、直切要点
- 出题时即生成人设化 stem，interviewer 直接用（无需二次包装）。

**理由**：人设应在"考生第一眼看到的题目"就生效，而非只在追问。压力面出题就该有压迫感。这也避免了之前"风格只在追问可见"的割裂。

### 决策 2：去反问（彻底删）

- `INTENSITY_CONFIG.has_qa_session` 全 False。
- 评估 prompt 的 action 选项移除 `enter_qa`（只留 probe/next/end）。
- `_VALID_ACTIONS` 减 `enter_qa`；`_decide`/`_apply_guardrails` 移除 enter_qa 分支；`interviewer_node` 删 enter_qa 分支。
- `_after_questions` 简化：题库问完直接 end（不再 enter_qa）。

**理由**：用户明确去反问。彻底删（不只默认关）最干净，少一份分支复杂度。

### 决策 3：顺带确诊「类型没生效」

- interview_type 链路是通的（前端→createSession→session_setup→generate_question_bank→出题 prompt）。用户感觉"没生效"可能因 `full` 档混合各题型，或出题 LLM 偶尔偏离。
- 在本 change 内查 1-2 场实际题库的 `category` 分布：
  - 若 category 与所选类型一致 → 是感觉问题（UI 提示即可）
  - 若偏离 → 出题 prompt 强化类型约束

## 不做

- 不改评估/决策/护栏核心（evolve 已定，本次只动 enter_qa 相关分支）。
- 不预生成追问（用户已否决——追问措辞依赖回答，不能提前）。
- 不动异步开局。
