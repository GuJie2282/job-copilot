"""
Prompt 模板管理

功能：
1. 集中管理所有 Prompt 模板
2. 支持简历解析 Prompt
3. 支持后续功能（JD 匹配、简历优化、模拟面试）

作者：求职 Copilot 项目
日期：2026-07-03
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any, Optional, List


# ============================================================================
# 简历解析 Prompt
# ============================================================================

# 标准提取 Prompt（高质量文本）
STANDARD_EXTRACTION_PROMPT = """
你是一位专业的简历信息提取专家。你的任务是从用户的简历文本中提取结构化的个人画像。

## 输入格式
你将收到一段简历文本。

## 输出格式
请严格按照以下 JSON Schema 输出，不要添加任何额外内容：

```json
{
  "basic_info": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "location": "string"
  },
  "education": [
    {
      "school": "string",
      "degree": "string",
      "major": "string",
      "graduation_year": "string",
      "gpa": "string (optional)"
    }
  ],
  "work_experience": [
    {
      "company": "string",
      "position": "string",
      "duration": "string",
      "description": "string",
      "achievements": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft_skills": ["string"],
    "languages": ["string"]
  },
  "projects": [
    {
      "name": "string",
      "role": "string",
      "description": "string",
      "outcome": "string"
    }
  ],
  "job_target": {
    "target_positions": ["string"],
    "target_companies": ["string"],
    "location_preference": "string",
    "salary_range": "string",
    "industry": "string"
  }
}
```

## 提取规则
1. **准确性优先**：只提取明确提到的信息，不要编造
2. **保留原文**：尽量使用原文的表述，不要改写
3. **字段缺失**：如果某个字段找不到，填 null（不是 "null" 字符串）
4. **时间格式**：时间保持原文格式（如 "2020-2022" 或 "2020年9月"）
5. **技能分类**：
   - technical: 编程语言、框架、工具
   - soft_skills: 沟通、领导力、团队协作
   - languages: 英语、日语等语言能力
6. **多条记录**：教育、工作、项目可能有多个，用数组表示

## 简历文本
{resume_text}

请开始提取：
"""

# 容错提取 Prompt（低质量文本）
FAULT_TOLERANT_EXTRACTION_PROMPT = """
你是一位专业的简历信息提取专家。你的任务从用户的简历文本中提取结构化的个人画像。

## 当前状态
收到的简历文本质量较差（可能是：
- 文本过少
- 结构不清晰
- 格式混乱
- 缺少常见关键词

## 输入格式
你将收到一段简历文本。

## 输出格式
请严格按照以下 JSON Schema 输出，不要添加任何额外内容：

```json
{
  "basic_info": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "location": "string"
  },
  "education": [
    {
      "school": "string",
      "degree": "string",
      "major": "string",
      "graduation_year": "string",
      "gpa": "string (optional)"
    }
  ],
  "work_experience": [
    {
      "company": "string",
      "position": "string",
      "duration": "string",
      "description": "string",
      "achievements": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft_skills": ["string"],
    "languages": ["string"]
  },
  "projects": [
    {
      "name": "string",
      "role": "string",
      "description": "string",
      "outcome": "string"
    }
  ],
  "job_target": {
    "target_positions": ["string"],
    "target_companies": ["string"],
    "location_preference": "string",
    "salary_range": "string",
    "industry": "string"
  }
}
```

## 提取规则（容错模式）
1. **宁可留空，不要编造**：找不到的信息填 null，不要猜测
2. **时间不明确 → 填"未知"**：如果时间信息模糊，填 "未知"
3. **优先提取核心信息**：姓名、教育、工作经历最重要
4. **容忍格式混乱**：即使格式不标准，也要尝试提取
5. **分词提取**：如果缺少结构化信息，尝试从文本中提取关键词
6. **保守估计**：如果不确定，宁可不填也不要填错

## 核心字段优先级
1. **必需**：姓名、至少一个教育经历、至少一个工作经历（如果有）
2. **重要**：联系方式、技能
3. **可选**：项目、求职目标

## 简历文本
{resume_text}

请开始提取（容错模式）：
"""

# 重试 Prompt（置信度 < 60% 时使用）
RETRY_EXTRACTION_PROMPT = """
你是一位专业的简历信息提取专家。你的任务是从用户的简历文本中重新提取结构化的个人画像。

## 当前状态
之前的提取结果置信度较低（<60%），某些字段可能提取不准确。

## 输入格式
你将收到一段简历文本。

## 输出格式
请严格按照以下 JSON Schema 输出，不要添加任何额外内容：

```json
{
  "basic_info": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "location": "string"
  },
  "education": [
    {
      "school": "string",
      "degree": "string",
      "major": "string",
      "graduation_year": "string",
      "gpa": "string (optional)"
    }
  ],
  "work_experience": [
    {
      "company": "string",
      "position": "string",
      "duration": "string",
      "description": "string",
      "achievements": ["string"]
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft_skills": ["string"],
    "languages": ["string"]
  },
  "projects": [
    {
      "name": "string",
      "role": "string",
      "description": "string",
      "outcome": "string"
    }
  ],
  "job_target": {
    "target_positions": ["string"],
    "target_companies": ["string"],
    "location_preference": "string",
    "salary_range": "string",
    "industry": "string"
  }
}
```

## 重试规则（提高准确率）
1. **仔细核对**：确保每个字段都在原文中能找到依据
2. **保留原文**：尽量使用原文的表述，不要改写或概括
3. **保守提取**：如果信息模糊，宁可不填也不要填错
4. **检查关键词**：重点关注"姓名"、"学校"、"公司"、"职位"等关键词
5. **时间格式**：时间保持原文格式，不要转换
6. **完整性检查**：提取完成后，检查每个字段是否合理

## 简历文本
{resume_text}

