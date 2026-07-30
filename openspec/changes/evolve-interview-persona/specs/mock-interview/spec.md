# Spec Delta: 模拟面试（mock-interview）— 人设贯穿出题 + 去反问

## MODIFIED Requirements

### Requirement: 面试官人设

系统 SHALL 提供可配置的面试官人设，由风格与角色两个正交维度组成，压力面作为风格叠加；人设 SHALL 贯穿出题口吻、提问语气与追问，而非仅作用于追问。

#### Scenario: 风格影响出题口吻
- **WHEN** 用户配置人设风格
- **THEN** 系统 SHALL 支持多种风格（严肃、轻松、风趣、温和、压力）
- **AND** 所选风格 SHALL 影响出题的题目口吻（压力面带质疑压迫、轻松面口语亲切）
- **AND** 所选风格 SHALL 影响追问语气

#### Scenario: 角色配置
- **WHEN** 配置人设角色
- **THEN** 系统 SHALL 按公司、职位、资深度装配角色背景
- **AND** 角色背景 SHALL 影响提问的专业方向与深度

#### Scenario: 压力面叠加
- **WHEN** 用户选择压力面
- **THEN** 系统 SHALL 在所选题型基础上叠加挑战性人设（质疑、施压），贯穿出题与追问
- **AND** 压力面 SHALL NOT 替换原有题型，而是作为风格层叠加

#### Scenario: 预置人设组合
- **WHEN** 用户不自行配置人设
- **THEN** 系统 SHALL 提供若干预置人设组合供选择

---

### Requirement: 换题与结束

系统 SHALL 由评估模型自主决定换题与结束的时机，受防崩盘护栏约束；系统 SHALL NOT 包含反问环节。

#### Scenario: 切换下一题
- **WHEN** 模型判断当前题无需继续且护栏允许
- **THEN** 系统 SHALL 切换到下一题

#### Scenario: 模型主动结束
- **WHEN** 模型基于整场表现判断无需继续，且已达最低总轮数
- **THEN** 系统 SHALL 结束面试并进入复盘

#### Scenario: 用户主动结束
- **WHEN** 用户主动选择结束
- **THEN** 系统 SHALL 基于已有对话流水生成复盘并标注提前结束

#### Scenario: 无反问环节
- **WHEN** 面试推进至题库末尾或模型决定收尾
- **THEN** 系统 SHALL 直接进入结束与复盘
- **AND** 系统 SHALL NOT 设置反问环节
