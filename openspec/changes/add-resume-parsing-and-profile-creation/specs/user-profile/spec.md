# Spec: 简历解析与个人画像（user-profile + resume-parsing）

## ADDED Requirements

### Requirement: 简历文件解析

系统 SHALL 支持从用户上传的 PDF 和 docx 文件中提取文本内容。

#### Scenario: 上传可搜索的 PDF
- **WHEN** 用户上传一个可搜索的 PDF 文件（非扫描件）
- **THEN** 系统 SHALL 成功提取文本内容
- **AND** 提取的文本 SHALL 保留基本结构（段落、分块）
- **AND** 响应时间 SHALL 小于 5 秒（文件大小 < 5MB）

#### Scenario: 上传 Word 文档
- **WHEN** 用户上传一个 .docx 文件
- **THEN** 系统 SHALL 成功提取文本内容
- **AND** 提取的文本 SHALL 保留段落结构

#### Scenario: 上传扫描件 PDF
- **WHEN** 用户上传一个扫描件 PDF（全是图片，无文本层）
- **THEN** 系统 SHALL 检测到这是扫描件
- **AND** 系统 SHALL 返回友好的错误提示
- **AND** 错误提示 SHALL 包含降级方案建议（复制粘贴文本、手动填写）

#### Scenario: 上传加密的 PDF
- **WHEN** 用户上传一个有密码保护的 PDF 文件
- **THEN** 系统 SHALL 检测到文件已加密
- **AND** 系统 SHALL 返回错误提示"文件已加密，请先解除密码保护"
- **AND** 系统 SHALL 不尝试解析文件内容

#### Scenario: 上传不支持的文件格式
- **WHEN** 用户上传一个非 PDF/docx 的文件（如 .jpg、.png）
- **THEN** 系统 SHALL 返回错误提示"文件格式不支持，请上传 PDF 或 Word 文档"
- **AND** 系统 SHALL 列出支持的格式列表

#### Scenario: 上传过大的文件
- **WHEN** 用户上传一个大于 10MB 的文件
- **THEN** 系统 SHALL 检测到文件过大
- **AND** 系统 SHALL 返回警告"文件过大，可能是扫描件，建议使用可搜索的 PDF"
- **AND** 系统 SHALL 提示用户可以复制粘贴文本

---

### Requirement: 文本粘贴输入

系统 SHALL 支持用户直接粘贴简历文本进行解析。

#### Scenario: 粘贴简历文本
- **WHEN** 用户粘贴一段完整的简历文本（>200 字符）
- **THEN** 系统 SHALL 接受文本输入
- **AND** 系统 SHALL 进行文本质量检测
- **AND** 系统 SHALL 继续后续提取流程

#### Scenario: 粘贴的文本过短
- **WHEN** 用户粘贴的文本少于 200 字符
- **THEN** 系统 SHALL 检测到文本过短
- **AND** 系统 SHALL 显示警告"文本过少，可能不是完整简历"
- **AND** 系统 SHALL 询问用户是否继续

#### Scenario: 粘贴的文本是非简历内容
- **WHEN** 用户粘贴的文本缺少常见的简历关键词（如"教育"、"工作"、"经历"）
- **THEN** 系统 SHALL 检测到文本结构不清晰
- **AND** 系统 SHALL 显示警告"文本中缺少常见的简历关键词"
- **AND** 系统 SHALL 建议用户检查或补充内容

---

### Requirement: 文本质量检测

系统 SHALL 评估提取或粘贴的文本质量，并给出质量分数。

#### Scenario: 高质量文本
- **WHEN** 文本质量分数 ≥ 0.8
- **THEN** 系统 SHALL 认定为高质量文本
- **AND** 系统 SHALL 直接进行 LLM 提取，无需额外警告

#### Scenario: 中等质量文本
- **WHEN** 文本质量分数在 0.6 - 0.8 之间
- **THEN** 系统 SHALL 认定为中等质量
- **AND** 系统 SHALL 显示警告"解析成功，但可能存在问题"
- **AND** 系统 SHALL 列出具体问题（如"文本过少"、"结构不清晰"）
- **AND** 系统 SHALL 允许用户继续或修改文本

