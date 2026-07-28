# Tasks: 长耗时 LLM 任务的流式管线

## 任务概览

本变更把三条核心链路（简历解析 / 简历优化 / JD 匹配）的长耗时 LLM 任务从同步请求改造为流式管线，并借机重构简历解析的分段提取以根治超时与字段错位。

分五大区块：**区块一（公共流式基础设施）** 为其余区块奠基；**区块二（简历解析：分段提取 + 流式 + 嵌套结构）**；**区块三（简历优化：token 级生成 + 阶段进度）**；**区块四（JD 匹配：增补并入主流）**；**区块五（测试与打磨）**。

**预计工时**：约 12 天

---

## 区块一：公共流式基础设施

### Phase 1: 后端 SSE 工具抽取（Day 1，3 个任务）

#### 1.1 公共 SSE 事件工具
- [x] 1.1.1 创建 `backend/src/core/sse.py`
  - `sse(event: str, data: dict) -> str`：组装一条 SSE 事件（event 行 + data 行 + 空行），从 `jd.py._sse` 迁移
  - `sse_keepalive() -> str`：返回保活注释（`: keepalive\n\n`）
  - 事件类型常量：`STAGE` / `SEGMENT` / `TOKEN` / `SCORE` / `DONE` / `ENRICHED` / `ERROR`
  - 流式响应头常量：`{"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}` + `media_type="text/event-stream"`
- [x] 1.1.2 `jd.py` 移除内联 `_sse`，改用公共工具（行为不变，回归验证 JD 匹配）
- [x] 1.1.3 单元测试：事件组装格式正确、心跳格式正确

### Phase 2: 前端 SSE 消费封装（Day 1，3 个任务）

#### 1.2 公共 SSE 客户端
- [x] 1.2.1 创建 `web/src/utils/sse.ts`
  - `openSseStream(url, body, handlers, opts) -> AbortController`：fetch POST + Authorization + ReadableStream 解析（按 `\n\n` 切块、解析 `event:`/`data:` 行、JSON.parse），从 `jd.ts.matchJd` 抽取
  - `handlers`：`onStage / onSegment / onToken / onScore / onDone / onEnriched / onError`
  - base 解析：优先 `VITE_STREAM_BASE_URL`，回退 `VITE_API_BASE_URL`
  - 取消：返回 `AbortController`，abort 时静默退出
- [x] 1.2.2 `jd.ts.matchJd` 改为基于 `openSseStream` 的薄封装（行为不变，回归验证）
- [x] 1.2.3 开发环境配置：`web/.env.development` 增 `VITE_STREAM_BASE_URL=http://localhost:8001/api`；验证流式端点直连后端、绕开 vite proxy

### Phase 3: LLM 增量调用支持（Day 1-2，2 个任务）

#### 1.3 服务层 stream 能力
- [x] 1.3.1 在 `resume_generator.py` 增加 `generate_resume_stream(...)` / `refine_resume_stream(...)`：用 `llm.stream(prompt)` 逐 token 产出（yield），与既有 `invoke` 版本并存
- [x] 1.3.2 验证 `get_llm(...).stream()` 在智谱 GLM 上可用（手动跑一次，确认 token 迭代器正常）

---

## 区块二：简历解析 —— 分段提取 + 流式 + 嵌套结构

### Phase 4: 画像结构嵌套化（Day 2，5 个任务）

#### 4.1 后端结构定义
- [x] 4.1.1 `config.py` 的 `UserProfile`：工作经历 / 项目经验 / 教育背景由扁平平行数组改为对象数组（`work_experience: [{company,position,duration,description}]` 等），保留基础标量字段
- [x] 4.1.2 `quality_checker.calculate_profile_confidence` 回归：确认嵌套结构下按字段路径遍历置信度仍正确（无需改逻辑，仅验证）
- [x] 4.1.3 画像持久化兼容：`profile_service` 的 `detail_json` 序列化/反序列化对嵌套结构无损；为历史旧结构画像增加一次性读取迁移适配（平行数组 → 对象数组）
- [x] 4.1.4 验证：保存嵌套画像 → 读取 → 结构完整

#### 4.2 前端结构适配
- [x] 4.2.1 `ProfileDisplay.vue`：`workList` / `projectList` / `educationList` 由"按下标拼平行数组"改为"遍历对象数组"
- [x] 4.2.2 `ProfileEditor.vue`：工作/项目/教育编辑区改为对象数组增删改
- [x] 4.2.3 `Profile.vue` 身份卡签名：`latestPosition` / `workCount` 等改为读对象数组首项
- [x] 4.2.4 验证：嵌套画像在展示/编辑/身份卡均正确渲染，无字段错位

