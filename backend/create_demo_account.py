"""
创建/重置「公网演示账号」脚本

为什么需要它：
    本项目的注册流程要求邮箱验证码，而开发环境（ENV=development）的验证码只打印在
    后端控制台（见 src/services/code_service.py）。把项目通过隧道暴露到公网给别人试用时，
    对方看不到你本机的控制台，也就没法自己完成注册。

    所以这里直接绕过验证码流程，在数据库里预置一个「已验证」的账号，
    你只要把网址 + 邮箱 + 密码一起发给对方即可。

用法（必须在 backend 目录下、用项目自己的虚拟环境运行）：
    python create_demo_account.py                         # 用默认邮箱，随机生成密码
    python create_demo_account.py --email me@x.com         # 指定邮箱
    python create_demo_account.py --password 'Abc12345'    # 指定密码
    python create_demo_account.py --delete                 # 删除该演示账号

注意：
    - 脚本可重复执行：账号已存在就重置密码，不会重复建。
    - 数据库文件位置与后端一致（backend/job_copilot.db），因为两边都以 backend 为工作目录。
"""

import argparse
import os
import secrets
import sys

# 让脚本能 `from src.xxx import ...`：把 backend 目录加进模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 读取 backend/.env —— 必须在导入 src.models 之前，因为 base.py 在导入时就读 DATABASE_URL
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.core.security import get_password_hash  # noqa: E402
from src.models.base import Base, SessionLocal, engine  # noqa: E402
from src.models.user import User  # noqa: E402

# 导入其余模型模块，确保 Base.metadata 认识所有表（create_all 才会把表建全）
from src.models import interview, knowledge, profile, resume  # noqa: E402,F401

DEFAULT_EMAIL = "demo@jobcopilot.com"
DEFAULT_NAME = "演示用户"


def main() -> int:
    parser = argparse.ArgumentParser(description="创建/重置公网演示账号")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help=f"演示账号邮箱（默认 {DEFAULT_EMAIL}）")
    parser.add_argument("--password", default=None, help="密码（不传则随机生成并打印）")
    parser.add_argument("--name", default=DEFAULT_NAME, help="显示名")
    parser.add_argument("--delete", action="store_true", help="删除该账号而不是创建")
    args = parser.parse_args()

    email = args.email.strip().lower()

    # 建表（幂等：表已存在时什么都不做）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()

        if args.delete:
            if not existing:
                print(f"没有找到账号 {email}，无需删除")
                return 0
            db.delete(existing)
            db.commit()
            print(f"已删除账号 {email}")
            return 0

        # 生成密码：可读性优先，方便口头/微信转发给面试官
        password = args.password or f"JobCopilot@{secrets.randbelow(10**6):06d}"
        password_hash = get_password_hash(password)

        if existing:
            # 已存在 → 重置密码，并确保是「已验证 / 已激活」状态
            existing.password_hash = password_hash
            existing.is_verified = True
            existing.is_active = True
            action = "已重置"
        else:
            # 不存在 → 新建。is_verified=True 是为了跳过邮箱验证码那一步
            db.add(
                User(
                    name=args.name,
                    email=email,
                    password_hash=password_hash,
                    is_active=True,
                    is_verified=True,
                )
            )
            action = "已创建"

        db.commit()

        # commit 之后才取 ID：id 由模型上的 default 在 flush 时生成，提交前取到的是 None
        saved = db.query(User).filter(User.email == email).first()
        user_id = saved.id if saved else "（读取失败）"

        # 打印结果（这几行是给你复制去发给对方的）
        print()
        print("=" * 56)
        print(f"  演示账号{action}")
        print("=" * 56)
        print(f"  邮箱：{email}")
        print(f"  密码：{password}")
        print(f"  用户 ID：{user_id}")
        print("=" * 56)
        print("  把「隧道网址 + 上面这组邮箱密码」一起发给对方即可登录。")
        print("  想换密码：重跑本脚本并加 --password '新密码'")
        print("=" * 56)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