#### Scenario: 低质量文本
- **WHEN** 文本质量分数 < 0.6
- **THEN** 系统 SHALL 认定为低质量
- **AND** 系统 SHALL 强烈建议用户检查或修改文本
- **AND** 系统 SHALL 提供降级方案（手动填写、重新上传）

#### Scenario: 质量检测指标
- **WHEN** 系统评估文本质量
- **THEN** 系统 SHALL 综合考虑以下指标：
  - 文本长度（<200 字符扣分）
  - 中文比例（<30% 扣分）
  - 结构完整性（缺少关键词扣分）
  - 乱码程度（特殊字符过多扣分）

---

### Requirement: LLM 结构化提取

系统 SHALL 调用 LLM 从文本中提取结构化个人画像。

#### Scenario: 标准提取（高质量文本）
- **WHEN** 文本质量分数 ≥ 0.8
- **THEN** 系统 SHALL 使用标准提取 Prompt
- **AND** 系统 SHALL 要求 LLM 提取完整的画像字段
- **AND** 系统 SHALL 不添加额外的容错提示

#### Scenario: 容错提取（低质量文本）
- **WHEN** 文本质量分数 < 0.8
- **THEN** 系统 SHALL 使用容错提取 Prompt
- **AND** Prompt SHALL 包含容错规则：
  - "时间不明确 → 填'未知'"
  - "信息找不到 → 填 null"
  - "宁可留空，不要编造"
- **AND** 系统 SHALL 优先提取核心信息（姓名、教育、工作）

#### Scenario: 提取字段定义
- **WHEN** 系统 LLM 提取画像
- **THEN** 提取的结果 SHALL 包含以下字段：
  - 基础信息：姓名、手机、邮箱、所在地
  - 教育背景：学校、学历、专业、毕业年份、GPA
  - 工作经历：公司、职位、时间、职责、成就
  - 技能：技术技能、软技能、语言能力
  - 项目经验：项目名称、角色、描述、成果
  - 求职目标：目标岗位、目标公司、地点偏好、薪资范围、行业

#### Scenario: LLM 输出格式约束
- **WHEN** 系统 LLM 提取画像
- **THEN** 系统 SHALL 使用 JSON Schema 约束输出格式
- **AND** LLM SHALL 返回符合 Pydantic BaseModel 的 JSON
- **AND** 如果 LLM 输出格式不符合，系统 SHALL 重试一次

---

### Requirement: 置信度计算

系统 SHALL 计算每个提取字段的置信度（百分比）。

#### Scenario: 精确匹配
- **WHEN** 字段的值在原始文本中完全匹配
- **THEN** 系统 SHALL 给出 95% 的置信度

#### Scenario: 模糊匹配
- **WHEN** 字段的值在原始文本中去掉标点和空格后匹配
- **THEN** 系统 SHALL 给出 85% 的置信度

#### Scenario: 关键词部分匹配
- **WHEN** 字段的值有 70% 以上的关键词在原始文本中
- **THEN** 系统 SHALL 给出 70% 的置信度

#### Scenario: 无法验证
- **WHEN** 字段的值在原始文本中找不到任何匹配
- **THEN** 系统 SHALL 给出 50% 的置信度
- **AND** 系统 SHALL 标记该字段"可能需要确认"

---

### Requirement: 画像展示

系统 SHALL 以友好的界面展示提取的个人画像。

#### Scenario: 完整画像展示
- **WHEN** 画像提取成功
- **THEN** 系统 SHALL 展示所有字段
- **AND** 系统 SHALL 按模块分组展示（基础信息、教育、工作、技能、项目、求职目标）
- **AND** 每个字段 SHALL 显示名称和提取的值

#### Scenario: 置信度显示
- **WHEN** 展示画像字段
- **THEN** 系统 SHALL 在每个字段旁显示置信度百分比
- **AND** 高置信度（≥80%） SHALL 用绿色标签
- **AND** 中等置信度（60-80%） SHALL 用黄色标签
- **AND** 低置信度（<60%） SHALL 用红色标签

#### Scenario: 缺失字段提示
- **WHEN** 某个字段提取失败（值为 null）
- **THEN** 系统 SHALL 显示"未提取到"标记
- **AND** 系统 SHALL 提示用户手动补充