请开始重新提取（重试模式）：
"""


# ============================================================================
# Prompt 模板函数
# ============================================================================

def get_extraction_prompt(
    resume_text: str,
    quality_score: float = 1.0,
    is_retry: bool = False
) -> str:
    """
    获取合适的提取 Prompt

    Args:
        resume_text: 简历文本
        quality_score: 文本质量分数（0.0-1.0）
        is_retry: 是否是重试

    Returns:
        prompt: 完整的 Prompt 字符串

    注意：统一委托给 get_json_extraction_prompt（f-string 安全，避免简历含
          { } 字符时 .format() 崩溃；同时 schema 与 UserProfile 字段对齐）。
          重试模式追加额外提示，引导 LLM 更仔细地核对。
    """
    prompt = get_json_extraction_prompt(resume_text, quality_score)
    if is_retry:
        prompt = "上次提取失败，请更仔细地逐字段核对原文，严格按 JSON 格式输出。\n\n" + prompt
    return prompt


def create_chat_prompt_template() -> ChatPromptTemplate:
    """
    创建聊天 Prompt 模板（用于对话节点）

    Returns:
        prompt_template: ChatPromptTemplate 对象
    """
    template = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的求职教练，名字叫"求职 Copilot"。

你的任务是帮助用户：
1. 建立个人画像（解析简历）
2. 匹配职位需求（JD 匹配）
3. 优化简历（简历优化）
4. 模拟面试（面试练习）

## 说话风格
- 友好、专业、鼓励性
- 避免使用过于技术性的术语
- 适当使用 emoji 让对话更生动
- 简洁明了，不要长篇大论

## 回答原则
- 准确、有帮助、不编造
- 如果不确定，坦诚告知
- 尊重用户的隐私和选择
- 提供具体的建议，而不是泛泛而谈

请开始对话！"""),
        MessagesPlaceholder(variable_name="messages"),
    ])

    return template


def get_json_extraction_prompt(resume_text: str, quality_score: float = 1.0) -> str:
    """
    获取 JSON 格式提取 Prompt（用于非结构化输出的 LLM）

    Args:
        resume_text: 简历文本
        quality_score: 文本质量分数

    Returns:
        prompt: 完整的 Prompt 字符串
    """
    # 根据质量分数选择提示
    quality_hint = ""
    if quality_score < 0.8:
        quality_hint = """
## 注意事项
- 文本质量较低，可能存在格式问题或乱码
- 请尽量提取可识别的信息
- 如果字段无法识别，使用 null 而不要编造
"""

    prompt = f"""你是一位专业的简历信息提取专家。你的任务是从用户的简历文本中提取结构化的个人画像。

## 输入格式
你将收到一段简历文本。

## 输出格式
请严格按照以下 JSON 格式输出，**必须包裹在 markdown 代码块中**：

```json
{{
  "name": "string",
  "phone": "string 或 null",
  "email": "string 或 null",
  "location": "string 或 null",
  "self_summary": "个人总结/自我评价原文（string 或 null）",
  "schools": ["string"],
  "degrees": ["string"],
  "majors": ["string"],
  "graduation_years": ["string"],
  "companies": ["string"],
  "positions": ["string"],
  "durations": ["string"],
  "work_descriptions": ["每段工作/实习经历的职责与成果详情，保留原文细节；与 companies 一一对应同序，找不到填 null"],
  "technical_skills": ["Python", "需求分析", "Axure"],
  "soft_skills": ["沟通能力", "团队协作"],
  "languages": ["英语（CET-6）"],
  "project_names": ["string"],
  "project_roles": ["string"],
  "project_descriptions": ["每个项目的内容、职责与成果详情，保留原文细节；与 project_names 一一对应同序，找不到填 null"],
  "achievements": ["荣誉、奖项、证书，如：奖学金、竞赛获奖"],
  "target_positions": ["string"],
  "target_companies": ["string"],
  "location_preference": "string 或 null",
  "salary_range": "string 或 null",
  "industry": "string 或 null"
}}
```

## 提取规则
1. **仔细核对**：确保每个字段都在原文中能找到依据
2. **保留原文**：尽量使用原文的表述，不要改写或概括
3. **保守提取**：如果信息模糊，使用 null 而不要编造
4. **数组格式 + 技能拆分**：schools、companies 等字段必须是数组，即使只有一个元素。技能数组（technical_skills/soft_skills/languages）每项必须独立：严禁把多个技能用顿号/逗号塞进同一个字符串（错误 ["需求分析、原型设计、Python"]；正确 ["需求分析","原型设计","Python"]），即使简历原文把技能写成一行顿号连写，也要逐项拆开
5. **null 值**：对于找不到的字段，使用 null 而不是空字符串或省略
6. **详情字段（最重要）**：work_descriptions / project_descriptions 必须保留经历与项目的**原始细节**
   （如「需求分析：…」「产品设计：…」「成果数据：…」「核心成果：…」），**不要概括成一句话**；
   按数组顺序与 companies / project_names 一一对应，某段没有详情就填 null。
   这是画像最有价值的部分，务必完整提取。
7. **荣誉**：achievements 提取奖学金、竞赛获奖、专业证书等
8. **个人总结**：self_summary 提取简历里的个人总结 / 自我评价原文
{quality_hint}

## 简历文本
{resume_text}

请开始提取（**必须输出完整的 JSON**）：
"""

    return prompt


# ============================================================================
# 分段提取 Prompt（简历解析流式 + 提质量，对应 change add-streaming-pipeline 决策 5）
# 把「一次提整份画像」拆成 basic/education/work/project/skills 五段，每段独立提取：
# 上下文聚焦、输出短、准确率高；字段绑死在嵌套对象内，杜绝扁平平行数组错位。
# ============================================================================

