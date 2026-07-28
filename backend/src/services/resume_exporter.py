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

⚠️ 精修工作台锚点（evolve-resume-refine Tasks 1）：
  Markdown 是简历的「唯一真相源」，HTML 是它的程序化派生渲染。为了让用户能在左侧
  预览里「所见即所得」地改文字、并把改动精确回写到对应 Markdown 行（而不是重建整份
  导致未编辑字段丢失），装配时给每个可编辑原子注入 `data-md-line` 锚点，记录它对应
  Markdown 全文的第几行（0-based）。精修的 patch-draft 端点据此做「局部回写」。
  - 单字段单行的原子（bullet / summary / stack-row / name / role / education / contact / date）
    靠 data-md-line 即可定位；回写时按原行前缀（`- ` / `key:` / 纯文本）重组。
  - 经历的 org 与 role 共享一行（`## org | role`），额外加 data-md-field 区分，回写时
    同行合并重组。

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

# 普通模块（非 self-intro）里不应出现 self-intro 式的字段行。但 LLM 偶尔会把字段名当正文写
# （典型：「# 教育背景」模块下写 `education: 学校 · 专业 · 学历`，导致字面「education:」泄漏进简历正文）。
# 这些 key 是已知字段名而非正文，渲染普通模块时遇到就剥掉 key、只显示 value；
# 未在集合里的半角冒号文本（如「核心能力: xxx」作纯文本段）照常保留，避免误伤。
_KV_DROP_KEYS = {
    "name", "role", "education", "phone", "email", "location", "gender", "links",
    "school", "degree", "major", "university", "college", "gpa",
    "学校", "专业", "学历", "学位", "院系",
}


# ============================================================================
# MD 解析（带全局行号，供精修锚点用）
# ============================================================================

def parse_resume_md(md: str) -> List[Dict[str, Any]]:
    """
    按 `# ` 一级标题把简历拆成模块列表。

    Returns:
        [{"title": 模块名, "lines": [模块内行], "start_line": 模块内首行的全局行号}, ...]
        顺序与 MD 一致。start_line 用于给装配出的原子打 data-md-line 锚点：
        模块内第 i 行的全局行号 = start_line + i（# 标题行本身不算）。
    """
    lines = md.splitlines()
    h1_idx = [i for i, ln in enumerate(lines) if ln.startswith("# ")]
    sections = []
    for k, start in enumerate(h1_idx):
        end = h1_idx[k + 1] if k + 1 < len(h1_idx) else len(lines)
        title = lines[start][2:].strip()
        sections.append({
            "title": title,
            "lines": lines[start + 1:end],
            "start_line": start + 1,  # lines[0] 在全文中的行号（# 标题在 start，其后一行是 start+1）
        })
    return sections


def _parse_intro(lines: List[str], start_line: int = 0) -> Tuple[Dict[str, str], Dict[str, int]]:
    """
    解析 self-intro 模块的 key: value（含缩进子项，如 links）。

    Args:
        lines:      模块内行（不含 # 标题）
        start_line: lines[0] 的全局行号（用于记录每个字段所在行，供锚点）
    Returns:
        (intro, line_map)
        - intro:    {key: value}（同原逻辑）
        - line_map: {key: 该 key 所在全局行号}（links 多行子项用其 KV 行号近似）
    """
    intro: Dict[str, str] = {}
    line_map: Dict[str, int] = {}
    last_key = None
    for i, ln in enumerate(lines):
        raw = ln.strip()
        if not raw:
            continue
        global_line = start_line + i
        m = KV_RE.match(raw)
        if m:
            k, v = m.group(1).lower(), m.group(2).strip()
            intro[k] = v
            line_map[k] = global_line
            last_key = k
        elif raw.startswith("- ") and last_key:
            sub = raw[2:].strip()
            intro[last_key] = f"{intro[last_key]}\n{sub}" if intro[last_key] else sub
            # links 子项挂到 last_key；行号用其 KV 行（若 KV 行本身没记录则补当前行）
            if last_key not in line_map:
                line_map[last_key] = global_line
    return intro, line_map


