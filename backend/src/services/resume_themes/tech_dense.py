"""
主题：技术密排风（tech-dense）

移植自 amlei-resume skill 的 references/themes/theme-tech-dense.md：
- 单栏 · 高密度 · 工程蓝单点缀色 · 技术栈前置（mono chips）· `•` 列表符
- 适用于互联网技术 / 算法 / 后端 / 基础架构 / AI 工程岗

本文件提供：
- STYLE：完整 <style> 块（渲染时整段贴在产物最前）
- 组件渲染函数：render_header / render_section_head / render_entry / render_bullet /
  render_summary / render_stack —— 由 resume_exporter 解析 MD 后调用

组件 class 与 STYLE 一一对应，装配出的 HTML 由预览壳（preview_shell.html）
负责 A4 分页与打印。

作者：求职 Copilot 项目
日期：2026-07-22
"""

import re
import html as _html


# ============================================================================
# 完整 <style>（移植自 skill theme-tech-dense.md，去掉 MVP 不用的论文/竞赛样式）
# ============================================================================

STYLE = """<style>
  :root{
    --bg:oklch(94% .004 240);--paper:oklch(99.4% .002 240);--ink:oklch(19% .015 240);--muted:oklch(43% .013 240);
    --faint:oklch(55% .011 240);--border:oklch(87% .008 240);--hair:oklch(90% .006 240);
    --accent:oklch(46% .17 242);--accent-ink:oklch(38% .15 242);--accent-soft:oklch(95% .03 242);
    --font-sans:'PingFang SC','HarmonyOS Sans SC','Microsoft YaHei','Hiragino Sans GB',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
    --font-mono:'JetBrains Mono','SF Mono',ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace;
  }
  body{background:var(--bg);color:var(--ink);font-family:var(--font-sans);font-size:14px;line-height:1.58;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' on;text-rendering:optimizeLegibility}
  .page{background:var(--paper)}
  .page-content{padding:13mm 15mm 13mm}
  /* Header */
  .resume-header{display:grid;grid-template-columns:1fr auto;gap:18px;align-items:center;padding-bottom:12px;border-bottom:2px solid var(--ink)}
  .name-row{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
  .name-row .name{font-weight:700;font-size:26px;letter-spacing:.04em}
  .name-row .role{font-size:13px;font-weight:600;color:var(--accent-ink);background:var(--accent-soft);padding:3px 9px}
  .contact{margin-top:8px;font-family:var(--font-mono);font-size:11px;color:var(--muted)}
  .contact .sep{color:var(--accent);margin:0 6px}
  .contact a{color:var(--accent-ink);text-decoration:none}
  .edu-line{margin-top:6px;font-family:var(--font-sans);font-size:12px;color:var(--accent-ink);font-weight:500}
  /* SectionHead */
  .sec-head{display:flex;align-items:center;gap:8px;margin-top:15px;margin-bottom:8px}
  .sec-head h2{font-size:14px;font-weight:700;letter-spacing:.16em;color:var(--ink)}
  .sec-head::after{content:"";flex:1;height:1px;background:var(--hair)}
  .summary p{font-size:13px;line-height:1.7;text-align:justify;text-wrap:pretty}
  .summary p strong{color:var(--accent-ink);font-weight:600}
  /* 技术栈 chips */
  .stack{display:flex;flex-direction:column;gap:6px}
  .stack-row{display:grid;grid-template-columns:64px 1fr;gap:10px;align-items:start}
  .stack-row .cat{font-family:var(--font-mono);font-size:11px;color:var(--accent);padding-top:3px;letter-spacing:.04em}
  .chips{display:flex;flex-wrap:wrap;gap:4px}
  .chip{font-family:var(--font-mono);font-size:11.5px;color:var(--ink);border:1px solid var(--border);padding:1.5px 7px}
  .chip.strong{color:var(--accent-ink);background:var(--accent-soft);border-color:oklch(80% .04 242);font-weight:600}
  /* Entry */
  .entry{margin-bottom:10px}
  .entry-main{display:grid;grid-template-columns:1fr auto;align-items:baseline;gap:14px}
  .entry-title{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
  .entry-title .org,.entry-title .proj{font-size:14px;font-weight:700}
  .entry-title .role{font-size:13px;color:var(--accent-ink);font-weight:500}
  .entry-date{font-family:var(--font-mono);font-size:11px;color:var(--faint);white-space:nowrap}
  /* Bullet（独立原子，自由换页） */
  .bullet{position:relative;padding-left:13px;font-size:12.5px;line-height:1.68;color:var(--ink);margin-bottom:2px;text-align:justify;text-wrap:pretty}
  .bullet::before{content:"•";position:absolute;left:1px;top:5px;color:var(--accent);font-size:10px;line-height:1}
  .bullet .num,.bullet .kw{font-family:var(--font-mono);color:var(--accent-ink);font-weight:600}
</style>"""


