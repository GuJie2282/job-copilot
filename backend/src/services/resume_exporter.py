"""
简历导出装配服务（resume_exporter）

职责：把 Markdown 简历程序化装配成带主题样式的 HTML，并套预览壳（A4 分页 + 打印 PDF）。

与 amlei-resume skill 的区别：skill 靠 LLM 按 export.md 指引「装配」HTML（慢、不稳定）；
本模块是**纯程序化装配**（代码解析 MD → 套主题组件 → 注入预览壳），快且稳定，
适合在 LangGraph 节点里同步产出。

核心入口：
- export_resume(md, target_position, title) → 完整预览页 HTML（供前端预览 + 浏览器打印 PDF）
- assemble_html(md, theme_id)                → 产物正文（<style> + 组件原子，不含预览壳）
- wrap_preview(body_html, title)             → 套预览壳（注入三个槽位）
- audit(md, body_html)                        → 装配后审查（模块/经历/bullet 数量对比，防遗漏）

作者：求职 Copilot 项目
日期：2026-07-22
"""

import os
import re
import logging
from typing import List, Dict, Any, Tuple

from src.services.resume_themes import get_theme, select_theme
from src.services.resume_validator import SELF_INTRO_SLUGS  # 复用首模块标识

logger = logging.getLogger(__name__)

# 预览壳路径（同目录的 preview_shell.html，移植自 skill 的 assets/preview-shell.html）
SHELL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume_themes", "preview_shell.html")

# 判定为「技能/技术栈」类模块的关键词（用 Stack 组件渲染）
SKILL_KEYWORDS = ("技能", "技术栈", "技术能力", "技术", "skills", "skill")
# KV 行正则（与 validator 一致）
KV_RE = re.compile(r"^([A-Za-z一-龥][\w一-龥\-]*)\s*:\s*(.+)$")


# ============================================================================
# MD 解析
# ============================================================================

def parse_resume_md(md: str) -> List[Dict[str, Any]]:
    """
    按 `# ` 一级标题把简历拆成模块列表。

    Returns:
        [{"title": 模块名, "lines": [模块内行]}, ...]，顺序与 MD 一致。
    """
    lines = md.splitlines()
    h1_idx = [i for i, ln in enumerate(lines) if ln.startswith("# ")]
    sections = []
    for k, start in enumerate(h1_idx):
        end = h1_idx[k + 1] if k + 1 < len(h1_idx) else len(lines)
        title = lines[start][2:].strip()
        sections.append({"title": title, "lines": lines[start + 1:end]})
    return sections


def _parse_intro(lines: List[str]) -> Dict[str, str]:
    """
    解析 self-intro 模块的 key: value（含缩进子项，如 links）。
    """
    intro: Dict[str, str] = {}
    last_key = None
    for ln in lines:
        raw = ln.strip()
        if not raw:
            continue
        m = KV_RE.match(raw)
        if m:
            k, v = m.group(1).lower(), m.group(2).strip()
            intro[k] = v
            last_key = k
        elif raw.startswith("- ") and last_key:
            sub = raw[2:].strip()
            intro[last_key] = f"{intro[last_key]}\n{sub}" if intro[last_key] else sub
    return intro


def _parse_stack(lines: List[str]) -> List[Tuple[str, List[str]]]:
    """
    解析技能模块的 `- 类别: 值`（值用 · 分隔成多 chip）。
    """
    rows = []
    for ln in lines:
        raw = ln.strip()
        if not raw.startswith("- "):
            continue
        body = raw[2:].strip()
        if ":" not in body and "：" not in body:
            continue
        # 中英文冒号都支持
        parts = re.split(r"[:：]", body, maxsplit=1)
        cat, val = parts[0], parts[1]
        chips = [c.strip() for c in re.split(r"[·、,，/]", val) if c.strip()]
        if cat.strip() and chips:
            rows.append((cat.strip(), chips))
    return rows


# ============================================================================
# 装配
# ============================================================================

