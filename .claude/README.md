# .claude 文件夹说明

这个文件夹包含 **job-copilot** 项目的 Claude Code 相关配置。

## 文件说明

### `settings.json`
项目主配置文件，包含：
- **Python 配置**：虚拟环境路径、Python 解释器设置
- **TypeScript 配置**：严格模式、类型检查配置
- **LLM 配置**：DeepSeek/OpenAI API 配置
- **权限配置**：允许的 Bash 命令（开发相关）
- **终端配置**：Shell 类型、会话前钩子
- **UI 配置**：主题、字体设置

### `skills/` （可选）
项目特定的 Claude Code 技能脚本，例如：
- `langgraph-debug.claude` - LangGraph 调试技能
- `frontend-dev.claude` - 前端开发辅助技能

### `memory/` （可选）
项目级别的记忆文件，用于存储：
- 用户画像模板
- 常用 Prompt 模板
- 开发规范和约定

## 使用方式

Claude Code 会自动读取 `settings.json` 中的配置。

**核心功能**：
1. **自动激活 Python 虚拟环境**：每次会话开始时自动激活 `.venv`
2. **TypeScript 严格模式**：前端代码自动进行类型检查
3. **权限管理**：预授权常用开发命令，减少提示
4. **LLM 配置**：统一管理 API Key 和模型设置

## 开发工作流

### 启动后端（LangGraph Agent）
```bash
# Claude 会自动激活虚拟环境
python -m src.main
```

### 启动前端（Vue 3）
```bash
cd web
npm run dev
```

### 运行测试
```bash
# 后端测试
pytest

# 前端测试
cd web
npm run test
```

## 注意事项

1. **API Key 安全**：`.env` 文件包含敏感信息，已在 `.gitignore` 中排除
2. **虚拟环境**：Python 依赖安装在 `.venv` 中，不要提交到 Git
3. **TypeScript 严格模式**：前端代码必须通过类型检查才能提交
4. **权限控制**：只允许项目开发相关的命令，确保安全

## 自定义配置

如需修改配置，编辑 `settings.json` 文件：

**修改 LLM 提供商**：
```json
"llm": {
  "defaultProvider": "openai",  // 改为 openai
  ...
}
```

**添加新的权限**：
```json
"permissions": {
  "allow": [
    {
      "tool": "Bash",
      "prompt": "你的命令描述"
    }
  ]
}
```

**修改 UI 主题**：
```json
"ui": {
  "theme": "light"  // 改为 light 主题
}
```

## 相关文档

- [Claude Code 官方文档](https://docs.anthropic.com/claude-code)
- [settings.json 架构](https://raw.githubusercontent.com/Anthropic/claude-code/main/settings-schema.json)
- [项目 CLAUDE.md](../CLAUDE.md)
- [前端 README](../web/README.md)
