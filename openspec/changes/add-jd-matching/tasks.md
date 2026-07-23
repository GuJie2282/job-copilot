# Tasks: JD 匹配分析

## 任务概览

本变更分两大区块：**区块一（前置：画像持久化）** 与 **区块二（核心：JD 匹配）**，外加前端与测试；另含 **区块三（流式化与 Gap 增补 lazy 改造，对应 design 决策 9/11）**——因原同步方案实测超时而追加。

**预计工时**：约 11 天

---

## 区块一：前置 —— 画像持久化

### Phase 1: 数据层（Day 1，4 个任务）

#### 1.1 user_profiles 表
- [x] 1.1.1 在 `backend/src/models/` 下创建 `profile.py`，定义 `UserProfileModel`
  - 标量列：`id`(UUID)、`user_id`(FK→users, UNIQUE)、`name`、`email`、`phone`、`location`、`location_preference`、`salary_range`、`industry`、`quality_score`、`source`
  - JSON 列：`detail_json`（教育/工作/项目/技能/语言/目标岗位等不定长列表）
  - JSON 列：`confidence_json`（字段置信度）
  - 时间戳：`created_at`、`updated_at`
- [x] 1.1.2 在 `models/__init__.py` 中导出新模型
- [x] 1.1.3 在应用启动时确保建表（`Base.metadata.create_all`）
- [x] 1.1.4 验证表结构（手动插入/查询一条）

#### 1.2 jd_match_results 表
- [x] 1.2.1 在 `models/profile.py`（或新建 `models/jd_match.py`）中定义 `JdMatchResultModel`
  - 标量列：`id`(UUID)、`user_id`(FK)、`overall_score`、`skill_score`、`experience_score`、`education_score`、`soft_skill_score`、`jd_text`
  - JSON 列：`job_profile_json`、`gaps_json`、`confidence_json`
  - 时间戳：`created_at`
- [x] 1.2.2 导出并建表
- [x] 1.2.3 验证表结构

---

### Phase 2: 画像存取服务与 API 改造（Day 2，6 个任务）

#### 2.1 画像存取 service
- [x] 2.1.1 创建 `backend/src/services/profile_service.py`
  - `save_profile(db, user_id, profile, confidence, quality_score, source)`：upsert（首次插入/已存在则覆盖更新）
  - `get_profile(db, user_id)`：读取，不存在返回 None
  - `delete_profile(db, user_id)`：删除
- [x] 2.1.2 处理 `detail_json` 的无损序列化/反序列化（画像 dict ↔ JSON 列）
- [x] 2.1.3 单元测试：保存 → 读取 → 更新 → 删除的完整循环

#### 2.2 改造 resume API
- [x] 2.2.1 改造 `POST /api/resume/update-profile`：移除 TODO，调用 `save_profile` 真正存库
- [x] 2.2.2 改造 `GET /api/resume/profile`：调用 `get_profile` 真正读库
- [x] 2.2.3 改造 `DELETE /api/resume/profile`：调用 `delete_profile` 真正删除
- [x] 2.2.4 改造 `GET /api/resume/export-profile`：从库读取真实画像
- [x] 2.2.5 简历解析（`parse-file`/`parse-text`）成功后衔接：用户确认画像后调用 `save_profile` 落库
- [x] 2.2.6 验证：解析简历 → 画像落库 → 刷新仍能读回

---

## 区块二：核心 —— JD 匹配

### Phase 3: JD 解析与匹配服务（Day 3-4，10 个任务）

#### 3.1 JD 结构化解析
- [x] 3.1.1 创建 `backend/src/services/jd_parser.py`，实现 `parse_jd(jd_text)` → `job_profile`
- [x] 3.1.2 在 `graph/prompts.py` 中新增 JD 解析 Prompt（四分类：硬技能/软技能/隐性偏好/红线项；标注 must_have；保留原文 evidence；输出置信度）
- [x] 3.1.3 定义 `JobProfile` Pydantic 模型（四类要求 + 每条的 requirement/must_have/evidence/confidence）
- [x] 3.1.4 用 `get_structured_llm` + `invoke_llm_with_retry` 调用，保证输出稳定

