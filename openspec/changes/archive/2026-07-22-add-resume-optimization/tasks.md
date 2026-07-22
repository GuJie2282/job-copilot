# Tasks: 简历优化（画像驱动的简历生成与定制）

## 任务概览

本变更分七大阶段：**数据层 → 生成与评估服务 → 路径 A 子图与 API → 导出 → 路径 B 精修 → 前端 → 测试**。

路径 A（自动生成）在 Phase 4 结束（Day 12）即可先行交付 MVP，路径 B（精修）作为 Phase 5 的增量。

**预计工时**：约 22 天

---

## Phase 1: 数据层与持久化（Day 1-2，4 个任务）

#### 1.1 resumes 表
- [x] 1.1.1 在 `backend/src/models/` 下创建 `resume.py`，定义 `ResumeModel`
  - 标量列：`id`(UUID)、`user_id`(FK→users)、`target_position`、`jd_result_id`(FK→jd_match_results, 可空)、`version`、`status`(draft/refining/finalized)、`theme`、`content_md`(TEXT)、`html`(TEXT, 可空)、`eval_score`
  - JSON 列：`eval_report_json`（6 维评估报告）
  - 时间戳：`created_at`、`updated_at`
  - 联合约束：`(user_id, target_position, version)` 唯一
- [x] 1.1.2 在 `models/__init__.py` 中导出新模型
- [x] 1.1.3 在应用启动时确保建表
- [x] 1.1.4 验证表结构（手动插入/查询一条）

#### 1.2 简历存取 service
- [x] 1.2.1 创建 `backend/src/services/resume_store_service.py`
  - `save_resume(db, user_id, target_position, ..., version, status)`：写入新版本
  - `get_resume(db, resume_id)`：读取单份（含指定版本）
  - `list_resumes(db, user_id)`：按岗位分组、按版本与时间组织
  - `next_version(db, user_id, target_position)`：计算下一版本号
- [x] 1.2.2 处理 `eval_report_json` 的无损序列化
- [x] 1.2.3 单元测试：保存 → 读取 → 多版本 → 列表分组

---

## Phase 2: 生成与评估服务（Day 3-6，10 个任务）

#### 2.1 简历生成服务
- [x] 2.1.1 创建 `backend/src/services/resume_generator.py`，实现 `generate_resume(profile, gaps, target_position)` → Markdown 简历
- [x] 2.1.2 在 `graph/prompts.py` 中新增简历生成 Prompt
  - 输入画像 + Gap 清单 + 目标岗位
  - 内嵌 Gap→改写策略映射（硬技能/软技能/隐性/红线四类）
  - 内嵌表述规则：STAR + 强动词、脱敏（业务功能替代项目原名）、平实不解释常识、不编造（缺素材标"待补充"）
  - 输出结构规范：`# self-intro` 首模块、教育背景含毕业年份、`## 机构 | 角色`、date 格式、只 `#`/`##`
- [x] 2.1.3 Gap→改写策略映射模块（独立函数，按 gap.type 返回策略指令）
- [x] 2.1.4 画像信息不足时的降级（标注"待补充"，不虚构）
- [x] 2.1.5 无 Gap 时降级为通用生成（不针对特定 Gap）

#### 2.2 简历评估服务（6 维 LLM 评估）
- [x] 2.2.1 创建 `backend/src/services/resume_evaluator.py`，实现 `evaluate_resume(resume_md, target_position, gaps, profile)` → 评估报告
- [x] 2.2.2 在 `graph/prompts.py` 中新增 6 维评估 Prompt
  - 六维度（基础规范15%/JD匹配25%/成果量化25%/结构清晰10%/差异化15%/语言表达10%）
  - 每项标记 通过/不通过/部分通过 + 具体建议
  - 输出加权总分、通过项汇总、按优先级（高/中/低）排序的改进列表
  - 量化可信度把关（数字是否可追溯至画像）
