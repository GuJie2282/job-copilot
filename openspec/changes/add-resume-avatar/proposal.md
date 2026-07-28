# Proposal: 简历头像（add-resume-avatar）

## Why

当前简历模板左上角没有头像，简历显得不完整。完整链路存在四处缺口：

- **画像层无头像**：`UserProfileModel` 没有头像字段（`users.avatar` 列存在但全栈无读写），用户无处维护头像。
- **解析不提图**：上传 pdf/docx 解析时只提取文本，丢弃了简历里现成的证件照。
- **模板无头像位**：`tech_dense.render_header` 只渲染 name/role/education/contact，没有头像渲染。
- **PDF 导出隐患**：后端用 Playwright `set_content` 渲染 PDF，相对 URL 的图片加载不出来——即使加了头像，导出 PDF 也会丢图。

头像能让简历更专业、更完整，也是「画像驱动生成」链路的自然延伸（画像有头像 → 简历带头像）。

## What Changes

1. **画像维护头像**：画像层新增 `avatar_url`（独立标量列，不进 `detail_json`）；画像页支持上传图片（校验类型/大小、魔数校验、压缩）；`.id-avatar` 由首字母占位改为真实图片。
2. **解析自动提取头像**：上传 pdf/docx 解析时，从首页提取「最像证件照」的图（位置 + 宽高比 + 尺寸几何启发式），存文件系统，URL 写入返回的 `profile.avatar_url`；提取失败/无图/误选风险时降级（不阻塞解析，提示用户手动上传）。
3. **模板左上角渲染头像**：`tech_dense.render_header` grid 布局加头像列，有 `avatar_url` 就渲染圆形头像；头像**不进 Markdown 真相源**（作为渲染参数注入，避免 LLM 误改 / 精修误删）。
4. **PDF 导出图片可见**：`resume_pdf` 渲染前把 HTML 里的 `/static/...` 相对图片 URL 替换成 base64 data URL（解决 Playwright `set_content` 不解析相对 URL 的问题）。
5. **图片存储与服务**：后端挂 `StaticFiles`（`/static` → `data/`），头像存 `data/avatars/{user_id}.{ext}`；vite proxy 扩 `/static`。

## Capabilities

- `user-profile`（ADDED）：画像头像维护（上传 / 存储 / 回显）+ 解析时从简历文件提取头像。
- `resume-optimization`（ADDED）：简历模板头像显示 + PDF 导出图片可见性。

## Impact

- **后端**：
  - `models/profile.py`：`UserProfileModel` 加 `avatar_url` 标量列。
  - `services/profile_service.py`：`SCALAR_FIELDS` 加 `avatar_url`。
  - `services/resume_parser.py`：新增 pdf/docx 头像提取（pdfplumber `page.images` + 几何过滤；python-docx `doc.part.rels` 取图）。
  - `api/resume.py`：`parse_resume_file` 解析后提图（删除临时文件前）；新增 `POST /resume/avatar` 上传端点。
  - `services/resume_themes/tech_dense.py`：`render_header` 加 `avatar_url` 参数 + 头像 CSS。
  - `services/resume_exporter.py`：`export_resume` / `assemble_html` 透传 `avatar_url`。
  - `services/resume_pdf.py`：渲染前相对 URL → base64 data URL。
  - `main.py`：挂 `StaticFiles` + 建目录。
- **前端**：
  - `ProfileEditor.vue` / `ProfileDisplay.vue` / `Profile.vue`：头像上传（el-upload）+ 回显。
  - `api/resume.ts`：`uploadAvatar`。
  - `vite.config.ts`：proxy 扩 `/static`。
- **依赖**：无新依赖（pdfplumber / python-docx 已装）。
- **风险**：PDF 导出图片加载（用 data URL 兜底）；头像误选（几何过滤 + 用户画像页可换 / 可删）；临时文件删除时机（提图在删除前）；数据库加列（开发期删库重建或手动 ALTER，项目无 alembic 迁移）。
- **依赖关系**：`user-profile` capability 的主 spec 仍在 `add-resume-parsing-and-profile-creation`（未归档）。本 change 的 user-profile delta 用 ADDED Requirements 描述头像行为，与解析的文本提取不冲突；按序归档合并。
- **面试讲点**：画像驱动的全链路（维护 → 提取 → 渲染 → 导出）；静态资源服务 + PDF 渲染兜底（Playwright `set_content` 限制）；几何启发式选图与人脸检测的取舍；头像不进真相源的解耦（避免 LLM / 精修误改）。