#### 3.2 匹配计算
- [x] 3.2.1 创建 `backend/src/services/matcher.py`，实现 `calculate_match(job_profile, user_profile)` → 维度得分
- [x] 3.2.2 硬技能程序化比对：技能集匹配（含同义词/近义词归一）→ satisfied/partial/missing + 画像依据
- [x] 3.2.3 经验/学历维度：基于画像工作经历、教育记录做规则比对
- [x] 3.2.4 隐性偏好 LLM 判断：新增隐性判断 Prompt，调用 LLM 给出满足程度 + 理由
- [x] 3.2.5 加权汇总：四维度按可配置权重（技能0.4/经验0.3/学历0.15/软技能0.15）→ 总分
- [x] 3.2.6 红线惩罚：任一红线未满足 → 总分 ×0.7 且封顶 60 + 标记

#### 3.3 差距分析
- [x] 3.3.1 创建 `backend/src/services/gap_analyzer.py`，实现 `analyze_gaps(job_profile, user_profile, match_result)` → Gap 清单
- [x] 3.3.2 Gap 四分类（硬技能差距/软技能表述弱/隐性偏好缺位/红线预警）+ 应对建议（新增 Gap 生成 Prompt）
- [x] 3.3.3 严重度排序（红线 > 硬技能 > 隐性 > 软技能）+ 置信度传导（画像字段低置信度 → 该 Gap 标注"待确认"）

---

### Phase 4: LangGraph 子图与 API（Day 5-6，13 个任务）

#### 4.1 State 扩展
- [x] 4.1.1 在 `graph/state.py` 中新增 JD 匹配字段：`jd_text`、`job_profile`、`match_result`(overall+dimensions)、`gaps`、`match_confidence`、`match_status`、`result_id`
- [x] 4.1.2 更新 `create_initial_state` 与状态辅助函数

#### 4.2 JD 匹配节点
- [x] 4.2.1 创建 `graph/nodes/jd_match.py`
- [x] 4.2.2 实现 `jd_intake_node`（收 JD 文本 + 长度/结构校验）
- [x] 4.2.3 实现 `jd_quality_check_node`（JD 质量门）
- [x] 4.2.4 实现 `jd_parsing_node`（调用 jd_parser）
- [x] 4.2.5 实现 `profile_load_node`（读 user_profiles；缺失则设 match_status=profile_missing）
- [x] 4.2.6 实现 `match_calc_node`（调用 matcher）
- [x] 4.2.7 实现 `gap_analysis_node`（调用 gap_analyzer）
- [x] 4.2.8 实现 `report_format_node`（写 jd_match_results + 组装报告）
- [x] 4.2.9 实现条件边函数（画像缺失→END 引导；JD 质量过低→提示；LLM 失败→重试/降级）

#### 4.3 图注册
- [x] 4.3.1 在 `graph/graph.py` 中注册 JD 匹配节点与子图边
- [x] 4.3.2 在 router 条件边中新增 `jd_match` 分支

#### 4.4 API
- [x] 4.4.1 创建 `backend/src/api/jd.py`，实现 `POST /api/jd/match`（鉴权 + 接收 jd_text + 调图谱 + 返回报告）
- [x] 4.4.2 实现 `GET /api/jd/history`（按当前用户查历史匹配，时间倒序）
- [x] 4.4.3 实现 `GET /api/jd/results/{id}`（单条匹配详情）
- [x] 4.4.4 在 `main.py` 中注册 jd_router
- [x] 4.4.5 重试与降级：JD 解析/隐性判断失败时指数退避重试，耗尽返回友好错误并保留 JD

---

## 前端

### Phase 5: JD 匹配前端（Day 7-9，11 个任务）

#### 5.1 API 与类型
- [x] 5.1.1 创建 `web/src/api/jd.ts`（match / history / results 调用封装）
- [x] 5.1.2 在 `web/src/types/index.ts` 中补充 JobProfile / MatchResult / Gap 类型

#### 5.2 主页面与输入
- [x] 5.2.1 创建 `web/src/views/JdMatcher.vue` 主页面
- [x] 5.2.2 创建 `JdInput.vue`（JD 粘贴 + 字数提示 + 校验）—— JD 输入集成在 JdMatcher 主页面内
- [x] 5.2.3 在路由与导航中添加"JD 匹配"入口（需登录）
- [x] 5.2.4 画像缺失时引导跳转"建立画像"

