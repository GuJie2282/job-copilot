"""
简历主题包

每个主题是一个模块（提供 STYLE + 组件渲染函数），登记在 THEMES。
新增主题：在本目录加 theme_xxx.py（提供 STYLE + render_* 函数），在此登记。

主题选择（select_theme）：按目标岗位推荐契合主题，无明确倾向用默认。
MVP 只实现 tech-dense 一套，其余岗位暂默认 tech-dense（规则结构已就位，后续加主题扩展）。

作者：求职 Copilot 项目
日期：2026-07-22
"""

from . import tech_dense

# 主题登记表：theme_id → 主题模块
THEMES = {
    "tech_dense": tech_dense,
}

# 默认主题（岗位无明确倾向时用）
DEFAULT_THEME = "tech_dense"

# 岗位关键词 → 主题（后续加主题时扩展；MVP 全归 tech_dense）
_THEME_RULES = [
    ("tech_dense", ["技术", "算法", "后端", "前端", "工程", "开发", "数据", "ai",
                    "软件", "架构", "运维", "测试", "产品", "运营"]),
]


def select_theme(target_position: str) -> str:
    """
    按目标岗位推荐主题。

    Args:
        target_position: 目标岗位
    Returns:
        theme_id（MVP 均返回 tech_dense；规则结构为后续多主题预留）
    """
    pos = (target_position or "").lower()
    for theme_id, keywords in _THEME_RULES:
        if any(k in pos for k in keywords):
            return theme_id if theme_id in THEMES else DEFAULT_THEME
    return DEFAULT_THEME


def get_theme(theme_id: str):
    """按 id 取主题模块；未知 id 回退默认主题。"""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])
