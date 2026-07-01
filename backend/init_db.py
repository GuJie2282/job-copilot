"""
数据库初始化脚本

快速创建数据库表，无需配置 Alembic
适用于开发环境和快速启动
"""

from src.models.base import Base, engine
from src.models.user import User, VerificationCode, RefreshToken


def init_database():
    """
    初始化所有数据库表
    """
    print("🔧 正在初始化数据库...")

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库初始化完成！")
        print("\n📊 已创建以下表：")
        print("   - users (用户表)")
        print("   - verification_codes (验证码表)")
        print("   - refresh_tokens (刷新令牌表)")
        print("\n💾 数据库文件位置:")
        print(f"   {engine.url}")
        print("\n🚀 现在可以启动后端服务：")
        print("   python src/main.py")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    init_database()