def _parse_stack(lines: List[str], start_line: int = 0) -> Tuple[List[Tuple[str, List[str]]], List[int]]:
    """
    解析技能模块的 `- 类别: 值`（值用 · 分隔成多 chip）。

    Args:
        lines:      模块内行
        start_line: lines[0] 的全局行号
    Returns:
        (rows, row_lines)
        - rows:      [(category, [chip, ...]), ...]
        - row_lines: 每行对应的全局行号（与 rows 平行，供 stack-row 锚点）
    """
    rows: List[Tuple[str, List[str]]] = []
    row_lines: List[int] = []
    for i, ln in enumerate(lines):
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
            row_lines.append(start_line + i)
    return rows, row_lines


# ============================================================================
# 装配
# ============================================================================

def assemble_html(md: str, theme_id: str = "tech_dense", avatar_url: str = "") -> str:
    """
    把 Markdown 简历装配成产物正文：<style> + 组件原子（不含预览壳）。

    映射规则（对应 design 决策 5 + skill export.md）：
    - `# self-intro` → Header
    - `# 技能/技术栈` → SectionHead + Stack(chips)
    - 其他 `# 模块` → SectionHead + 正文（## 经历→Entry，- bullet→Bullet，纯文本→Summary）

    装配时把每个模块的 start_line 透传给解析与渲染，使产出的可编辑原子带上
    data-md-line 锚点（精修局部回写用，见文件头说明）。
    """
    theme = get_theme(theme_id)
    sections = parse_resume_md(md)
    atoms: List[str] = []

    for sec in sections:
        title = sec["title"]
        title_l = title.lower().strip()
        start_line = sec["start_line"]  # 模块内首行的全局行号

        # 1. self-intro → Header
        if title_l in SELF_INTRO_SLUGS:
            intro, line_map = _parse_intro(sec["lines"], start_line)
            atoms.append(_render_header_from_intro(intro, line_map, theme, avatar_url))
            continue

        # 2. 技能类模块 → SectionHead + Stack
        if any(k in title_l for k in SKILL_KEYWORDS):
            rows, row_lines = _parse_stack(sec["lines"], start_line)
            atoms.append(theme.render_section_head(title))
            stack_html = theme.render_stack(rows, row_lines=row_lines)
            if stack_html:
                atoms.append(stack_html)
            continue

        # 3. 普通模块 → SectionHead + 正文
        atoms.append(theme.render_section_head(title))
        atoms.extend(_render_section_body(sec["lines"], start_line, theme))

    body = theme.STYLE + "\n" + "\n".join(a for a in atoms if a)
    return body


def _render_header_from_intro(intro: Dict[str, str], line_map: Dict[str, int], theme, avatar_url: str = "") -> str:
    """
    从解析的 intro 渲染 Header：name/role/education + contact 拼接。
    把各字段的行号透传给 theme.render_header，使其带上 data-md-line 锚点。
    """
    name = intro.get("name", "")
    role = intro.get("role", "")
    education = intro.get("education", "")

    # contact 各字段：文本片段 + 它们各自的全局行号（平行）
    contact: List[str] = []
    contact_lines: List[int] = []
    for k in ("gender", "location", "phone", "email"):
        v = intro.get(k)
        if v:
            contact.append(theme._esc(v))  # 已转义的纯文本片段
            contact_lines.append(line_map.get(k))
    # links 子项（- GitHub: url）渲染为链接；行号统一用 links 的 KV 行
    links_raw = intro.get("links", "")
    links_line = line_map.get("links")
    for line in links_raw.split("\n"):
        if ":" in line:
            label, _, url = line.partition(":")
            url = url.strip()
            if url:
                contact.append(f'<a href="{theme._esc(url)}">{theme._esc(label.strip())}</a>')
                contact_lines.append(links_line)
    return theme.render_header(
        name, role, education, contact,
        avatar_url=avatar_url,
        name_line=line_map.get("name"),
        role_line=line_map.get("role"),
        edu_line=line_map.get("education"),
        contact_lines=contact_lines,
    )


