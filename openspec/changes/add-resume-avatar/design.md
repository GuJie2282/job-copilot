# Design: 简历头像（add-resume-avatar）

## 决策 1：头像存文件系统 + StaticFiles 服务（不进 DB）

头像存 `backend/data/avatars/{user_id}.{ext}`，后端挂 `StaticFiles(directory=data)` 到 `/static`，URL 形如 `/static/avatars/{user_id}.jpg` 入库。

**为什么不进 DB（base64）**：画像每次读写都会带上图片字节，JSON 列膨胀、读写变慢、备份变重；文件系统持久，可被浏览器预览 / PDF 渲染 / 精修预览三处复用，DB 只存 URL 字符串。

**一人一头像**：用 `{user_id}.{ext}` 单文件覆盖（最新即所用），不做版本留痕（MVP 够用）。原子写：先写临时文件再 `os.replace`，防并发覆盖写坏。

**目录选址**：`backend/data/` 已存在（gitignore 忽略），`data/avatars/` 子目录，启动时 `os.makedirs(exist_ok=True)`。

## 决策 2：avatar_url 作为独立标量列（不进 detail_json）

`UserProfileModel` 新增 `avatar_url = Column(String(500), nullable=True)`，并加入 `profile_service.SCALAR_FIELDS`（与 name/phone 同列管理）。

**为什么不塞 detail_json**：`save_profile` 对 `detail_json` 是整体覆盖语义——`update-profile` 若不带回 `avatar_url` 会被冲掉。独立标量列不受 detail_json 覆盖影响，且与 name/phone 同性质（单值标量）。

**不复用 users.avatar**：`users` 存账户、`user_profiles` 存求职档案（见 `models/profile.py` 注释）；头像是简历物料，归画像层（user_profiles）更内聚，生成简历时画像快照自带头像。

**数据库加列**：项目用 `Base.metadata.create_all` 建表，无 alembic 迁移。开发期给已有表加列：删库重建（dev 可接受）或手动 `ALTER TABLE user_profiles ADD COLUMN avatar_url VARCHAR(500)`。tasks 里注明。

## 决策 3：解析提图用 pdfplumber（已装）+ 几何启发式，漏图降级

- **PDF**：`pdfplumber` 的 `page.images` 返回每张图的位置（bbox）与尺寸。筛选「位于页面上半部（top < 页高 / 2）+ 宽高比 0.7~1.3 + 边长 80~400pt」，按「越靠左上 + 越接近正方形」打分，选最高分一张；`page.within_bbox(img['bbox']).extract_image()` 取 bytes + ext。
- **DOCX**：`python-docx` 遍历 `doc.part.rels` 找 `RT.IMAGE`，取 `.blob`；优先选首个 inline 图片。
- **漏图 / 误选降级**：扫描件 PDF 已被 `quick_check` 拒；无图 / 多图难以判定时不猜，跳过提取，返回不带 avatar_url，前端提示用户「未识别到头像，可在画像页手动上传」。解析流程不因提图失败而中断。
- **不做**：OCR、人脸识别、外链图片下载。MVP 用几何过滤 + 用户确认（画像页能看到提取结果，可换可删）。

**为什么不追加 PyMuPDF**：pdfplumber 已覆盖绝大多数可搜索 PDF；PyMuPDF 仅在矢量内嵌图场景更鲁棒，属边际收益，暂不引入新依赖（Windows wheel 虽可用）。后续若漏图率高再评估。

**临时文件时机**：`parse_resume_file` 当前解析完即 `os.remove` 临时文件。提图必须在删除前完成（提图依赖原始文件路径）。

## 决策 4：头像不进 Markdown 真相源，作为渲染参数注入

头像 `avatar_url` 作为 `export_resume` / `assemble_html` 的显式参数，从画像透传到 `render_header`，**不写进简历 Markdown 的 self-intro**。

**为什么**：
- LLM 生成 MD 时不一定写 avatar 行，写进去了也可能被 LLM 误改 / 误脱敏（URL 变字符串乱码）。
- 精修的 `apply_patches_to_md` / `__collectPatches` 按文本行回写，图片不是文本原子，进 MD 会增加回写出错面。
- 头像在画像页统一维护（上传 / 提取 / 换 / 删），单一来源，简历只消费。

**精修里不换图**：头像不挂 `data-md-line` 锚点、不进 contenteditable。用户要换头像回画像页。这保证头像改动不与文本精修冲突，也最小化精修机制改动。

> 兼容说明：`resume_validator._KV_DROP_KEYS` 已含 `"avatar"`——即便历史 MD 里残留 `avatar:` 字段行，普通模块渲染时会剥 key 不泄漏；self-intro 若有 `avatar:` 行，`_parse_intro` 会解析但 `_render_header_from_intro` 不消费（忽略）。

## 决策 5：PDF 导出图片可见——相对 URL 转 base64 data URL

`resume_pdf.render_html_to_pdf` 用 Playwright `page.set_content(html)`。`set_content` 的 base URL 是 `about:blank`，**不解析相对 URL**（`/static/x.jpg` 加载失败）。`set_content` 也不支持 `base_url` 参数（`page.goto` 才支持）。

**方案**：渲染前用 `re.sub` 扫 HTML 里所有 `src="/static/..."`，读 `data/` 下对应文件，替换成 `src="data:image/{ext};base64,{b64}"`。HTML 自包含，无网 / 无 base URL 也能渲染，跨环境稳定。

**不压缩（MVP）**：为不引入 Pillow 依赖（proposal 约束「无新依赖」），上传仅限制 ≤ 2MB（魔数校验后原样存盘）。base64 膨胀 HTML（比 binary 大 33%）在 2MB 内可接受；若后续 PDF 体积成问题，再评估前端 canvas 压缩或装 Pillow。

## 决策 6：vite proxy 扩 /static（dev 环境）

dev 下前端 `VITE_API_BASE_URL=/api` 走 vite proxy。头像 URL `/static/avatars/...` 默认不走 proxy → dev 环境 404。

**方案**：`vite.config.ts` proxy 规则加 `/static` → `localhost:8001`。生产环境前后端同域或反代另行处理。

## 决策 7：上传端点与安全

新增 `POST /api/resume/avatar`（multipart）：接收 `UploadFile` → 校验类型（image/jpeg, image/png）+ 大小（≤ 2MB）+ 魔数（防伪装可执行文件）→ 压缩 → 原子写 `data/avatars/{user_id}.{ext}` → URL 写 `user_profiles.avatar_url` → 返回新 URL。

参考 `voice.py` 的 UploadFile 范式 + `parse_resume_file` 的 multipart 处理。

## 取舍与边界

- **范围**：画像页上传 / 维护 + 解析提取 + 模板显示 + PDF 可见。
- **不做**：精修换图、OCR / 人脸识别、对象存储、头像版本留痕。
- **依赖 add-resume-parsing**：user-profile capability 的 spec 仍在 `add-resume-parsing-and-profile-creation`（未归档）。本 change 的 user-profile delta 用 ADDED Requirements，与解析的文本提取不冲突；归档时按序合并。
