"""
敏感信息脱敏工具

提供各种敏感信息的脱敏函数，确保日志中不泄露敏感数据：
- mask_email: 脱敏邮箱
- mask_phone: 脱敏手机号
- mask_token: 脱敏Token
- mask_code: 脱敏验证码
- mask_password: 脱敏密码

作者：求职 Copilot 项目
创建时间：2025-01-01
"""


def mask_email(email: str) -> str:
    """脱敏邮箱：test@example.com → te**@example.com

    参数：
        email: 邮箱地址

    返回：
        str: 脱敏后的邮箱
    """
    if "@" not in email:
        return email
    username, domain = email.split("@", 1)
    if len(username) <= 2:
        return f"{username[0]}**@{domain}"
    return f"{username[:2]}**@{domain}"


def mask_phone(phone: str) -> str:
    """脱敏手机号：13812345678 → 138****5678

    参数：
        phone: 手机号

    返回：
        str: 脱敏后的手机号
    """
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def mask_token(token: str) -> str:
    """脱敏 Token：显示前8位和后4位

    参数：
        token: Token字符串

    返回：
        str: 脱敏后的Token
    """
    if len(token) < 12:
        return "***"
    return f"{token[:8]}...{token[-4:]}"


def mask_code(code: str) -> str:
    """脱敏验证码：123456 → 12****

    参数：
        code: 验证码

    返回：
        str: 脱敏后的验证码
    """
    if len(code) < 2:
        return "***"
    return f"{code[:2]}****"


def mask_password(password: str) -> str:
    """脱敏密码：完全隐藏

    参数：
        password: 密码

    返回：
        str: 脱敏后的密码（固定长度）
    """
    return "***"
