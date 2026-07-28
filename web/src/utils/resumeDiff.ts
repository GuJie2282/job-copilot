/**
 * 简历 MD 行级 diff（evolve-refine-partial-update tasks 1.1/1.2）。
 *
 * 用于精修局部更新：找 newMd 相对 oldMd 改动的行号（对应 data-md-line 锚点），
 * 前端只局部替换这些原子，不整体刷新 iframe。
 *
 * 简化策略（避开 LCS 的行号偏移坑——删/增行会让后续行号错位，导致局部替换错原子）：
 * - 行数不变 → 逐行比，找改动行（行号与 data-md-line 一致，无偏移）
 * - 行数变化（增/删段落）→ bigChange，前端 fallback 整体 srcdoc 刷新
 * - 改动行占比超阈值 → bigChange（大改 fallback）
 *
 * 即：局部更新只承接「改文本不改结构」的改写（AI 一轮通常如此）；
 * 结构性重写（增删段落）走整体刷新兜底，保证不错乱。
 */

export interface DiffResult {
  /** newMd 中被改动的行号（0-based，对应 data-md-line）；bigChange 时为空 */
  changedLines: number[]
  /** true → 行数变化或改动过多，建议整体刷新（调用方 fallback） */
  bigChange: boolean
  /** bigChange 原因（提示用） */
  reason?: string
}

const BIG_CHANGE_RATIO = 0.3

export function diffResumeLines(oldMd: string, newMd: string): DiffResult {
  const oldLines = (oldMd || '').split('\n')
  const newLines = (newMd || '').split('\n')

  // 行数变 = 结构改动（增删段落）→ 行号会偏移，局部更新不安全 → fallback
  if (oldLines.length !== newLines.length) {
    return {
      changedLines: [],
      bigChange: true,
      reason: `行数变化（${oldLines.length} → ${newLines.length}），属结构改动`,
    }
  }

  const changedLines: number[] = []
  for (let i = 0; i < newLines.length; i++) {
    if (oldLines[i] !== newLines[i]) changedLines.push(i)
  }

  const ratio = changedLines.length / Math.max(newLines.length, 1)
  if (ratio > BIG_CHANGE_RATIO) {
    return {
      changedLines: [],
      bigChange: true,
      reason: `改动占比 ${(ratio * 100).toFixed(0)}% 超过 ${BIG_CHANGE_RATIO * 100}%`,
    }
  }

  return { changedLines, bigChange: false }
}
