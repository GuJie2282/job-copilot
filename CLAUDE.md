# CLAUDE.md — job-copilot（求职 Copilot）

本文件为 Claude Code 提供项目指引。在这个项目里工作时，**请先读完本文件**。
回答时都使用中文。

---

## 项目概述

**job-copilot（求职 Copilot）** 是一个基于 **LangGraph** 的 AI 求职 Agent，定位为"带记忆的全链路求职教练"。核心能力链路：

```
建立画像 → JD 匹配分析 → 简历定制优化 → 模拟面试 → 复盘沉淀
```

这是一个**个人面试作品集项目**（非商业生产项目），目标是产出一个能演示、有技术深度、体现产品与工程思维的 AI Agent，用于求职。

## ⚠️ 重要：项目负责人背景（协助时务必考虑）

- 负责人正在求职 **AI 产品经理（AI PM）** 方向。
- **技术背景较弱**：调过 LLM API、懂基本概念，但不熟练写代码。
- 因此协助原则：
  - **降低技术门槛**：代码多写中文注释，循序渐进；复杂概念要解释清楚。
  - 优先保证"**能跑起来、能看懂**"，再追求工程优雅。不堆砌高级用法。
  - 这是面试项目，**技术选型要能讲出道理**（为什么用 LangGraph、为什么这样设计状态机）——适当点出"这里面试可以怎么讲"。

## 技术栈

| 项 | 选型 | 说明 |
|----|------|------|
| 语言 | Python 3.10+ | AI Agent 生态主流 |
| Agent 框架 | **LangGraph** | 状态机驱动的 Agent 编排，面试加分项 |
| LLM 接入 | LangChain `ChatOpenAI` | OpenAI 兼容接口，默认接 DeepSeek，可换 OpenAI/通义/智谱 |
| 记忆 | MemorySaver（内存） | MVP；后续可换 SQLite/Postgres 持久化 |
| 配置 | python-dotenv | 从 .env 读 API Key |

## 目录结构

```
job-copilot/
├── CLAUDE.md              # 本文件
├── README.md              # 项目说明 + 快速开始
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量模板（复制为 .env 后填 key）
├── .gitignore
├── docs/                  # 文档
│   ├── 产品方案.md        # PRD + 商业分析 + AI 能力边界
│   ├── 行动计划.md        # 开发路线图
│   └── 技术架构.md        # 技术架构设计
├── src/                   # 源码
│   ├── main.py            # 入口（终端 CLI 对话）
│   ├── config.py          # 配置（LLM 初始化）
│   ├── state.py           # AgentState 状态定义
│   ├── graph.py           # LangGraph 图定义（核心）
│   ├── prompts.py         # 所有 Prompt 集中管理
│   ├── nodes/             # 各业务节点（每个能力一个）
│   │   └── chatbot.py     # 对话节点（MVP 先这一个）
│   └── tools/             # 工具（联网搜索等，后续扩展）
├── tests/                 # 测试
└── data/                  # 数据（用户画像/面经，后续扩展）
```

## 运行方式

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活（三选一）：
#    PowerShell:  .venv\Scripts\Activate.ps1     （报"禁止运行脚本"则先执行一次
#                  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned）
#    Git Bash:    source .venv/Scripts/activate
#    cmd:         .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
#    PowerShell: Copy-Item .env.example .env      Git Bash: cp .env.example .env
#    然后编辑 .env 填入 LLM_API_KEY

# 5. 启动
python -m src.main
```

## 开发规范

1. **中文注释为主**——负责人技术薄弱，注释帮 ta 理解每段代码在干嘛。
2. **渐进式开发**：先跑通单节点对话，再加意图路由和业务节点。
3. **简单优先**：不过度抽象、不提前优化。Simplicity first。
4. **Prompt 集中管理**：所有提示词放 `src/prompts.py`，便于调优和复用。
5. **每个节点函数写清职责**：用 docstring 说明这个节点做什么、输入输出是什么。

## LangGraph 关键概念（给后续会话快速回忆）

- **StateGraph**：状态机。节点是函数，边控制流转。
- **AgentState（TypedDict）**：在各节点间传递的状态。`messages` 用 `add_messages` reducer 自动累加历史。
- **节点（node）**：接收 state、返回 state 部分更新的函数。
- **边（edge）**：`START → node → END`，或用条件边（conditional edge）做意图路由。
- **checkpointer + thread_id**：实现多轮对话记忆（同一 thread_id 共享上下文）。

## 当前进度（MVP）

**已完成**：
- 项目骨架（state / config / graph / prompts / nodes / main）
- 单节点对话 Agent（chatbot），带"求职教练"人设，支持多轮记忆

**待开发**（见 [docs/行动计划.md](docs/行动计划.md)）：
- 意图路由（判断用户要做什么：改简历 / 匹配 JD / 模拟面试）
- 四个业务节点：画像提取 / JD 匹配 / 简历优化 / 模拟面试
- 工具（tools）：如需要联网搜岗位
- 测试与打磨

## 常见开发任务

### 如何添加一个新的业务节点

LangGraph 的设计让加新能力很简单，只需 3 步：

```python
# 1. 在 src/nodes/ 下创建新文件，如 profile.py
from src.config import get_llm
from src.state import AgentState

llm = get_llm()

def profile_node(state: AgentState) -> dict:
    """
    建立用户画像节点。
    输入：state（含 messages）
    输出：{"messages": [AI 的回复]}
    """
    # 调用 LLM 处理...
    return {"messages": [response]}

# 2. 在 src/graph.py 中注册节点
from src.nodes.profile import profile_node

builder.add_node("profile", profile_node)

# 3. 添加边（或条件边）控制流转
builder.add_edge("router", "profile")  # 或用条件边
```

**面试讲点**：加新功能 = 加一个节点 + 配一条边，不用改别的代码。这是状态机的解耦优势。

### 调试技巧

- **打印调试**：在节点函数里加 `print()` 或 `pprint(state)`，看传入的 state 长什么样。
- **LangGraph Studio**：官方可视化调试工具，能画出图、看每步状态变化（进阶用法，项目后期可研究）。
- **Prompt 调优**：改 `src/prompts.py` 里的提示词，重启程序即可生效，不用改代码。

### 环境变量说明

`.env` 文件中的关键配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | LLM 服务商的 API Key | DeepSeek/智谱/OpenAI 的 key |
| `LLM_BASE_URL` | API 地址 | DeepSeek: `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` / `gpt-4o-mini` / `glm-4-flash` |

**注意**：`.env` 文件含敏感信息，已在 `.gitignore` 中排除，不要提交到 git。

## OpenSpec（规范驱动开发）

本项目用 OpenSpec 管理变更：先把能力写成 spec（行为规格），再实现。新增/修改任何能力，都应先在 `openspec/changes/` 建变更，而不是直接改 `openspec/specs/`。

- `openspec/AGENTS.md` — OpenSpec 指引与编写规范（**写 spec 前先读**）
- `openspec/project.md` — 项目上下文
- `openspec/specs/` — 已交付能力的规范（当前含 `conversation`）
- `openspec/changes/` — 进行中的变更

工作流：explore → propose → apply → sync → archive。

---

## 相关文档

- [产品方案](docs/产品方案.md) — PRD + 商业分析 + AI 能力边界（面试主讲）
- [行动计划](docs/行动计划.md) — 开发路线图
- [技术架构](docs/技术架构.md) — 技术设计与面试讲点
