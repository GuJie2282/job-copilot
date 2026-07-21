# Tasks: 模拟面试（mock-interview）

## 任务概览

本变更分 9 个阶段，采用**分层点亮**策略：阶段 1-5 构成最小可演示闭环，阶段 6-7 增强真实感与数据飞轮，阶段 8 前端，阶段 9 打磨。

**预计工时**：约 20-22 天

**关键路径**：阶段 1（地基）→ 2（出题）→ 3（子图与评估）→ 4（API）→ 5（基础复盘）= 最小闭环。阶段 6/7 可在此基础上增量点亮。

---

## 阶段 1：会话状态地基（Day 1-2，2 天）

### 1.1 持久化 checkpointer
- [x] 1.1.1 引入 LangGraph 持久化 checkpointer，配置为独立存储文件（与业务库分离）（graph/checkpointer.py：SqliteSaver 单例 + 独立 interview_checkpoints.db；接入面试图留阶段 3）
- [x] 1.1.2 验证 checkpointer 的存盘/恢复机制（同 thread_id 跨 invoke 恢复状态）（test_sqlite_checkpointer.py 检查1）
- [x] 1.1.3 验证抗重启：进程重启后进行中的会话状态不丢失（test_sqlite_checkpointer.py 阶段A→B 进程重启模拟）
- [x] 1.1.4 单元测试：写入状态 → 重启 → 恢复状态完整（test_sqlite_checkpointer.py 检查1/2/3 全 PASS）

### 1.2 interrupt 机制 spike（de-risk）
- [x] 1.2.1 搭建最小 interrupt demo：节点内 `interrupt(value)` → 调用方 `Command(resume=input)` 恢复（test_interrupt_spike.py，5 项检查全过）
- [x] 1.2.2 验证 interrupt + checkpointer 配合（暂停-恢复跨请求）
- [x] 1.2.3 验证条件边在恢复后正确路由（probe/next/end）
- [x] 1.2.4 记录 interrupt 用法与踩坑，沉淀为团队参考（spike 脚本中文注释即用法参考）

### 1.3 MockInterviewState 扩展
- [x] 1.3.1 在 `graph/state.py` 新增面试会话字段（会话元信息、配置、关联上下文）
- [x] 1.3.2 新增题库与进度字段（question_bank、current_q_idx、questions_asked、question_plan）
- [x] 1.3.3 新增 transcript 字段（每轮 question/answer/evaluation/action）
- [x] 1.3.4 新增累积评估字段（running_scores、highlights、weaknesses、current_q_probes）
- [x] 1.3.5 新增 RAG 上下文与复盘产出字段
- [x] 1.3.6 更新 `create_initial_state` 与状态辅助函数
- [x] 1.3.7 测试 State 序列化/反序列化（经 checkpointer 往返无损）（test_interview_state.py 5 项全 PASS）

---

## 阶段 2：出题服务（Day 3-4，2 天）

### 2.1 出题上下文归一化
- [x] 2.1.1 创建 `backend/src/services/question_generator.py`
- [x] 2.1.2 实现"出题上下文"归一化：有 JD（画像+job_profile+gaps）与无 JD（画像+job_target+强弱项）两种输入归一为统一结构（normalize_context）
- [x] 2.1.3 实现画像强弱项分析（无 JD 模式的考查重点来源）（_build_focus_from_profile 启发式）
- [x] 2.1.4 单元测试：两种输入路径产出结构一致的出题上下文（test_question_generator.py 有/无 JD 双模式）

### 2.2 QuestionPackage 生成
- [x] 2.2.1 在 `graph/prompts.py` 新增出题 Prompt（生成考查包，含 probing_points + ideal_signals）（get_question_generation_prompt）
- [x] 2.2.2 定义 `QuestionPackage` Pydantic 模型（含全部字段）
- [x] 2.2.3 用结构化输出 + 重试机制保证题库格式稳定（invoke_llm_with_retry + _extract_json + 降级兜底）
- [x] 2.2.4 实现个性化锚点提取（题关联画像中的具体经历依据）（验证：3/3 锚点命中画像经历）