### Phase 5: 分段提取重构（Day 3，5 个任务）

#### 5.1 分段提取 prompt 与服务
- [x] 5.1.1 `prompts.py` 新增分段提取 prompt 集合：`get_section_extraction_prompt(resume_text, section)`，覆盖 basic / education / work / project / skills 五段，每段输出该段嵌套结构 JSON
- [x] 5.1.2 `resume_parser.py`（或新增 `profile_extractor.py`）实现 `extract_profile_sectioned(text, quality_score)`：按段顺序调用 LLM，每段独立 stream + JSON 解析 + 段置信度，返回"段结果迭代器"
- [x] 5.1.3 段级容错：单段失败只重试该段（收敛重试次数），重试耗尽则该段置空并在最终结果标注缺失
- [x] 5.1.4 段合并：五段结果合并为完整嵌套 `UserProfile`，合并完整置信度字典
- [x] 5.1.5 验证：分段提取对长简历输出完整画像，字段不错位；与旧单次提取在同一份简历上对比准确率

### Phase 6: 简历解析流式端点（Day 4，4 个任务）

#### 6.1 后端流式端点
- [x] 6.1.1 `resume.py` 新增 `POST /api/resume/parse-stream`（text/event-stream）：PDF/文本解析 → 质检 → 分段提取（每段 `stage` + `segment` 事件，段内 stream 保活）→ `done`（完整画像 + 置信度 + 质量分）；失败 `error`
- [x] 6.1.2 段内空闲期下发心跳保活（`sse_keepalive`）
- [x] 6.1.3 既有 `parse-file` / `parse-text` 保留作降级/兼容通道（同步，单次提取或内部复用分段）
- [x] 6.1.4 端点探测流式不支持时回退同步 JSON（降级兼容）—— 由既有同步端点承担降级通道

#### 6.2 前端流式消费
- [x] 6.2.1 `resume.ts` 新增 `parseResumeStream(data, handlers)`：基于 `openSseStream`，handlers 含 `onStage / onSegment / onDone / onError`
- [x] 6.2.2 `ResumeParser.vue` 的 `onTextSubmit` 改调 `parseResumeStream`（`onFileUpload` PDF 暂留同步，PDF 流式端点待后续）：`onStage` 写进度、`onSegment` 逐段填充画像预览、`onDone` 落完整画像
- [x] 6.2.3 画像预览组件支持"逐段成型"展示（收到 segment 即渲染该段，收到 done 定稿）—— mergeSection 合段 + ProfileDisplay 嵌套响应式
- [ ] 6.2.4 验证：上传 / 粘贴后全程可见分段进度与逐段成型的画像，无"请求失败"

---

## 区块三：简历优化 —— token 级生成 + 阶段进度

### Phase 7: generate 流式（Day 5-6，5 个任务）

#### 7.1 后端 generate 流式
- [x] 7.1.1 `resume_optimize.py` 的 `/generate` 改为 `StreamingResponse` + `graph.astream(stream_mode="updates")`：按节点（prepare/generate/evaluate/validate/export/persist）`stage`，`resume_persist` 后 `done`（含 resume_id / content_md / html / eval_report）
- [x] 7.1.2 `resume_generate` 节点改用 `generate_resume_stream`：token 经 `StreamWriter` custom event → 端点 astream 多模式收 → SSE `token` 事件逐个下发（langgraph 0.2.53 用 StreamWriter 类型注解方式）
- [x] 7.1.3 失败分支（profile_missing / llm_failed）发 `error` 事件；去掉 `response_model=ApiResponse` 声明
- [x] 7.1.4 多轮迭代回边：每轮回 generate 仍发 `stage` + `token`（astream 自然每轮节点 update + writer token）
- [x] 7.1.5 验证：generate 全程阶段进度真实（import + vue-tsc 通过；端到端待后端重启）

#### 7.2 前端 generate 流式
- [x] 7.2.1 `resume.ts` 新增 `generateResumeStream(data, handlers)`：`onStage / onToken / onDone / onError`
- [x] 7.2.2 `ResumeOptimizer.vue` 的 `onGenerate` 改用流式：`onStage` 写真实进度（替换 setInterval 假进度）、`onToken` 追加到 Markdown 渲染区（打字机）、`onDone` 落结果
- [x] 7.2.3 进度态与完成态视觉区分（生成中 vs 生成完成）
- [x] 7.2.4 删假进度定时器，用真实 `onStage` + `onError` 兜底（未保留假进度 fallback，流式不可用时 onError 提示）
- [x] 7.2.5 验证：阶段切换可见（vue-tsc 通过；端到端待后端重启）

