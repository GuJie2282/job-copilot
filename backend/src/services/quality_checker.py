"""
文本质量检测与置信度计算模块

功能：
1. 文本质量检测（长度、中文比例、结构完整性、乱码检测）
2. 置信度计算（精确匹配、模糊匹配、关键词匹配）

作者：求职 Copilot 项目
日期：2026-07-03
"""

import re
from typing import Dict, List, Tuple, Any


# ============================================================================
# 常量定义
# ============================================================================

# 质量阈值
MIN_TEXT_LENGTH = 200  # 最小文本长度
MIN_CHINESE_RATIO = 0.3  # 最小中文比例（30%）
QUALITY_THRESHOLD_HIGH = 0.8  # 高质量阈值
QUALITY_THRESHOLD_MEDIUM = 0.6  # 中等质量阈值
QUALITY_THRESHOLD_LOW = 0.4  # 低质量阈值

# 简历关键词（用于结构完整性检测）
RESUME_KEYWORDS = [
    '教育', '学历', '学校', '大学', '学院',
    '工作', '经历', '职位', '公司', '企业',
    '技能', '能力', '语言', '英语',
    '项目', '经验', '实习',
    '邮箱', '电话', '手机', '联系',
    '姓名', '性别', '年龄'
]

# 置信度等级
CONFIDENCE_EXACT_MATCH = 0.95  # 精确匹配（95%）
CONFIDENCE_FUZZY_MATCH = 0.85  # 模糊匹配（85%）
CONFIDENCE_KEYWORD_MATCH = 0.70  # 关键词匹配（70%）
CONFIDENCE_DEFAULT = 0.50  # 默认置信度（50%）

# 乱码检测（特殊字符比例阈值）
MAX_SPECIAL_CHAR_RATIO = 0.2  # 最大特殊字符比例（20%）


# ============================================================================
# 文本质量检测功能
# ============================================================================

def check_text_length(text: str) -> Tuple[bool, float, str]:
    """
    检查文本长度

    Args:
        text: 待检测文本

    Returns:
        (is_valid, score, message)
        - is_valid: 是否通过检测
        - score: 质量分数（0.0-1.0）
        - message: 检测消息
    """
    text_length = len(text.strip())

    if text_length < MIN_TEXT_LENGTH:
        shortage = MIN_TEXT_LENGTH - text_length
        return False, 0.3, f"文本过短（{text_length} 字符），建议至少 {MIN_TEXT_LENGTH} 字符。当前缺少 {shortage} 字符。"
    elif text_length < MIN_TEXT_LENGTH * 2:
        return True, 0.6, f"文本长度适中（{text_length} 字符）。"
    else:
        return True, 1.0, f"文本长度充足（{text_length} 字符）。"


def check_chinese_ratio(text: str) -> Tuple[bool, float, str]:
    """
    检查中文比例

    Args:
        text: 待检测文本

    Returns:
        (is_valid, score, message)
        - is_valid: 是否通过检测
        - score: 质量分数（0.0-1.0）
        - message: 检测消息
    """
    # 匹配中文字符（包括中文标点）
    chinese_pattern = re.compile(r'[一-鿿　-〿]')
    chinese_chars = chinese_pattern.findall(text)
    chinese_count = len(chinese_chars)

    total_count = len(text.strip())
    if total_count == 0:
        return False, 0.0, "文本为空。"

    chinese_ratio = chinese_count / total_count

    if chinese_ratio < MIN_CHINESE_RATIO:
        return False, 0.4, f"中文比例过低（{chinese_ratio:.1%}），建议至少 {MIN_CHINESE_RATIO:.0%}。可能是外文简历或缺少关键信息。"
    elif chinese_ratio < MIN_CHINESE_RATIO + 0.2:
        return True, 0.7, f"中文比例适中（{chinese_ratio:.1%}）。"
    else:
        return True, 1.0, f"中文比例良好（{chinese_ratio:.1%}）。"


def check_structure_completeness(text: str) -> Tuple[bool, float, str]:
    """
    检查结构完整性（通过关键词匹配）

    Args:
        text: 待检测文本

    Returns:
        (is_valid, score, message)
        - is_valid: 是否通过检测
        - score: 质量分数（0.0-1.0）
        - message: 检测消息
    """
    found_keywords = []
    for keyword in RESUME_KEYWORDS:
        if keyword in text:
            found_keywords.append(keyword)

    keyword_count = len(found_keywords)
    total_keywords = len(RESUME_KEYWORDS)
    keyword_ratio = keyword_count / total_keywords

    if keyword_ratio < 0.3:
        return False, keyword_ratio, f"缺少常见的简历关键词（仅找到 {keyword_count}/{total_keywords} 个）。当前文本结构不清晰，可能不是完整简历。"
    elif keyword_ratio < 0.5:
        return True, keyword_ratio, f"包含部分简历关键词（{keyword_count}/{total_keywords} 个）。结构基本完整，建议检查是否缺少重要信息。"
    else:
        return True, 1.0, f"包含完整简历关键词（{keyword_count}/{total_keywords} 个）。结构清晰。"