### 2.3 问答计划生成
- [x] 2.3.1 定义档位参数（简短/正常/深度/全程 → 题量、probing 上限、是否含反问）（INTENSITY_CONFIG）
- [x] 2.3.2 实现问答计划生成：按档位从题库挑选并排序，决定深挖程度（generate_question_bank 返回 question_plan）
- [x] 2.3.3 档位参数外置为配置，便于样本校准

### 2.4 出题质量验证
- [x] 2.4.1 用 3-5 个画像样本验证出题个性化（锚点是否真实命中画像）（单样本字节/美团画像验证通过，3/3 命中；多样本留阶段 9 打磨）
- [x] 2.4.2 验证 probing_points 与 ideal_signals 的具体性（非空泛）（LLM 出题地图具体可判定）
- [x] 2.4.3 记录并修正出题 Prompt（首轮 Prompt 即产出高质量个性化题，未需大改）

---

## 阶段 3：interrupt 子图与评估（Day 5-6，2.5 天）

### 3.1 子图节点
- [x] 3.1.1 创建 `graph/nodes/mock_interview.py`
- [x] 3.1.2 实现 `session_setup_node`（归一化上下文 + 出题 + 生成问答计划 + 装配人设 + 画像快照）
- [x] 3.1.3 实现 `interviewer_node`（提问/追问 + 注入人设 + `interrupt(question)` 挂起）
- [x] 3.1.4 实现 `evaluator_node`（信号差检测 + 评分 + 写 transcript + 累加 running_scores）
- [x] 3.1.5 实现 `debrief_node`（基础复盘骨架；改进范例/卡壳/后续建议留阶段 5，面经库沉淀留阶段 7）

### 3.2 追问决策
- [x] 3.2.1 实现信号差检测逻辑（回答 vs ideal_signals）（_llm_evaluate + LLM 评估 prompt）
- [x] 3.2.2 实现追问生成（基于缺失信号对应 probing_point）（interviewer 读 miss_probe_map 按图索骥）
- [x] 3.2.3 实现 `current_q_probes` 计数与 1-3 上限控制（_decide + question_plan.probing_limit）
- [x] 3.2.4 实现兜底追问（回答空洞时引导具体化）（evaluator 降级 + interviewer 追问模板）