# 各段的目标 schema 与提取焦点（每段输出对应 JSON 片段）
_SECTION_SCHEMAS = {
    "basic": {
        "schema": {
            "name": "string 或 null",
            "phone": "string 或 null",
            "email": "string 或 null",
            "location": "string 或 null",
            "self_summary": "个人总结/自我评价原文（string 或 null）",
        },
        "focus": "基本信息与个人总结：姓名、电话、邮箱、所在地、自我评价",
    },
    "education": {
        "schema": [
            {"school": "string", "degree": "string", "major": "string", "graduation_year": "string"}
        ],
        "focus": "教育背景:每段教育的学校、学历、专业、毕业年份（多条用数组）",
    },
    "work": {
        "schema": [
            {
                "company": "string",
                "position": "string",
                "duration": "string",
                "description": "职责与成果详情，保留原文细节",
            }
        ],
        "focus": "工作/实习经历:在【企业/公司】做的经历（含实习、正式工作，以及在企业内做的项目），每段的公司、职位、时间、职责与成果详情（保留原文细节）",
    },
    "project": {
        "schema": [
            {"name": "string", "role": "string", "description": "项目内容、职责与成果，保留原文细节"}
        ],
        "focus": "项目经验:仅提取【个人项目】（无企业/公司归属的独立项目，如校园项目、个人 side project）;实习/工作经历中（在企业内做的）项目属于工作段，不要放进项目段。每个项目的名称、担任角色、详情（保留原文细节）",
    },
    "skills": {
        "schema": {
            # ⚠️ 每个技能必须是数组里的「独立一项」（如 "Python"），严禁合并成一个顿号/逗号字符串
            "technical_skills": ["Python", "FastAPI", "需求分析", "原型设计", "Axure"],
            "soft_skills": ["沟通能力", "团队协作"],
            "languages": ["英语（CET-6）"],
            "achievements": ["仅荣誉、奖项、证书（奖学金/竞赛获奖/CET 等）；严禁把项目成果或工作职责当荣誉"],
        },
        "focus": (
            "技能与荣誉:技术技能、软技能、语言能力、仅荣誉奖项证书（项目成果属于 project 段，不要放进 achievements）。"
            "⚠️技能拆分（重要）：每个技能必须是数组里的【独立一项】，逐个拆开；严禁用顿号/逗号/空格把多个技能塞进同一个字符串。"
            "错误：[\"需求分析、原型设计、Python\"]；正确：[\"需求分析\",\"原型设计\",\"Python\"]。"
            "即使简历原文把技能写成一行顿号连写，也要拆成数组多项。"
        ),
    },
}


def get_section_extraction_prompt(resume_text: str, section: str) -> str:
    """
    分段提取 Prompt：只提取指定段，输出该段嵌套 JSON 片段。

    Args:
        resume_text: 简历全文（每段都传全文，让 LLM 聚焦提取某一类）
        section: 段名 basic / education / work / project / skills
    Returns:
        prompt 字符串
    """
    import json

    spec = _SECTION_SCHEMAS[section]
    schema_json = json.dumps(spec["schema"], ensure_ascii=False, indent=2)
    return (
        f"你是简历信息提取专家。本次**只提取「{spec['focus']}」**这一类信息，忽略其他内容。\n\n"
        "## 输出格式\n"
        "严格按以下 JSON 输出，**必须包裹在 ```json 代码块中**，不要任何解释：\n\n"
        f"```json\n{schema_json}\n```\n\n"
        "## 规则\n"
        "1. **段归属（按企业分界）**：工作段 = 在企业/公司做的经历（含实习、正式工作，以及企业内做的项目）；项目段 = 个人项目（无企业归属，如校园项目、个人项目）。按此分界果断归类：有企业/公司的归工作段，无企业的归项目段，不要纠结。\n"
        "2. **保留原文**：用原文表述，不要改写或概括；详情字段（description）保留原始细节，不要压成一句话。\n"
        "3. **保守提取**：找不到的字段填 null；本段数组字段若无内容填 []。\n"
        "4. **多条用对象数组**：教育/工作/项目通常多条，每条是一个对象，各字段绑死在同一对象内（严禁用平行数组）。\n"
        "5. **果断简洁（重要）**：对边界情况果断判断（如某项目写在实习段下，仍归项目段；实习经历归工作段），**不要反复权衡同一问题**；思考过程简洁、一次定论，不重复循环。\n\n"
        "## 简历文本\n"
        f"{resume_text}\n\n"
        "请开始提取（只输出本段 JSON）："
    )


# ============================================================================
# JD 结构化解析 Prompt
# ============================================================================

def get_jd_parsing_prompt(jd_text: str) -> str:
    """
    获取 JD 结构化解析 Prompt（四分类：硬技能/软技能/隐性偏好/红线项）

    与简历解析一样采用 JSON Prompt，让 LLM 把 JD 拆成结构化「要求画像」，
    每条要求保留原文依据（evidence），并区分必须项/加分项（must_have）。
    """
    prompt = f"""你是一位资深招聘专家。你的任务是把职位描述（JD）解析为结构化的「要求画像」。

## 输出格式
请严格按以下 JSON 格式输出，**必须包裹在 ```json 代码块中**：

```json
{{
  "position_title": "岗位名称（string 或 null）",
  "summary": "JD 一句话概要（string 或 null）",
  "hard_skills": [
    {{"requirement": "具体要求", "must_have": true, "evidence": "JD 原文片段"}}
  ],
  "soft_skills": [
    {{"requirement": "具体要求", "must_have": false, "evidence": "JD 原文片段"}}
  ],
  "implicit_preferences": [
    {{"requirement": "JD 暗示但未明说的偏好", "must_have": false, "evidence": "JD 原文片段"}}
  ],
  "red_lines": [
    {{"requirement": "硬性门槛", "must_have": true, "evidence": "JD 原文片段"}}
  ]
}}
```

## 四分类规则
1. **hard_skills（硬技能）**：明确要求的技能、工具、年限、资质（如"熟练 Python""3 年以上经验""本科及以上"）
2. **soft_skills（软技能）**：沟通、领导力、抗压、学习能力等能力要求
3. **implicit_preferences（隐性偏好）**：JD 未明说但有暗示的倾向（如"大厂背景优先""创业经历加分""有 toB 经验优先"）
4. **red_lines（红线项）**：硬性门槛，不满足基本不予考虑（如"必须 985/211""接受频繁出差""持 PMP 证书"）

## 字段规则
- **must_have**：带"必须/要求/任职资格/需要"等强约束措辞 → true；带"优先/加分/nice to have/了解即可"→ false
- **evidence**：尽量给出该要求在 JD 原文中的出处片段（便于追溯）
- **不编造**：只提取 JD 中实际出现或明确暗示的要求

## JD 文本
{jd_text}

请开始解析（必须输出完整的 JSON）：
"""
    return prompt


# ============================================================================
# 隐性偏好 LLM 判断 Prompt
# ============================================================================

