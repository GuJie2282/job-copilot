# Tasks: 面试节奏自主决策

## 1. 评估 Prompt 增加节奏决策输出
- [x] 1.1 `get_evaluation_prompt` 输出 JSON 增 `action`（probe | next | enter_qa | end）与 `action_reason`（一句自然语言理由）字段
- [x] 1.2 Prompt 补充节奏决策指引：像真人面试官，依据回答充分度 / 疑虑 / 亮点 / 整场判断自主选择动作；给出每个 action 的选择准则
- [x] 1.3 追问措辞 `next_probe_followup` 语义扩展：可基于临场方向，不限于缺失信号对应的可挖掘点

## 2. 评估函数解析决策
- [x] 2.1 `_llm_evaluate` 返回 dict 增 `action` 与 `action_reason`；含合法性校验（非法 / 缺失 → action 为 None，触发降级）
- [x] 2.2 评估 LLM 整体失败降级：action 取 None，交由规则 fallback

## 3. 节奏决策改写 + 护栏
- [x] 3.1 `_decide` 改为：优先读 LLM action，经护栏校验后采用
- [x] 3.2 将原计数器规则重构为 `_rule_decide_fallback` 保留（降级与紧急回滚用）
- [x] 3.3 实现护栏：最低总轮数（2）、单题追问上限（5）、反问至多 1 次、最高总轮数上限（题库量 ×(1+5)）
- [x] 3.4 护栏越界纠正：开场 end→继续；单题超 5→换题；反问已过→换题/结束；超总上限→结束
- [x] 3.5 action 为 None / 非法时回退 `_rule_decide_fallback`

## 4. transcript 与解释性
- [x] 4.1 evaluator 的 transcript entry 增 `decision_reason`（取自 `action_reason`）
- [x] 4.2 interviewer probe 分支：`next_probe_followup` 已含临场追问措辞；保留模板降级兜底（评估漏产时）

## 5. 复盘纳入决策理由
- [x] 5.1 `get_debrief_prompt` 输入纳入每轮 `decision_reason`（+ action）
- [x] 5.2 复盘逐题回顾呈现节奏理由（"这轮为何追问 / 换题 / 结束"），保证可读通顺

## 6. 测试
- [x] 6.1 `_decide` 单测：LLM action 采纳路径 + 规则 fallback 路径分组断言（test_pacing.py 20 例全过）
- [x] 6.2 护栏单测：开场 end、连追越界、反问重复、超总上限——断言纠正到合法动作（test_pacing.py）
- [x] 6.3 `test_followup_quality.py` 调用处适配（`_llm_evaluate` 签名、新增 action 字段；护栏上限 3→5）
- [x] 6.4 e2e 断言策略调整：验证面试在 [最低, 最高] 轮数内正常结束 + transcript 完整 + 复盘生成，不断言精确路径

## 7. 验证
- [ ] 7.1 重启后端，e2e 账号跑一场 short 面试，观察节奏自主性（是否提前结束 / 连追 / 临场追问）
- [ ] 7.2 降级验证：模拟评估超时，确认回退规则、面试不中断
- [ ] 7.3 复盘可读性：确认 `decision_reason` 在复盘中可见且通顺
