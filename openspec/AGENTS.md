# OpenSpec — job-copilot

本项目用 OpenSpec 做"规范驱动开发"：先把要做的能力写成 spec（行为规格），再实现。每个变更（change）走 propose → apply → sync → archive 流程。

## 目录结构

```
openspec/
├── AGENTS.md                          # 本文件（给 AI agent 的 OpenSpec 指引）
├── project.md                         # 项目上下文
├── specs/                             # 已交付能力的规范（source of truth）
│   └── <capability>/spec.md
└── changes/                           # 进行中的变更
    └── <change-id>/
        ├── .openspec.yaml             # schema: spec-driven + created 日期
        ├── proposal.md                # Why / What Changes / Capabilities / Impact
        ├── design.md                  # 设计决策与权衡
        ├── tasks.md                   # 实施任务清单
        └── specs/<capability>/spec.md # 该变更的 spec 增量（delta）
```

## 工作流

1. **explore**：想清楚要做什么、为什么（可对话澄清）
2. **propose**：在 `changes/<id>/` 生成 proposal + design + tasks + spec delta
3. **apply**：按 `tasks.md` 逐步实施
4. **sync**：实施完成后，把 delta 合并进 `openspec/specs/`
5. **archive**：归档已完成的 change

> 新增/修改任何能力，都应先在 `changes/` 建变更，而不是直接改 `specs/`。

## 编写规范（必须遵守）

### spec 是行为规格
- 用 `系统 SHALL ...` 描述系统行为，**不绑定具体实现技术**（写"持久化用户画像"而非"用 SQLite 存"）。技术选型放 `design.md` / `tasks.md`。
- 每个 Requirement 下用 `#### Scenario` 列场景：
  ```
  #### Scenario: <场景名>
  - **WHEN** <条件>
  - **THEN** <预期行为>
  ```
- **主 spec**（`specs/` 下）用 `## Requirements`；**变更 delta**（`changes/<id>/specs/` 下）用 `## ADDED Requirements` / `## MODIFIED Requirements` / `## REMOVED Requirements`。

### change 文档面向真实开发
- **不带变更对比痕迹**：决策标题不用"（保留/推翻/修改原方案）""（新增）"等标注；正文不写"原方案…""本次变更相对前一版…"。权衡可保留 rationale，但用中性措辞。
- **不写 demo 说法**：不写"只做前端 demo"，任务清单按正常实施任务编写。

### .openspec.yaml 格式
```yaml
schema: spec-driven
created: YYYY-MM-DD
```

## 能力命名约定
- capability 用 **kebab-case 英文**：如 `conversation`、`resume-optimization`、`jd-matching`、`mock-interview`、`user-profile`。
- spec.md 正文用**中文**撰写。
- change-id 用动词短语 kebab-case：如 `add-resume-optimization`、`add-mock-interview`。
