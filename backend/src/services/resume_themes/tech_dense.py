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
  .resume-header{display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:center;padding-bottom:12px;border-bottom:2px solid var(--ink)}
  .resume-header .avatar{width:56px;height:56px;border-radius:50%;object-fit:cover;border:1px solid var(--hair)}
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
  /* 待补充标记：红框突出，精修/预览时防漏补 */
  .bullet .todo,.summary .todo,.desc .todo{display:inline-block;border:1.5px solid #e03131;color:#e03131;background:rgba(224,49,49,.06);padding:0 5px;border-radius:3px;font-style:normal;font-weight:600;line-height:1.5}
</style>"""


# ============================================================================
# 组件渲染函数（接收解析后的数据，返回 HTML 原子字符串）
# ============================================================================

def _esc(s) -> str:
    """HTML 转义（None → 空串）"""
    return _html.escape(str(s)) if s else ""


def _inline(text: str) -> str:
    """
    行内格式化：先转义，再把 **xx** → <strong>（强调字色）；「（待补充：…）」→ 红框突出（防漏补）。
    数字/关键词的 .num/.kw 高亮 MVP 暂不做（避免误伤），保留扩展位。
    """
    t = _esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', t)
    # 「（待补充：xxx）」/「(待补充: xxx)」→ 红框 span（精修时提醒漏补充）
    t = re.sub(r"([（(]\s*待补充\s*[：:]\s*[^）)]+?[）)])",
               r'<span class="todo">\1</span>', t)
    return t


def _md_attr(md_line) -> str:
    """
    生成 data-md-line 锚点属性（精修工作台用，evolve-resume-refine）。

    Markdown 是简历的唯一真相源，HTML 的每个可编辑原子带上它对应的 MD 行号后，
    用户在预览里改文字就能精确回写到那一行（局部回写，不重建整份、不丢未编辑字段）。
    传入 None（行号未知）则不注入。
    """
    return f' data-md-line="{md_line}"' if md_line is not None else ""


def render_header(name: str, role: str, education: str, contact_parts: list,
                  *, avatar_url: str = "", name_line=None, role_line=None, edu_line=None, contact_lines=None) -> str:
    """
    渲染 Header（self-intro 模块）。name/role/education 与各 contact 片段均带 data-md-line 锚点。

    Args:
        name / role / education: 同前
        contact_parts: 联系方式片段列表（已转义的 HTML，如 phone/email/location/链接）
        avatar_url: 头像 URL（来自画像，不进 MD 真相源；空串则不渲染头像）
        name_line / role_line / edu_line: 各字段对应 MD 行号（None 则不锚）
        contact_lines: 与 contact_parts 平行的行号列表（按原索引取，跳过空片段）
    Returns:
        Header HTML
    """
    # 配对每个 contact 片段与其源行号（按原索引对齐）
    contact_pairs = []
    for idx, part in enumerate(contact_parts):
        if part:
            ln = contact_lines[idx] if contact_lines and idx < len(contact_lines) else None
            contact_pairs.append((part, ln))
    contact_html = '<span class="sep">·</span>'.join(
        f'<span{_md_attr(ln)}>{p}</span>' for p, ln in contact_pairs
    )
    edu_html = f'<div class="edu-line"{_md_attr(edu_line)}>{_esc(education)}</div>' if education else ""
    # 头像（不挂 data-md-line：头像不参与精修文本回写，换图走画像页单一来源）
    avatar_html = f'<img class="avatar" src="{_esc(avatar_url)}" alt="头像">' if avatar_url else ""
    return (
        f'<header class="resume-header">'
        f'{avatar_html}'
        f'<div class="ident">'
        f'<div class="name-row"><span class="name"{_md_attr(name_line)}>{_esc(name)}</span>'
        f'<span class="role"{_md_attr(role_line)}>{_esc(role)}</span></div>'
        f'{edu_html}'
        f'<div class="contact">{contact_html}</div>'
        f'</div>'
        f'</header>'
    )


def render_section_head(title: str) -> str:
    """渲染模块标题（# 模块名）。data-stick 让标题与首条内容同页。"""
    return f'<div class="sec-head" data-stick="1"><h2>{_esc(title)}</h2></div>'


def render_summary(text: str, md_line=None) -> str:
    """渲染模块下的纯文本段（如个人简介）。md_line 为该段对应 MD 行号（精修锚点）。"""
    return f'<div class="summary"{_md_attr(md_line)}><p>{_inline(text)}</p></div>'


def render_entry(org: str, role: str, date: str, bullets: list,
                 *, org_line=None, date_line=None, bullet_lines=None) -> str:
    """
    渲染经历条目（## 机构 | 角色）+ 其下 bullet。

    org 与 role 共享一行（`## org | role`），故两者都用 org_line；额外用 data-md-field
    区分，使精修回写时能把同行的 org/role 合并重组。date 单独一行，各 bullet 各自一行。

    Args:
        org / role / date / bullets: 同前
        org_line:     `## ` 行号（org/role 共享）
        date_line:    date 行号
        bullet_lines: 与 bullets 平行的行号列表
    """
    bullets_html = "".join(
        render_bullet(b, md_line=(bullet_lines[i] if bullet_lines and i < len(bullet_lines) else None))
        for i, b in enumerate(bullets)
    )
    role_html = (
        f'<span class="role"{_md_attr(org_line)} data-md-field="entry-role">{_esc(role)}</span>'
        if role else ""
    )
    date_html = (
        f'<span class="entry-date"{_md_attr(date_line)} data-md-field="date">{_esc(date)}</span>'
        if date else ""
    )
    return (
        f'<div class="entry" data-stick="1">'
        f'<div class="entry-main">'
        f'<div class="entry-title">'
        f'<span class="org"{_md_attr(org_line)} data-md-field="entry-org">{_esc(org)}</span>'
        f'{role_html}</div>'
        f'{date_html}'
        f'</div>'
        f'{bullets_html}'
        f'</div>'
    )


def render_bullet(text: str, md_line=None) -> str:
    """渲染单条经历要点（独立原子，可自由换页）。md_line 为对应 MD 行号（精修锚点）。"""
    return f'<div class="bullet"{_md_attr(md_line)}>{_inline(text)}</div>'


def render_stack(rows: list, row_lines=None) -> str:
    """
    渲染技能栈（mono chips，前置）。每个 stack-row 带 data-md-line 锚点指向 `- 类别: chips` 行。

    Args:
        rows:      [(category, [chip, chip]), ...]，如 [("编程语言", ["Python", "Java"])]
        row_lines: 与 rows 平行的行号列表（精修回写时按行重组 cat + chips）
    """
    rows_html = ""
    for i, (cat, chips) in enumerate(rows):
        ln = row_lines[i] if row_lines and i < len(row_lines) else None
        chips_html = "".join(f'<span class="chip">{_esc(c)}</span>' for c in chips if c)
        rows_html += (
            f'<div class="stack-row"{_md_attr(ln)}><span class="cat">{_esc(cat)}</span>'
            f'<div class="chips">{chips_html}</div></div>'
        )
    return f'<div class="stack">{rows_html}</div>' if rows_html else ""
