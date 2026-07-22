"""
简历格式校验服务（resume_validator）

职责：对生成的简历做「确定性格式校验」，作为 6 维 LLM 评估之外的第二层质量门。
只查硬规则（结构/格式），不查语义（语义交由 resume_evaluator 的 LLM 评估）。

移植自 amlei-resume skill 的 scripts/validate_resume.py，适配 job-copilot：
- 函数式 API（供 LangGraph 节点调用），去掉 CLI argparse 与文件系统依赖
- 保留 MD 硬规则与 HTML 产物硬规则
- 返回结构化结果（errors / warnings），ERROR 必须清零才允许导出

两层质量门（对应 design.md 决策 3）：
  LLM 评估（语义）+ 本模块（格式硬规则）= 双保险

作者：求职 Copilot 项目
日期：2026-07-22
"""

import re
from typing import List

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """格式校验结果。errors 必须清零才能导出；warnings 供参考不阻断。"""
    errors: List[str] = Field(default_factory=list, description="致命错误（必须修复）")
    warnings: List[str] = Field(default_factory=list, description="建议检查（不阻断）")

    @property
    def passed(self) -> bool:
        """无 error 即视为通过（warning 不阻断导出）"""
        return len(self.errors) == 0


# ── 规则常量（移植自 skill validate_resume.py）──
# self-intro 首模块的合法标识（中英文变体）
SELF_INTRO_SLUGS = {"self-intro", "self_intro", "selfintro", "self intro", "个人信息", "基本信息"}
REQUIRED_INTRO_KEYS = ["name"]  # self-intro 必填字段
# self-intro 已知键（出现未知键只提示，不报错）
KNOWN_INTRO_KEYS = {
    "name", "role", "gender", "location", "phone", "phone-number",
    "email", "site", "github", "csdn", "blog", "website", "linkedin",
    "portfolio", "avatar", "age", "birth", "political", "hometown",
    "ethnicity", "education-level", "platform", "education", "links",
}
# 教育背景模块的合法标识
EDUCATION_SLUGS = {"教育", "教育背景", "education", "学历", "学习经历"}

