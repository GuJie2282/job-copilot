# Design: 首页引导链路进化 + 全站 CTA 可见性

## 设计原则

1. **链路条 = 新手引导进度，不是静态阶段展示**。必须随用户真实完成度推进，否则引导失真（这正是现状"卡在 JD 匹配"的根因）。
2. **链式推进**：stage N 完成要求 stage N-1 先完成，不能跳过中间环节（符合"引导走完链路"的语义）。
3. **严格完成定义**：每个环节的 done 基于"真正完成"（匹配有分 / 简历 finalized / 面试 finished），而非"任何记录"。门槛高，但 done 含义可靠。
4. **CTA 始终可见**：主操作按钮不应被内容推出视口——配置型用 sticky 底部 bar，结果型用 CTA 上移。
5. **动效编码状态、克制不为动而动**：done 段流光（已通过的流动感）+ active pulse（当前强调），todo 静态；尊重 `prefers-reduced-motion`。

---

## 设计决策 A：首页链路条（home-onboarding）

### A1. 链式 + 严格完成判定

判定表（stage N done = 「数据 N 满足」AND「stage N-1 done」）：

| stage | 数据源 | done 判定 |
|-------|--------|----------|
| 01 建立画像 | `getProfile` | 有画像 |
| 02 JD 匹配 | `matchHistory` | 有 `overall_score != null` 的记录 |
| 03 简历优化 | `listResumes` | 任一版本 `status === 'finalized'` |
| 04 模拟面试 | `listSessions` | 任一 `status === 'finished'` |

`active` = 第一个 `!done` 的 stage；全 done → 祝贺态。

**为什么链式**：用户表述"跳到第三个""移到最后"暗示有序推进。链式可避免"有面试记录但没做匹配"时 stage4 done 而 stage2/3 todo 的跳跃——那不合引导逻辑。

**为什么严格**：用户在探索中明确选了"严格（真正完成）"。done 含义可靠（真做过且完成），引导进度真实。代价是用户要真完成才推进，但这正是"引导走完链路"的应有之义。

**边界**：`listResumes` 返回 `{岗位: [版本]}`，需遍历所有岗位的版本找 `finalized`；`listSessions` 返回 `items[]`，找 `finished`。

### A2. 数据拉取

Home 新增两个静默拉取（沿用现有 `loadMatches` 模式，失败不阻断页面）：
- `loadResumes()` → `listResumes(user_id)` → 判定有无 finalized
- `loadSessions()` → `listSessions(user_id)` → 判定有无 finished

`onMounted` 加这两个调用。`stages` computed 消费其结果。

### A3. 动效：done 段流光 + active pulse

- **done 段连线**（`.track-node.done::before`）：渐变背景 + `background-position` 流动动画（流光感）
- **active 节点**（`.active .node-dot`）：pulse 光环（现状保留）
- **done / todo 节点**：静态（避免全动太吵）
- 都尊重 `prefers-reduced-motion`（禁用流光 + pulse）

**为什么流光而非"每节点都 pulse"**：用户在探索中选了"连线流光 + active pulse"。流光让 done 段有"已通过的流动感"，整条链路活起来但不闹（只有 active 节点强 pulse）。比"每节点都呼吸"更克制，也更突出 active。

### A4. 祝贺态

四个环节全 done 时：
- 隐藏 `next-card`（已无"下一步"概念）
- 显示祝贺卡：「🎉 你已走完全链路！」+ 文案 + CTA「再去匹配一个岗位」
- `thesis` 换成完成论点

**祝贺态 CTA 为什么指向"再去匹配"**：匹配是可重复的高频动作，把用户引回链路起点继续练（而非结束）。也可考虑「再练一场面试」，待实现时定。

### A5. 链路条放大

圆点 18→24px、节点名 sm→base、连线 2→3px、节点区间 padding 加大——让 signature 更有存在感，呼应"链路条是首页主角"。

---

## 设计决策 B：CTA 可见性（page-cta-visibility）

### B1. 配置/输入型 → sticky 底部 CTA bar

典型：InterviewSetup（5 段配置 + 底部「开始面试」，整页 2121px）。

改：主 CTA + **配置摘要**固定视口底部（`position: sticky; bottom: 0`），配置区可滚动但 CTA 始终可见。
- 摘要示例：「全程 · 实战 · 字节跳动 · 严肃」（人设卡信息的浓缩，用户不滚也知道选了啥、随时能开始）
- 一石二鸟：CTA 可见 + 配置概览

### B2. 结果型 → CTA 上移 / 双 CTA

JdMatcher / ResumeOptimizer 结果超长，次级 CTA（「据此生成简历」「进入精修」）埋在结果深处。
改：结果区**顶部也放一个 CTA**（或结果区 sticky），用户看完匹配仪表 / 简历预览想直接操作时不用往下找。

### B3. 详情型 → 操作 sticky 或顶部

Profile 详情长（1655px），「编辑 / 保存」在 ProfileDisplay 底部。
改：操作按钮 sticky 或顶部固定。

### B4. 是否抽共用 sticky bar 组件

InterviewSetup / JdMatcher / Profile 都要 sticky CTA。可抽 `StickyActionBar.vue`（slot 放 CTA + 摘要）。
**权衡**：抽组件一致性好，但各页 CTA / 摘要内容不同，slot 设计有成本。决策：**先各页独立实现**，等模式稳定（2-3 页落地）再抽组件，避免过早抽象。