#### Scenario: 多条记录展示
- **WHEN** 字段包含多条记录（如教育背景、工作经历）
- **THEN** 系统 SHALL 按时间倒序排列
- **AND** 系统 SHALL 用列表形式展示

---

### Requirement: 文本预览与编辑

系统 SHALL 在画像提取前展示提取的文本，并允许用户编辑。

#### Scenario: 文本预览
- **WHEN** 文件解析成功或文本粘贴成功
- **THEN** 系统 SHALL 先展示提取的文本
- **AND** 系统 SHALL 显示文本质量检测的警告（如果有）
- **AND** 系统 SHALL 提供"确认并继续"和"重新上传"选项

#### Scenario: 文本编辑
- **WHEN** 用户在文本预览页面编辑文本
- **THEN** 系统 SHALL 允许用户自由修改文本
- **AND** 系统 SHALL 在用户点击"确认"后使用修改后的文本
- **AND** 系统 SHALL 重新进行质量检测和 LLM 提取

#### Scenario: 编辑后重新提取
- **WHEN** 用户编辑文本后点击"确认"
- **THEN** 系统 SHALL 使用编辑后的文本进行 LLM 提取
- **AND** 系统 SHALL 重新计算质量分数
- **AND** 系统 SHALL 返回新的画像结果

---

### Requirement: 画像编辑与修正

系统 SHALL 允许用户手动编辑和修正提取的画像。

#### Scenario: 编辑单个字段
- **WHEN** 用户点击某个字段的"编辑"按钮
- **THEN** 系统 SHALL 显示该字段的编辑表单
- **AND** 系统 SHALL 允许用户修改字段值
- **AND** 系统 SHALL 在用户保存后更新字段

#### Scenario: 补充缺失字段
- **WHEN** 某个字段提取失败（值为 null）
- **THEN** 系统 SHALL 提供"补充"按钮
- **AND** 用户 SHALL 能手动填写该字段
- **AND** 填写后置信度 SHALL 标记为"100%（用户确认）"

#### Scenario: 批量编辑
- **WHEN** 用户点击"编辑画像"按钮
- **THEN** 系统 SHALL 显示完整的编辑表单
- **AND** 系统 SHALL 包含所有可编辑字段
- **AND** 系统 SHALL 提供表单验证

#### Scenario: 保存修改
- **WHEN** 用户编辑完画像并点击"保存"
- **THEN** 系统 SHALL 更新 user_profile
- **AND** 系统 SHALL 记录修改时间戳
- **AND** 系统 SHALL 返回保存成功的提示

---

### Requirement: 错误处理与降级

系统 SHALL 在解析失败时提供友好的错误提示和降级方案。

#### Scenario: 文件解析失败
- **WHEN** 文件解析失败（损坏、加密、扫描件）
- **THEN** 系统 SHALL 返回明确的错误类型
- **AND** 错误提示 SHALL 说明可能的原因
- **AND** 系统 SHALL 提供至少两种降级方案：
  - 复制粘贴文本
  - 手动填写画像

#### Scenario: LLM 提取失败
- **WHEN** LLM 提取失败（API 错误、超时）
- **THEN** 系统 SHALL 返回错误提示"提取失败，请稍后重试"
- **AND** 系统 SHALL 保留已提取的文本（用户不需要重新上传）

#### Scenario: 文本质量过低
- **WHEN** 文本质量分数 < 0.4
- **THEN** 系统 SHALL 显示"解析结果可能不可用"
- **AND** 系统 SHALL 强烈建议用户检查或修改文本
- **AND** 系统 SHALL 提供"手动填写"备选方案

---

### Requirement: 画像持久化

系统 SHALL 持久化存储用户的个人画像。

#### Scenario: 首次保存画像
- **WHEN** 用户首次建立画像并确认
- **THEN** 系统 SHALL 将 user_profile 存储到持久化介质
- **AND** MVP 阶段使用内存存储（MemorySaver）
- **AND** v1 阶段升级为 SQLite 数据库

#### Scenario: 更新画像
- **WHEN** 用户编辑并保存画像
- **THEN** 系统 SHALL 更新持久化的 user_profile
- **AND** 系统 SHALL 更新修改时间戳
- **AND** 系统 SHALL 保留修改历史（可选）

