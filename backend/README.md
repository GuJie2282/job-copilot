# 求职 Copilot 后端服务

基于 **FastAPI + LangGraph** 的 AI 求职教练后端：用户认证、简历解析、JD 匹配、简历优化、模拟面试、面经库 RAG、语音转写。

> 想看项目全貌和前后端一起启动的步骤，请先读[根目录 README](../README.md)。本文件只讲后端。

---

## 技术栈

| 层 | 选型 |
|---|---|
| Web 框架 | FastAPI + uvicorn |
| Agent 编排 | **LangGraph**（状态机）· LangChain `ChatOpenAI` |
| 数据库 | SQLAlchemy + SQLite（业务库）· LangGraph `SqliteSaver`（会话状态库） |
| 认证 | JWT（python-jose）+ bcrypt（passlib）+ 邮箱验证码 |
| 限流 | slowapi（IP 级） |
| 语音 | faster-whisper（本地转写）· PyAV 解码音频（**无需系统 ffmpeg**） |
| RAG | 智谱 embedding + numpy 余弦相似度 + rank_bm25 |
| PDF 导出 | playwright（服务端渲染 A4） |

---

## 快速开始

### 1. 安装依赖

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Git Bash；PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium   # 简历 PDF 导出用，约 150MB，只需装一次
```

### 2. 配置环境变量

模板在**仓库根目录**，复制到 `backend/.env`：

```bash
cp ../.env.example .env            # Git Bash；PowerShell: Copy-Item ..\.env.example .env
```

然后至少填 `LLM_API_KEY`（默认服务商是智谱，[注册](https://open.bigmodel.cn/)有免费额度）。
完整变量说明见 [`.env.example`](../.env.example) 内的注释。实际被读取的变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_API_KEY` | 无（**必填**） | 未配置时 LLM 调用会抛 `ValueError` |
| `LLM_BASE_URL` | 按模型名匹配 | 服务商 OpenAI 兼容接口地址 |
| `LLM_MODEL` | `deepseek-chat` | 快档模型（延迟敏感：评估、对话） |
| `LLM_MODEL_STRONG` | `glm-4.5` | 主力档模型（质量敏感：出题、复盘、解析） |
| `PORT` | `8000` | ⚠️ 本地请设为 **8001**（前端代理指向 8001） |
| `HOST` | `0.0.0.0` | 监听地址 |
| `FRONTEND_URL` | `http://localhost:3000` | CORS 白名单 |
| `ENV` | `development` | 非 production 时验证码打印到控制台 |
| `JWT_SECRET_KEY` | 代码内开发用默认值 | **上线必须换成强随机字符串** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access Token 有效期 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh Token 有效期 |
| `REMEMBER_ME_REFRESH_TOKEN_DAYS` | `30` | 勾选「记住我」时的有效期 |
| `DATABASE_URL` | `sqlite:///./job_copilot.db` | 业务库连接串 |
| `WHISPER_MODEL` | `small` | 语音模型：tiny / small / medium |

> 端口：代码里 `PORT` 的默认值是 `8000`，但**前端 vite 代理写死指向 8001**（见 [web/vite.config.ts](../web/vite.config.ts)）。所以必须用模板里的 `PORT=8001`，否则前端所有接口连不上。
> 限流阈值目前在 [core/limiter.py](src/core/limiter.py) 里硬编码（不读 `.env`）。

### 3. 启动

```bash
python -m src.main        # 开发模式（热重载）；服务在 http://localhost:8001
```

> ⚠️ 必须用 **`python -m src.main`**（模块方式）。写成 `python src/main.py` 会把 `backend/src` 当成根目录，直接报 `ModuleNotFoundError: No module named 'src'`。
>
> 也可以：`uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload`

- Swagger UI：http://localhost:8001/docs
- 健康检查：http://localhost:8001/health

**首次启动会自动建表**，无需手动初始化：入口处调用 `Base.metadata.create_all`，并对已存在的表做轻量补列迁移（见 [src/main.py](src/main.py)）。

---

## 目录结构

