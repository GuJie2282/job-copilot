# 求职 Copilot（job-copilot）

> 基于 **LangGraph** 的 AI 求职 Agent —— 你的私人求职教练

---

## 这是什么

一个用 Python + LangGraph 写的 AI 求职助手。它能陪你走完求职全链路：

| 能力 | 说明 |
|------|------|
| 📋 **建立画像** | 把你的简历/经历结构化，作为后续所有能力的基础 |
| 🎯 **JD 匹配分析** | 解析岗位要求，评估匹配度，指出 Gap 和应对方法 |
| 📝 **简历定制优化** | 针对目标岗位改写简历（STAR 法则，绝不编造） |
| 🎤 **模拟面试** | 多轮对话面试 + 实时追问 + 复盘反馈报告 |

**差异化**：带长期记忆的全链路闭环，越用越懂你——区别于市面上"只改简历"或"只模拟面试"的单点工具。

---

## 技术栈

- **Python 3.10+** · **LangGraph**（状态机驱动 Agent 编排）· LangChain · DeepSeek（OpenAI 兼容）

> 为什么用 LangGraph？因为它把 Agent 的"流程"显式建模成状态机，可控、可调试、可讲——比裸调 API 更能体现工程能力。详见 [技术架构](docs/技术架构.md)。

---

## 快速开始

### 方式一：AI Agent 对话（LangGraph 核心能力）

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活（三选一，看你的终端）：
#    PowerShell:  .venv\Scripts\Activate.ps1
#    Git Bash:    source .venv/Scripts/activate
#    cmd:         .venv\Scripts\activate
#    （PowerShell 若报"禁止运行脚本"，先执行一次：
#     Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned）

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
#    PowerShell: Copy-Item .env.example .env
#    Git Bash:   cp .env.example .env
#    然后编辑 .env，填入 LLM_API_KEY

# 5. 启动
python -m src.main
```

### 方式二：完整 Web 应用（含后端认证）

```bash
# 1. 启动后端服务（认证 API）
cd backend
pip install -r requirements.txt
python -c "from src.models.base import Base, engine; Base.metadata.create_all(bind=engine); print('数据库初始化完成')"
python src/main.py  # 后端运行在 http://localhost:8000

# 2. 启动前端服务（Vue 3 界面）
cd ../web
npm install  # 首次运行
npm run dev   # 前端运行在 http://localhost:3000

# 3. 访问应用
# - 前端界面：http://localhost:3000
# - 后端文档：http://localhost:8000/docs
```

**后端文档**: [backend/README.md](backend/README.md) - 详细的 API 文档和部署指南

> 💡 **没有 DeepSeek Key？** 去 https://platform.deepseek.com/ 注册，充值几块钱够用很久。
> 💡 **想用 OpenAI/通义/智谱？** 改 `.env` 里的 `LLM_BASE_URL` 和 `LLM_MODEL` 即可，代码不用动。

---

## 目录结构

```
job-copilot/
├── CLAUDE.md              # 项目指引（给 Claude Code）
├── README.md              # 本文件
├── requirements.txt       # 依赖
├── .env.example           # 配置模板
├── docs/                  # 产品/架构文档
├── src/
│   ├── main.py            # 入口（终端对话）
│   ├── graph.py           # LangGraph 图定义（核心）
│   ├── nodes/             # 各业务节点
│   ├── prompts.py         # Prompt 库
│   └── ...
└── tests/
```

---

## 路线图

- [x] **v0.1 MVP**：单节点对话 Agent（求职教练人设 + 多轮记忆）
- [ ] **v0.2**：意图路由 + 简历优化节点
- [ ] **v0.3**：JD 匹配分析节点
- [ ] **v0.4**：模拟面试节点 + 复盘报告
- [ ] **v0.5**：用户画像持久化（长期记忆）
- [ ] **v1.0**：完整闭环 + Web 界面（可选）

---

## 文档

- 📄 [产品方案](docs/产品方案.md) — PRD + 商业分析 + AI 能力边界
- 📅 [行动计划](docs/行动计划.md) — 开发路线图
- 🏗️ [技术架构](docs/技术架构.md) — 技术设计与面试讲点

---

*这是一个个人面试作品集项目。*
