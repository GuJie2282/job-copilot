"""
分段画像提取服务（profile_extractor）

把「一次 LLM 提取整份画像」重构为「按段提取」（对应 change add-streaming-pipeline
决策 5）：basic / education / work / project / skills 五段，每段独立 LLM 调用。

优势：
- 单段上下文聚焦、输出短，准确率高（治「项目名错位」等结构化提取错误）
- 单段小，不易超时；配合 stream 连接持续活跃
- 天然分段进度点（每段完成即推送，供流式管线）
- 单段失败只重试该段、最终降级为空值，不波及全局（容错）

提供两个入口：
- extract_profile_sectioned:       同步跑五段，返回完整嵌套画像 dict（供旧 parse-file/parse-text 复用）
- extract_profile_sectioned_stream: 生成器，逐段 yield (section, data)（供流式端点 parse-stream）

作者：求职 Copilot 项目
日期：2026-07-23
"""
import json
import re
import time
import logging
from typing import Dict, Any, Generator, Tuple

from src.graph.config import get_llm
from src.graph.prompts import get_section_extraction_prompt
from src.services.llm_retry import is_retryable

logger = logging.getLogger(__name__)

# 五段的提取顺序（前端进度展示与画像逐段成型按此顺序）
SECTION_ORDER = ["basic", "education", "work", "project", "skills"]

# 各段失败时的默认空值（保证合并时结构完整，单段失败不波及全局）
_SECTION_DEFAULT: Dict[str, Any] = {
    "basic": {"name": None, "phone": None, "email": None, "location": None, "self_summary": None},
    "education": [],
    "work": [],
    "project": [],
    "skills": {"technical_skills": [], "soft_skills": [], "languages": [], "achievements": []},
}

# 各段的中文进度文案（SSE stage 事件用）
SECTION_LABEL: Dict[str, str] = {
    "basic": "提取基本信息…",
    "education": "提取教育背景…",
    "work": "提取工作经历…",
    "project": "提取项目经验…",
    "skills": "提取技能与荣誉…",
}


def _extract_json_loose(text: str) -> Any:
    """
    从 LLM 输出中提取 JSON：先抠 ```json``` 代码块，再 json.loads，失败用 json_repair 容错。
    """
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    raw = m.group(1) if m else text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
            return repair_json(raw, return_objects=True)
        except Exception:
            return None


def _extract_one_section(
    resume_text: str,
    section: str,
    llm,
    max_retries: int = 1,
) -> Tuple[Dict[str, Any], bool]:
    """
    提取单段：stream 调用（连接持续活跃）→ 完整 JSON → 该段 dict。

    Args:
        resume_text: 简历全文
        section: 段名
        llm: 已配置好档位/温度/超时的 LLM 实例
        max_retries: 单段失败重试次数（收敛，默认 1；超时类重试意义有限）
    Returns:
        (data, ok): data 是该段 dict；ok=True 成功，False 失败（data 为默认空值）
    """
    prompt = get_section_extraction_prompt(resume_text, section)
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # stream 模式：token 持续流，连接活跃，避免单次总时长超时被 SDK 切断
            chunks = []
            for chunk in llm.stream(prompt):
                delta = chunk.content or ""
                if delta:
                    chunks.append(delta)
            data = _extract_json_loose("".join(chunks))
            if data is None:
                raise ValueError(f"段 {section} JSON 解析失败")
            # basic 段补全默认键，避免缺字段导致下游 UserProfile 校验问题
            if section == "basic" and isinstance(data, dict):
                for k in _SECTION_DEFAULT["basic"]:
                    data.setdefault(k, None)
            return data, True
        except Exception as e:
            last_error = e
            if not is_retryable(e):
                break
            if attempt < max_retries:
                time.sleep(1.0 * (2 ** attempt))

    logger.warning(f"段 {section} 提取失败，降级为默认空值：{type(last_error).__name__}: {last_error}")
    default = _SECTION_DEFAULT[section]
    return (json.loads(json.dumps(default)), False)  # 深拷贝默认值，避免共享引用


def _merge_sections(parts: Dict[str, Any]) -> Dict[str, Any]:
    """把五段结果合并为完整嵌套 UserProfile dict。"""
    basic = parts.get("basic") or {}
    skills = parts.get("skills") or {}
    return {
        "name": basic.get("name"),
        "phone": basic.get("phone"),
        "email": basic.get("email"),
        "location": basic.get("location"),
        "self_summary": basic.get("self_summary"),
        "education": parts.get("education") or [],
        "work_experience": parts.get("work") or [],
        "projects": parts.get("project") or [],
        "technical_skills": skills.get("technical_skills") or [],
        "soft_skills": skills.get("soft_skills") or [],
        "languages": skills.get("languages") or [],
        "achievements": skills.get("achievements") or [],
    }


def extract_profile_sectioned(
    resume_text: str,
    quality_score: float = 1.0,
) -> Dict[str, Any]:
    """
    同步分段提取：顺序跑五段，返回完整嵌套画像 dict。

    供旧 parse-file/parse-text 端点复用（同步）；流式端点用 extract_profile_sectioned_stream。
    """
    llm = get_llm(temperature=0.0, tier="fast", timeout=60.0)  # 分段提取用 fast 档：分段已聚焦（治错位），fast 快、5 段累计可控；strong 实测 5 段串行过慢  # 分段提取：主力档 + 长超时
    parts: Dict[str, Any] = {}
    for section in SECTION_ORDER:
        data, _ok = _extract_one_section(resume_text, section, llm)
        parts[section] = data
    return _merge_sections(parts)


def extract_profile_sectioned_stream(
    resume_text: str,
    quality_score: float = 1.0,
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """
    流式分段提取：逐段 yield (section, data)。

    供流式端点 parse-stream：每段完成后 yield 该段结果，调用方下发 segment 事件。
    单段失败 yield 该段默认空值（不中断流，已成功段仍可见）。
    """
    llm = get_llm(temperature=0.0, tier="fast", timeout=60.0)  # 分段提取用 fast 档：分段已聚焦（治错位），fast 快、5 段累计可控；strong 实测 5 段串行过慢
    for section in SECTION_ORDER:
        data, _ok = _extract_one_section(resume_text, section, llm)
        yield section, data
