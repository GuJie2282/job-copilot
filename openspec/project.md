# 项目上下文 — job-copilot

## 这是什么
**求职 Copilot**：基于 LangGraph 的 AI 求职 Agent，定位"带记忆的全链路求职教练"。能力链路：建立画像 → JD 匹配 → 简历优化 → 模拟面试 → 复盘沉淀。

差异化：带长期记忆的全链路闭环，越用越懂你——区别于市面上"只改简历"或"只模拟面试"的单点工具。

## 技术栈
- **语言**：Python 3.10+
- **Agent 框架**：LangGraph（状态机驱动）
- **LLM 接入**：LangChain `ChatOpenAI`（OpenAI 兼容接口）；当前使用智谱 GLM-4-flash，可切换 DeepSeek/OpenAI/通义。
- **记忆**：MemorySaver（内存，MVP）；后续持久化。

## 当前状态
- **v0.1 MVP**：单节点对话 Agent（chatbot 节点 + MemorySaver 多轮记忆），已实现 `conversation` 能力（求职教练对话）。
- **规划**：意图路由 + 四个业务节点（`user-profile` / `jd-matching` / `resume-optimization` / `mock-interview`）+ 用户画像持久化。

## 目标
个人面试作品集项目（求职 AI PM）。需可演示、有技术深度、能讲清设计取舍。技术选型与架构决策要能对应到产品价值。

## 相关文档
- 对外说明与快速开始：根 `README.md`
- 项目指引：根 `CLAUDE.md`
- 产品/架构文档在项目根 `docs/` 下，**仅本地维护、未纳入版本管理**（勿 `git add -f`）