# 标题层级正则（本格式只用 # 和 ##）
H1_RE = re.compile(r"^#\s+(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H_DEEP_RE = re.compile(r"^#{3,}\s+")  # ### 及更深：只支持 # 和 ##
# date 行格式：YYYY.MM — YYYY.MM | 至今
DATE_RE = re.compile(r"^date:\s*(\d{4}\.\d{2})\s*[-—–]\s*(\d{4}\.\d{2}|至今)\s*$")
# self-intro 的 key: value 行
KV_RE = re.compile(r"^([A-Za-z一-龥][\w一-龥\-]*)\s*:\s*(.+)$")

# HTML 产物：未填充占位符
PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


def validate_resume_md(text: str) -> ValidationResult:
    """
    校验 Markdown 简历的格式硬规则。

    检查项（ERROR）：
    - 必须有 `#` 一级标题，且首个必须是 `# self-intro`
    - self-intro 必含 `name:`
    - 必含教育信息（`# 教育背景` 模块 或 self-intro 的 education 字段），且含毕业年份
    - 无空标题
    - `date:` 格式必须为 `YYYY.MM — YYYY.MM|至今`

    检查项（WARNING）：
    - `###`+ 深标题、空模块、self-intro 未知字段
    """
    errors: List[str] = []
    warnings: List[str] = []
    lines = text.splitlines()

    # ── 首模块必须是 self-intro ──
    h1_idx = [i for i, ln in enumerate(lines) if H1_RE.match(ln)]
    if not h1_idx:
        errors.append("没有任何 `# 一级标题`——至少要有 `# self-intro` 首模块")
        return ValidationResult(errors=errors, warnings=warnings)

    first = H1_RE.match(lines[h1_idx[0]]).group(1).strip().lower()
    if first not in SELF_INTRO_SLUGS:
        errors.append(f"第一个一级标题必须是 `# self-intro`（当前是「{lines[h1_idx[0]].strip()}」）")

    # ── 解析 self-intro 块（首个 # 到下一个 # 之间），收集 key: value ──
    intro_end = h1_idx[1] if len(h1_idx) > 1 else len(lines)
    intro_lines = lines[h1_idx[0] + 1:intro_end]
    intro_kv: dict = {}
    last_kv_key = None
    for ln in intro_lines:
        raw = ln.strip()
        if not raw:
            continue
        m = KV_RE.match(raw)
        if m:
            k, v = m.group(1).lower(), m.group(2).strip()
            intro_kv[k] = v
            last_kv_key = k
        elif re.match(r'^[A-Za-z一-龥][\w一-龥\-]*\s*:\s*$', raw):
            # 只有 key 没值的占位（如 links:）
            k = raw.split(":")[0].strip().lower()
            intro_kv.setdefault(k, "")
            last_kv_key = k
        elif raw.startswith("- ") and last_kv_key:
            # 缩进子项（links / education 等），追加到当前 KV 值
            sub = raw[2:].strip()
            intro_kv[last_kv_key] = f"{intro_kv[last_kv_key]}\n{sub}" if intro_kv[last_kv_key] else sub

    if not intro_kv.get("name"):
        errors.append("self-intro 缺必填字段 `name:`（简历必须有姓名）")

    unknown = sorted(set(intro_kv) - KNOWN_INTRO_KEYS)
    if unknown:
        warnings.append(f"self-intro 有未知字段 {unknown}（不影响，仅提示）")

    # ── 教育背景（兼容三种格式：独立模块 / self-intro education 字段 / 缩进子项）──
    has_edu_module = any(
        H1_RE.match(ln) and H1_RE.match(ln).group(1).strip().lower() in EDUCATION_SLUGS
        for ln in lines
    )
    edu_val = (intro_kv.get("education") or "").strip()
    if not has_edu_module and not edu_val:
        errors.append("缺少教育信息——请加 `# 教育背景` 模块或 self-intro 的 `education:` 字段")
    if has_edu_module:
        edu_idx = next(
            i for i, ln in enumerate(lines)
            if H1_RE.match(ln) and H1_RE.match(ln).group(1).strip().lower() in EDUCATION_SLUGS
        )
        edu_end = edu_idx + 1
        while edu_end < len(lines) and not H1_RE.match(lines[edu_end]):
            edu_end += 1
        edu_text = "\n".join(lines[edu_idx:edu_end])
        has_grad_year = bool(re.search(r"\d{4}届", edu_text)) or bool(
            re.search(r"date:.*\d{4}\.\d{2}\s*[-—–]\s*\d{4}\.\d{2}", edu_text)
        )
        if not has_grad_year:
            errors.append("教育背景缺少毕业年份——标注如 `2026届` 或 date 中写明毕业年月")

    # ── 标题层级 / 空标题 ──
    for i, ln in enumerate(lines):
        if H_DEEP_RE.match(ln):
            warnings.append(f"第 {i + 1} 行出现 `###`+ 深标题，本格式只支持 `#`/`##`：{ln.strip()}")
        m = H1_RE.match(ln) or H2_RE.match(ln)
        if m and not m.group(1).strip():
            errors.append(f"第 {i + 1} 行标题为空：{ln}")

    # ── 空模块（某 # 到下一个 # 之间无正文无子标题）──
    h_starts = [i for i, ln in enumerate(lines) if H1_RE.match(ln)]
    h_starts.append(len(lines))
    for a, b in zip(h_starts[:-1], h_starts[1:]):
        has_sub = any(H2_RE.match(lines[j]) for j in range(a + 1, b))
        has_body = any(lines[j].strip() and not H2_RE.match(lines[j]) for j in range(a + 1, b))
        title = H1_RE.match(lines[a]).group(1).strip()
        if not has_sub and not has_body and title.lower() not in SELF_INTRO_SLUGS:
            warnings.append(f"模块「{title}」是空模块（标题下没有任何内容）")

    # ── date 行格式 ──
    for i, ln in enumerate(lines):
        if ln.strip().startswith("date:"):
            if not DATE_RE.match(ln.strip()):
                errors.append(
                    f"第 {i + 1} 行 date 格式错误：{ln.strip()}。"
                    "正确格式：date: 2024.07 — 2025.03 或 date: 2024.07 — 至今"
                )

    return ValidationResult(errors=errors, warnings=warnings)


def validate_resume_html(text: str) -> ValidationResult:
    """
    校验装配后 HTML 产物的格式硬规则。

    检查项（ERROR）：
    - 无残留 `{{占位符}}`（组件模板未替换干净）
    - 含 Header / 姓名区（self-intro 应渲染成 Header）

    检查项（WARNING）：
    - 含章节标题、含 <style>（主题样式）
    """
    errors: List[str] = []
    warnings: List[str] = []

    leftover = PLACEHOLDER_RE.findall(text)
    if leftover:
        sample = ", ".join(sorted(set(leftover)))
        errors.append(
            f"产物里有 {len(leftover)} 处未填充占位符（{sample}）——"
            "把组件模板里的 {{...}} 全部换成真实内容"
        )

    if not re.search(r'class="name"|class="cn"|<header', text, re.I):
        errors.append('产物里没有 Header（姓名区 .name / .cn / <header>）——self-intro 应渲染成 Header')

    if not re.findall(r'class="sec-h(?:ead)?"', text):
        warnings.append('产物里没有任何章节标题（.sec-head / .sec-h）——至少要有一个 `# 模块`')

    if "<style" not in text.lower():
        warnings.append("产物里没有 <style>——主题样式缺失")

    return ValidationResult(errors=errors, warnings=warnings)