def get_implicit_judgment_prompt(implicit_prefs: list, user_profile_text: str) -> str:
    """
    获取隐性偏好 LLM 判断 Prompt。

    隐性偏好（如"大厂背景优先""创业经历加分"）无法用规则判定，交由 LLM 结合画像综合判断。
    """
    prefs_text = "\n".join(f"- {p.get('requirement', '')}" for p in implicit_prefs)
    prompt = f"""你是资深招聘专家。请判断候选人画像在多大程度上满足以下 JD「隐性偏好」（非硬性要求，但有暗示的倾向）。

## JD 隐性偏好
{prefs_text}

## 候选人画像摘要
{user_profile_text}

## 输出格式
请严格按以下 JSON 输出，**必须包裹在 ```json 代码块中**，顺序与上面的偏好一一对应：

```json
[
  {{"requirement": "偏好内容", "status": "satisfied|partial|missing", "reason": "判断理由（结合画像）"}}
]
```

## 规则
- status：satisfied=画像明显体现该偏好；partial=部分体现；missing=未体现
- reason：简要说明判断依据，引用画像中的具体信息
- 客观判断，不编造画像中没有的信息

请输出 JSON：
"""
    return prompt


# ============================================================================
# Gap 应对建议生成 Prompt
# ============================================================================

def get_gap_suggestion_prompt(gaps: list, user_profile_text: str) -> str:
    """
    获取 Gap 应对建议生成 Prompt。

    给定差距清单与候选人画像，由 LLM 生成具体可执行的简历应对建议。
    """
    import json
    gaps_text = json.dumps(
        [{"type": g.get("type"), "requirement": g.get("requirement")} for g in gaps],
        ensure_ascii=False,
    )
    prompt = f"""你是资深求职教练。请针对以下「差距项（Gap）」，结合候选人画像，给出具体可执行的简历应对建议。

## 差距项
{gaps_text}

## 候选人画像摘要
{user_profile_text}

## 输出格式
请严格按以下 JSON 输出，**必须包裹在 ```json 代码块中**，为每个差距给一条建议：

```json
[
  {{"requirement": "差距对应的 JD 要求", "suggestion": "具体可执行的应对建议"}}
]
```

## 规则
- 建议要具体、可执行（如「用 STAR 法则补充 XX 项目」「挖掘 XX 经历对冲」），不要泛泛而谈
- 结合候选人画像的真实经历给建议，不编造
- 硬技能差距 → 放大相关项/转移焦点；软技能 → 用数据化事例佐证；隐性偏好 → 用类比经历对冲；红线 → 策略性呈现

请输出 JSON：
"""
    return prompt


# ============================================================================
# 简历生成 Prompt（画像 + 差距驱动，从零生成定制简历）
# ============================================================================

def get_resume_generation_prompt(
    profile_text: str,
    gaps_text: str,
    target_position: str,
    has_gaps: bool,
    jd_text: Optional[str] = None,
) -> str:
    """
    获取简历生成 Prompt（画像 + 差距驱动，从零生成定制简历 Markdown）。

    与 JD 解析 / 隐性判断不同：这里输出是**纯 Markdown 简历**（非 JSON），
    所以不要求 ```json``` 包裹，而是要求直接输出 Markdown 全文。

    Args:
        profile_text:    画像 JSON 文本（LLM 从中提取信息组织简历）
        gaps_text:       已拼接的「差距 + 改写策略」文本（has_gaps=False 时为空串）
        target_position: 目标岗位
        has_gaps:        是否有 Gap（False → 通用生成模式，不针对特定 Gap 定向强化）
    Returns:
        prompt 字符串
    """
    gap_section = (
        f"## 岗位差距与改写策略（针对这些差距定向强化）\n{gaps_text}\n"
        if has_gaps
        else "## 模式\n本次为通用生成（未提供岗位差距）。请基于画像生成一份专业、通用的简历，不针对特定 Gap 定向强化。\n"
    )
    # 方式 A：用户直接粘贴 JD 原文（未走 JD 匹配），作生成上下文让 LLM 针对性生成
    jd_section = (
        f"## 目标岗位 JD（参考原文，针对它定制生成）\n{jd_text}\n"
        if jd_text
        else ""
    )

    prompt = f"""你是资深简历顾问。基于候选人画像，针对目标岗位，从零生成一份定制简历（Markdown 格式）。

## 目标岗位
{target_position}

## 候选人画像
{profile_text}

{gap_section}{jd_section}## 简历格式规范（必须严格遵守，格式校验器会查这些硬规则）
- 首个一级标题必须是 `# self-intro`，下用 `key: value` 放 name / role / phone / email / location 等
- **字段行（`key: value`，如 name / role / education / phone）只允许出现在 `# self-intro` 模块内**；其他模块正文严禁写字段行，否则字段名会作为字面文字渲染进简历（如「教育背景」模块下写 `education:` 会多出一个「education:」）。
- 教育背景用独立模块 `# 教育背景`，下用 `## 学校 | 专业 · 学历` + `date: 入学 — 毕业`（**必须含毕业届或毕业年份**，date 用 YYYY.MM 格式）；**不要**用 `education:` 字段行
- 每个模块用 `# 模块名`（如 `# 教育背景` / `# 工作经历` / `项目经历` / `技能`）
- 经历用 `## 机构 | 角色`，下一行 `date:` **必须用 YYYY.MM 格式**（如 `date: 2025.06 — 至今` 或 `date: 2023.05 — 2025.06`），**严禁用「2025年06月」中文格式**
- 经历要点用**扁平**的 `- 要点`（每条独立一行，STAR + 量化，1-2 行），**不要嵌套子 bullet**（不要「- 主项」下再缩进「- 子项」；多条要点都平级用 `- `）
- 技能用 `- 类别: 值`（按领域分类，如 `- 编程语言: Python · Java`）
- 标题层级**只用** `#` 和 `##`，不要用 `###` 及更深

## 表述规则（务必遵守）
1. **只用画像里的信息**，绝不编造候选人没有的经历、项目或量化数字。
2. **缺素材的模块**：在该处写「（待补充：具体缺什么）」占位，**不要虚构**，宁缺毋滥。
3. 每条经历遵循 **STAR**（情境/任务/行动/结果）+ **强动词开头**（主导/设计/优化/推动/落地…）。
4. 涉及公司内部项目名一律**脱敏**：用业务功能或规模描述替代（如"核心交易链路""支撑日均百万订单的系统"），不用"某"式占位。
5. 表述**平实具体**：不解释领域常识，不用"吃苦耐劳""团队精神"式空话，每条 bullet 1-2 行。
6. **经历要点必须扁平（重点）**：每条 `- 要点` 独立一行、平级，**严禁嵌套**。正确写法：
   `- 主导 XX 系统 redesign，日活提升 30%`（一条一行，把细节揉进这一条）。
   **错误（禁止）**：`- 主项` 下再缩进 `- 子项`。需要展开细节时，合并进同一条 bullet（如「主导 XX，含需求分析、设计与推进，日活提升 30%」）。

## 思考约束
- 思考过程用中文（除字段名 / 工具名等必要英文外）。
- 不要无意义重复：不复述画像 / 差距 / 规范原文，不把同一简历内容反复起草多遍后只取一版。
- 其余推理充分自由发挥，以保证简历质量为先（思考可以详细，但不要原地打转重复）。

## 输出
**直接输出 Markdown 简历全文**，不要用代码块包裹，不要任何解释或前后缀文字。
"""
    return prompt