- [x] 2.2.3 定义评估报告 Pydantic 模型（维度/总分/通过判定/改进优先级）
- [x] 2.2.4 用 `get_structured_llm` + `invoke_llm_with_retry` 保证输出稳定

#### 2.3 格式校验服务（脚本硬规则）
- [x] 2.3.1 创建 `backend/src/services/resume_validator.py`，移植并改造自 amlei-resume 的 `validate_resume.py`
  - MD 校验：self-intro 首模块 / name 必填 / 教育背景含毕业年份 / 标题层级只 # ## / 空模块 / date 格式
  - HTML 校验：无残留 `{{占位符}}` / 含 Header / 含章节 / 含 style
- [x] 2.3.2 返回结构化结果（errors[] / warnings[]），供子图判定是否阻断导出

---

## Phase 3: 路径 A 子图与 API（Day 7-9，10 个任务）

#### 3.1 State 扩展
- [x] 3.1.1 在 `graph/state.py` 中新增 `ResumeOptimizeState`（见 design 的字段清单）
- [x] 3.1.2 更新 `FullAgentState` 组合、`create_initial_state` 与辅助函数

#### 3.2 简历优化节点（路径 A）
- [x] 3.2.1 创建 `graph/nodes/resume_optimize.py`
- [x] 3.2.2 实现 `resume_prepare_node`（加载画像 + Gap 快照 + 岗位；就绪性检查；缺失→END 引导；无 Gap→降级标记）
- [x] 3.2.3 实现 `resume_generate_node`（调用 resume_generator）
- [x] 3.2.4 实现 `resume_evaluate_node`（调用 resume_evaluator）
- [x] 3.2.5 实现条件边：评估不通过且未达上限 → 回 generate（带反馈）；通过或达上限 → validate
- [x] 3.2.6 实现 `resume_validate_node`（调用 resume_validator；ERROR→回 generate 修复）
- [x] 3.2.7 实现 `resume_export_node`（装配 HTML + 套预览壳；Phase 4 接入主题后补全）
- [x] 3.2.8 实现 `resume_persist_node`（落库 status=draft + 返回报告 + 标记 refine_offered）

#### 3.3 图注册与 API
- [x] 3.3.1 在 `graph/graph.py` 中注册简历优化节点与子图边；router 条件边新增 `resume_optimize` 分支
- [x] 3.3.2 创建 `backend/src/api/resume_optimize.py`
  - `POST /api/resume/generate`（鉴权 + 收岗位/jd_result_id + 调图谱 + 返回）
  - `GET /api/resume/list`、`GET /api/resume/{id}`、`GET /api/resume/{id}/pdf`
  - 在 `main.py` 注册 router
  - 重试与降级（生成失败/评估失败降级）

---

## Phase 4: 导出（主题 + HTML + PDF）（Day 10-12，7 个任务）

#### 4.1 主题系统
- [x] 4.1.1 在 `backend/src/services/resume_themes/` 下建立主题目录，实现 1-2 套 MVP 主题（借鉴 amlei-resume 的 `theme-tech-dense` / `theme-soe-formal`）
  - 每套主题含 `<style>` + 组件库（Header / SectionHead / Entry / Bullet 四类原子）
- [x] 4.1.2 主题选择策略（岗位契合推荐 / 默认主题）

#### 4.2 HTML 装配
- [x] 4.2.1 创建 `backend/src/services/resume_exporter.py`，实现 `assemble_html(resume_md, theme)` → HTML 产物
  - `# self-intro` → Header；`# 模块` → SectionHead + 正文；`## 机构|角色` → Entry + Bullet 原子
- [x] 4.2.2 套预览壳（A4 自动分页 + 导出 PDF 工具条），借鉴 amlei-resume 的 `wrap_preview.py`
- [x] 4.2.3 装配后审查（逐模块对比 MD 与 HTML 结构，无遗漏/无错序）

#### 4.3 PDF 与排版检查
- [x] 4.3.1 PDF 导出（MVP：前端浏览器打印；后端持久化 HTML 供前端预览页使用）
- [x] 4.3.2 排版质量检查（页数/末页填充率/行尾空白），不达标提示精简
- [x] 4.3.3 回填 Phase 3 的 `resume_export_node`，完成导出闭环