def _render_section_body(lines: List[str], start_line: int, theme) -> List[str]:
    """
    渲染普通模块正文：## 经历 → Entry（含 date/bullets）；- bullet → Bullet；纯文本 → Summary。
    跟踪每行的全局行号（= start_line + 模块内偏移），透传给 render_* 打锚点。
    """
    atoms: List[str] = []
    entry: Dict[str, Any] = None  # 当前经历条目
    entry_line: int = None        # 当前经历 `## ` 行的全局行号（org/role 共享）

    def flush():
        nonlocal entry, entry_line
        if entry:
            atoms.append(theme.render_entry(
                org=entry["org"], role=entry["role"], date=entry["date"], bullets=entry["bullets"],
                org_line=entry_line,
                date_line=entry["date_line"],
                bullet_lines=entry["bullet_lines"],
            ))
            entry = None
            entry_line = None

    for i, ln in enumerate(lines):
        raw = ln.strip()
        if not raw:
            continue
        global_line = start_line + i
        if raw.startswith("## "):
            flush()
            head = raw[3:].strip()
            # 机构 | 角色（兼容中英文竖线）
            if "|" in head or "｜" in head:
                parts = re.split(r"[|｜]", head, maxsplit=1)
                org, role = parts[0], parts[1]
            else:
                org, role = head, ""
            entry = {
                "org": org.strip(), "role": role.strip(), "date": "", "bullets": [],
                "date_line": None, "bullet_lines": [],
            }
            entry_line = global_line
        elif raw.lower().startswith("date:"):
            if entry:
                entry["date"] = raw.split(":", 1)[1].strip()
                entry["date_line"] = global_line
        elif raw.startswith("- "):
            bullet = raw[2:].strip()
            if entry:
                entry["bullets"].append(bullet)
                entry["bullet_lines"].append(global_line)
            else:
                atoms.append(theme.render_bullet(bullet, md_line=global_line))  # 模块级散落 bullet
        else:
            flush()
            # 纯文本段。若整行是「已知字段: 值」的 KV 行（LLM 误把字段名当正文，
            # 如教育背景模块下的 `education: ...`），剥掉 key 只渲染值，避免字面「education:」泄漏；
            # 未知 key / 普通半角冒号文本照常保留。
            text = raw
            m = KV_RE.match(raw)
            if m and m.group(1).lower() in _KV_DROP_KEYS:
                text = m.group(2).strip()
            atoms.append(theme.render_summary(text, md_line=global_line))
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
# 装配后审查（防遗漏/错序 + 锚点覆盖）
# ============================================================================