```
backend/
├── src/
│   ├── main.py              # FastAPI 入口：建表、CORS、限流、注册路由
│   ├── api/                 # 路由层（HTTP 边界）
│   │   ├── auth.py          #   认证
│   │   ├── resume.py        #   简历解析 / 画像 / 头像 / 导出
│   │   ├── resume_optimize.py #  简历优化 + 精修（SSE 流式）
│   │   ├── jd.py            #   JD 匹配（SSE 流式 + 增量补充）
│   │   ├── interview.py     #   模拟面试会话
│   │   ├── voice.py         #   语音转写
│   │   └── knowledge.py     #   面经库
│   ├── graph/               # LangGraph 核心
│   │   ├── graph.py         #   主图（意图路由 + 四条流程）
│   │   ├── state.py         #   状态定义
│   │   ├── nodes/           #   节点：profile / jd_match / resume_optimize / resume_refine / mock_interview
│   │   ├── checkpointer.py  #   会话状态持久化（SqliteSaver）
│   │   ├── config.py        #   LLM 初始化 + 分层选模
│   │   └── prompts.py       #   Prompt 集中管理
│   ├── services/            # 业务逻辑（解析/匹配/出题/复盘/RAG/语音/导出/校验）
│   ├── models/              # SQLAlchemy 数据模型
│   ├── schemas/             # Pydantic 请求/响应
│   └── core/                # 安全(JWT/bcrypt)、限流、日志、SSE 工具
├── test_*.py                # 分阶段验证脚本（见下）
├── requirements.txt
└── README.md
```

---

## API 概览

所有路由统一挂在 `/api` 下，前端通过 vite 代理访问。

| 分组 | 前缀 | 主要端点 |
|---|---|---|
| 认证 | `/api/auth` | `POST /register`、`/login`、`/send-code`、`/logout`、`/refresh` |
| 简历解析 | `/api/resume` | `POST /parse-file`、`/parse-text`、`/parse-stream`、`POST /update-profile`、`POST /avatar`、`GET /profile` |
| 简历优化 | `/api/resume` | `POST /generate`、`GET /list`、`GET /{id}`、`GET /{id}/pdf`、`POST /{id}/refine`、`/{id}/refine-stream`、`/{id}/finalize` |
| JD 匹配 | `/api/jd` | `POST /match`、`POST /{id}/enrich`、`GET /history`、`GET /results/{id}` |
| 模拟面试 | `/api/interview` | `POST /sessions`、`POST /sessions/{id}/answer`、`GET /sessions/{id}`、`GET /sessions/{id}/debrief` |
| 语音转写 | `/api/interview/voice` | `POST /transcribe` |
| 面经库 | `/api/knowledge` | `GET /personal`、`/personal/weakness`、`GET /company`、`POST /company/ugc` |

---

## 数据存储

| 库文件 | 内容 | 生成方式 |
|---|---|---|
| `backend/job_copilot.db` | 业务资产：用户、画像、JD 匹配、简历、面经 | 启动时 `create_all` 自动建表 |
| `backend/interview_checkpoints.db` | 会话状态：面试进度、精修草稿 | LangGraph `SqliteSaver` 运行时写入 |

两者已在 `.gitignore` 排除。重置数据库：删掉对应的 `.db` 文件后重启即可。

---

## 关于 `test_*.py`

`backend/` 根目录下的 `test_*.py` **不是单元测试套件**，而是开发过程中**分阶段的验证脚本**（命名带 `_spike` / `_smoke` / `_e2e` 的尤其明显）：它们需要真实 LLM Key 和数据库，用于验证某个能力在真实链路上跑得通（如 `test_interrupt_spike.py` 验证 interrupt 行为、`test_rag_integration.py` 验证 RAG 数据飞轮）。

运行方式（在 `backend/` 目录下，用模块方式，保证 `import src` 可用）：

```bash
python -m test_rag_integration        # 注意：不是 python test_rag_integration.py
```

正式的自动化测试在前端：[web/tests/e2e/](../web/tests/e2e/)（Playwright 端到端）。

---

## 常见问题

**Q：注册时验证码在哪？**
开发环境（`ENV=development`，默认）会把验证码打印到后端控制台，见 [services/code_service.py](src/services/code_service.py)。

**Q：Token 有效期？**
Access Token 15 分钟，Refresh Token 7 天（勾选「记住我」30 天），前端会自动刷新。

**Q：换了 LLM 服务商要改代码吗？**
不用。改 `.env` 里的 `LLM_BASE_URL` + `LLM_MODEL` + `LLM_MODEL_STRONG` + Key 即可。

**Q：语音转写需要装 ffmpeg 吗？**
不需要。音频解码走 PyAV（由 faster-whisper 的依赖带入）。

**Q：限流能按用户吗？**
目前只有 IP 级全局限流，用户级限流未实现（见 [core/limiter.py](src/core/limiter.py) 的 `get_user_id`）。
