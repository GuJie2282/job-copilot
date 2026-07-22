# Spec: 个人画像持久化（user-profile）

## MODIFIED Requirements

### Requirement: 画像持久化

系统 SHALL 将用户的个人画像持久化存储到数据库，按用户维度维护（每个用户仅维护一份当前画像），供 JD 匹配、简历优化、模拟面试等下游能力读取。

#### Scenario: 首次保存画像
- **WHEN** 用户首次建立画像并确认
- **THEN** 系统 SHALL 将完整画像（含基础信息、教育、工作、技能、项目、求职目标及字段置信度）写入数据库
- **AND** 系统 SHALL 以用户标识关联画像记录
- **AND** 系统 SHALL 记录创建时间

#### Scenario: 更新画像
- **WHEN** 用户编辑并保存画像
- **THEN** 系统 SHALL 覆盖更新该用户的画像记录
- **AND** 系统 SHALL 更新修改时间戳
- **AND** 系统 SHALL 完整保留画像所有结构化字段（含不定长的经历与技能列表）

#### Scenario: 读取画像
- **WHEN** 下游能力（如 JD 匹配）需要用户画像
- **THEN** 系统 SHALL 能按用户标识读取完整画像
- **AND** 系统 SHALL 同时返回画像与各字段置信度

#### Scenario: 画像唯一性
- **WHEN** 同一用户多次建立或更新画像
- **THEN** 系统 SHALL 保证每个用户仅有一份当前画像
- **AND** 新的保存操作 SHALL 覆盖既有记录，而非产生重复

#### Scenario: 删除画像
- **WHEN** 用户请求删除画像
- **THEN** 系统 SHALL 删除该用户的画像记录
- **AND** 此后读取 SHALL 返回"无画像"状态

#### Scenario: 存储完整性
- **WHEN** 系统持久化画像
- **THEN** 系统 SHALL 完整保留画像中的不定长列表数据（教育经历、工作经历、项目、技能、求职目标）
- **AND** 系统 SHALL 保证读取后能无损还原画像结构

#### Scenario: 画像缺失可识别
- **WHEN** 下游能力请求一个尚未建立画像的用户
- **THEN** 系统 SHALL 返回明确的"画像不存在"状态
- **AND** 系统 SHALL 支持下游据此引导用户先建立画像

---

## ADDED Requirements

（此变更对 user-profile 仅落实既有持久化要求，不新增其他 Requirement）

---

## REMOVED Requirements

（此变更不删除任何 Requirements）