# ============================================================================
# 组件渲染函数（接收解析后的数据，返回 HTML 原子字符串）
# ============================================================================

def _esc(s) -> str:
    """HTML 转义（None → 空串）"""
    return _html.escape(str(s)) if s else ""


def _inline(text: str) -> str:
    """
    行内格式化：先转义，再把 **xx** → <strong>（强调字色）。
    数字/关键词的 .num/.kw 高亮 MVP 暂不做（避免误伤），保留扩展位。
    """
    t = _esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', t)
    return t


def render_header(name: str, role: str, education: str, contact_parts: list) -> str:
    """
    渲染 Header（self-intro 模块）。

    Args:
        name:          姓名
        role:          求职意向/方向（如 "AI 产品经理"）
        education:     教育一行（如 "清华大学 · 计算机 · 本科 · 2022届"）
        contact_parts: 联系方式片段列表（已转义的 HTML，如 phone/email/location）
    Returns:
        Header HTML
    """
    contact_html = '<span class="sep">·</span>'.join(p for p in contact_parts if p)
    edu_html = f'<div class="edu-line">{_esc(education)}</div>' if education else ""
    return (
        f'<header class="resume-header">'
        f'<div class="ident">'
        f'<div class="name-row"><span class="name">{_esc(name)}</span>'
        f'<span class="role">{_esc(role)}</span></div>'
        f'{edu_html}'
        f'<div class="contact">{contact_html}</div>'
        f'</div>'
        f'</header>'
    )


def render_section_head(title: str) -> str:
    """渲染模块标题（# 模块名）。data-stick 让标题与首条内容同页。"""
    return f'<div class="sec-head" data-stick="1"><h2>{_esc(title)}</h2></div>'


def render_summary(text: str) -> str:
    """渲染模块下的纯文本段（如个人简介）。"""
    return f'<div class="summary"><p>{_inline(text)}</p></div>'


def render_entry(org: str, role: str, date: str, bullets: list) -> str:
    """
    渲染经历条目（## 机构 | 角色）+ 其下 bullet。

    Args:
        org:     机构/公司（或项目名）
        role:    角色/方向
        date:    时间段（如 "2024.07 — 至今"）
        bullets: bullet 文本列表
    """
    bullets_html = "".join(render_bullet(b) for b in bullets)
    role_html = f'<span class="role">{_esc(role)}</span>' if role else ""
    date_html = f'<span class="entry-date">{_esc(date)}</span>' if date else ""
    return (
        f'<div class="entry" data-stick="1">'
        f'<div class="entry-main">'
        f'<div class="entry-title"><span class="org">{_esc(org)}</span>{role_html}</div>'
        f'{date_html}'
        f'</div>'
        f'{bullets_html}'
        f'</div>'
    )


def render_bullet(text: str) -> str:
    """渲染单条经历要点（独立原子，可自由换页）。"""
    return f'<div class="bullet">{_inline(text)}</div>'


def render_stack(rows: list) -> str:
    """
    渲染技能栈（mono chips，前置）。

    Args:
        rows: [(category, [chip, chip]), ...]，如 [("编程语言", ["Python", "Java"])]
    """
    rows_html = ""
    for cat, chips in rows:
        chips_html = "".join(f'<span class="chip">{_esc(c)}</span>' for c in chips if c)
        rows_html += (
            f'<div class="stack-row"><span class="cat">{_esc(cat)}</span>'
            f'<div class="chips">{chips_html}</div></div>'
        )
    return f'<div class="stack">{rows_html}</div>' if rows_html else ""
