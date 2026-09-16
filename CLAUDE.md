# CLAUDE.md — job-copilot（求职 Copilot）

本文件为 Claude Code 提供项目指引。在这个项目里工作时，**请先读完本文件**。
回答时都使用中文。

---

## 项目概述

**job-copilot（求职 Copilot）** 是一个基于 **LangGraph** 的全链路 AI 求职 Agent，定位为"带记忆的全链路求职教练"。核心能力链路：

```
建立画像 → JD 匹配分析 → 简历定制优化 → 模拟面试 → 复盘沉淀
```

这是一个**个人面试作品集项目**（非商业生产项目），目标是产出一个能演示、有技术深度、体现产品与工程思维的 AI Agent，用于求职。

**当前形态**：全栈应用 —— 后端 `backend/`（FastAPI + LangGraph + SQLite）+ 前端 `web/`（Vue 3 + TS + Element Plus）。根目录 `src/` 是早期的单节点 CLI 原型，**仅留档，不要在上面继续开发**。

## ⚠️ 重要：项目负责人背景（协助时务必考虑）

- 负责人正在求职 **AI 产品经理（AI PM）** 方向。
- **技术背景较弱**：调过 LLM API、懂基本概念，但不熟练写代码。
- 因此协助原则：
  - **降低技术门槛**：代码多写中文注释，循序渐进；复杂概念要解释清楚。
  - 优先保证"**能跑起来、能看懂**"，再追求工程优雅。不堆砌高级用法。
  - 这是面试项目，**技术选型要能讲出道理**（为什么用 LangGraph、为什么按生命周期切图）——适当点出"这里面试可以怎么讲"。

## 技术栈

| 项 | 选型 | 说明 |
|----|------|------|
| 语言 | Python 3.10+ / TypeScript | — |
| Agent 框架 | **LangGraph** | 状态机驱动的 Agent 编排，面试加分项 |
| LLM 接入 | LangChain `ChatOpenAI` | OpenAI 兼容接口。默认智谱 GLM，可换 DeepSeek/OpenAI/通义 |
| 后端 | FastAPI + SQLAlchemy + SQLite | 业务库 `job_copilot.db` |
| 会话状态 | LangGraph `SqliteSaver` | 独立库 `interview_checkpoints.db`，支撑 interrupt + 抗重启 |
| 前端 | Vue 3 + TS + Vite + Element Plus + Pinia | — |
| 语音 | faster-whisper（本地） | PyAV 解码，无需系统 ffmpeg |
| RAG | 智谱 embedding + numpy + rank_bm25 | 不引向量数据库 |
| 配置 | python-dotenv | 从 `backend/.env` 读（模板在根目录 `.env.example`） |

## 目录结构

```
job-copilot/
├── README.md              # 项目说明 + 快速开始（对外，面试官会看）
├── CLAUDE.md              # 本文件
├── LICENSE
├── .env.example           # 环境变量模板（复制为 backend/.env）
├── backend/               # 后端：FastAPI + LangGraph
│   ├── src/
│   │   ├── main.py        # 入口（建表、CORS、限流、注册路由）
│   │   ├── api/           # 路由层：auth/resume/resume_optimize/jd/interview/voice/knowledge
│   │   ├── graph/         # LangGraph 核心
│   │   │   ├── graph.py   #   主图（意图路由 + 四条流程）
│   │   │   ├── nodes/     #   profile / jd_match / resume_optimize / resume_refine / mock_interview
│   │   │   ├── state.py   #   状态定义
│   │   │   ├── config.py  #   LLM 初始化 + 分层选模
│   │   │   ├── prompts.py #   Prompt 集中管理
│   │   │   └── checkpointer.py  # 会话状态持久化
│   │   ├── services/      # 业务服务（解析/匹配/出题/RAG/语音/导出/校验）
│   │   ├── models/ schemas/ core/
│   │   └── ...
│   ├── test_*.py          # 分阶段验证脚本（非单元测试，见 backend/README.md）
│   └── requirements.txt
├── web/                   # 前端：Vue 3 + TS
│   ├── src/{views,api,stores,router,styles,components,types}
│   └── tests/e2e/         # Playwright 端到端测试
├── docs/                  # 产品方案 / 技术架构 / 行动计划 / 前端需求 / screenshots
├── openspec/              # 规范驱动开发（先写 spec 再实现）
├── amlei-resume/          # 简历能力的参考实现来源（非运行时依赖，见其 README）
└── src/                   # 早期 CLI 原型（仅留档）
```

## 运行方式

完整步骤见 [README](README.md)。要点：

```bash
# 后端（必须用 -m 模块方式，且端口必须是 8001，前端代理写死指向它）
cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
python -m playwright install chromium      # 简历 PDF 导出用
cp ../.env.example .env                    # 然后填 LLM_API_KEY
python -m src.main

# 前端
cd web && npm install && npm run dev       # http://localhost:3000
```

**易踩的坑（勿改坏）**：
- `python src/main.py` 会报 `ModuleNotFoundError: No module named 'src'`，必须用 `python -m src.main`。
- `PORT` 默认值是 8000，但前端代理指向 8001，所以要靠 `.env` 里的 `PORT=8001`。
- 依赖要装到 `backend/.venv`，不要污染全局 Python。

## 开发规范

