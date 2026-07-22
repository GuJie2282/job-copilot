# 🚀 快速启动指南

## 环境配置

### 1. 配置后端环境变量

编辑 `backend/.env` 文件，添加以下内容：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./job_copilot.db

# JWT 配置
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_DAYS=7

# 环境配置
ENV=development

# CORS 配置
FRONTEND_URL=http://localhost:3000

# 限流配置
RATE_LIMIT_GLOBAL="100/minute"
RATE_LIMIT_SEND_CODE="5/minute"

# 服务器端口
PORT=8001

# ========================================
# LLM 配置（重要！）
# ========================================
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 2. 获取 API Key

#### 选项 A：使用 DeepSeek（推荐，免费额度大）
1. 访问 https://platform.deepseek.com/
2. 注册账号
3. 进入 API Keys 页面
4. 创建新的 API Key
5. 复制 API Key 到 `.env` 文件的 `LLM_API_KEY`

#### 选项 B：使用 OpenAI
1. 访问 https://platform.openai.com/
2. 注册账号
3. 进入 API Keys 页面
4. 创建新的 API Key
5. 配置：
```bash
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

#### 选项 C：使用其他兼容模型
只要兼容 OpenAI API 格式即可，例如：
- 智谱 AI (zhipu.ai)
- 通义千问 (qianwen.aliyun.com)
- 等等

---

## 启动服务

### 3. 启动后端服务

打开终端（Terminal / PowerShell / Git Bash），进入后端目录：

```bash
cd backend
python -m src.main
```

**成功标志**：
- 看到 `Uvicorn running on http://0.0.0.0:8001`
- 看到 `Application startup complete`

**验证后端**：
- 访问 http://localhost:8001/docs
- 应该看到 Swagger API 文档
- 检查是否有 `/api/resume/health` 端点

### 4. 启动前端服务

**打开新的终端**（保持后端运行），进入前端目录：

```bash
cd web
npm run dev
```

**成功标志**：
- 看到 `Local: http://localhost:3000/`
- 看到 `Network: use --host to expose`

**验证前端**：
- 访问 http://localhost:3000
- 应该看到登录页面或主页

---

## 测试功能

### 5. 测试简历解析

#### 方式 A：通过 API 测试（推荐）

**使用示例文本**：
```bash
curl -X POST "http://localhost:8001/api/resume/parse-text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "张三\n电话：13800138000\n邮箱：zhangsan@example.com\n\n教育背景\n清华大学 计算机科学与技术 本科 2018-2022\n\n工作经历\nABC科技公司 软件工程师 2022-至今\n\n技能\nPython, Java, 机器学习"
  }'
```

#### 方式 B：通过前端界面测试

1. 访问 http://localhost:3000
2. 登录或注册账号
3. 进入"简历解析"页面
4. 选择"粘贴文本"
5. 粘贴示例简历文本
6. 点击"开始解析"

**预期结果**：
- 显示"正在解析..."
- 显示文本预览
- 显示质量分数
- 显示个人画像
- 显示置信度标签
- 显示"完成后引导"

### 6. 测试文件上传

1. 准备一份 PDF 或 Word 简历文件
2. 在前端选择"上传文件"
3. 拖拽或选择文件
4. 点击"开始解析"

**预期结果**：
- 显示上传进度
- 显示解析状态
- 显示解析结果

---

## 常见问题排查

### 问题 1：后端启动失败

**症状**：
```
ModuleNotFoundError: No module named 'langgraph'
```

**解决**：
```bash
cd backend
pip install -r requirements.txt
```

### 问题 2：前端启动失败

**症状**：
```
Cannot find module '@/components/XXX'
```

**解决**：
```bash
cd web
npm install
npm run dev
```

### 问题 3：API 调用失败

**症状**：
- 网络错误
- CORS 错误

**检查**：
1. 后端是否正常运行（端口 8001）
2. 前端是否正常运行（端口 3000）
3. `.env` 文件中的 `FRONTEND_URL` 是否正确

### 问题 4：LLM 调用失败

**症状**：
- 500 错误
- 提示"LLM 提取失败"

**检查**：
1. API Key 是否正确
2. 网络是否能访问 LLM 服务
3. 查看后端日志

---

## 功能验证清单

### 后端 API 测试
- [ ] 健康检查：`GET /api/resume/health`
- [ ] 文件上传：`POST /api/resume/parse-file`
- [ ] 文本解析：`POST /api/resume/parse-text`
- [ ] 获取示例：`GET /api/resume/sample-resumes`

### 前端界面测试
- [ ] 页面能正常打开
- [ ] 输入方式选择正常
- [ ] 文件上传界面显示
- [ ] 文本输入界面显示
- [ ] 错误提示友好

### 端到端测试
- [ ] 能选择"粘贴文本"
- [ ] 能输入简历文本
- [ ] 能看到解析进度
- [ ] 能看到文本预览
- [ ] 能看到画像展示
- [ ] 能看到置信度标签
- [ ] 能看到完成后引导

---

## 成功标准

### 最小可用版本（MVP）✅
- 后端服务启动成功
- 前端页面加载成功
- 能通过文本粘贴解析简历
- 能显示画像结果

### 完整版本 ✅
- 所有上述 MVP 标准
- 能上传文件解析
- 能手动填写画像
- 能编辑和导出画像

---

## 预期输出

### 后端日志（成功启动）
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 前端日志（成功启动）
```
VITE v5.0.0  ready in 1234 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
➜  press h to show help
```

### API 响应示例
```json
{
  "status": "success",
  "message": "文本解析成功",
  "data": {
    "text_length": 245,
    "source": "text"
  },
  "quality_score": 0.85,
  "profile": {
    "name": "张三",
    "phone": "13800138000",
    "email": "zhangsan@example.com"
  },
  "confidence": {
    "name": {
      "score": 0.95,
      "level": "高"
    }
  }
}
```

---

## 下一步

### 如果测试成功
✅ 恭喜！功能已就绪
- 可以继续 Phase 6（测试与打磨）
- 或 Phase 7（演示准备）
- 或开始使用真实简历测试

### 如果测试失败
🔧 检查常见问题：
1. 后端是否启动（端口 8001）
2. 前端是否启动（端口 3000）
3. API Key 是否配置
4. 网络连接是否正常

---

**需要帮助？**
- 查看后端日志：`backend/` 目录
- 查看前端日志：浏览器控制台
- 检查 API 文档：http://localhost:8001/docs

---

**准备好了吗？开始配置和测试吧！** 🚀