#### 5.3 报告展示
- [x] 5.3.1 创建 `MatchReport.vue`（总分 + 匹配等级）—— 总分/等级集成在 JdMatcher 内
- [x] 5.3.2 创建 `ScoreRadar.vue`（四维度雷达图，可用 ECharts/Chart.js）—— 用纯 SVG 实现，无额外依赖
- [x] 5.3.3 创建 `GapList.vue`（Gap 按四类分组 + 建议 + 严重度标签）
- [x] 5.3.4 创建 `RedlineAlert.vue`（红线项醒目预警）—— 红线预警集成在 JdMatcher 内
- [x] 5.3.5 匹配项明细（可展开查看 JD 原文 + 画像依据 + 置信度）—— JD 要求画像 + Gap 现状/依据展示

#### 5.4 历史与体验
- [x] 5.5.1 历史匹配列表（点击回看详情）
- [x] 5.5.2 分阶段进度提示（解析 JD → 提取要求 → 比对 → 生成报告）

---

## 测试与打磨

### Phase 6: 测试与打磨（Day 10-11，8 个任务）

#### 6.1 样本测试
- [ ] 6.1.1 准备 5-8 份不同行业/风格的 JD 样本
- [ ] 6.1.2 逐份验证四分类准确性、维度得分合理性、Gap 建议 quality
- [ ] 6.1.3 记录并修正 Prompt（JD 解析 / 隐性判断 / Gap 建议）

#### 6.2 边界与置信度
- [ ] 6.2.1 边界：JD 过短、过长、非 JD 内容、画像缺失、画像低质
- [ ] 6.2.2 置信度校验：低置信度项是否正确标注"待确认"
- [ ] 6.2.3 红线场景：学历/资质不满足时的惩罚与预警是否正确

#### 6.3 性能与集成
- [ ] 6.3.1 端到端验证：评分链 < 30 秒且分数优先可见；流式连接不触发客户端超时（见区块三 Phase 7/8）
- [ ] 6.3.2 闭环验证：JD 匹配 Gap 结构能否被（占位的）简历优化模块消费

---

## 区块三：流式化与 Gap 增补 lazy 改造（对应 design 决策 9/11）

> 缘起：原同步 match 端点串行 3 次 strong 档 LLM，偶发慢/限流即冲破前端 90s 超时；叠加 async 端点内同步 invoke 阻塞事件循环。改为阶段级 SSE 流式 + 评分链/增补链拆分。

### Phase 7: 后端流式与评分链/增补链拆分

#### 7.1 拆分匹配图
- [x] 7.1.1 将 gap_analysis（隐性判断 + Gap 建议 LLM）从主图剥离到增补链
- [x] 7.1.2 主图收敛为评分链：jd_intake → quality → parsing → profile_load → match_calc → persist
- [x] 7.1.3 校验 overall 仅由规则维度（技能/经验/学历/软技能）+ 红线惩罚得出，不依赖 judge_implicit

#### 7.2 持久化前移
- [x] 7.2.1 match_calc 之后立即写库（分数 + 规则 Gap 骨架 + job_profile），生成 result_id
- [x] 7.2.2 规则 Gap 骨架生成（无 LLM 建议；隐性 Gap 占位"分析中"）
- [x] 7.2.3 report_format 职责调整为"持久化 + 组装报告骨架"，不再生成 LLM 建议

#### 7.3 SSE 流式 match 端点
- [x] 7.3.1 POST /api/jd/match 改为 async + `graph.astream(stream_mode="updates")`，返回 `StreamingResponse`（text/event-stream）
- [x] 7.3.2 节点完成映射为 SSE 事件：`event:stage`（进度）/ `event:score`（分数+result_id）/ `event:done`（骨架）/ `event:error`
- [ ] 7.3.3 验证：评分链进行中，其他请求（如 history）不被阻塞（事件循环未阻塞）

#### 7.4 Gap 增补端点（lazy）
- [x] 7.4.1 新增 `POST /api/jd/{id}/enrich`（async）：跑 judge_implicit + Gap 建议（顺序执行——建议需覆盖判为差距的隐性项，并行优化留作后续），via `asyncio.to_thread` 不阻塞事件循环
- [x] 7.4.2 结果 UPDATE 同一 `jd_match_results` 行（回填 gaps_json）
- [x] 7.4.3 失败降级：增补 LLM 失败 → 模板建议/隐性 partial，不影响已持久化分数