def assemble_html(md: str, theme_id: str = "tech_dense") -> str:
    """
    把 Markdown 简历装配成产物正文：<style> + 组件原子（不含预览壳）。

    映射规则（对应 design 决策 5 + skill export.md）：
    - `# self-intro` → Header
    - `# 技能/技术栈` → SectionHead + Stack(chips)
    - 其他 `# 模块` → SectionHead + 正文（## 经历→Entry，- bullet→Bullet，纯文本→Summary）
    """
    theme = get_theme(theme_id)
    sections = parse_resume_md(md)
    atoms: List[str] = []

    for sec in sections:
        title = sec["title"]
        title_l = title.lower().strip()

        # 1. self-intro → Header
        if title_l in SELF_INTRO_SLUGS:
            intro = _parse_intro(sec["lines"])
            atoms.append(_render_header_from_intro(intro, theme))
            continue

        # 2. 技能类模块 → SectionHead + Stack
        if any(k in title_l for k in SKILL_KEYWORDS):
            rows = _parse_stack(sec["lines"])
            atoms.append(theme.render_section_head(title))
            stack_html = theme.render_stack(rows)
            if stack_html:
                atoms.append(stack_html)
            continue

        # 3. 普通模块 → SectionHead + 正文
        atoms.append(theme.render_section_head(title))
        atoms.extend(_render_section_body(sec["lines"], theme))

    body = theme.STYLE + "\n" + "\n".join(a for a in atoms if a)
    return body


def _render_header_from_intro(intro: Dict[str, str], theme) -> str:
    """从解析的 intro 渲染 Header：name/role/education + contact 拼接。"""
    name = intro.get("name", "")
    role = intro.get("role", "")
    education = intro.get("education", "")

    contact = []
    for k in ("gender", "location", "phone", "email"):
        v = intro.get(k)
        if v:
            contact.append(theme._esc(v))  # 已转义的纯文本片段
    # links 子项（- GitHub: url）渲染为链接
    links_raw = intro.get("links", "")
    for line in links_raw.split("\n"):
        if ":" in line:
            label, _, url = line.partition(":")
            url = url.strip()
            if url:
                contact.append(f'<a href="{theme._esc(url)}">{theme._esc(label.strip())}</a>')
    return theme.render_header(name, role, education, contact)


def _render_section_body(lines: List[str], theme) -> List[str]:
    """渲染普通模块正文：## 经历 → Entry（含 date/bullets）；- bullet → Bullet；纯文本 → Summary。"""
    atoms: List[str] = []
    entry: Dict[str, Any] = None  # 当前经历条目

    def flush():
        nonlocal entry
        if entry:
            atoms.append(theme.render_entry(
                org=entry["org"], role=entry["role"], date=entry["date"], bullets=entry["bullets"]
            ))
            entry = None

    for ln in lines:
        raw = ln.strip()
        if not raw:
            continue
        if raw.startswith("## "):
            flush()
            head = raw[3:].strip()
            # 机构 | 角色（兼容中英文竖线）
            if "|" in head or "｜" in head:
                parts = re.split(r"[|｜]", head, maxsplit=1)
                org, role = parts[0], parts[1]
            else:
                org, role = head, ""
            entry = {"org": org.strip(), "role": role.strip(), "date": "", "bullets": []}
        elif raw.lower().startswith("date:"):
            if entry:
                entry["date"] = raw.split(":", 1)[1].strip()
        elif raw.startswith("- "):
            bullet = raw[2:].strip()
            if entry:
                entry["bullets"].append(bullet)
            else:
                atoms.append(theme.render_bullet(bullet))  # 模块级散落 bullet
        else:
            flush()
            atoms.append(theme.render_summary(raw))  # 纯文本段
    flush()
    return atoms


# ============================================================================
# 预览壳包装
# ============================================================================