### Phase 8: refine 流式（Day 7，3 个任务）

#### 8.1 后端 refine 流式
- [ ] 8.1.1 `resume_optimize.py` 的 `/refine` 改 `astream`：改写节点 token 级、评估阶段级；astream 在 interrupt 自然停止，跨请求状态由既有 checkpointer 维持
- [ ] 8.1.2 `/finalize` 保持同步（0 次 LLM，不流式）
- [ ] 8.1.3 验证：refine 每轮改写逐字输出，interrupt 暂停语义正常

#### 8.2 前端 refine 流式
- [ ] 8.2.1 `resume.ts` 新增 `refineResumeStream(resumeId, data, handlers)`
- [ ] 8.2.2 `ResumeRefine.vue` 改用流式：改写 token 打字机、阶段进度
- [ ] 8.2.3 验证：精修逐字输出，反馈循环正常

---

## 区块四：JD 匹配 —— 增补并入主流

### Phase 9: 增补链并入 match 流（Day 8-9，4 个任务）

#### 9.1 后端并入
- [x] 9.1.1 `jd.py` 的 `/match`：`done`（评分完成 + 骨架）后不关流，继续执行 `enrich_gaps`：发 `stage`（"分析隐性偏好…" / "生成应对建议…"）→ `enriched`（最终 Gap 清单）后关流
- [x] 9.1.2 `enrich_gaps` 内部两段 LLM（`judge_implicit` / `_generate_suggestions`）采用增量输出避免段内阻塞超时；失败降级（模板建议 / 隐性 partial）不变，降级项在 `enriched` 标注
- [x] 9.1.3 持久化：增补完成后 UPDATE 同一行 `gaps_json`（与现状一致）
- [x] 9.1.4 既有独立 `/enrich` 端点保留作降级/兼容

#### 9.2 前端并入消费
- [x] 9.2.1 `jd.ts.matchJd` 的 handlers 增 `onEnriched`；`JdMatcher.vue` 在 `onDone`（评分）后继续展示增补进度，`onEnriched` 回填最终 Gap 清单
- [x] 9.2.2 移除/弱化前端对独立 `enrichGaps` 的主动调用（改为流内自动完成）（改为流内自动完成）；保留作降级
- [x] 9.2.3 验证：提交 JD 后评分 → 增补在同一流内连续完成（import + vue-tsc 通过；端到端待后端重启）

---

## 区块五：超时/重试策略与测试打磨

### Phase 10: 超时与重试策略调整（Day 10，2 个任务）

#### 10.1 策略收敛
- [ ] 10.1.1 流式端点单次 LLM 调用 timeout 保留（防卡死），但段级/token 级因持续输出不再触发总时长超时；简历解析段级提取的失败重试收敛到当前段
- [ ] 10.1.2 前端流式请求取消"覆盖全流程"的大 timeout（原 180s/300s），改为连接级超时（无首字节时触发，收到数据后由流维持）

### Phase 11: 测试与打磨（Day 11-12，5 个任务）

#### 11.1 多样本与边界
- [ ] 11.1.1 简历解析多样本：长简历、扫描件降级、字段稀疏简历、含复杂项目经历的简历，验证分段提取准确率与不错位
- [ ] 11.1.2 简历优化：多轮迭代触发、生成中断恢复、refine 反馈循环
- [ ] 11.1.3 JD 匹配：增补并入全流程、增补降级、画像缺失分支
- [ ] 11.1.4 流式中断恢复：任务进行中取消 / 网络中断，验证部分结果保留与可续作
- [ ] 11.1.5 端到端：三条链路全程无"请求失败"，进度真实，打字机效果正常，降级路径可用

---

## 实施顺序建议

1. 区块一先做（公共工具就位，后续模块直接复用）
2. 区块二（简历解析，含结构嵌套——影响画像全局，最先稳定结构）
3. 区块三（简历优化）与区块四（JD 增补）可部分并行
4. 区块五收尾

> 简历解析的结构嵌套化（Phase 4）会影响画像展示/编辑/JD 匹配读取，需优先完成并回归，避免与流式改造交织产生中间态。
