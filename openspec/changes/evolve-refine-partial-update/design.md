# Design: 精修局部更新与并发编辑（evolve-refine-partial-update）

## 设计原则

1. **不碰 LLM 可靠性**：AI 仍输出完整 MD（重写整份，结构稳定）。局部更新是前端的事，不让 LLM 输出 patch（patch 易错：行号偏、漏改、结构乱）。
2. **锚点统一**：复用 evolve-resume-refine 的 `data-md-line`（+ `data-md-field`）锚点——它本就是「HTML 原子 ↔ Markdown 行」的映射，局部更新按它定位被改原子。
3. **并发以原子为粒度**：用户编辑与 AI 改写以「可编辑原子」为单位并发。不同原子互不干扰；同原子才算冲突。
4. **真相源仍是 Markdown**：局部更新只改 DOM（派生），不改 Markdown 真相源；真相源仍由 `flushEdits` 落地。局部更新让「AI 改时用户编辑」不丢，但最终仍要 flush 才进 MD。

---

## 核心设计决策

### 决策 1：路径 B（完整 MD + 前端 diff），而非 LLM 增量 patch

| 方案 | 机制 | 问题 |
|---|---|---|
| LLM 输出 patch（路径 A） | AI 吐 `[{行号, 新文本}]`，前端 apply | LLM 输出 patch **很不可靠**：行号错、漏改、结构乱；用户插删行后行号偏移，patch 基于旧基线错位 |
| **完整 MD + 前端 diff（路径 B，采用）** | AI 输出完整 MD（稳），前端 diff 找改的行，局部更新 DOM | 不碰 LLM 可靠性；diff 在前端可控；代价是前端要 diff + 局部 DOM 替换 |

### 决策 2：MD 行级 diff 在前端做（LCS）

前端拿到 done 的 `new_md`，和当前 `resumeMd` 做**行级 LCS diff**，输出「改动行集合」：增/删/改的行号。

- 用行（`splitlines()`）作为 diff 单位，匹配 `data-md-line`（也是行号锚点）。
- 实现自写轻量 LCS（简历行数百级，O(n²) 可接受），不引外部 diff 库（依赖洁癖）。
- 边界：用户插删整行（如加一段经历）→ 行号偏移。此时 diff 出「大段改动」→ 退化为整体刷新（兜底，保证不错乱）。即：**改动行数超过阈值（如 >30% 行）时，fallback 整体 srcdoc 刷新**。

### 决策 3：局部 DOM 替换（DOMParser + data-md-line 定位）

```
new_html (done.html)
   │ DOMParser 解析
   ▼
按 data-md-line 建索引 {line → 新原子 DOM}
   │
   ▼ 遍历 diff 改动行
iframe.contentDocument.querySelector([data-md-line="L"])
   → 替换为 newHtmlDoc 的同 line 原子（cloneNode）
   │
   ▼ 替换后
触发 preview_shell 的 __reflow（重排分页）+ __refineRehook（重挂 contenteditable）
```

- 父页同源可访问 iframe `contentDocument`（srcdoc 同源，collectPatches 已用此能力）。
- 替换粒度：bullet / entry-org / entry-role / date / summary / stack-row / header 字段——即 `data-md-line` 覆盖的所有可编辑原子。
- 未涉及原子：DOM 不动，用户编辑（contenteditable 文本）原地保留。

### 决策 4：分页与编辑态协调

preview_shell 的 `render()` 把原子分配到 `.page`（A4 分页）。局部替换某原子后，高度可能变 → 分页要重排。

- 替换后调 `__reflow`（preview_shell 已有的重排函数），重排分页。
- `__reflow` 末尾已有 `__refineRehook`（evolve-resume-refine 加的）重挂 contenteditable——替换后的新原子自动获得编辑态。

### 决策 5：同原子冲突检测与 UX

冲突定义：AI 要替换的原子（`data-md-line=L`），用户在 iframe 里编辑过它（未 flush，DOM 文本 ≠ 基线）。

