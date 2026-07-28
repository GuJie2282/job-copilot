# Spec: 简历头像显示（resume-optimization delta）

## ADDED Requirements

### Requirement: 简历模板头像显示

系统 SHALL 在生成的简历模板左上角渲染用户画像中的头像（若有），使简历更完整专业。

#### Scenario: 画像有头像
- **WHEN** 系统生成或渲染简历，且用户画像含头像 URL
- **THEN** 系统 SHALL 在简历头部左上角渲染圆形头像
- **AND** 头像 SHALL 不进入简历 Markdown 真相源（仅作为渲染参数注入）

#### Scenario: 画像无头像
- **WHEN** 用户画像未设置头像
- **THEN** 系统 SHALL 不渲染头像位（布局正常不空位）

#### Scenario: 头像不参与精修回写
- **WHEN** 用户在精修工作台编辑简历文本
- **THEN** 头像 SHALL 不可被文本编辑改动（不挂编辑锚点）
- **AND** 更换头像 SHALL 通过画像页完成（单一来源）

---

### Requirement: PDF 导出图片可见性

系统 SHALL 保证导出的 PDF 中头像等图片可见，不受 Playwright 渲染机制对相对 URL 的限制。

#### Scenario: 导出含头像的简历 PDF
- **WHEN** 系统导出一份含头像的简历为 PDF
- **THEN** 系统 SHALL 在渲染前将图片的相对 URL 转换为自包含的内联数据（data URL）
- **AND** 导出的 PDF SHALL 正确显示头像
