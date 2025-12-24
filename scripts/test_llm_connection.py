"""
测试 LLM 连接
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.extractor import EventExtractor
from backend.config import settings


async def test_connection():
    """测试 LLM 连接"""
    print("=" * 50)
    print("测试 LLM 连接配置")
    print("=" * 50)
    
    # 检查配置
    print(f"\n📋 配置信息:")
    print(f"   API Key: {'✅ 已设置' if settings.super_mind_api_key else '❌ 未设置'}")
    print(f"   Base URL: {settings.openai_base_url}")
    print(f"   Model: {settings.openai_model}")
    
    if not settings.super_mind_api_key:
        print("\n❌ 错误: API Key 未设置，请检查 .env 文件")
        return
    
    # 初始化 Extractor
    try:
        extractor = EventExtractor()
        print(f"\n✅ EventExtractor 初始化成功")
        print(f"   Base URL: {extractor.base_url}")
        print(f"   Model: {extractor.model}")
    except Exception as e:
        print(f"\n❌ EventExtractor 初始化失败: {e}")
        return
    
    # 测试 API 连接（可选，会消耗配额）
    print(f"\n🔗 测试 API 连接...")
    print("   注意: 这将实际调用 API，会消耗配额")
    
    try:
        # 创建一个简单的测试请求
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=extractor.api_key,
            base_url=extractor.base_url,
        )
        
        response = await client.chat.completions.create(
            model=extractor.model,
            messages=[
                {"role": "user", "content": "请回复'连接成功'"}
            ],
            max_tokens=10,
        )
        
        content = response.choices[0].message.content
        print(f"   ✅ API 调用成功!")
        print(f"   响应: {content}")
        
    except Exception as e:
        print(f"   ❌ API 调用失败: {e}")
        print(f"   这可能是因为:")
        print(f"   - API Key 无效")
        print(f"   - Base URL 不正确")
        print(f"   - 网络连接问题")
        return
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过！LLM 连接正常")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_connection())