def check_special_chars(text: str) -> Tuple[bool, float, str]:
    """
    检查乱码（特殊字符比例）

    Args:
        text: 待检测文本

    Returns:
        (is_valid, score, message)
        - is_valid: 是否通过检测
        - score: 质量分数（0.0-1.0）
        - message: 检测消息
    """
    # 匹配常见乱码字符（非字母、数字、中文、常见标点）
    # 正常字符：字母、数字、中文、常见标点、空格、换行
    # 注意：字面量 '-' 放在字符类开头，避免被解释为范围；字符类内的普通标点无需转义
    normal_pattern = re.compile(r'[-\w一-鿿\s.,;:!?()""''　-〿]')
    normal_chars = normal_pattern.findall(text)
    normal_count = len(normal_chars)

    total_count = len(text.strip())
    if total_count == 0:
        return False, 0.0, "文本为空。"

    special_ratio = 1 - (normal_count / total_count)

    if special_ratio > MAX_SPECIAL_CHAR_RATIO:
        return False, 1.0 - special_ratio, f"特殊字符比例过高（{special_ratio:.1%}），可能存在乱码。建议检查文本编码或格式。"
    elif special_ratio > MAX_SPECIAL_CHAR_RATIO / 2:
        return True, 1.0 - special_ratio, f"特殊字符比例适中（{special_ratio:.1%}）。"
    else:
        return True, 1.0, f"特殊字符比例正常（{special_ratio:.1%}）。"


def check_text_quality(text: str) -> Tuple[float, List[str]]:
    """
    综合检查文本质量

    Args:
        text: 待检测文本

    Returns:
        (quality_score, warnings)
        - quality_score: 质量分数（0.0-1.0）
        - warnings: 警告列表

    评分标准：
    - 1.0 (优秀): 所有检测都通过
    - 0.8-1.0 (良好): 大部分检测通过
    - 0.6-0.8 (中等): 部分检测不通过
    - 0.4-0.6 (较差): 多项检测不通过
    - 0.0-0.4 (差): 文本质量很差
    """
    warnings = []
    scores = []

    # 1. 检查文本长度
    is_valid, score, message = check_text_length(text)
    scores.append(score)
    if not is_valid:
        warnings.append(message)
    else:
        # 只在通过时添加信息性消息
        if score < 1.0:
            warnings.append(message)

    # 2. 检查中文比例
    is_valid, score, message = check_chinese_ratio(text)
    scores.append(score)
    if not is_valid:
        warnings.append(message)
    else:
        if score < 1.0:
            warnings.append(message)

    # 3. 检查结构完整性
    is_valid, score, message = check_structure_completeness(text)
    scores.append(score)
    if not is_valid:
        warnings.append(message)
    else:
        if score < 1.0:
            warnings.append(message)

    # 4. 检查乱码
    is_valid, score, message = check_special_chars(text)
    scores.append(score)
    if not is_valid:
        warnings.append(message)
    else:
        if score < 1.0:
            warnings.append(message)

    # 计算平均分
    quality_score = sum(scores) / len(scores)

    return quality_score, warnings


# ============================================================================
# 置信度计算功能
# ============================================================================

def calculate_confidence(field_value: str, original_text: str) -> float:
    """
    计算字段的置信度（百分比）

    Args:
        field_value: 字段值（LLM 提取的值）
        original_text: 原始文本（简历全文）

    Returns:
        confidence_score: 置信度分数（0.0-1.0）

    计算规则：
    - 0.95 (95%): 精确匹配（字段值在原文中完全匹配）
    - 0.85 (85%): 模糊匹配（去掉标点和空格后匹配）
    - 0.70 (70%): 关键词匹配（70% 以上的关键词在原文中）
    - 0.50 (50%): 无法验证（在原文中找不到任何匹配）
    """
    if not field_value or not field_value.strip():
        return 0.0

    # 规则 1：精确匹配（95%）
    if field_value in original_text:
        return CONFIDENCE_EXACT_MATCH

    # 规则 2：模糊匹配（85%）
    # 去除标点和空格后比较
    clean_field = re.sub(r'[-\s.,;:!?()""''.]', '', field_value)
    clean_text = re.sub(r'[-\s.,;:!?()""''.]', '', original_text)
    if clean_field and clean_field in clean_text:
        return CONFIDENCE_FUZZY_MATCH

    # 规则 3：关键词匹配（70%）
    # 提取字段值中的关键词（长度 >= 2 的词）
    keywords = re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', field_value)
    if keywords:
        matched_count = 0
        for keyword in keywords:
            if keyword in original_text:
                matched_count += 1

        match_ratio = matched_count / len(keywords)
        if match_ratio >= 0.7:
            return CONFIDENCE_KEYWORD_MATCH

    # 规则 4：无法验证（50%）
    return CONFIDENCE_DEFAULT


