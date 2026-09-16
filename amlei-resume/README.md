# amlei-resume（参考实现，非本项目运行时依赖）

本目录**不是** job-copilot 的功能代码，也**不被** job-copilot 运行时导入。它是一份独立的「简历撰写」Agent Skill（作者 amlei），在本项目里作为**参考实现**保留，原因：

job-copilot 的简历能力在实现时移植了它的部分设计，代码注释里做了标注：

| 移植来源 | 落到本项目的位置 |
|---|---|
| `references/resume-evaluator.md`（六维评估标准） | [backend/src/services/resume_evaluator.py](../backend/src/services/resume_evaluator.py) |
| `references/themes/*.md`（版式主题） | [backend/src/services/resume_themes/](../backend/src/services/resume_themes/) |
| `scripts/validate_resume.py`（事实校验思路） | [backend/src/services/resume_validator.py](../backend/src/services/resume_validator.py) |
| `references/export.md`（HTML 装配式导出） | 未采用——改为 Playwright 服务端渲染 A4，见 [resume_exporter.py](../backend/src/services/resume_exporter.py) 的对比说明 |

保留它的意义是**保留出处**：能看清哪些是借鉴、哪些是自己重写的判断。其中 `scripts/boss_zhipin.py` 是原作者用于个人求职流程的浏览器自动化脚本，与本项目无关。

> 如果只关心 job-copilot 本身，可以忽略本目录。
