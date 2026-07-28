# Spec: 画像头像（user-profile delta）

## ADDED Requirements

### Requirement: 画像头像维护

系统 SHALL 支持用户在个人画像中维护一张头像图片，并持久化其访问地址，使画像成为简历头像的单一来源。

#### Scenario: 上传头像
- **WHEN** 用户在画像页上传一张图片（jpeg / png，≤ 2MB）
- **THEN** 系统 SHALL 校验文件类型与大小
- **AND** 系统 SHALL 校验文件魔数（防止伪装扩展名）
- **AND** 系统 SHALL 持久化图片并以 URL 形式记录在画像中
- **AND** 系统 SHALL 在画像页回显该头像

#### Scenario: 更新头像
- **WHEN** 用户上传新头像
- **THEN** 系统 SHALL 用新头像覆盖旧头像（一人一头像）
- **AND** 系统 SHALL 更新画像中的头像 URL

#### Scenario: 无头像时的回退
- **WHEN** 画像未设置头像
- **THEN** 系统 SHALL 在画像页以姓名首字母占位（不显示破裂图片）

#### Scenario: 上传非法文件
- **WHEN** 用户上传非图片文件或超大文件
- **THEN** 系统 SHALL 拒绝上传并返回明确的错误提示

---

### Requirement: 解析时从简历文件提取头像

系统 SHALL 在用户上传 PDF/docx 简历解析时，尝试从文件中提取头像图片并存入画像，作为手动上传之外的补充来源。

#### Scenario: PDF 含可识别头像
- **WHEN** 用户上传一个含证件照的可搜索 PDF
- **THEN** 系统 SHALL 从首页提取最像头像的图片（位置靠上、宽高比接近 1、尺寸合理）
- **AND** 系统 SHALL 将其存入画像（覆盖头像 URL）
- **AND** 系统 SHALL 不阻塞文本解析流程

#### Scenario: docx 含内嵌图片
- **WHEN** 用户上传一个含内嵌头像图片的 docx
- **THEN** 系统 SHALL 提取该图片并存入画像

#### Scenario: 无法识别头像
- **WHEN** 文件无图片、有多张难以判定的图片、或为扫描件
- **THEN** 系统 SHALL 跳过头像提取（不猜测）
- **AND** 系统 SHALL 不阻塞解析
- **AND** 系统 SHALL 提示用户可在画像页手动上传头像

#### Scenario: 提取的头像不正确
- **WHEN** 系统提取的图片不是用户期望的头像（如 logo、签名）
- **THEN** 系统 SHALL 允许用户在画像页更换或删除
