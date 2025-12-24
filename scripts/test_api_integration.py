"""
API 集成测试（使用 HTTP 请求）
"""
import asyncio
import httpx
import json
from pathlib import Path


async def test_api_integration():
    """测试 API 集成"""
    print("=" * 70)
    print("🌐 API 集成测试（HTTP 请求）")
    print("=" * 70)
    
    base_url = "http://localhost:8000"
    story_id = "sanguo_api_test"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # ==================== 测试 1: 获取状态 ====================
        print(f"\n{'='*70}")
        print("测试 1: GET /state/{story_id}")
        print(f"{'='*70}")
        
        try:
            response = await client.get(f"{base_url}/state/{story_id}")
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 成功获取状态")
                print(f"   - Story ID: {data['meta']['story_id']}")
                print(f"   - Turn: {data['meta']['turn']}")
                print(f"   - 玩家位置: {data['player']['location_id']}")
            else:
                print(f"   ❌ 错误: {response.text}")
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return
        
        # ==================== 测试 2: 处理草稿 ====================
        print(f"\n{'='*70}")
        print("测试 2: POST /draft/process")
        print(f"{'='*70}")
        
        test_cases = [
            {
                "name": "简单对话",
                "user_message": "玩家向曹操打招呼",
                "assistant_draft": "玩家向曹操打招呼，曹操点头回应。",
            },
            {
                "name": "物品获得",
                "user_message": "玩家在地上发现了一把剑",
                "assistant_draft": "玩家在地上发现了一把青釭剑，将其拾起放入背包。",
            },
            {
                "name": "角色移动",
                "user_message": "玩家决定前往许昌",
                "assistant_draft": "玩家离开洛阳，经过长途跋涉，终于到达了许昌。",
            },
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   📋 测试用例 {i}: {test_case['name']}")
            print(f"   用户消息: {test_case['user_message']}")
            print(f"   助手草稿: {test_case['assistant_draft']}")
            
            try:
                response = await client.post(
                    f"{base_url}/draft/process",
                    json={
                        "story_id": story_id,
                        "user_message": test_case["user_message"],
                        "assistant_draft": test_case["assistant_draft"],
                    },
                    timeout=60.0,  # 给 LLM 调用更多时间
                )
                
                print(f"   状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ 处理成功")
                    print(f"   - 最终动作: {data['final_action']}")
                    
                    if data.get("state"):
                        print(f"   - 新 Turn: {data['state']['meta']['turn']}")
                        print(f"   - 玩家位置: {data['state']['player']['location_id']}")
                        if data['state']['player']['inventory']:
                            print(f"   - 玩家库存: {data['state']['player']['inventory']}")
                    
                    if data.get("recent_events"):
                        print(f"   - 最近事件: {len(data['recent_events'])} 个")
                        for event in data['recent_events'][:3]:
                            print(f"     * [{event['type']}] {event['summary']}")
                    
                    if data.get("questions"):
                        print(f"   - 需要澄清: {len(data['questions'])} 个问题")
                        for q in data['questions']:
                            print(f"     * {q}")
                    
                    if data.get("rewrite_instructions"):
                        print(f"   - 重写指令: {data['rewrite_instructions'][:100]}...")
                    
                    if data.get("violations"):
                        print(f"   - 违反规则: {len(data['violations'])} 个")
                        for v in data['violations'][:3]:
                            print(f"     * {v.get('rule_id', 'Unknown')}: {v.get('message', '')[:50]}...")
                else:
                    print(f"   ❌ 错误: {response.status_code}")
                    print(f"   {response.text[:200]}")
                    
            except httpx.TimeoutException:
                print(f"   ⚠️  请求超时（LLM 调用可能需要更长时间）")
            except Exception as e:
                print(f"   ❌ 请求失败: {e}")
        
        # ==================== 测试 3: RAG 查询 ====================
        print(f"\n{'='*70}")
        print("测试 3: POST /rag/query")
        print(f"{'='*70}")
        
        try:
            response = await client.post(
                f"{base_url}/rag/query",
                json={
                    "story_id": story_id,
                    "query": "曹操的武器是什么？",
                    "top_k": 5,
                },
            )
            
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 查询成功")
                print(f"   - 查询: {data['query']}")
                print(f"   - 结果数量: {len(data['results'])}")
            else:
                print(f"   ❌ 错误: {response.text}")
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
        
        # ==================== 测试 4: 查看最终状态 ====================
        print(f"\n{'='*70}")
        print("测试 4: 查看最终状态")
        print(f"{'='*70}")
        
        try:
            response = await client.get(f"{base_url}/state/{story_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 最终状态:")
                print(f"   - Turn: {data['meta']['turn']}")
                print(f"   - 最后事件: {data['meta']['last_event_id']}")
                print(f"   - 玩家位置: {data['player']['location_id']}")
                print(f"   - 玩家库存: {data['player']['inventory']}")
                print(f"   - 角色数量: {len(data['entities']['characters'])}")
                print(f"   - 物品数量: {len(data['entities']['items'])}")
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
        
        # ==================== 总结 ====================
        print(f"\n{'='*70}")
        print("✅ API 集成测试完成！")
        print(f"{'='*70}")
        print(f"\n💡 提示:")
        print(f"   - 访问 http://localhost:8000/ 查看测试页面")
        print(f"   - 访问 http://localhost:8000/docs 查看 Swagger UI")


if __name__ == "__main__":
    print("\n⚠️  请确保 API 服务器正在运行:")
    print("   python run_server.py")
    print("\n等待 3 秒后开始测试...\n")
    
    import time
    time.sleep(3)
    
    asyncio.run(test_api_integration())