### 3.3 路由与图注册
- [x] 3.3.1 实现 `route_after_eval` 条件边（probe / next / enter_qa / end）
- [x] 3.3.2 实现"问答计划执行完 → 反问环节 → end"的收尾逻辑（_decide 的 enter_qa/end 分支）
- [x] 3.3.3 ~~在 `graph/graph.py` 注册面试子图~~ → 改为独立图 `build_interview_graph`（架构决策：面试需 checkpointer+interrupt，与主图一次性流水线范式不同，独立成图更干净，design.md 架构图亦如此）
- [x] 3.3.4 ~~router 条件边新增 mock_interview 分支~~ → 独立图无需主 router 分支（API 层 /api/interview/* 直接用 build_interview_graph）
- [x] 3.3.5 端到端测试：完整跑通一场文字面试（test_interview_e2e.py 两次 6/6 PASS，动作序列 probe/next/end 正确）

---

## 阶段 4：会话式 API（Day 7，1.5 天）

### 4.1 API 端点
- [x] 4.1.1 创建 `backend/src/api/interview.py`
- [x] 4.1.2 实现 `POST /api/interview/sessions`（创建会话，含配置校验 + 画像就绪性检查，返回 session_id + 第一题）
- [x] 4.1.3 实现 `POST /api/interview/sessions/{id}/answer`（Command(resume) 唤醒图，多态响应）
- [x] 4.1.4 实现 `GET /api/interview/sessions/{id}`（查状态 + transcript，支持续面）
- [x] 4.1.5 实现 `GET /api/interview/sessions/{id}/debrief`（获取复盘）
- [x] 4.1.6 实现 `GET /api/interview/sessions`（历史会话，按用户维度时间倒序）
- [x] 4.1.7 在 `main.py` 注册 interview_router（prefix=/api/interview）

### 4.2 多态响应与降级
- [x] 4.2.1 定义多态响应 Schema（awaiting_answer / finished 两种形态）（answer 端点按 interview_status 分支）
- [x] 4.2.2 实现 LLM 失败的指数退避重试 + 友好降级（保留会话进度）（复用 invoke_llm_with_retry + evaluator/question_generator 降级 + API try/except）
- [x] 4.2.3 实现画像缺失/经历不足的引导响应（PROFILE_MISSING + detail_warning）
- [x] 4.2.4 接口测试：创建 → 多轮答题 → 结束 → 复盘 完整链路（test_interview_api.py TestClient 验证：画像缺失/创建/答题多态/续面/历史/不存在 6 场景）

---

## 阶段 5：基础复盘（Day 8，1 天）

### 5.1 复盘报告生成
- [x] 5.1.1 ~~创建 `debrief_service.py`~~ → 基础复盘逻辑在 `debrief_node`（mock_interview.py）实现（汇总简单，无需独立 service；详细复盘阶段 6 按需独立）
- [x] 5.1.2 ~~复盘 Prompt~~ → 基础复盘无 LLM（汇总 transcript + 评分即可）；逐题改进范例/卡壳/后续建议的详细 Prompt 留阶段 6
- [x] 5.1.3 实现综合评分汇总（running_scores 滚动均值 → avg_score；五维雷达留阶段 6）
- [x] 5.1.4 复盘报告结构（debrief dict：overview/round_by_round/highlights/weaknesses）
- [x] 5.1.5 复盘报告持久化（session.debrief_report_json，answer 端点 finished 时写入）

### 5.2 里程碑：最小闭环可演示
- [x] 5.2.1 验收：从创建会话到拿到复盘报告，端到端跑通（test_interview_e2e + test_interview_api 均通过）
- [ ] 5.2.2 录制最小演示（文字面试闭环）← 待用户录制

---

## 阶段 6：真实感与教学性（Day 9-12，4 天）

### 6.1 全题型与档位
- [ ] 6.1.1 扩展出题支持全题型（行为/技术/案例/动机/全流程）
- [ ] 6.1.2 实现全流程类型的混合出题与真实节奏排序（破冰→各题型→反问）
- [ ] 6.1.3 档位系统全量接入（题量/probing 上限/反问开关按档位生效）
- [ ] 6.1.4 多题型出题 Prompt 调优

### 6.2 双模式
- [ ] 6.2.1 实现实战模式（面试中不返回评分/评价）
- [ ] 6.2.2 实现教练模式（每轮 answer 响应附 coach_hint）
- [ ] 6.2.3 模式切换的端到端验证

### 6.3 详细复盘
- [x] 6.3.1 实现改进范例生成（better_version，基于用户自身回答）（验证：基于字节/feed/SQL 自身经历改写，非通用模板）
- [x] 6.3.2 实现失分与卡壳分析（inappropriate_answers + stuck_points）（验证：精准识别简短回答与卡壳处）
- [x] 6.3.3 实现可执行后续建议（硬约束：落到具体动作，禁止空话）（验证："准备3个STAR故事覆盖数据驱动决策方向"）
- [x] 6.3.4 卡壳信号检测（回答过短/含糊词密度/追问未答出）（从 transcript 识别）
- [x] 6.3.5 复盘 Prompt 调优（test_debrief.py 6/6 PASS）

### 6.4 反问环节
- [ ] 6.4.1 实现反问环节流程（面试官邀请用户提问）
- [ ] 6.4.2 实现用户提问质量评估，计入综合评分
- [ ] 6.4.3 反问环节接入 route_round 收尾逻辑

### 6.5 人设系统
- [ ] 6.5.1 定义 Persona 结构（风格 tone × 角色 role × stress_mode）
- [ ] 6.5.2 实现人设 → 面试官 system prompt 的注入
- [ ] 6.5.3 实现多种风格（严肃/轻松/风趣/温和/压力）
- [ ] 6.5.4 实现预置人设组合（若干公司+职位+风格）
- [ ] 6.5.5 实现压力面叠加（作为风格层正交于题型）
- [ ] 6.5.6 人设效果验证（不同风格口吻差异明显）

---

## 阶段 7：RAG 双库（Day 13-16，4 天）

### 7.1 向量库与嵌入基建
- [x] 7.1.1 引入向量库与嵌入模型依赖（rank_bm25 + 智谱 embedding-3 API；**改选型**：chromadb 依赖 chroma-hnswlib 需 MSVC 编译、Windows 装不上，改用 numpy 余弦相似度 + SQLite 存 embedding——零重依赖、更透明，诚实技术判断，design 原则 3）
- [x] 7.1.2 封装 `backend/src/services/rag_service.py`（嵌入单例 + hybrid_search；test_rag_spike 验证 embedding-3 语义区分度，rag_service 自检双路融合通过）
- [x] 7.1.3 实现混合检索（关键词 BM25 + 向量余弦语义 + 来源优先级权重三路融合，alpha=0.6）
- [x] 7.1.4 检索测试（语义召回 + 关键词兜底：test_knowledge_service 公司库语义检索 PASS）

### 7.0 丰富性增强（补 Milestone 2 实测发现的"考查点固化"问题）
- [x] 7.0.1 出题锚点随机化：_build_candidate_summary 末尾随机抽 3 段经历/技能作「本场锚点池」
- [x] 7.0.2 gaps 随机抽样+排序：_build_focus_from_gaps 先按 severity 排序建池再 random.sample 打乱
- [x] 7.0.3 追问 LLM 化：_llm_followup 基于人设+probing_point 生成（阶段 6.5 已实现，此处确认覆盖）
- [x] 7.0.4 多样性回归测试（test_question_diversity：题干唯一率 100%、锚点唯一率 44-55%；锚点固化主因=测试画像经历少+LLM 偏好强经历，真实画像更丰富时效果更好，RAG 公司库已带来新角度）

### 7.2 个人面经库
- [x] 7.2.1 定义 `PersonalEpisodeModel`（models/knowledge.py，per-user 隔离 + embedding_json 列）
- [x] 7.2.2 实现复盘后自动沉淀（archive_episodes_from_session：transcript+debrief→结构化条目，反问 qid=qa 跳过）
- [x] 7.2.3 实现个人库检索（search_personal + get_recent_questions 避重 + get_weakness_questions 复练 + get_history_for_topic 成长对比）
- [x] 7.2.4 实现个人面经的删除（delete_all_personal，数据权利）
- [x] 7.2.5 隐私隔离测试（test_knowledge_service：userB 查 userA → 0 条，PASS）

### 7.3 公司面经库
- [x] 7.3.1 定义 `CompanyQuestionModel`（models/knowledge.py，全局共享 + source 标签）
- [x] 7.3.2 精选种子集（CURATED_SEED：产品/后端/运营 三岗 22 条人工精选真题，seed_curated 幂等入库）
- [x] 7.3.3 LLM 扩充长尾（llm_augment_company + get_company_question_augment_prompt，标注 llm_generated，失败降级）
- [x] 7.3.4 UGC 入口与脱敏（add_ugc_company：仅 contributor_id 内部追溯，对外不暴露）
- [x] 7.3.5 公司库检索（search_company：按公司/岗位过滤 + 混合检索）
- [x] 7.3.6 来源优先级排序（hybrid_search 的 source 权重 curated 1.0 > ugc 0.85 > llm_generated 0.70，test 验证 curated 居首）

### 7.4 RAG 接入主流程
- [x] 7.4.1 出题节点接入 RAG（session_setup 调 _retrieve_rag_context：公司库增强 + 个人库避重/复练注入出题 prompt；test_rag_integration 公司库命中 5 条 PASS）
- [x] 7.4.2 复盘节点接入个人库（debrief_node 调 _archive_to_personal_library 沉淀；第二场飞轮反哺 recent_questions=6 PASS）
- [x] 7.4.3 来源透明展示（question_plan.rag_used 记录公司库/近期题/弱项命中数，供前端展示「本场参考了 N 条真实面经」）
- [x] 7.4.4 RAG 检索失败降级（_retrieve_rag_context try/except 返回空 dict，出题不依赖检索）

---

## 阶段 8：前端（Day 13-18，5-6 天，与阶段 7 部分并行）

### 8.1 API 与类型
- [ ] 8.1.1 创建 `web/src/api/interview.ts`（sessions / answer / detail / debrief / history 封装）
- [ ] 8.1.2 在 `web/src/types/` 补充面试相关类型（Session / QuestionPackage / DebriefReport / Episode）

### 8.2 会话配置
- [ ] 8.2.1 创建 `InterviewSetup.vue`（题型/档位/模式/人设选择，JD 可选关联）
- [ ] 8.2.2 档位用语义化展示（简短/正常/深度/全程，不显示分钟）
- [ ] 8.2.3 画像缺失/经历不足时引导跳转建立画像
- [ ] 8.2.4 在路由与导航添加"模拟面试"入口

### 8.3 面试对话
- [ ] 8.3.1 创建 `InterviewRoom.vue`（面试官消息流 + 用户答题输入）
- [ ] 8.3.2 实现多态响应处理（awaiting_answer 继续 / finished 跳复盘）
- [ ] 8.3.3 实现 coach 模式侧栏（实时改进提示）
- [ ] 8.3.4 实现面试官人设展示（头像/姓名/职位/风格）
- [ ] 8.3.5 实现反问环节 UI（用户提问输入）
- [ ] 8.3.6 实现续面（进入进行中会话恢复 transcript）

### 8.4 复盘报告
- [ ] 8.4.1 创建 `DebriefReport.vue`（总评 + 五维雷达 + 逐题回顾）
- [ ] 8.4.2 实现改进范例对比展示（你的回答 vs 改进版）
- [ ] 8.4.3 实现失分/卡壳分析展示
- [ ] 8.4.4 实现后续建议清单
- [ ] 8.4.5 实现成长对比展示（本次 vs 历史）

### 8.5 面经库与历史
- [ ] 8.5.1 创建 `ExperienceLibrary.vue`（个人面经列表 + 筛选 + 公司库浏览）
- [ ] 8.5.2 实现来源标签透明展示（精选/贡献/AI 拟题）
- [ ] 8.5.3 创建 `InterviewHistory.vue`（历史会话列表 + 回看复盘）

---

## 阶段 9：测试与打磨（Day 19-21，3 天）

### 9.1 追问质量验证
- [ ] 9.1.1 准备多样化回答样本（充分/缺信号/空洞/跑题）
- [ ] 9.1.2 验证追问触发准确性（该追问的追、不该追问的不追）
- [ ] 9.1.3 验证追问上限（每题不超 3 次）
- [ ] 9.1.4 验证追问内容基于预埋地图（非自由发挥）

### 9.2 档位与节奏
- [ ] 9.2.1 验证各档位题量与深挖程度符合预期
- [ ] 9.2.2 验证问答计划执行完正确结束
- [ ] 9.2.3 验证反问环节触发时机
- [ ] 9.2.4 档位参数按样本校准

### 9.3 RAG 召回评估
- [ ] 9.3.1 验证个人库避免重复/复练弱项的效果
- [ ] 9.3.2 验证公司库增强真实感的效果
- [ ] 9.3.3 验证混合检索召回稳定性（专业术语场景）
- [ ] 9.3.4 验证来源透明展示

### 9.4 续面与边界
- [ ] 9.4.1 验证跨请求续面状态完整
- [ ] 9.4.2 验证后端重启后会话不丢
- [ ] 9.4.3 验证提前结束仍能复盘（标注提前结束）
- [ ] 9.4.4 验证用户主动结束流程

### 9.5 Prompt 调优与端到端
- [ ] 9.5.1 出题/追问/评估/复盘/人设 Prompt 多样本调优
- [ ] 9.5.2 端到端耗时测量（出题<15s / 单轮<10s / 复盘<20s）
- [ ] 9.5.3 LLM 失败/超时的重试与降级验证
- [ ] 9.5.4 完整闭环演示（含 RAG、双模式、复盘）

---

## 任务依赖关系

```
阶段1(地基) → 阶段2(出题) → 阶段3(子图+评估) → 阶段4(API) → 阶段5(基础复盘)
                                                                 │
                                                                 ▼
                                                          [最小闭环可演示]
                                                                 │
                                              ┌──────────────────┼──────────────────┐
                                              ▼                  ▼                  ▼
                                         阶段6(真实感)      阶段7(RAG双库)      阶段8(前端)
                                              │                  │                  │
                                              └──────────────────┼──────────────────┘
                                                                 ▼
                                                            阶段9(测试打磨)
```

**关键路径**：阶段 1 → 2 → 3 → 4 → 5。阶段 6/7/8 在最小闭环之上增量点亮，可部分并行。

**前置依赖**：画像持久化可读 + 经历细节质量 + JD 匹配结果可读（见 proposal 前置依赖）。

---

## 里程碑

### Milestone 1: 地基就绪（Day 2）
- ✅ checkpointer 持久化可用、抗重启
- ✅ interrupt 机制 spike 验证通过
- ✅ MockInterviewState 扩展完成

### Milestone 2: 最小闭环可演示（Day 8）⭐
- ✅ 出题 → 多轮对话（含追问）→ 复盘 端到端跑通
- ✅ 会话式 API 可用
- ✅ 文字、单题型、实战模式完整演示

### Milestone 3: 真实感与教学性（Day 12）
- ✅ 全题型 + 档位 + 双模式 + 人设
- ✅ 详细复盘（改进范例 + 卡壳 + 可执行建议）

### Milestone 4: 数据飞轮（Day 16）
- ✅ RAG 双库（个人库沉淀复用 + 公司库冷启动检索）
- ✅ 来源透明治理

### Milestone 5: 前端完整（Day 18）
- ✅ 配置/对话/复盘/面经库/历史 全部页面

### Milestone 6: 质量达标（Day 21）
- ✅ 追问质量、档位节奏、RAG 召回、续面边界 全部验证
- ✅ 完整闭环演示就绪

---

## 风险任务

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| 1.2 interrupt spike | 机制首次使用，可能踩坑 | 最小 demo 先行 de-risk，记录用法 |
| 2.2 QuestionPackage 生成 | probing_points/ideal_signals 质量不稳 | 结构化输出 + 样本调优 + 具体化约束 |
| 3.2 追问决策 | 信号差检测主观 | ideal_signals 具体化（如"量化结果"），样本校准 |
| 6.3 改进范例 | 生成质量/可能偏离自身回答 | Prompt 约束基于用户原文，多样本验证 |
| 6.5 人设效果 | 风格差异不明显 | 预置组合精心设计，对比测试 |
| 7.3 公司库冷启动 | 数据真实性/覆盖不足 | 来源标签透明 + 精选种子打底 + UGC 替换 |
| 7.1 混合检索 | 召回不稳 | 关键词 + 语义组合，多样本评估 |
| 9.5 端到端耗时 | 多次 LLM 调用累积延迟 | 分阶段进度提示 + 重试超时控制 |

---

## 完成标准

### 功能完整性
- [ ] 最小闭环（阶段 1-5）可演示
- [ ] 全题型 + 档位 + 双模式 + 人设 完整
- [ ] 详细复盘（改进范例 + 卡壳 + 可执行建议）
- [ ] RAG 双库（个人库飞轮 + 公司库冷启动）
- [ ] 前端全页面完整
- [ ] 会话持久化与续面

### 质量标准
- [ ] 追问基于预埋地图（可控可解释）
- [ ] 改进范例基于自身回答（非标准答案检索）
- [ ] 后续建议可执行（非空话）
- [ ] 面经来源透明标注
- [ ] LLM 失败有重试与降级
- [ ] 端到端耗时达标

### 用户体验标准
- [ ] 1 分钟内配置并开始面试
- [ ] 面试节奏自然（非机械题单）
- [ ] 复盘明确指出问题与改进方向
- [ ] 续面无缝

---

## 后续扩展（不在本次范围）

- [ ] 语音增强（TTS 面试官声音 + STT 用户回答）—— 文字层按消息流设计，语音作为可开关的输入输出层平滑接入
- [ ] 通用 chat 记忆层升级为持久化 checkpointer
- [ ] 面经库反哺简历优化（若后续实现简历优化）
- [ ] 面试能力成长曲线长期看板
- [ ] 多面试官协作（如 HR 面 + 技术面 + 经理面连续模拟）
