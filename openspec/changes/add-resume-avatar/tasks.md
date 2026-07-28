# Tasks: 简历头像（add-resume-avatar）

## 1. 画像层：avatar_url 字段
- [x] 1.1 `models/profile.py`：`UserProfileModel` 加 `avatar_url = Column(String(500), nullable=True, comment="头像 URL")`
- [x] 1.2 `services/profile_service.py`：`SCALAR_FIELDS` 加 `"avatar_url"`；确认 `get_profile` 返回含 avatar_url、`save_profile` 能 upsert avatar_url
- [x] 1.3 数据库迁移：main.py 启动时自动检查并 ALTER 补 avatar_url 列（重启后端即生效，不丢数据，无需手动 SQL）

## 2. 图片存储与静态服务
- [x] 2.1 `main.py`：启动时 `os.makedirs("data/avatars", exist_ok=True)` + `app.mount("/static", StaticFiles(directory="data"), name="static")`
- [x] 2.2 `vite.config.ts`：proxy 扩 `/static` → `localhost:8001`
- [x] 2.3 新增头像上传端点 `POST /api/resume/avatar`（multipart）：类型 / 大小 / 魔数校验 → 原子写 → URL 入库 → 返回新 URL（不引入 Pillow 压缩，靠 ≤2MB 限制；压缩留后续）

## 3. 解析提取头像（pdf / docx）
- [x] 3.1 `services/resume_parser.py`：新增 `extract_pdf_avatar(file_path)`（pdfplumber `page.images` + 几何过滤 + `within_bbox().extract_image()`）
- [x] 3.2 `services/resume_parser.py`：新增 `extract_docx_avatar(file_path)`（python-docx `doc.part.rels` 找 `RT.IMAGE` 取 `.blob`）
- [x] 3.3 `api/resume.py` `parse_resume_file`：解析后、删临时文件前调提图；成功则存 FS + URL 写入返回的 `profile.avatar_url`；失败降级不阻塞

## 4. 简历模板渲染头像
- [x] 4.1 `services/resume_themes/tech_dense.py`：STYLE `.resume-header` grid 改 `auto 1fr` + 新增 `.avatar` 圆形样式
- [x] 4.2 `tech_dense.py` `render_header`：加 `avatar_url` 参数，有值渲染 `<img class="avatar">`（不带 data-md-line）
- [x] 4.3 `services/resume_exporter.py`：`export_resume` / `assemble_html` 加 `avatar_url` 参数，透传到 `_render_header_from_intro` → `theme.render_header`
- [x] 4.4 生成 / 精修链路：调 `assemble_html` / `export_resume` 处把画像 `avatar_url` 透传（refine-stream 的 `wrap_preview`、refine finalize、pdf 端点、generate 的 resume_export_node）

## 5. PDF 导出图片可见
- [x] 5.1 `services/resume_pdf.py`：渲染前把 HTML 里 `/static/...` 相对 URL 替换成 base64 data URL（`re.sub` + 读 `data/` 文件）
- [x] 5.2 决策：不引入 Pillow 压缩（proposal 约束无新依赖），上传仅限 ≤2MB（2.3 已实现）；base64 膨胀在 2MB 内可接受，压缩留后续

## 6. 前端：画像页头像维护
- [x] 6.1 `api/resume.ts`：新增 `uploadAvatar(userId, formData)`（multipart）
- [x] 6.2 `Profile.vue`：identity-card 头像位加点击上传（label + input file → uploadAvatar → 回显），不另开 Editor/Display 组件
- [x] 6.3 `Profile.vue`：`.id-avatar` 有 avatar_url 渲染 `<img>`，无则回落首字母占位

## 7. 验证
- [ ] 7.1 画像页上传头像 → 回显
- [ ] 7.2 上传带头像的 pdf/docx → 解析后画像自动有头像
- [ ] 7.3 生成简历 → 模板左上角显示头像
- [ ] 7.4 导出 PDF → 头像可见（data URL 兜底生效）
- [ ] 7.5 精修简历 → 头像显示正常、不参与回写、换图走画像页
- [ ] 7.6 漏图 / 无图 / 扫描件 → 降级提示，不阻塞解析