# ============================================================================
# 简历精修 Prompt（路径 B：按用户反馈改写草稿）
# ============================================================================

def get_resume_refine_prompt(
    current_md: str,
    feedback: str,
    profile_text: str,
    gaps_text: str,
    target_position: str,
    has_gaps: bool,
) -> str:
    """
    获取简历精修 Prompt（路径 B：基于现有草稿 + 用户反馈做针对性改写）。

    与生成的区别：已有草稿作底，只改反馈涉及的部分（+连带必要调整），不重写整篇。

    Args:
        current_md:      当前简历草稿（Markdown）
        feedback:        用户反馈（要改什么）
        profile_text:    画像 JSON 文本
        gaps_text:       Gap 清单文本（参考）
        target_position: 目标岗位
        has_gaps:        是否有 Gap
    Returns:
        prompt 字符串
    """
    gap_section = (f"## 岗位差距（参考）\n{gaps_text}\n" if has_gaps else "")
    prompt = f"""你是资深简历顾问。基于现有简历草稿，按用户反馈做针对性精修。

## 目标岗位
{target_position}

## 用户反馈（要改什么）
{feedback}

## 候选人画像
{profile_text}
{gap_section}
## 当前简历草稿
{current_md}

## 精修规则
1. **按反馈针对性修改**：「展开某段」→ 补 STAR 细节与量化；「换强调」→ 调整经历顺序或表述重心；「补素材」→ 融入用户在反馈里给出的具体细节。
2. **保留整体结构**：只改反馈涉及的部分（+连带必要的调整），不要重写整篇。
3. **格式规范不变**：`# self-intro` 首模块、`## 机构 | 角色`、`date:`、标题只用 `#`/`##`。
4. **表述规则不变**：STAR + 强动词、脱敏、不编造（画像里没有的不要写，缺素材标「待补充」）。

## 思考要求（重要——思考过程用户可见，务必精简）
思考控制在 **5 句以内**，只讲四件事，点到为止：
1. **定位**：用户要改哪一处（1 句，指到具体行/句）
2. **取材**：从画像取哪个具体素材来改（1 句，引用关键词即可，**不要复述整段画像**）
3. **改法**：打算怎么改写（1-2 句）
4. **核查**：有没有编造、格式是否合规（1 句）

**禁止**（这些会让思考又长又没用）：
- 复述精修规则 / 输出格式（你已知，不用再讲给自己听）
- 把候选人画像整段罗列或转述
- **把简历草稿（current_md）完整复述一遍**——简历用户在左侧已能看到，思考里只需引用「要改的那一句/那一段」，不要重抄整份简历
- 反复自我修正、推翻重来（想清楚再写，不要把犹豫过程倒出来）
- 把同一句话拆解后用多种组合重复表达

思考是给用户看「你怎么想的」，不是你的草稿纸。

## 输出格式（严格遵守）
分两段输出，用分隔符隔开，使前端能把「自然语言说明」与「改写后简历」分开呈现：
1. `<<<REPLY>>>` 后是一段自然语言说明（1-3 句）：告诉用户你这次做了哪些修改、为什么。
2. `<<<RESUME>>>` 后是修改后的完整 Markdown 简历。

示例：
<<<REPLY>>>我把第二段经历的量化数据补上了（DAU 提升 30%），并把 AI 项目前置以突出落地能力。<<<RESUME>>>
# self-intro
name: 张三
...（完整 Markdown 简历，不要代码块包裹）

自然语言说明要简短具体；简历段必须完整、格式规范（`# self-intro` 首模块、`## 机构 | 角色`、`date:`、标题只用 `#`/`##`）。
"""
    return prompt


# ============================================================================
# 简历 6 维评估 Prompt（LLM 内容评估——对应 design 决策 3）
# ============================================================================

