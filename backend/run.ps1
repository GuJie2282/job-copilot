# 求职 Copilot 后端服务启动脚本

# 确保在 backend 目录
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptPath

# 运行应用
python -m src.main
