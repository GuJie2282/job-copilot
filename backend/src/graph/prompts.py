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
from typing import Dict, Any, Optional


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
  "technical_skills": ["string"],
  "soft_skills": ["string"],
  "languages": ["string"],
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
4. **数组格式**：schools、companies 等字段必须是数组，即使只有一个元素
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
# 模拟面试出题 Prompt（生成 QuestionPackage 考查包）
# ============================================================================

def get_question_generation_prompt(
    candidate_summary: str,
    focus_areas: str,
    interview_type: str,
    question_count: int,
    probing_limit: int,
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

    Returns:
        prompt 字符串，要求 LLM 输出 ```json``` 包裹的 QuestionPackage 列表。
    """
    prompt = f"""你是一位资深面试官。请为候选人生成一份个性化的模拟面试题库。

## 候选人画像
{candidate_summary}

## 本场考查重点
{focus_areas}

## 出题要求
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
) -> str:
    """
    获取面试回答评估 Prompt（信号差检测）。

    拿候选人回答比对 ideal_signals，输出命中/缺失信号 + 缺失→可挖掘点映射，
    让追问「按图索骥、可控可解释」，而非 LLM 临场自由发挥。
    """
    import json
    sig_text = json.dumps(ideal_signals, ensure_ascii=False)
    probe_text = json.dumps(probing_points, ensure_ascii=False)
    prompt = f"""你是一位严谨的面试评估官。评估候选人对面试问题的回答质量。

## 面试问题
{question}

## 该题理想信号（好回答应体现）
{sig_text}

## 可挖掘点（可用于追问的方向）
{probe_text}

## 候选人回答
{answer}

## 输出格式（**必须包裹在 ```json 代码块中**）
```json
{{
  "hit_signals": ["回答命中的理想信号"],
  "miss_signals": ["回答未体现的理想信号"],
  "miss_probe_map": {{ "缺失信号": "对应的可挖掘点（追问方向）" }},
  "score": 75,
  "highlight": "回答亮点（无则 null）",
  "weakness": "回答失分点（无则 null）"
}}
```

## 规则
1. score 0-100：按理想信号命中度 + 回答深度（具体、有数据、有反思）综合评分。
2. miss_signals：理想信号中回答未体现的（回答充分则空数组）。
3. miss_probe_map：为每个缺失信号映射一个可挖掘点（追问方向）；不足以对应则值填 null。
4. highlight/weakness：具体简短、引用回答内容；没有则 null。
5. 客观严谨，不奉承。

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

## 面试记录（每轮含：问题、候选人回答、得分、缺失信号）
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

请输出 JSON：
"""
    return prompt


# ============================================================================
# 模拟面试 追问生成 Prompt（带面试官人设口吻——对应 design.md 决策 10）
# ============================================================================

def get_followup_prompt(
    persona: Optional[Dict[str, Any]],
    probing_point: str,
    question: str,
    answer: str,
) -> str:
    """
    获取追问生成 Prompt。

    把追问从「固定模板」升级为「LLM 基于人设生成」——让追问自然、有风格口吻
    （严肃/轻松/风趣/压力），替代机械的"关于你刚才的回答，我想再深入一下——…"。

    追问方向（probing_point）仍由出题时预埋 + evaluator 信号差检测决定（按图索骥），
    只是【措辞】交给人设化的 LLM。
    """
    persona = persona or {}
    tone = persona.get("tone", "专业")
    role = persona.get("role") or {}
    role_str = f"{role.get('company', '')}{role.get('position', '')}".strip() or "面试官"
    stress = persona.get("stress_mode")
    style = persona.get("style_prompt", "")
    stress_hint = "\n（压力面模式：可适度质疑、追问到底，考察候选人抗压能力。）" if stress else ""

    prompt = f"""你是面试官（{role_str}），风格{tone}。{style}{stress_hint}

刚才你问了候选人：「{question}」
候选人回答：「{answer}」

你想就「{probing_point}」这个方向继续深挖。请用你的风格，生成一句自然的追问——
像真人面试官的口吻，不要机械模板，不要每次都用"关于你刚才的回答"开头。

只输出追问这一句话本身，不要引号、不要解释、不要前缀标签。
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