def audit(md: str, body_html: str) -> Dict[str, Any]:
    """
    逐模块对比 MD 与 HTML 结构，报告数量差异（防装配遗漏）；并检查可编辑原子的锚点覆盖率
    （精修局部回写依赖锚点，漏锚点 = 该处手改无法回写）。

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

    # 锚点覆盖率（evolve-resume-refine Tasks 1.4）：可编辑原子应都带 data-md-line
    bullets_anchored = body_html.count('class="bullet" data-md-line')
    if html_bullets and bullets_anchored < html_bullets:
        issues.append(
            f"{html_bullets - bullets_anchored} 个 bullet 缺 data-md-line 锚点（精修手改无法回写）"
        )
    anchored_total = body_html.count('data-md-line=')
    if md_bullets and anchored_total == 0:
        issues.append("装配产物无任何 data-md-line 锚点（精修回写不可用）")

    return {
        "md_modules": md_modules,
        "html_sec_head": html_sec_head,
        "md_entries": md_entries,
        "html_entries": html_entries,
        "md_bullets": md_bullets,
        "html_bullets": html_bullets,
        "anchors": anchored_total,
        "issues": issues,
    }


# ============================================================================
# 精修局部回写（evolve-resume-refine Tasks 2）：锚点 patch → Markdown
# ============================================================================

def apply_patches_to_md(md: str, patches: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """
    把「锚点 patch」局部应用到 Markdown 真相源（精修手改回写的核心）。

    设计要点：**只替换被改的行，不重建整份**——未触及的行原样保留，从而避免「全量
    HTML→MD 反序列化」丢字段、错结构的老问题（见 design 决策 2）。

    patch 由前端从带 data-md-line / data-md-field 的可编辑原子采集，格式：
      {"line": N, "field": "...", "text": "...", "cat": "...", "chips": [...]}
      - line:  目标行号（0-based，对应 data-md-line）
      - field: 可选。标识同行多字段中的某一个：
               entry-org / entry-role（经历机构与角色共享一行，需合并重组）
               stack（技能行按 cat + chips 重组）
               date / name / role / education / contact（KV 行，保留 key 前缀）
      - text:  新文本（多数情况）
      - cat + chips: field="stack" 时，重组 `- 类别: chip · chip`

    Returns:
        (new_md, warnings)
        - new_md: 回写后的 Markdown 全文
        - warnings: 未命中 / 无法回写的 patch 说明（不静默丢，前端可提示）
    """
    lines = md.splitlines()
    warnings: List[str] = []

    def _line_ok(line):
        return line is not None and 0 <= line < len(lines)

    # 1) 经历 org/role 共享一行：按 line 聚合后一次重组（避免互相覆盖）
    entry_groups: Dict[int, Dict[str, str]] = {}
    other: List[Dict[str, Any]] = []
    for p in patches:
        line, field = p.get("line"), p.get("field")
        if field in ("entry-org", "entry-role"):
            if not _line_ok(line):
                warnings.append(f"经历字段 patch 行号无效：{p}")
                continue
            key = "org" if field == "entry-org" else "role"
            entry_groups.setdefault(line, {})[key] = p.get("text", "")
        else:
            other.append(p)

    for line, grp in entry_groups.items():
        original = lines[line]
        if not original.startswith("## "):
            warnings.append(f"行 {line} 非 `## ` 经历行，跳过经历字段回写")
            continue
        head = original[3:].strip()
        if "|" in head or "｜" in head:
            parts = re.split(r"[|｜]", head, maxsplit=1)
            cur_org, cur_role = parts[0].strip(), parts[1].strip()
        else:
            cur_org, cur_role = head, ""
        new_org = grp.get("org", cur_org)
        new_role = grp.get("role", cur_role)
        lines[line] = f"## {new_org} | {new_role}" if new_role else f"## {new_org}"

    # 2) 其他 patch：按 field / 原行格式逐条重组
    for p in other:
        line, field, text = p.get("line"), p.get("field"), p.get("text", "")
        if not _line_ok(line):
            warnings.append(f"patch 行号无效：{p}")
            continue
        original = lines[line]
        raw = original.strip()

        if field == "stack":
            cat, chips = p.get("cat", ""), p.get("chips", [])
            if raw.startswith("- "):
                lines[line] = f"- {cat}: {' · '.join(chips)}" if chips else f"- {cat}:"
            else:
                warnings.append(f"行 {line} 非技能行，无法按 stack 回写")
        elif field == "date":
            lines[line] = f"date: {text}"
        elif field in ("name", "role", "education", "contact"):
            m = KV_RE.match(raw)
            if m:
                lines[line] = f"{m.group(1)}: {text}"  # 保留原 key 前缀
            else:
                warnings.append(f"行 {line} 非 KV 行，无法回写 {field}")
        else:
            # 无 field：按原行格式推断（bullet `- ` / KV / 纯文本 summary）
            m = KV_RE.match(raw)
            if raw.startswith("- "):
                lines[line] = f"- {text}"               # bullet（`- xxx`）
            elif m:
                lines[line] = f"{m.group(1)}: {text}"   # KV（contact 等，无 field 时兜底）
            else:
                lines[line] = text                       # summary 纯文本

    result = "\n".join(lines)
    # 保留原 md 的末尾换行（splitlines 会丢失），避免回写无故改变末尾空白
    if md.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result, warnings


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

def export_resume(md: str, target_position: str = "", title: str = None, avatar_url: str = "") -> Dict[str, Any]:
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
    body_html = assemble_html(md, theme_id, avatar_url)
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
