"""
LLM 配置和初始化

功能：
1. 配置 LLM（DeepSeek、OpenAI 等）
2. 支持结构化输出（JSON Schema）
3. 提供统一的 LLM 接口

作者：求职 Copilot 项目
日期：2026-07-03
"""

import os
from typing import Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel


# ============================================================================
# 配置常量
# ============================================================================

# 默认配置
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.0  # 简历解析需要确定性输出
DEFAULT_MAX_TOKENS = 4096

# 支持的模型配置
MODEL_CONFIGS = {
    "deepseek-chat": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "LLM_API_KEY",
        "default_temperature": 0.0,
        "default_max_tokens": 4096,
    },
    "gpt-4o-mini": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_temperature": 0.0,
        "default_max_tokens": 4096,
    },
    "glm-4-flash": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "LLM_API_KEY",
        "default_temperature": 0.0,
        "default_max_tokens": 4096,
    },
    "glm-4.5": {
        # 主力档：质量敏感任务（出题/复盘/简历解析/JD 解析）。与 flash 共用智谱 base_url + key
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "LLM_API_KEY",
        "default_temperature": 0.0,
        "default_max_tokens": 4096,
    },
}


# ============================================================================
# LLM 初始化函数
# ============================================================================

def get_llm(
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 60.0,
    tier: str = "fast",
) -> BaseChatModel:
    """
    获取 LLM 实例

    Args:
        model: 模型名称（如 "glm-4.5"、"glm-4-flash"）。显式指定时优先级最高，tier 被忽略
        temperature: 温度参数（0.0-1.0，简历解析建议用 0.0）
        max_tokens: 最大生成 tokens
        api_key: API Key（可选，默认从环境变量读取）
        base_url: API Base URL（可选，默认从配置读取）
        timeout: LLM 调用超时（秒）
        tier: 模型档位（仅在 model 未指定时生效）——分层选模，平衡质量与成本/延迟：
              "fast"   快档（默认，LLM_MODEL=glm-4-flash，免费）：延迟敏感场景（评估、对话）
              "strong" 主力档（LLM_MODEL_STRONG=glm-4.5）：质量敏感场景（出题、复盘、简历/JD 解析）

    Returns:
        llm: LLM 实例

    示例：
        >>> llm = get_llm()                       # 快档（默认）
        >>> llm = get_llm(tier="strong")          # 主力档（质量敏感任务）
        >>> llm = get_llm(model="gpt-4o-mini")    # 显式指定模型（tier 被忽略）
        >>> llm = get_llm(temperature=0.7)        # 提高温度，增加创造性
    """
    # 模型选择优先级：显式 model > tier 对应环境变量 > 默认
    if model is None:
        if tier == "strong":
            # 主力档：质量敏感任务（出题/复盘/简历解析等）
            model = os.getenv("LLM_MODEL_STRONG", "glm-4.5")
        else:
            # 快档（默认）：延迟敏感任务（评估/对话）
            model = os.getenv("LLM_MODEL", DEFAULT_MODEL)

    # 获取模型配置
    model_config = MODEL_CONFIGS.get(model, MODEL_CONFIGS[DEFAULT_MODEL])

    # 获取 API Key
    if api_key is None:
        api_key = os.getenv(model_config["api_key_env"])
        if not api_key:
            raise ValueError(
                f"API Key not found. Please set {model_config['api_key_env']} "
                f"in environment variables or .env file."
            )

    # 获取 Base URL
    if base_url is None:
        base_url = os.getenv("LLM_BASE_URL", model_config.get("base_url"))

    # 创建 LLM 实例
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,  # LLM 调用超时（默认 60s；答题循环内的评估/追问传更短快速降级，出题/复盘/简历传更长）
        # 关闭 openai SDK 内置重试！我们的 llm_retry / 各 service 自己的重试循环已全程兜底，
        # 若再叠加 SDK 的 max_retries=2，单次"超时"会被放大成 3×（SDK 3 次）×（我们的 N 次）≈ 数分钟~9 分钟挂起
        # （GLM 抖动时实测：parse_jd 卡 7 分钟+ 用户全程"分析中"）。重试权统一归我们的代码。
        max_retries=0,
    )

    return llm