### Phase 8: 前端流式消费与两段状态

#### 8.1 SSE 流式读取
- [x] 8.1.1 `web/src/api/jd.ts`：matchJd 改为原生 `fetch` + `ReadableStream` 手写 SSE 解析（POST 友好，不用 EventSource）
- [x] 8.1.2 `event:stage` → 真实进度文案；`event:score` → 立即渲染总分/四维度（取代 JdMatcher.vue 的假进度定时器）
- [x] 8.1.3 `event:error` → 友好提示；`event:done` → 拿到 result_id + Gap 骨架

#### 8.2 骨架 + 增补回填
- [x] 8.2.1 主链 done 后渲染规则 Gap 骨架（隐性 Gap 显示"分析中…"占位）
- [x] 8.2.2 以 result_id 调 enrich（该请求超时放宽至 ~60s），回填后 Gap 卡片更新建议与隐性状态
- [x] 8.2.3 enrich 失败时保留骨架 + 模板建议，不阻断展示

---

## 任务依赖关系

```
Phase 1 (数据层) → Phase 2 (画像存取) ──┐
                                         ├──▶ Phase 3 (匹配服务)
                                         │         ↓
                                         │    Phase 4 (子图+API)
                                         │         ↓
                                         │    Phase 5 (前端) ──并行─▶
                                         │         ↓
                                         └──▶ Phase 6 (测试)
```

**关键路径**：Phase 1 → 2 → 3 → 4 → 6。区块一（Phase 1-2）必须先完成，JD 匹配才能读画像。

---

## 里程碑

### Milestone 1: 画像可持久化（Day 2 完成）
- ✅ 画像存取 service 可用
- ✅ resume API 真正存取画像
- ✅ 解析简历后画像落库、刷新可读回

### Milestone 2: 匹配服务可用（Day 4 完成）
- ✅ JD 结构化解析（四分类）
- ✅ 四维度匹配 + 总分
- ✅ Gap 四分类 + 建议

### Milestone 3: API 可调用（Day 6 完成）
- ✅ JD 匹配子图跑通
- ✅ /api/jd/match 返回完整报告
- ✅ 结果落库、历史可查

### Milestone 4: 前端完整（Day 9 完成）
- ✅ JD 输入 + 报告 + 雷达图 + Gap + 红线
- ✅ 历史回看

### Milestone 5: 质量达标（Day 11 完成）
- ✅ 多 JD 样本测试通过
- ✅ 可解释性（依据 + 置信度）完善
- ✅ 闭环接口（Gap → 简历优化）验证

---

## 风险任务

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| 3.1.2 JD 解析 Prompt | 四分类不准 | 多样本调优 + 结构化约束 + 置信度标注 |
| 3.2.4 隐性偏好判断 | 主观性强 | 附理由 + 低置信度标注 |
| 3.2.5 权重设计 | 总分失真 | 权重可配置，样本校准 |
| 4.4.5 LLM 重试降级 | 重试仍失败 | 保留 JD + 友好提示 |
| 5.3.2 雷达图 | 图表库集成 | 复用项目已有图表方案或选轻量库 |
| 7.3/8.1 SSE 流式 | 首个流式先例、POST+SSE 需手写解析 | fetch+ReadableStream 阶段事件映射；astream 解事件循环阻塞 |

---

## 完成标准

### 功能完整性
- [ ] 画像持久化存取正常（区块一）
- [ ] JD 匹配全流程跑通（区块二）
- [ ] 前端报告完整展示
- [ ] 历史匹配可回看
- [x] match 端点 SSE 流式输出，分数优先可见、不超时（区块三）
- [x] enrich 端点 lazy 回填 Gap 建议与隐性判断（区块三）

### 质量标准
- [ ] JD 四分类合理（多样本验证）
- [ ] 每个得分点可解释（依据 + 置信度）
- [ ] Gap 清单可被下游消费
- [ ] 错误处理与降级完善

---

## 后续扩展（不在本次范围）

- [ ] 向量语义匹配增强（P2）
- [ ] 匹配结果横向对比（多 JD 同屏对比）
- [ ] 按 Gap 类型统计用户短板画像
- [ ] JD 自动抓取与岗位推荐