def get_resume_evaluation_prompt(
    resume_md: str,
    target_position: str,
    gaps_text: str,
    profile_text: str,
) -> str:
    """
    获取简历 6 维评估 Prompt。

    输出结构化 JSON 评估报告（维度得分/总分/通过判定/改进优先级）。
    **只评估、给建议，不直接改写简历**（改写由生成节点根据反馈做）。

    Args:
        resume_md:       简历 Markdown 全文
        target_position: 目标岗位
        gaps_text:       差距清单 JSON 文本（评估 JD 匹配维度时参考）
        profile_text:    画像 JSON 文本（核对量化数字是否可追溯）
    Returns:
        prompt 字符串
    """
    prompt = f"""你是严谨的简历质量评估者。对一份生成的简历，从 6 个维度逐项检查，输出结构化评估报告。
**只评估、给建议，不直接改写简历。**

## 目标岗位
{target_position}

## 候选人画像（用于核对量化数字是否可追溯至画像）
{profile_text}

## 岗位差距（评估"JD 匹配"维度时参考，看简历是否针对这些差距做了改写）
{gaps_text}

## 简历全文
{resume_md}

## 六个评估维度（加权算 overall_score 0-100）
1. **basic_norm 基础规范**（weight 0.15）：联系方式齐全 / name 必填 / self-intro 完整 / 时间线无断层 / 排版 / 脱敏合规（无公司内部项目原名，无"某"式占位）
2. **jd_match JD 匹配**（weight 0.25）：关键词命中 / 能力对齐(技能重叠≥60%) / 相关经历前置 / 隐性需求体现
3. **quantification 成果量化**（weight 0.25）：STAR 完整 / 至少 1 个可验证数字 / 强动词开头 / 无职责罗列；**量化数字须可追溯至画像，无法追溯或明显编造 → 该维度 fail**
4. **structure 结构清晰**（weight 0.10）：模块顺序合理 / 层级(# ##)正确 / 无冗余重复 / 每段 3-5 条 bullet
5. **differentiation 差异化**（weight 0.15）：独特亮点 / 加分项(作品/开源/专利) / 层级适配(初级重执行·高级重决策)
6. **language 语言表达**（weight 0.10）：简洁无套话 / 客观基于事实 / 具体不抽象 / 主语明确(我非我们)

## 输出格式（**必须包裹在 ```json 代码块中**）
```json
{{
  "overall_score": 82,
  "passed": false,
  "dimensions": {{
    "basic_norm": {{"score": 90, "weight": 0.15, "passed": true, "items": [{{"check": "联系方式齐全", "result": "pass", "note": null}}]}},
    "jd_match": {{"score": 75, "weight": 0.25, "passed": false, "items": [{{"check": "关键词命中", "result": "partial", "note": "缺 Kafka，建议补充相关项目"}}]}},
    "quantification": {{"score": 70, "weight": 0.25, "passed": false, "items": [{{"check": "量化指标", "result": "partial", "note": "部分 bullet 缺数字"}}]}},
    "structure": {{"score": 85, "weight": 0.10, "passed": true, "items": [{{"check": "模块顺序", "result": "pass", "note": null}}]}},
    "differentiation": {{"score": 80, "weight": 0.15, "passed": true, "items": [{{"check": "独特亮点", "result": "pass", "note": null}}]}},
    "language": {{"score": 88, "weight": 0.10, "passed": true, "items": [{{"check": "简洁无套话", "result": "pass", "note": null}}]}}
  }},
  "feedback_priorities": [
    {{"priority": "high", "suggestion": "为第二段经历补充可验证的量化指标"}},
    {{"priority": "medium", "suggestion": "将 XX 项目前置以突出岗位相关"}}
  ]
}}
```

## 规则
1. **result**：每项 pass / fail / partial；note 仅在不通过时给具体建议，通过则 null。
2. **维度 passed**：该维度所有检查项无 fail 才 true。
3. **整体 passed**：六个维度都 passed 才 true。
4. **overall_score 必须等于 Σ(维度 score × weight)**：先逐维度真实打分，再加权求和。**严禁把维度全填 0**（那是偷懒）——每个维度都要根据其检查项给出真实的 0-100 分（通常 50-95 区间）；**也严禁维度全 0 却 overall 非零**。
5. **feedback_priorities**：针对 fail 项，按 high / medium / low 给**可执行**建议（如"补量化""前置相关经历"），不要空话。
6. 客观严谨，不奉承；量化数字无法追溯 → quantification 判 fail。

请输出 JSON：
"""
    return prompt


# ============================================================================
# 模拟面试出题 Prompt（生成 QuestionPackage 考查包）
# ============================================================================

def get_question_generation_prompt(
    candidate_summary: str,
    focus_areas: str,
    interview_type: str,
    question_count: int,
    probing_limit: int,
    company_hints: Optional[List[str]] = None,
    recent_questions: Optional[List[str]] = None,
    weakness_hints: Optional[List[str]] = None,
) -> str:
    """
    获取模拟面试出题 Prompt。

    核心设计（对应 design.md 决策 4）：每道题不是一段文本，而是「考查包」，
    出题时即预埋两张地图——
      - probing_points: 可挖掘点（evaluator 追问的弹药）
      - ideal_signals:  理想信号（evaluator 评判回答 + 决定是否追问的标尺）
    这样追问「按图索骥」（信号差检测），而非 LLM 临场自由发挥。

    Args:
        candidate_summary: 候选人画像摘要（姓名/经历/项目/技能，含细节）
        focus_areas:       考查重点（有 JD 时来自 Gap 清单；无 JD 时来自画像强弱项）
        interview_type:    面试类型（behavioral/technical/case/motivation/full）
        question_count:    本场题量
        probing_limit:     每题追问上限（决定 probing_points 的数量，1-3）
        company_hints:     RAG 公司库检索到的真实面经题（借鉴风格 + 增强真实感）
        recent_questions:  用户近期练过的题（出题避免重复——数据飞轮：个人库反哺）
        weakness_hints:    用户历史弱项考查点（建议本轮复练——数据飞轮：弱项复练）

    Returns:
        prompt 字符串，要求 LLM 输出 ```json``` 包裹的 QuestionPackage 列表。
    """
    # RAG 上下文（条件拼接：有才显示）——对应 spec 7.4 出题接入 RAG（公司库增强 + 个人库避免重复/复练）
    rag_section = ""
    if company_hints:
        _hints = "\n".join(f"  - {h}" for h in company_hints[:5])
        rag_section += f"\n## 可参考的真实面经（借鉴风格与考查角度，勿原样照搬）\n{_hints}\n"
    if recent_questions:
        _recent = "\n".join(f"  - {q}" for q in recent_questions[:8])
        rag_section += f"\n## 候选人近期练过的题（必须避免与这些重复，换角度/换经历切入）\n{_recent}\n"
    if weakness_hints:
        _weak = "\n".join(f"  - {w}" for w in weakness_hints[:5])
        rag_section += f"\n## 候选人历史弱项考查点（建议本轮优先复练这些方向）\n{_weak}\n"

    prompt = f"""你是一位资深面试官。请为候选人生成一份个性化的模拟面试题库。

## 候选人画像
{candidate_summary}

## 本场考查重点
{focus_areas}
{rag_section}## 出题要求
- 面试类型：{interview_type}
- 题目数量：{question_count} 道
- 每题可深挖程度：{probing_limit} 个追问方向（probing_points 数量上限 = {probing_limit}）

## 输出格式
请严格按以下 JSON 格式输出，**必须包裹在 ```json 代码块中**，输出一个数组：

```json
[
  {{
    "category": "behavioral | technical | case | motivation",
    "intent": "这道题考查什么能力（一句话）",
    "stem": "面试官要问候选人的完整问题",
    "anchor": "本题针对候选人画像中的哪段具体经历/项目/技能（必须真实命中画像，用于个性化）",
    "probing_points": ["可挖掘的方向 1", "可挖掘的方向 2"],
    "ideal_signals": ["好回答应体现的信号 1", "好回答应体现的信号 2"],
    "estimated_minutes": 4
  }}
]
```

## 出题规则（务必遵守）
1. **个性化锚点（最重要）**：每题的 anchor 必须真实对应候选人画像里的某段经历/项目/技能。
   读「候选人画像」，把问题绑定到候选人真实做过的事，而不是泛泛的通用题。
   若画像经历不足，anchor 填 "通用考查（画像经历不足）"。
2. **考查重点覆盖**：优先围绕「本场考查重点」出题；重点项要多出、深挖。
3. **probing_points 要具体可问**：如「具体的数据结果？」「你个人的贡献？」「遇到的最大冲突？」，
   不要写「深入了解」这种空泛方向。数量 = {probing_limit}。
4. **ideal_signals 要具体可判定**：如「量化结果」「个人主动性」「遇到困难与反思」，
   不要写「回答得好」这种无法判定的信号。数量 = {probing_limit}。
5. **题型对齐**：category 必须符合面试类型要求（{interview_type}）；full 类型可混合各题型。
6. **stem 像真人面试官**：自然口语，如「看你简历里提到 XX，能具体讲讲吗？」，不要写成考卷题。
7. **estimated_minutes**：按题目复杂度估 3-6 分钟。

请开始生成（必须输出完整的 JSON 数组）：
"""
    return prompt