def get_structured_llm(
    model: Optional[str] = None,
    schema: Optional[BaseModel] = None,
    tier: str = "fast",
    **kwargs
) -> BaseChatModel:
    """
    获取支持结构化输出的 LLM 实例

    Args:
        model: 模型名称
        schema: Pydantic BaseModel（用于结构化输出）
        tier: 模型档位（同 get_llm，"fast"快档 / "strong"主力档）
        **kwargs: 其他参数（temperature、max_tokens 等）

    Returns:
        llm: 支持结构化输出的 LLM 实例

    示例：
        >>> class UserProfile(BaseModel):
        ...     name: str
        ...     email: str
        >>> llm = get_structured_llm(schema=UserProfile, tier="strong")  # 简历解析用主力档
        >>> result = llm.invoke("简历文本")
        >>> print(result.name)
    """
    llm = get_llm(model, tier=tier, **kwargs)

    # 如果提供了 schema，使用 with_structured_output
    if schema is not None:
        # 尝试使用不同的方法来提高兼容性
        try:
            # 智谱模型可能需要明确指定方法
            llm = llm.with_structured_output(schema, method=["json_mode", "function_calling"])
        except Exception:
            # 如果失败，回退到默认方式
            llm = llm.with_structured_output(schema)

    return llm


# ============================================================================
# 用户画像 JSON Schema
# ============================================================================

# ----------------------------------------------------------------------------
# 画像嵌套子模型（教育/工作/项目各字段绑死在同一实体，杜绝扁平平行数组错位）
# ----------------------------------------------------------------------------

class EducationItem(BaseModel):
    """单段教育经历：学校/学历/专业/毕业年份绑死在同一学校实体"""
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[str] = None


class WorkExperienceItem(BaseModel):
    """单段工作/实习经历：公司/职位/时间/职责详情绑死在同一经历实体"""
    company: Optional[str] = None
    position: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None  # 职责与成果详情（保留原文细节）


class ProjectItem(BaseModel):
    """单个项目：名称/角色/详情绑死在同一项目实体"""
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None  # 项目内容、职责与成果（保留原文细节）


class UserProfile(BaseModel):
    """
    用户画像的数据模型（用于结构化输出）

    结构：教育/工作/项目用「嵌套对象数组」（每个实体的字段绑死在一起），
    杜绝旧「扁平平行数组靠下标对齐」导致的字段错位（如项目名张冠李戴）。
    """

    # 基础信息
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    self_summary: Optional[str] = None  # 个人总结 / 自我评价（保留原文）

    # 教育/工作/项目（嵌套对象数组）
    education: Optional[list[EducationItem]] = None
    work_experience: Optional[list[WorkExperienceItem]] = None
    projects: Optional[list[ProjectItem]] = None

    # 技能（扁平数组，天然无错位问题）
    technical_skills: Optional[list[str]] = None
    soft_skills: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    achievements: Optional[list[str]] = None  # 荣誉、奖项、证书

    # 求职目标
    target_positions: Optional[list[str]] = None
    target_companies: Optional[list[str]] = None
    location_preference: Optional[str] = None
    salary_range: Optional[str] = None
    industry: Optional[str] = None


# ============================================================================
# 配置验证
# ============================================================================

def validate_config() -> tuple[bool, str]:
    """
    验证 LLM 配置是否正确

    Returns:
        (is_valid, message)
        - is_valid: 配置是否有效
        - message: 验证消息
    """
    # 检查 API Key
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    model_config = MODEL_CONFIGS.get(model, MODEL_CONFIGS[DEFAULT_MODEL])
    api_key_env = model_config["api_key_env"]
    api_key = os.getenv(api_key_env)

    if not api_key:
        return False, f"❌ API Key 未配置：请在 .env 文件中设置 {api_key_env}"

    # 检查 Base URL
    base_url = os.getenv("LLM_BASE_URL")
    if not base_url and "base_url" in model_config:
        base_url = model_config["base_url"]

    if not base_url:
        return False, f"❌ Base URL 未配置：请在 .env 文件中设置 LLM_BASE_URL"

    # 尝试创建 LLM 实例
    try:
        llm = get_llm()
        return True, f"✅ LLM 配置有效（模型：{model}）"
    except Exception as e:
        return False, f"❌ LLM 初始化失败：{str(e)}"


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LLM 配置测试")
    print("=" * 60)

    # 测试配置验证
    print("\n[TEST 1] 验证配置")
    is_valid, message = validate_config()
    print(message)

    if is_valid:
        # 测试创建 LLM 实例
        print("\n[TEST 2] 创建 LLM 实例")
        try:
            llm = get_llm()
            print(f"✓ LLM 实例创建成功")
            print(f"  - 模型: {llm.model_name}")
            print(f"  - 温度: {llm.temperature}")
            print(f"  - 最大 tokens: {llm.max_tokens}")
        except Exception as e:
            print(f"✗ LLM 实例创建失败: {e}")

        # 测试结构化输出
        print("\n[TEST 3] 创建结构化输出 LLM")
        try:
            llm_structured = get_structured_llm(schema=UserProfile)
            print(f"✓ 结构化输出 LLM 创建成功")
            print(f"  - Schema: UserProfile")
        except Exception as e:
            print(f"✗ 结构化输出 LLM 创建失败: {e}")

    print("\n" + "=" * 60)
