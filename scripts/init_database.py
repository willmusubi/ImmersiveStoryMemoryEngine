"""
初始化数据库脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.database import init_database


async def main():
    """初始化数据库"""
    print("初始化数据库...")
    await init_database()
    print("✅ 数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())

