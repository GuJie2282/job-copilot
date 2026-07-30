# Tasks: 面试官人设贯穿出题 + 去反问

## 1. 出题吃 persona
- [ ] 1.1 `generate_question_bank` 加 `persona` 参数
- [ ] 1.2 `get_question_generation_prompt` 加 persona 段（tone/role/stress → stem 口吻指引：压力/轻松/严肃）
- [ ] 1.3 `session_setup_node` 传 `state["persona"]` 给 `generate_question_bank`

## 2. 去反问（彻底删）
- [ ] 2.1 `INTENSITY_CONFIG` 的 `has_qa_session` 全 False
- [ ] 2.2 评估 prompt 的 action 选项移除 `enter_qa`（只留 probe/next/end）
- [ ] 2.3 `_VALID_ACTIONS` 减 `enter_qa`；`_decide`/`_apply_guardrails` 移除 enter_qa 分支
- [ ] 2.4 `_after_questions` 简化为题库问完直接 end
- [ ] 2.5 `interviewer_node` 删 enter_qa 分支

## 3. 确诊类型
- [ ] 3.1 查 1-2 场实际面试题库 `category` 分布，确认 interview_type 是否生效；若不生效则强化出题 prompt 类型约束

## 4. 验证
- [ ] 4.1 选「压力面」跑一场，确认**新题**带压迫口吻（非只在追问）
- [ ] 4.2 确认不再进入反问环节（题库问完直接结束/复盘）
- [ ] 4.3 `test_pacing.py` 适配（移除 enter_qa 相关用例）