---

## Phase 5: 路径 B 人机协同精修（Day 13-16，7 个任务）

#### 5.1 interrupt + checkpointer 集成
- [x] 5.1.1 复用 `graph/checkpointer.py`，为简历精修会话配置 thread_id（= resume 会话 ID）
- [x] 5.1.2 在 `resume_optimize.py` 节点中实现 interrupt：精修模式下评估后暂停，等待用户反馈

#### 5.2 精修节点
- [x] 5.2.1 实现 `resume_refine_node`（按用户反馈改写草稿 → 重新评估 → interrupt）
- [x] 5.2.2 实现画像追问机制（Gap 需要画像不具备的素材时，interrupt 向用户追问；回答融入改写；提示同步回画像）
- [x] 5.2.3 实现 `resume_finalize_node`（用户满意 → 格式校验 → 导出定稿 PDF → 落库 status=finalized）

#### 5.3 精修 API
- [x] 5.3.1 实现 `POST /api/resume/{id}/refine`（接收反馈 → 恢复会话 → 改写 → 返回 interrupt 响应）
- [x] 5.3.2 实现 `POST /api/resume/{id}/finalize`（满意 → 定稿）
- [x] 5.3.3 会话态与持久态分离：中间态走 checkpointer，确认导出才写 DB

---

## Phase 6: 前端（Day 17-20，10 个任务）

#### 6.1 API 与类型
- [x] 6.1.1 创建 `web/src/api/resume.ts`（generate / refine / finalize / list / detail / pdf 调用封装）
- [x] 6.1.2 在 `web/src/types/` 中补充 Resume / ResumeEvalReport / Gap 类型

#### 6.2 生成主页面
- [x] 6.2.1 创建 `web/src/views/ResumeOptimizer.vue` 主页面（触发生成、选岗位/关联匹配、查看产出）
- [x] 6.2.2 从 JD 匹配报告的 Gap 列表旁接入"生成简历"入口
- [x] 6.2.3 分阶段进度提示（准备 → 生成 → 评估 → 迭代 → 导出）
- [x] 6.2.4 画像缺失时引导跳转"建立画像"

#### 6.3 预览与评估
- [x] 6.3.1 创建 `ResumePreview.vue`（HTML 预览 + 导出 PDF 工具条）
- [x] 6.3.2 创建 `ResumeEvalReport.vue`（6 维得分 + 通过项 + 改进优先级）

#### 6.4 精修与历史
- [x] 6.4.1 创建 `ResumeRefine.vue`（路径 B：反馈输入 + 追答回填 + 轮次展示 + 满意定稿）
- [x] 6.4.2 创建 `ResumeHistory.vue`（按岗位分组、按版本回看、下载 PDF）
- [x] 6.4.3 路由与导航添加"简历优化"入口（需登录）

---

## Phase 7: 测试与打磨（Day 21-22，6 个任务）

#### 7.1 样本测试
- [x] 7.1.1 准备 3-5 个不同岗位的画像 + JD + Gap 样本
- [x] 7.1.2 逐样本验证：生成忠实度、Gap 改写映射体现、6 维评估合理性、PDF 排版
- [x] 7.1.3 记录并修正 Prompt（生成 / 评估 / Gap 改写）

#### 7.2 边界与降级
- [x] 7.2.1 边界：画像缺失、画像低质、无 Gap（通用降级）、迭代不收敛
- [x] 7.2.2 降级：生成 LLM 失败、评估 LLM 失败（仅格式校验交付）、格式校验 ERROR 修复
- [x] 7.2.3 路径 B：interrupt 恢复、画像追问、会话跨请求一致性

---

## 任务依赖关系