def calculate_field_confidence(
    field_name: str,
    field_value: str,
    original_text: str
) -> Tuple[float, str]:
    """
    计算单个字段的置信度，并返回置信度等级

    Args:
        field_name: 字段名称（用于返回消息）
        field_value: 字段值
        original_text: 原始文本

    Returns:
        (confidence_score, confidence_level)
        - confidence_score: 置信度分数（0.0-1.0）
        - confidence_level: 置信度等级（"高", "中", "低"）
    """
    confidence = calculate_confidence(field_value, original_text)

    if confidence >= 0.80:
        level = "高"
    elif confidence >= 0.60:
        level = "中"
    else:
        level = "低"

    return confidence, level


def calculate_profile_confidence(
    profile: Dict[str, Any],
    original_text: str
) -> Dict[str, Dict[str, Any]]:
    """
    计算整个画像的置信度

    Args:
        profile: 个人画像（结构化数据）
        original_text: 原始文本

    Returns:
        confidence_result: 置信度结果字典
        - 字段路径 -> {"score": 置信度分数, "level": 置信度等级}

    示例：
        >>> profile = {
        ...     "basic_info": {"name": "张三", "phone": "13800138000"},
        ...     "education": [{"school": "清华大学"}]
        ... }
        >>> confidence_result = calculate_profile_confidence(profile, resume_text)
        >>> print(confidence_result["basic_info.name"])
        >>> {"score": 0.95, "level": "高"}
    """
    confidence_result = {}

    # 遍历画像的所有字段
    def traverse_object(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                traverse_object(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                traverse_object(item, current_path)
        elif isinstance(obj, str):
            # 计算字符串字段的置信度
            score, level = calculate_field_confidence(path, obj, original_text)
            confidence_result[path] = {
                "score": score,
                "level": level
            }

    traverse_object(profile)

    return confidence_result


# ============================================================================
# 辅助功能
# ============================================================================

def format_quality_report(quality_score: float, warnings: List[str]) -> str:
    """
    格式化质量报告

    Args:
        quality_score: 质量分数
        warnings: 警告列表

    Returns:
        formatted_report: 格式化的报告字符串
    """
    if quality_score >= QUALITY_THRESHOLD_HIGH:
        status = "高质量"
        emoji = "✅"
    elif quality_score >= QUALITY_THRESHOLD_MEDIUM:
        status = "中等质量"
        emoji = "⚠️"
    else:
        status = "低质量"
        emoji = "❌"

    report = f"""
{emoji} 文本质量报告
{'='*40}
质量分数: {quality_score:.2f} / 1.00
质量等级: {status}
{'='*40}
"""

    if warnings:
        report += "\n检测详情：\n"
        for i, warning in enumerate(warnings, 1):
            report += f"{i}. {warning}\n"
    else:
        report += "\n所有检测项通过！\n"

    return report


def format_confidence_report(confidence_result: Dict[str, Dict[str, Any]]) -> str:
    """
    格式化置信度报告

    Args:
        confidence_result: 置信度结果字典

    Returns:
        formatted_report: 格式化的报告字符串
    """
    report = "\n📊 字段置信度报告\n"
    report += "=" * 40 + "\n"

    # 按字段路径排序
    sorted_fields = sorted(confidence_result.items())

    for field_path, conf_data in sorted_fields:
        score = conf_data["score"]
        level = conf_data["level"]

        # 根据等级选择 emoji
        if level == "高":
            emoji = "✅"
        elif level == "中":
            emoji = "⚠️"
        else:
            emoji = "❌"

        report += f"{emoji} {field_path}: {score:.2f} ({level})\n"

    return report


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("文本质量检测与置信度计算模块测试")
    print("=" * 60)

    # 测试文本
    test_text = """
    张三
    电话：13800138000
    邮箱：zhangsan@example.com

    教育背景
    清华大学 计算机科学与技术 本科 2018-2022

    工作经历
    ABC公司 软件工程师 2022-至今

    技能
    Python, Java, 机器学习
    """

    print("\n[TEST] 文本质量检测")
    quality_score, warnings = check_text_quality(test_text)
    print(format_quality_report(quality_score, warnings))

    print("\n[TEST] 置信度计算")
    test_profile = {
        "basic_info": {
            "name": "张三",
            "phone": "13800138000",
            "email": "zhangsan@example.com"
        },
        "education": [
            {
                "school": "清华大学",
                "major": "计算机科学与技术",
                "degree": "本科"
            }
        ]
    }

    confidence_result = calculate_profile_confidence(test_profile, test_text)
    print(format_confidence_report(confidence_result))

    print("\n" + "=" * 60)
