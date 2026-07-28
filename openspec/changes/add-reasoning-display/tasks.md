# Tasks: AI 思考过程展示（reasoning）

## 任务概览

建立在 add-streaming-pipeline 的流式通道上，为三模块（简历优化 / 简历解析 / JD 匹配）接入 AI 思考过程（reasoning）展示。

分四区块：**区块一（公共 reasoning 层）** 奠基；**区块二（简历优化，去打字机改思考）**；**区块三（简历解析 + JD 匹配）**；**区块四（测试打磨）**。

**依赖**：add-streaming-pipeline 的 SSE 基础（sse 工具 / openSseStream / StreamingResponse）。
**模型**：接 reasoning 的 LLM 调用 glm-4-flash → glm-4.5（strong，唯一支持 reasoning）。
**预计工时**：5-6 天

---

## 区块一：公共 reasoning 层

### Phase 1: reasoning stream 服务 + SSE 事件（Day 1）

#### 1.1 后端 reasoning stream 服务
- [x] 1.1.1 创建 `backend/src/services/llm_reasoning.py`：`stream_chat_with_reasoning(prompt, model="glm-4.5", temperature, timeout)` async generator，用 `AsyncOpenAI` 直调智谱兼容接口，读 `delta.reasoning_content` + `delta.content`，yield `("reasoning"|"content", delta)`
- [ ] 1.1.2 重试与降级：stream 失败降级为纯 content（不发 reasoning，不阻断业务）；参考既有 llm_retry 的可重试判定
- [ ] 1.1.3 验证：spike 脚本确认 reasoning + content 都能 stream 拿到（复用 test_reasoning_openai_spike.py 范式）

#### 1.2 SSE reasoning 事件
- [ ] 1.2.1 `src/core/sse.py` 加 `REASONING = "reasoning"` 常量
- [ ] 1.2.2 前端 `src/utils/sse.ts` 的 `SseHandlers` 加 `onReasoning?: (p: { delta: string }) => void`；`dispatch` 加 `case 'reasoning'`

---

## 区块二：简历优化（去 content 打字机，改 reasoning）

### Phase 2: generate 接 reasoning（Day 2）

#### 2.1 后端
- [ ] 2.1.1 `resume_generator.py` 新增 `generate_resume_reasoning_stream(profile, gaps, target_position, jd_text)`，内部调 `stream_chat_with_reasoning`（glm-4.5），yield `("reasoning"|"content", delta)`；复用 `get_resume_generation_prompt`
- [ ] 2.1.2 `resume_generate_node` 改用 `generate_resume_reasoning_stream`，`writer` 推两类 custom event：`{"type":"reasoning","delta":...}` 与 `{"type":"token","delta":...}`
- [ ] 2.1.3 generate 端点 astream custom 解包：`type==reasoning` → SSE `reasoning`；`type==token` → SSE `token`（content，但前端不再逐字渲染）

#### 2.2 前端：去打字机 + reasoning 区
- [x] 2.2.1 `ResumeOptimizer.vue` 移除 `streamingMd` ref 与 content 打字机区（onToken 回调移除/置空）
- [ ] 2.2.2 加 `reasoningText` ref + `onReasoning`（追加）；新增"AI 思考中"区（灰色 / 斜体 / 可折叠 details）
- [ ] 2.2.3 简历最终由 `onDone` 一次性渲染（content_md，既有 result 区）
- [x] 2.2.4 验证：generate 时展示 AI 思考（逐字）+ 简历最终一次性出（import + vue-tsc 通过；端到端待重启）

---

## 区块三：简历解析 + JD 匹配

### Phase 3: 简历解析分段提取接 reasoning（Day 3）

#### 3.1 后端
- [ ] 3.1.1 `profile_extractor._extract_one_section` 改用 `stream_chat_with_reasoning`（glm-4.5），yield reasoning + content；段内 reasoning 供端点下发
- [x] 3.1.2 `parse-stream` 端点：每段提取期间发 SSE `reasoning`（思考），段完成发 SSE `segment`（结果）—— 改 parse-stream event_stream 直接用 stream_chat_with_reasoning
- [ ] 3.1.3 档位 fast → strong（接受慢，靠 reasoning 持续输出保活）

#### 3.2 前端
- [x] 3.2.1 `ResumeParser.vue` 加 reasoningText + onReasoning + "AI 思考中"区（与画像逐段成型并存）

### Phase 4: JD 匹配接 reasoning（Day 4）

#### 4.1 后端
- [x] 4.1.1 JD 结构化解析（`jd_parsing` 节点）改 async + `stream_chat_with_reasoning`（glm-4.5），writer 推 reasoning
- [x] 4.1.2 `match` 端点：astream 多模式（updates+custom），JD 解析 reasoning → SSE reasoning
- [ ] 4.1.3 （可选）增补阶段 `judge_implicit` / `_generate_suggestions` 接 reasoning

#### 4.2 前端
- [x] 4.2.1 `JdMatcher.vue` 加 reasoningText + onReasoning + "AI 思考中"区

---

## 区块四：测试打磨（Day 5）

#### 5.1 多场景验证
- [ ] 5.1.1 三模块 reasoning 展示端到端（思考逐字 + 业务结果）
- [ ] 5.1.2 reasoning 区可折叠（冗长思考可收起）
- [ ] 5.1.3 降级：reasoning 拿不到时退化为纯 content 流式（业务不阻断）
- [ ] 5.1.4 保活：strong + reasoning 长耗时下连接不超时（reasoning 持续输出）

---

## 实施顺序

1. 区块一（公共层）先行
2. 区块二（简历优化，最直观，用户最关注去打字机）
3. 区块三（简历解析 + JD 匹配）
4. 区块四（测试）

> 注意：本变更把 add-streaming-pipeline 里改 fast 的环节（简历解析分段）再改回 strong（接 reasoning）。以本变更为准——用户接受 strong 慢，靠 reasoning 持续输出保活 + 补偿体验。