# ============================================================================
# 模拟面试 评估 Prompt（信号差检测——对应 design.md 决策 5）
# ============================================================================

def get_evaluation_prompt(
    question: str,
    ideal_signals: list,
    probing_points: list,
    answer: str,
    persona: Optional[Dict[str, Any]] = None,
    interview_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    获取面试回答评估 Prompt（信号差检测 + 节奏决策 + 追问措辞）。

    拿候选人回答比对 ideal_signals，输出命中/缺失信号 + 评分 + 追问措辞，
    并由 LLM 自主决定下一节奏动作（action：追问/换题/反问/结束）。

    【evolve-interview-pacing】节奏决策（action）并入本次评估一起产出——取代原
    写死的计数器规则 _decide。LLM 依据回答充分度 / 疑虑 / 亮点 / 整场进度，像真人
    面试官一样自主选择动作；护栏（_decide 内）仅防崩盘兜底。追问方向可参考但不仅
    限于预埋可挖掘点（图为弹药、临场可发挥）。若 action≠probe 则 next_probe_followup
    填 null。
    """
    import json
    # ── 人设解析（追问措辞与 action 决策的口吻依据）──
    persona = persona or {}
    tone = persona.get("tone", "专业")
    role = persona.get("role") or {}
    role_str = f"{role.get('company', '')}{role.get('position', '')}".strip() or "面试官"
    stress = persona.get("stress_mode")
    style = persona.get("style_prompt", "")
    stress_hint = "压力面模式：可适度质疑、追问到底，考察候选人抗压。" if stress else ""

    # ── 整场进度上下文（支撑 action 的"整场判断"，如是否提前结束）──
    ctx = interview_context or {}
    round_no = ctx.get("round")
    total_q = ctx.get("total_questions")
    has_qa = ctx.get("has_qa_session")
    qa_done = ctx.get("qa_done")
    avg_so_far = ctx.get("avg_score_so_far")
    progress_parts = []
    if round_no:
        progress_parts.append(f"当前第 {round_no} 轮")
    if total_q:
        progress_parts.append(f"题库共 {total_q} 题")
    if avg_so_far is not None:
        progress_parts.append(f"前几轮平均分 {avg_so_far}")
    if has_qa:
        progress_parts.append("含反问环节" + ("（已进行）" if qa_done else "（尚未进行）"))
    progress_line = "；".join(progress_parts) if progress_parts else "无进度信息"

    sig_text = json.dumps(ideal_signals, ensure_ascii=False)
    probe_text = json.dumps(probing_points, ensure_ascii=False)
    prompt = f"""你是一位严谨又像真人的面试官。评估候选人对面试问题的回答质量，并决定接下来怎么走这场面试。

## 面试问题
{question}

## 该题理想信号（好回答应体现）
{sig_text}

## 可挖掘点（可用于追问的方向，非穷尽）
{probe_text}

## 候选人回答
{answer}

## 整场进度
{progress_line}

## 输出格式（**必须包裹在 ```json 代码块中**）
```json
{{
  "hit_signals": ["回答命中的理想信号"],
  "miss_signals": ["回答未体现的理想信号"],
  "miss_probe_map": {{ "缺失信号": "对应的可挖掘点（追问方向）" }},
  "score": 75,
  "highlight": "回答亮点（无则 null）",
  "weakness": "回答失分点（无则 null）",
  "action": "probe | next | enter_qa | end",
  "action_reason": "一句话说明为什么选这个动作（像面试官的内心判断）",
  "next_probe_followup": "若 action=probe：按人设口吻的一句自然追问；否则 null"
}}
```

## 规则
1. score 0-100：按理想信号命中度 + 回答深度（具体、有数据、有反思）综合评分。
2. miss_signals：理想信号中回答未体现的（回答充分则空数组）。
3. miss_probe_map：为每个缺失信号映射一个可挖掘点；不足以对应则值填 null。
4. highlight/weakness：具体简短、引用回答内容；没有则 null。
5. **action（节奏决策，本次一并产出）**——你就是面试官（{role_str}，风格{tone}），像真人一样决定这场面试接下来怎么走：
   - **probe（追问）**：回答还没说透——有疑虑、有矛盾、有可深挖的点（含候选人主动提到、值得追的方向，不限于上方可挖掘点）。听出味道就追。
   - **next（换下一题）**：这道已问清楚（无论答得好坏），不必再纠缠，往下走。
   - **enter_qa（进入反问）**：你问得差不多了，把舞台交给候选人提问（仅当整场进度含反问环节且尚未进行）。
   - **end（结束面试）**：你已能对候选人下判断，没必要继续——可能表现足够亮眼已无需再考，也可能明显不胜任再问也是浪费。**不必非走完全部题**，该收尾就收尾。
   {style}{stress_hint}
6. **action_reason**：一句话讲清判断依据（如"回答缺量化数据，追问具体结果"/"已充分体现数据驱动，换题"/"全程浮于表面，提前结束"）。
7. **next_probe_followup（追问措辞）**：仅当 action=probe 时给出。挑一个最值得深挖的方向（可来自缺失信号对应的可挖掘点，也可来自回答里临场的亮点/疑点），用你的风格写**一句**自然追问。像真人面试官口吻，不要机械模板，不要每次都用"关于你刚才的回答"开头；不带引号、不带前缀标签，只写追问这一句本身。action≠probe 时填 null。
8. 客观严谨，不奉承。
9. **语音识别容错**：回答可能来自语音转写，含同音/近音错字（如「日活」→「日火」、「复购」→「负购」、「站会」→「占会」）或口语化表达与停顿。请结合上下文按**语义**判断信号命中、评分与 action 决策，不要因字面小瑕疵误判——例如「日火提升 15%」应理解为「日活提升」，判为命中「量化结果」类信号。

请输出 JSON：
"""
    return prompt


# ============================================================================
# 模拟面试 详细复盘 Prompt（改进范例 / 卡壳 / 后续建议）
# ============================================================================

def get_debrief_prompt(profile_summary: str, transcript_json: str, target_position: str) -> str:
    """
    获取详细复盘 Prompt。

    基于完整面试记录，生成结构化复盘：
      - 逐题改进范例（better_version，基于候选人【自身经历】改写，非通用标准答案）
      - 不合适的回答（跑题/空洞/负面）
      - 卡壳处
      - 可执行后续建议

    对应 design.md 决策 7：改进范例「基于自身回答生成」vs「检索标准答案」——培养反思非背诵。
    """
    prompt = f"""你是一位资深面试教练。基于以下完整面试记录，生成结构化详细复盘，帮助候选人改进。

## 候选人画像
{profile_summary}

## 目标岗位
{target_position}

## 面试记录（每轮含：问题、候选人回答、得分、缺失信号、节奏动作 action、节奏理由 decision_reason）
{transcript_json}

## 输出格式（**必须包裹在 ```json 代码块中**）
```json
{{
  "overall_summary": "一句话总评候选人整体表现（客观）",
  "round_reviews": [
    {{
      "round": 1,
      "better_version": "基于候选人【自己的真实经历】改写的改进版回答",
      "improvement_point": "这条改进版相比原回答，好在哪里（具体）"
    }}
  ],
  "inappropriate_answers": ["不合适的回答（跑题/空洞/负面/造假感），指明第几轮、为什么不合适"],
  "stuck_points": ["卡壳处：第几轮、卡在哪、可能的原因"],
  "next_steps": ["可执行的后续准备建议"]
}}
```

## 规则（务必遵守）
1. **better_version 必须基于候选人自身经历改写**：读画像里的真实经历/项目，把原回答用 STAR + 量化重写。
   绝不编造候选人没有的经历，也不给通用模板答案——这是「基于自身回答的改进」，不是「标准答案」。
2. **improvement_point**：具体引用原回答内容，说明改进版强在哪。
3. **inappropriate_answers / stuck_points**：从面试记录里识别，每条指明轮次。回答过短/含糊/缺数据 = 卡壳信号。
4. **next_steps 必须可执行**：如「针对目标岗位，准备 3 个 STAR 故事覆盖『数据驱动决策』方向」。
   **禁止**「加强沟通能力」「提升逻辑思维」式空话。结合目标岗位与候选人弱点。
5. 客观、建设性，不奉承。
6. **参考节奏判断**：每轮记录含 action（面试官当轮动作：probe 追问 / next 换题 / enter_qa 反问 / end 结束）与 decision_reason（该动作的自然语言理由）。分析候选人表现时可参考这些节奏信号——例如连续 probe 往往说明回答屡未说透、提前 end 反映表现已定性，有助于定位卡壳与失分。
7. **语音识别容错**：面试记录可能来自语音转写，含同音/近音错字（如「日活」→「日火」、「复购」→「负购」、「漏斗」→「漏豆」）或口语化表达。理解候选人回答时按**语义**还原真实意图，better_version / improvement_point / inappropriate_answers / stuck_points 的判断均基于还原后的语义，不要因字面错字误判「跑题」或「卡壳」。

请输出 JSON：
"""
    return prompt


def get_company_question_augment_prompt(
    position: str,
    count: int = 5,
    company: Optional[str] = None,
) -> str:
    """
    公司面经库「LLM 扩充长尾」Prompt（spec：基于种子 + 公开信息生成，标注 llm_generated）。

    用途：某岗位公司库题量不足时，生成补充题填补长尾。
    约束：生成的题要贴近真实面试风格（像 HR/业务面会问的），而非教科书题目。
    """
    scope = f"{company}的" if company else ""
    prompt = f"""你是资深面试官，熟悉{scope}「{position}」岗位的真实面试。

请生成 {count} 道该岗位【真实面试中高频出现】的面试题。要求：
1. 贴近真实面试风格——像 HR 面、业务面、技术面真的会问的问题，不是教科书题目。
2. 覆盖行为面（讲经历）、专业/技术面、案例/情景面、动机面等不同题型。
3. 每题附「考察点」（一句话说明这题在考察什么）。

输出 JSON 数组，格式：
{{
  "questions": [
    {{"category": "behavioral|technical|case|motivation", "question": "面试题文本", "context": "考察点"}}
  ]
}}
只输出 JSON，不要其它解释。
"""
    return prompt


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Prompt 模板测试")
    print("=" * 60)

    # 测试文本
    test_resume = """
    张三
    电话：13800138000
    邮箱：zhangsan@example.com

    教育背景
    清华大学 计算机科学与技术 本科 2018-2022

    工作经历
    ABC公司 软件工程师 2022-至今
    """

    print("\n[TEST 1] 标准提取 Prompt（高质量文本）")
    prompt = get_extraction_prompt(test_resume, quality_score=0.9)
    print(f"✓ Prompt 长度: {len(prompt)} 字符")
    print(f"✓ 预览: {prompt[:200]}...")

    print("\n[TEST 2] 容错提取 Prompt（低质量文本）")
    prompt = get_extraction_prompt(test_resume, quality_score=0.5)
    print(f"✓ Prompt 长度: {len(prompt)} 字符")
    print(f"✓ 预览: {prompt[:200]}...")

    print("\n[TEST 3] 重试提取 Prompt")
    prompt = get_extraction_prompt(test_resume, is_retry=True)
    print(f"✓ Prompt 长度: {len(prompt)} 字符")
    print(f"✓ 预览: {prompt[:200]}...")

    print("\n" + "=" * 60)