- 检测：替换前，对比 iframe 内该原子的 `textContent` 与 `__initialTexts[L]`（preview_shell 的基线）。不等 → 用户编辑过 → 冲突。
- UX：冲突时**不静默覆盖**，弹轻量提示：「这一处你改过，AI 也改了。保留你的 / 采用 AI 的」。默认不替换（保留用户版），用户选了再动作。
- 非冲突（用户没动该原子）：直接局部替换。

### 决策 6：锚点无偏移问题（AI 基于最新 flush MD）

担心「用户手改插删行 → 行号偏移 → AI 的行号错位」？不会：
- AI 改写的基线是**已 flush 的 MD**（`resumeMd`，不含用户未 flush 的 DOM 编辑）。
- done 的 `new_md` 是 AI 基于 flush MD 改的。
- diff `new_md` vs `resumeMd`（同一基线）→ 行号一致，无偏移。
- 用户未 flush 的编辑在 iframe DOM（不在 `resumeMd`），不参与 diff；若未涉及被改原子，原地保留。

所以锚点稳定（diff 同基线）。用户插删行只在 flush 后发生（flush 后 `resumeMd` 更新，下轮 AI 基于新基线）。

### 决策 7：flushEdits 保留（落真相源）

局部更新让「AI 改时用户编辑」不丢（DOM 保留），但真相源（MD）仍要 flush 才更新：
- **定稿前**：flush（把并发期间用户编辑落 MD，定稿基于完整最新）。
- **导出 PDF 前**：flush。
- **下一轮 AI 改前**：可选 flush（让下轮 AI 基于含用户编辑的最新 MD）；或保留并发（下轮 AI 基于旧 flush MD，用户未 flush 编辑继续在 DOM）——MVP 选「下轮前 flush」（简单，保证 AI 基线最新）。

即：局部更新解的是「AI 改的那一刻不冲掉用户编辑」；flush 仍是「把用户编辑进真相源」的通道，时机从「每轮 AI 改前强制」放宽到「定稿/导出/下轮」。

---

## 待 spike 的点

1. **MD 行级 diff**：自写 LCS 的正确性（增删行场景），与「大改动 fallback 整体刷新」的阈值。
2. **DOM 替换后 preview_shell 协调**：替换原子 → `__reflow` 重排 → 分页/编辑态是否正确保持（尤其跨页原子）。
3. **stack-row / contact 多字段原子的局部替换**：这些原子内部结构复杂（chips / 多 span），替换是否需要整原子替换 vs 字段级。

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| diff 行级偏移（用户插删行） | 局部替换错原子 | 同基线 diff（决策 6）+ 大改动 fallback 整体刷新（决策 2） |
| DOM 替换后分页/编辑态乱 | 预览错乱 | `__reflow` + `__refineRehook`（决策 4），spike 验证 |
| 同原子冲突静默覆盖 | 用户编辑丢失 | 冲突检测 + 提示（决策 5），不静默 |
| 锚点未覆盖某原子 | 该处无法局部更新 | evolve-resume-refine 已覆盖主要原子；未覆盖的退化为整体刷新 |
| 局部更新的基线（__initialTexts）时序 | 冲突检测误判 | flush / partialUpdate 后更新基线（决策 5 + 7） |

---

## 面试讲解要点

1. **协同编辑冲突模型**：以「可编辑原子」为并发单位，不同原子并发、同原子冲突——经典的 OT/CRDT 思想的简化版（单客户端、原子粒度）。
2. **不碰 LLM 可靠性**：增量更新放前端（diff + DOM），而非让 LLM 输出 patch——工程上识别「哪一层做哪件事」的成本最低。
3. **DOM 局部更新 vs 整体重渲染**：性能（少重排）+ 并发（不冲编辑）+ 体验（无闪屏）的取舍，及 fallback 到整体刷新的安全网。
4. **锚点统一**：`data-md-line` 一套锚点，既支撑 evolve-resume-refine 的「手改回写」，又支撑本变更的「AI 改局部更新」——架构一致性。