```
Phase 1 (数据层) ──▶ Phase 2 (生成/评估服务) ──▶ Phase 3 (路径A 子图+API)
                                                        │
                                                        ▼
                                                  Phase 4 (导出) ──▶ ★ MVP 可交付（路径 A）
                                                        │
                                                        ▼
                                                  Phase 5 (路径B 精修)
                                                        │
                        Phase 6 (前端) ◀─── 并行 ──────┤
                                                        │
                                                        ▼
                                                  Phase 7 (测试)
```

**关键路径**：Phase 1 → 2 → 3 → 4 → 7。路径 A 在 Phase 4 完成时即可先行交付；路径 B（Phase 5）与前端（Phase 6）可作为增量并行推进。

---

## 里程碑

### Milestone 1: 数据层与生成评估服务可用（Day 6 完成）
- ✅ resumes 表与存取 service
- ✅ 简历生成（Gap→改写映射）
- ✅ 6 维评估 + 格式校验

### Milestone 2: 路径 A 子图跑通（Day 9 完成）
- ✅ 简历优化子图（生成→评估→迭代→校验）
- ✅ generate / list / detail API

### Milestone 3: MVP 可交付 —— 路径 A 完整闭环（Day 12 完成）★
- ✅ 主题系统 + HTML 装配 + PDF 导出
- ✅ 路径 A 端到端：画像+Gap → 自动生成迭代 → PDF → 落库
- ✅ 前端生成页 + 预览 + 评估报告

### Milestone 4: 路径 B 精修可用（Day 16 完成）
- ✅ interrupt + checkpointer 集成
- ✅ 反馈改写 + 画像追问 + 满意定稿
- ✅ refine / finalize API

### Milestone 5: 前端完整与质量达标（Day 22 完成）
- ✅ 精修交互 + 简历历史
- ✅ 多岗位样本测试通过
- ✅ 错误处理与降级完善

---

## 风险任务

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| 2.1.2 生成 Prompt | 内容失真/编造；Gap 改写不到位 | 画像作唯一事实源 + prompt 约束"不编造，缺素材标待补" + 评估层把关 |
| 2.2.2 6 维评估 Prompt | 主观性、不稳定 | 结构化输出约束 + 阈值可配置 + 样本调优 |
| 4.1.1 主题装配 | 组件库复杂、排版难控 | MVP 只 1-2 套主题，组件从简（4 类原子） |
| 4.3.1 PDF 导出 | 中文字体/分页 | MVP 用前端浏览器打印（同 skill 路线，零依赖）；后端渲染作可选增强 |
| 5.1.2 interrupt 集成 | 长程会话状态一致性 | 复用 mock-interview 的 checkpointer（已验证范式） |

---

## 完成标准

### 功能完整性
- [x] 路径 A 全流程跑通（生成 → 评估 → 迭代 → 校验 → 导出 PDF → 落库）
- [x] 路径 B 精修闭环（interrupt → 反馈改写 → 画像追问 → 满意定稿）
- [x] 简历按岗位多份、按版本多次持久化，可查历史与下载 PDF
- [x] 前端完整（生成页、预览、评估报告、精修、历史）

### 质量标准
- [x] 生成内容忠实于画像（不编造），量化可追溯
- [x] Gap 四类改写策略在简历中可追溯体现
- [x] 6 维评估稳定（同输入结果一致为主）
- [x] 双层质量门（LLM 评估 + 格式校验）均生效
- [x] 错误处理与降级完善

### 闭环标准
- [x] 兑现 JD 匹配 design 决策 4 的"Gap → 简历优化"接口契约
- [x] 路径 B 同构复用 mock-interview 的 interrupt/checkpointer

---

## 后续扩展（不在本次范围）

- [ ] 后端直接渲染 PDF（weasyprint / playwright），支持批量与定时导出
- [ ] 更多主题（借鉴 skill 的 7 套主题）
- [ ] 画像升级为"素材库"（一次建档、跨岗复用，对应 skill 的 profile.json 理念）
- [ ] JD 自动抓取（借鉴 skill 的 boss_zhipin.py）
- [ ] 简历横向对比（多岗位同屏对比）
- [ ] 生成过程的 SSE 流式输出