def wrap_preview(body_html: str, title: str = "简历预览") -> str:
    """
    把装配产物（<style> + 原子）注入预览壳，得到完整 A4 预览页（含打印 PDF 工具条）。

    预览壳的三个槽位（移植自 skill wrap_preview.py）：
    - <!--RESUME_STYLE--> ← 主题 <style>
    - <!--RESUME_BODY-->   ← 组件原子
    - {{TITLE}}            ← document.title（= 浏览器「另存为 PDF」默认文件名）
    """
    if not os.path.isfile(SHELL_PATH):
        logger.warning(f"预览壳不存在：{SHELL_PATH}，返回未包装的产物正文")
        return body_html

    with open(SHELL_PATH, encoding="utf-8") as f:
        shell = f.read()

    # 拆出开头的 <style> 与正文原子
    m = re.match(r"^\s*(<style\b[^>]*>.*?</style>)\s*(.*)", body_html, re.I | re.S)
    if m:
        style_html, atoms_html = m.group(1), m.group(2).strip()
    else:
        style_html, atoms_html = "", body_html.strip()

    out = (shell
           .replace("<!--RESUME_STYLE-->", style_html)
           .replace("<!--RESUME_BODY-->", atoms_html)
           .replace("{{TITLE}}", title))
    return out


# ============================================================================
# 装配后审查（防遗漏/错序）
# ============================================================================

def audit(md: str, body_html: str) -> Dict[str, Any]:
    """
    逐模块对比 MD 与 HTML 结构，报告数量差异（防装配遗漏）。

    注：self-intro 渲染成 Header（无 sec-head），故 html_sec_head 预期 = md_modules - 1。
    bullet：经历内的 bullet 渲染为 .bullet 原子；技能模块的 chips 不算 bullet。
    """
    md_modules = len([l for l in md.splitlines() if l.startswith("# ")])
    md_entries = len([l for l in md.splitlines() if l.startswith("## ")])
    md_bullets = len([l for l in md.splitlines() if l.startswith("- ")])
    html_sec_head = body_html.count('class="sec-head"')
    html_entries = body_html.count('class="entry"')
    html_bullets = body_html.count('class="bullet"')

    issues = []
    # 模块：md 模块数 - 1(self-intro) 应 = sec-head 数
    if html_sec_head < md_modules - 1:
        issues.append(f"模块可能遗漏：MD {md_modules} 个模块，HTML 仅 {html_sec_head} 个 sec-head")
    if html_entries != md_entries:
        issues.append(f"经历数不一致：MD {md_entries} 个 ##，HTML {html_entries} 个 .entry")

    return {
        "md_modules": md_modules,
        "html_sec_head": html_sec_head,
        "md_entries": md_entries,
        "html_entries": html_entries,
        "md_bullets": md_bullets,
        "html_bullets": html_bullets,
        "issues": issues,
    }


# ============================================================================
# 排版粗估（4.3.2 占位：真实页数/填充率需浏览器渲染，这里给字符数粗估）
# ============================================================================

def estimate_pages(md: str) -> Dict[str, Any]:
    """
    基于内容长度粗估页数（MVP 占位）。

    真正的页数/末页填充率/行尾空白需浏览器渲染（Playwright）才能精确测量，
    留到 Phase 7 打磨或接入 Playwright。这里按经验值（~1500 字符/页）粗估。
    """
    char_count = len(md or "")
    est = max(1, round(char_count / 1500))
    return {
        "char_count": char_count,
        "estimated_pages": est,
        "note": "粗估页数（按 ~1500 字符/页）；精确页数与填充率需浏览器渲染，待 Phase 7 / Playwright",
    }


# ============================================================================
# 主入口
# ============================================================================

def export_resume(md: str, target_position: str = "", title: str = None) -> Dict[str, Any]:
    """
    完整导出：选主题 → 装配 HTML → 套预览壳 → 审查 + 粗估页数。

    Args:
        md:               Markdown 简历全文
        target_position:  目标岗位（决定主题选择）
        title:            预览页标题（= PDF 默认文件名）；不传用"简历预览"
    Returns:
        {
            "html":         完整预览页 HTML（前端可直接渲染 + 打印 PDF），
            "body_html":    产物正文（<style> + 原子，不含预览壳），
            "theme":        使用的主题 id,
            "audit":        审查结果,
            "pages":        页数粗估,
        }
    """
    theme_id = select_theme(target_position)
    body_html = assemble_html(md, theme_id)
    full_html = wrap_preview(body_html, title or "简历预览")
    result = {
        "html": full_html,
        "body_html": body_html,
        "theme": theme_id,
        "audit": audit(md, body_html),
        "pages": estimate_pages(md),
    }
    logger.info("resume_exported", extra={"theme": theme_id, "issues": len(result["audit"]["issues"])})
    return result
