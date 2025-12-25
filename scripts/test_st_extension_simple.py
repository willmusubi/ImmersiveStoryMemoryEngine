#!/usr/bin/env python3
"""
SillyTavern 扩展简化测试（使用 urllib，不依赖 httpx）
"""
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


BASE_URL = "http://localhost:8000"
STORY_ID = "st_extension_test"


def make_request(url: str, method: str = "GET", data: Optional[Dict] = None, timeout: int = 30) -> tuple[int, Dict]:
    """发送HTTP请求"""
    try:
        if data:
            req_data = json.dumps(data).encode('utf-8')
            request = urllib.request.Request(
                url,
                data=req_data,
                headers={'Content-Type': 'application/json'},
                method=method
            )
        else:
            request = urllib.request.Request(url, method=method)
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            try:
                json_data = json.loads(body) if body else {}
            except:
                json_data = {}
            return status, json_data
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        try:
            json_data = json.loads(body) if body else {}
        except:
            json_data = {}
        return e.code, json_data
    except Exception as e:
        print(f"   请求失败: {e}")
        return 0, {}


def test_get_state() -> Optional[Dict]:
    """测试 GET /state/{story_id}"""
    print(f"\n{'='*70}")
    print("测试 GET /state/{story_id}")
    print(f"{'='*70}")
    
    url = f"{BASE_URL}/state/{STORY_ID}"
    status, data = make_request(url)
    
    if status == 200:
        print(f"   ✅ 成功获取状态")
        print(f"   - Story ID: {data.get('meta', {}).get('story_id', 'N/A')}")
        print(f"   - Turn: {data.get('meta', {}).get('turn', 'N/A')}")
        print(f"   - 玩家位置: {data.get('player', {}).get('location_id', 'N/A')}")
        return data
    else:
        print(f"   ❌ 获取状态失败 (状态码: {status})")
        return None


def test_state_summary(state: Dict) -> bool:
    """测试状态摘要生成"""
    print(f"\n{'='*70}")
    print("测试状态摘要生成")
    print(f"{'='*70}")
    
    try:
        lines = []
        lines.append("=== 故事状态摘要 ===")
        
        if state.get('time'):
            calendar = state['time'].get('calendar', '未知')
            lines.append(f"时间: {calendar}")
        
        if state.get('player') and state.get('entities'):
            location_id = state['player'].get('location_id')
            locations = state['entities'].get('locations', {})
            if location_id and location_id in locations:
                location_name = locations[location_id].get('name', location_id)
                lines.append(f"地点: {location_name}")
        
        if state.get('player') and state.get('entities'):
            party = state['player'].get('party', [])
            characters = state['entities'].get('characters', {})
            if party:
                party_names = [characters.get(cid, {}).get('name', cid) for cid in party]
                lines.append(f"队伍: {', '.join(party_names)}")
            else:
                lines.append("队伍: 无")
        
        if state.get('player') and state.get('entities'):
            inventory = state['player'].get('inventory', [])
            items = state['entities'].get('items', {})
            if inventory:
                item_names = [items.get(iid, {}).get('name', iid) for iid in inventory]
                lines.append(f"物品: {', '.join(item_names) if item_names else '无'}")
            else:
                lines.append("物品: 无")
        
        if state.get('quest'):
            active = state['quest'].get('active', [])
            completed = state['quest'].get('completed', [])
            if active:
                quest_titles = [q.get('title', '') for q in active]
                lines.append(f"进行中任务: {', '.join(quest_titles)}")
            if completed:
                lines.append(f"已完成任务: {len(completed)}个")
        
        if state.get('meta'):
            turn = state['meta'].get('turn', 0)
            lines.append(f"轮次: {turn}")
        
        lines.append("===================")
        
        summary = '\n'.join(lines)
        line_count = len(lines)
        
        print(f"   ✅ 状态摘要生成成功 ({line_count} 行)")
        print(f"   摘要预览:")
        for line in summary.split('\n')[:8]:
            print(f"      {line}")
        
        return True
    except Exception as e:
        print(f"   ❌ 状态摘要生成失败: {e}")
        return False


def test_draft_process() -> bool:
    """测试 POST /draft/process"""
    print(f"\n{'='*70}")
    print("测试 POST /draft/process")
    print(f"{'='*70}")
    
    url = f"{BASE_URL}/draft/process"
    data = {
        "story_id": STORY_ID,
        "user_message": "玩家向曹操打招呼",
        "assistant_draft": "曹操点头回应，表示欢迎。"
    }
    
    status, result = make_request(url, method="POST", data=data, timeout=60)
    
    if status == 200:
        final_action = result.get('final_action', '')
        print(f"   ✅ 草稿处理成功 (动作: {final_action})")
        
        if result.get('state'):
            print(f"   - 状态已更新")
        if result.get('recent_events'):
            print(f"   - 最近事件: {len(result['recent_events'])} 个")
        if result.get('rewrite_instructions'):
            print(f"   - 重写指令: {result['rewrite_instructions'][:100]}...")
        if result.get('questions'):
            print(f"   - 需要澄清: {len(result['questions'])} 个问题")
        
        return True
    else:
        print(f"   ❌ 草稿处理失败 (状态码: {status})")
        return False


def main():
    """主测试函数"""
    print("="*70)
    print("SillyTavern 扩展完整测试（简化版）")
    print("="*70)
    print(f"后端 URL: {BASE_URL}")
    print(f"测试 Story ID: {STORY_ID}")
    
    results = {
        'get_state': False,
        'state_summary': False,
        'draft_process': False,
    }
    
    # 测试1: 获取状态
    state = test_get_state()
    results['get_state'] = state is not None
    
    # 测试2: 状态摘要
    if state:
        results['state_summary'] = test_state_summary(state)
    
    # 测试3: 草稿处理
    results['draft_process'] = test_draft_process()
    
    # 汇总
    print(f"\n{'='*70}")
    print("测试结果汇总")
    print(f"{'='*70}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:20} {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试未通过")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