#### Scenario: 读取画像
- **WHEN** 用户再次访问系统
- **THEN** 系统 SHALL 从持久化介质读取 user_profile
- **AND** 系统 SHALL 在会话中恢复画像数据

---

### Requirement: API 响应格式

系统 SHALL 返回统一的 API 响应格式。

#### Scenario: 成功响应
- **WHEN** API 调用成功
- **THEN** 响应 SHALL 包含以下字段：
  - `status`: "success" | "warning"
  - `quality_score`: 0.0-1.0（文本质量分）
  - `profile`: object（结构化画像）
  - `confidence`: object（置信度）
  - `warnings`: array[string]（警告列表）

#### Scenario: 部分成功响应
- **WHEN** API 调用部分成功（有警告）
- **THEN** 响应 SHALL 包含：
  - `status`: "partial_success"
  - `warnings`: array[string]（具体警告）
  - `profile`: object（可能包含 null 字段）
  - `confidence`: object（置信度，部分为 0）

#### Scenario: 错误响应
- **WHEN** API 调用失败
- **THEN** 响应 SHALL 包含：
  - `status`: "error"
  - `error_code`: string（错误类型）
  - `error_message`: string（用户友好的错误描述）
  - `suggestions`: array[string]（降级方案建议）

---

## MODIFIED Requirements

（此变更不修改任何已有 Requirements）

---

## REMOVED Requirements

（此变更不删除任何已有 Requirements）

---

## 数据结构定义

### user_profile（个人画像）

```json
{
  "basic_info": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "location": "string"
  },
  "education": [
    {
      "school": "string",
      "degree": "string",
      "major": "string",
      "graduation_year": "string",
      "gpa": "string (optional)"
    }
  ],
  "work_experience": [
    {
      "company": "string",
      "position": "string",
      "duration": "string",
      "description": "string",
      "achievements": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft_skills": ["string"],
    "languages": ["string"]
  },
  "projects": [
    {
      "name": "string",
      "role": "string",
      "description": "string",
      "outcome": "string"
    }
  ],
  "job_target": {
    "target_positions": ["string"],
    "target_companies": ["string"],
    "location_preference": "string",
    "salary_range": "string",
    "industry": "string"
  }
}
```

### profile_confidence（置信度）

```json
{
  "basic_info": {
    "name": 0.95,
    "phone": 0.85,
    "email": 0.90,
    "location": 0.70
  },
  "education": [
    {
      "school": 0.95,
      "degree": 0.90,
      "major": 0.85,
      "graduation_year": 0.50
    }
  ],
  "work_experience": [...],
  "skills": {...},
  "projects": [...],
  "job_target": {...}
}
```

---

## 边界条件

### 输入边界
- 文件大小：0 - 10MB（超过拒绝）
- 文本长度：0 - 50000 字符（超过截断）
- 文本编码：UTF-8（其他编码尝试转换）

### 输出边界
- 置信度范围：0.0 - 1.0（0% - 100%）
- 质量分数范围：0.0 - 1.0
- 画像字段：所有字符串字段最大长度 500 字符

### 性能边界
- 文件解析：< 5 秒（< 5MB）
- LLM 提取：< 10 秒（< 5000 字符）
- 端到端：< 20 秒（上传 → 画像）

---

## 验收标准

### 功能验收
- [ ] 能解析可搜索的 PDF（成功率 ≥ 80%）
- [ ] 能解析 docx 文件（成功率 ≥ 90%）
- [ ] 能接受文本粘贴输入
- [ ] 能检测扫描件 PDF 并给出友好提示
- [ ] 能进行文本质量检测
- [ ] 能用 LLM 提取结构化画像
- [ ] 能计算字段置信度
- [ ] 能展示画像和置信度
- [ ] 能允许用户编辑画像
- [ ] 能持久化存储画像

### 质量验收
- [ ] 真实简历测试：10 份样本，成功率 ≥ 80%
- [ ] LLM 提取准确率：核心字段 ≥ 85%
- [ ] 错误提示友好：无技术术语，有解决方案
- [ ] 降级策略完善：至少两种备选方案

### 用户体验验收
- [ ] 用户能在 5 分钟内完成简历上传和画像建立
- [ ] 文本预览功能可用
- [ ] 置信度显示清晰（颜色区分）
- [ ] 错误提示有帮助（能指导用户下一步操作）
