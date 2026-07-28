# Proposal: 精修局部更新与并发编辑（evolve-refine-partial-update）

## Why

精修当前在 AI 改完后**整体刷新左侧 iframe**（srcdoc 替换）。这带来一个串行约束：为避免冲掉用户的手动编辑，`flushEdits` 不变量强制「先 flush 手改 → 再让 AI 改 → 整体刷新」。也就是用户**不能边手改边等 AI**——AI 改完那一刻 iframe 整体重建，未 flush 的编辑若不先落就会丢。

实际使用中，「改一处的同时让 AI 改另一处」是自然诉求。整体刷新的根因不是 LLM（它本就给完整 MD），而是**前端把整份简历重渲染**——其实 AI 一轮通常只改几处，其余原子不变。

## What Changes

- AI 输出**不变**（仍完整 MD，保可靠性）。
- 前端拿到新 MD 后，**和当前 MD 行级 diff**，找出本轮改动的行（对应可编辑原子）。
- 只**局部替换** iframe 内被改原子的 DOM（按 `data-md-line` 锚点定位），**不整体替换 srcdoc**；未涉及的原子保持不动。
- 不同原子的并发由此成立：用户在原子 A 编辑（未 flush），AI 改原子 B → 只更新 B，A 的编辑原地保留。
- 同原子冲突（用户和 AI 改了同一处）：替换前检测，提示用户选择（保留用户版 / 采用 AI 版）。
- `flushEdits` 保留用于定稿、导出、下一轮 AI 改写前（把并发期间累积的用户编辑落回 Markdown 真相源）。

## Capabilities

- `resume-optimization`（MODIFIED）：「人机协同精修」的「改写基于最新草稿」由串行 flush 改为并发局部更新（AI 改完局部刷新，用户未涉及编辑不丢）。
- `resume-optimization`（ADDED）：「精修局部更新与并发」——AI 改动局部下发、不同原子并发、同原子冲突提示。

## Impact

- **前端改动**：`ResumePreview.vue` 新增 `partialUpdate(newMd, newHtml)`（MD 行级 diff + DOMParser 解析新 html + 按 `data-md-line` 局部替换 iframe 内原子 + 触发 preview_shell 重排）；`ResumeRefine.vue` 的 onDone 由「整体刷新 html」改为 `partialUpdate`；保留 `flushEdits`（定稿/导出/下轮前）。
- **后端不动**：done 仍下发完整 `resume_md` + `html`（可靠性不变）；AI 输出不变。
- **依赖**：建立在 evolve-resume-refine 的 `data-md-line` 锚点 + `preview_shell` 编辑回流之上。
- **风险**：MD 行级 diff 的正确性（增删行场景）；局部 DOM 替换与 preview_shell 分页/编辑态的协调（替换后需重排、重挂 contenteditable）；同原子冲突的检测与 UX；`data-md-line` 锚点对所有可编辑原子的覆盖。
- **面试讲点**：协同编辑的冲突模型（不同原子并发 / 同原子冲突）；「DOM 局部更新 vs 整体重渲染」的取舍（性能 + 并发 + 不碰 LLM 可靠性）；锚点定位统一回写与局部更新。