1. **中文注释为主**——负责人技术薄弱，注释帮 ta 理解每段代码在干嘛。
2. **渐进式开发**：先跑通，再加能力；一次改一件事。
3. **简单优先**：不过度抽象、不提前优化。Simplicity first。
4. **Prompt 集中管理**：所有提示词放 `backend/src/graph/prompts.py`，便于调优和复用。
5. **每个节点函数写清职责**：用 docstring 说明这个节点做什么、输入输出是什么。
6. **不要提交**：`.env`、`*.db`、`.venv/`、`node_modules/`、`.verify/`（已在 `.gitignore` 排除，勿用 `git add -f` 绕过）。

## LangGraph 关键概念（给后续会话快速回忆）

- **StateGraph**：状态机。节点是函数，边控制流转。
- **状态（TypedDict）**：主状态 `FullAgentState`（`messages` 用 `add_messages` reducer 自动累加）；各流程有自己的扩展状态。
- **节点（node）**：接收 state、返回 state 部分更新的函数。
- **条件边**：做意图路由（主图的 `router`）与流程内分支（各 `route_after_*`）。
- **回边**：简历优化里 `resume_evaluate`/`resume_validate` 不通过会回到 `resume_generate` 重写——把"反思-修正"做成图上的环。
- **interrupt + checkpointer**：面试子图与简历精修子图用它实现"跨 HTTP 请求等用户输入 + 抗进程重启"。`thread_id` 决定恢复哪条会话。

**三张图**（详见 [docs/技术架构.md](docs/技术架构.md)）：

| 图 | 位置 | 范式 |
|---|---|---|
| 主图 | `graph/graph.py` | 意图路由 + 四条直线流程（无 checkpointer，一次跑完） |
| 面试子图 | `graph/nodes/mock_interview.py` | interrupt 长程会话 |
| 简历精修子图 | `graph/nodes/resume_refine.py` | interrupt 人机协同 |

## 当前进度

**已交付**（v0.1 → v0.7 全部完成）：
用户认证 · 简历解析建画像 · JD 匹配（SSE 流式）· 简历优化与精修（多主题 + PDF 导出 + 防编造校验）· 模拟面试（多轮追问 + 节奏自主决策 + 结构化复盘）· 面经库 RAG · 语音面试

**待办 / 已知缺口**：
- 用户级限流（目前仅 IP 级，见 `backend/src/core/limiter.py`）
- 部署上线（`web/.env.production` 里的域名是占位值）
- 若改动能力行为，记得同步 `openspec/specs/`（目前 specs 落后于已实现能力）

## OpenSpec（规范驱动开发）

本项目用 OpenSpec 管理变更：先把能力写成 spec（行为规格），再实现。新增/修改任何能力，都应先在 `openspec/changes/` 建变更，而不是直接改 `openspec/specs/`。

- `openspec/AGENTS.md` — OpenSpec 指引与编写规范（**写 spec 前先读**）
- `openspec/project.md` — 项目上下文
- `openspec/specs/` — 已交付能力的规范
- `openspec/changes/` — 进行中的变更（含 `archive/`）

工作流：explore → propose → apply → sync → archive。

## 常见开发任务

### 如何添加一个新的业务节点

```python
# 1. 在 backend/src/graph/nodes/ 下创建新文件，如 foo.py
from src.graph.config import get_llm
from src.graph.state import FullAgentState

def foo_node(state: FullAgentState) -> dict:
    """
    做某件事的节点。
    输入：state
    输出：该节点要更新的 state 片段
    """
    return {"...": ...}

# 2. 在 backend/src/graph/graph.py 中注册节点
builder.add_node("foo", foo_node)
builder.add_edge("router", "foo")     # 或加条件边做路由
```

**面试讲点**：加新功能 = 加一个节点 + 配一条边，不用改别的分支。这是状态机的解耦优势。

### 调试技巧

- **打印调试**：节点里 `print()` 或 `pprint(state)` 看传入的 state。
- **看会话状态**：面试/精修流程的状态在 `backend/interview_checkpoints.db` 里，`graph.get_state(config)` 可读。
- **Prompt 调优**：改 `backend/src/graph/prompts.py`，重启后端即生效。
- **前端验证**：`web/.verify/*.mjs` 是 Playwright 验证脚本（未纳入版本管理），可参考写法。

### 环境变量说明

关键变量（模板与完整注释见根目录 `.env.example`）：

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | LLM 服务商 API Key（**唯一必填**） |
| `LLM_BASE_URL` | 接口地址（智谱 `https://open.bigmodel.cn/api/paas/v4`） |
| `LLM_MODEL` | 快档模型（评估/对话），默认 `glm-4-flash` |
| `LLM_MODEL_STRONG` | 主力档模型（出题/复盘/解析），默认 `glm-4.5` |
| `PORT` | 后端端口，**必须 8001**（前端代理指向它） |
| `JWT_SECRET_KEY` | 上线必须换成强随机串 |

**注意**：`backend/.env` 含敏感信息，已在 `.gitignore` 排除，不要提交到 git。

---

## 相关文档

- [README](README.md) — 对外说明 + 快速开始（面试官视角）
- [产品方案](docs/产品方案.md) — PRD + 商业分析 + AI 能力边界（面试主讲）
- [技术架构](docs/技术架构.md) — 架构设计与面试讲点（已对齐现状）
- [行动计划](docs/行动计划.md) — 开发前的路线图（**历史文档**，与现状有出入）
- [前端页面需求](docs/前端页面需求.md) — 前端需求（**历史文档**）
- [backend/README.md](backend/README.md) · [web/README.md](web/README.md)
