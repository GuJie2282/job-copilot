# Tasks: 精修局部更新与并发编辑

## 1. spike：MD diff + 局部 DOM 替换可行性
- [ ] 1.1 MD 行级 diff（LCS）：自写轻量实现，输出改动行集合（增/删/改行号）；验证增删行场景
- [ ] 1.2 大改动阈值：改动行数超阈值（如 >30% 行）时 fallback 整体 srcdoc 刷新（防错乱）
- [ ] 1.3 DOMParser 解析 done.html，按 `data-md-line` 建索引 {line → 新原子}
- [ ] 1.4 局部替换 iframe 内同锚点原子（cloneNode）+ 调 `__reflow`/`__refineRehook`，验证分页/编辑态保持

## 2. partialUpdate 实现（ResumePreview）
- [ ] 2.1 `ResumePreview.vue` 新增 `partialUpdate(newMd, newHtml)`：diff + DOMParser + 局部替换 + 重排
- [ ] 2.2 覆盖所有 `data-md-line` 原子类型（bullet / entry-org·role / date / summary / stack-row / header 字段）
- [ ] 2.3 局部替换后触发 preview_shell 的 `__reflow` + `__refineRehook`（重排分页 + 重挂 contenteditable）
- [ ] 2.4 大改动 fallback 整体 srcdoc 刷新（保持现有整体刷新路径作兜底）

## 3. 同原子冲突检测与 UX
- [ ] 3.1 替换前对比 iframe 原子 textContent vs `__initialTexts` 基线，检测用户是否编辑过该原子
- [ ] 3.2 冲突时不静默覆盖，提示「保留用户版 / 采用 AI 版」
- [ ] 3.3 非冲突直接局部替换

## 4. ResumeRefine onDone 改 partialUpdate
- [ ] 4.1 onDone 由「整体刷新 html.value」改为「`partialUpdate(d.resume_md, d.html)`」
- [ ] 4.2 局部更新后更新 resumeMd（真相源）+ 通知 preview_shell 重记 `__initialTexts` 基线
- [ ] 4.3 保留 streaming 期间的思考/回复渲染（不变）

## 5. flushEdits 适配（时机放宽）
- [ ] 5.1 保留 flushEdits 用于定稿 / 导出 PDF 前
- [ ] 5.2 下一轮 AI 改前 flush（保证 AI 基线最新）；并发期间用户编辑在 DOM 保留不强制 flush
- [ ] 5.3 partialUpdate / flush 后更新 `__initialTexts` 基线（避免冲突误判）

## 6. 测试
- [ ] 6.1 MD diff 单测：改动行 / 增删行 / 大改动 fallback
- [ ] 6.2 局部更新 e2e：AI 改原子 B，用户编辑原子 A 不丢
- [ ] 6.3 同原子冲突：用户编辑 + AI 改同处 → 提示，不静默覆盖
- [ ] 6.4 大改动（AI 重写多段）→ fallback 整体刷新，不错乱

## 7. 验证
- [ ] 7.1 边改边等 AI：用户编辑一处，AI 改另一处，两者都保留
- [ ] 7.2 局部更新无闪屏（vs 整体刷新的对比）
- [ ] 7.3 分页正确（替换后 `__reflow` 重排无误）
- [ ] 7.4 定稿/导出前 flush，未保存编辑正确落真相源
