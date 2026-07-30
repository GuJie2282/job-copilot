# Proposal: 面试官人设贯穿出题 + 去反问（evolve-interview-persona）

## Why

用户反馈"面试官风格没生效"。根因（已确诊）：
- `session_setup` 调 `generate_question_bank` **不传 persona**（[mock_interview.py:100](../../../backend/src/graph/nodes/mock_interview.py#L100)）；
- 出题 prompt `get_question_generation_prompt` **无 persona 参数**；
- 新题提问直用 `pkg["stem"]` 原文，**无人设口吻包装**（[interviewer_node:193](../../../backend/src/graph/nodes/mock_interview.py#L193)）。

结果：persona 只在 evaluator 的追问措辞（next_probe_followup）生效，**新题永远是通用口吻** → 用户选了"压力面"但题目语气平淡，感觉风格没生效。

同时用户要求**去除反问环节**（当前 `has_qa_session` 在 normal/deep/full 档为 True）。

## What Changes

- **出题吃 persona**：`generate_question_bank` + `get_question_generation_prompt` 接收 persona，stem 按人设口吻生成（压力面带质疑压迫 / 轻松面口语亲切 / 严肃面专业克制）；`session_setup` 传 `state["persona"]` 给出题。
- **去反问**（彻底删，非默认关）：`INTENSITY_CONFIG.has_qa_session` 全 False；评估 prompt 的 action 移除 `enter_qa`；`_VALID_ACTIONS`/`_decide`/`_apply_guardrails`/`interviewer_node` 移除 enter_qa 路径。
- **顺带确诊「类型没生效」**：链路是通的（出题带 interview_type），疑似 `full` 档混合题型造成"没对准"的感觉——查 1-2 场实际题库 `category` 分布定夺。

## Capabilities

- `mock-interview`（MODIFIED）：面试官人设贯穿出题口吻；去除反问环节。

## Impact

- **改动**：`question_generator.py`（generate_question_bank + get_question_generation_prompt 接 persona）、`mock_interview.py`（session_setup 传 persona；_decide/_apply_guardrails/interviewer 去 enter_qa）、`prompts.py`（出题 prompt 加人设段 + 评估 prompt 去 enter_qa）。
- **不动**：评估/决策/护栏核心（evolve）、异步开局、interrupt/checkpointer。
- **风险**：出题 prompt 增 persona 段略增输入，但出题本就 strong 档，影响小。
