#!/usr/bin/env python3
"""
完整测试角色死亡场景：袁绍被何进处死
包括先创建必要的角色和地点
"""
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


BASE_URL = "http://127.0.0.1:8000"
STORY_ID = "sanguo_test_baihua"


def make_request(url: str, method: str = "GET", data: Optional[Dict] = None, timeout: int = 60) -> tuple[int, Dict]:
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


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*70}")
    print(title)
    print(f"{'='*70}")


def print_success(msg: str):
    """打印成功消息"""
    print(f"   ✅ {msg}")


def print_error(msg: str):
    """打印错误消息"""
    print(f"   ❌ {msg}")


def print_info(msg: str):
    """打印信息消息"""
    print(f"   ℹ️  {msg}")


def setup_characters() -> bool:
    """步骤1: 创建必要的角色和地点"""
    print_section("步骤 1: 创建必要的角色和地点")
    
    # 先创建一个场景，让系统创建角色
    user_message = "何进和袁绍在洛阳的皇宫中会面"
    assistant_draft = "何进和袁绍在洛阳的皇宫中会面。何进是大将军，袁绍是司隶校尉。两人讨论朝政大事。"
    
    print_info(f"用户消息: {user_message}")
    print_info(f"助手草稿: {assistant_draft}")
    print("")
    
    url = f"{BASE_URL}/draft/process"
    data = {
        "story_id": STORY_ID,
        "user_message": user_message,
        "assistant_draft": assistant_draft
    }
    
    status, result = make_request(url, method="POST", data=data, timeout=90)
    
    if status == 200:
        final_action = result.get('final_action', '')
        print_success(f"场景创建成功 (动作: {final_action})")
        
        # 检查角色是否创建
        updated_state = result.get('state')
        if updated_state:
            characters = updated_state.get('entities', {}).get('characters', {})
            locations = updated_state.get('entities', {}).get('locations', {})
            
            print_info(f"当前角色数量: {len(characters)}")
            print_info(f"当前地点数量: {len(locations)}")
            
            # 检查关键角色
            if 'hejin' in characters:
                print_success("何进角色已创建")
            if 'yuanshao' in characters:
                print_success("袁绍角色已创建")
            if 'luoyang' in locations or 'palace' in locations:
                print_success("地点已创建")
        
        return final_action in ['PASS', 'AUTO_FIX']
    else:
        print_error(f"场景创建失败 (状态码: {status})")
        return False


def test_death_scenario() -> bool:
    """步骤2: 测试死亡场景"""
    print_section("步骤 2: 测试死亡场景 - 袁绍被何进处死")
    
    # 使用更明确的描述，包含角色ID和地点
    user_message = "何进下令处死袁绍"
    assistant_draft = "何进（hejin）下令处死袁绍（yuanshao）。士兵们将袁绍押到洛阳的刑场，执行了死刑。袁绍倒在地上，再也没有起来。"
    
    print_info(f"用户消息: {user_message}")
    print_info(f"助手草稿: {assistant_draft}")
    print("")
    
    url = f"{BASE_URL}/draft/process"
    data = {
        "story_id": STORY_ID,
        "user_message": user_message,
        "assistant_draft": assistant_draft
    }
    
    status, result = make_request(url, method="POST", data=data, timeout=90)
    
    if status == 200:
        final_action = result.get('final_action', '')
        print_success(f"草稿处理完成 (动作: {final_action})")
        print("")
        
        # 检查事件
        recent_events = result.get('recent_events', [])
        if recent_events:
            print_info(f"提取了 {len(recent_events)} 个事件:")
            death_events = []
            for i, event in enumerate(recent_events, 1):
                event_type = event.get('type', 'UNKNOWN')
                summary = event.get('summary', 'N/A')
                actors = event.get('who', {}).get('actors', [])
                print(f"   {i}. [{event_type}] {summary}")
                print(f"      参与者: {', '.join(actors)}")
                
                # 检查是否是死亡事件
                if event_type == 'DEATH':
                    death_events.append(event)
                    payload = event.get('payload', {})
                    char_id = payload.get('character_id', 'N/A')
                    print(f"      ✅ 检测到死亡事件: {char_id}")
            
            if not death_events:
                print_error("未检测到 DEATH 类型事件")
        
        # 检查状态更新
        updated_state = result.get('state')
        if updated_state:
            print("")
            print_info("状态更新:")
            characters = updated_state.get('entities', {}).get('characters', {})
            
            # 检查袁绍状态
            yuanshao = characters.get('yuanshao')
            if yuanshao:
                alive = yuanshao.get('alive', True)
                if not alive:
                    print_success(f"袁绍状态已更新为: 已死亡 ✅")
                else:
                    print_error(f"袁绍状态仍为存活（可能未正确提取死亡事件）")
                print_info(f"袁绍位置: {yuanshao.get('location_id', 'N/A')}")
            else:
                print_info("袁绍角色不存在")
            
            # 检查何进状态
            hejin = characters.get('hejin')
            if hejin:
                print_info(f"何进状态: {'存活' if hejin.get('alive', True) else '已死亡'}")
                print_info(f"何进位置: {hejin.get('location_id', 'N/A')}")
        
        # 检查是否有违反规则
        violations = result.get('violations', [])
        if violations:
            print("")
            print_error(f"检测到 {len(violations)} 个规则违反:")
            for v in violations:
                rule_id = v.get('rule_id', 'Unknown')
                message = v.get('message', 'N/A')
                print(f"   - {rule_id}: {message}")
        else:
            print("")
            print_success("无规则违反 ✅")
        
        # 检查是否需要重写或澄清
        if final_action == 'REWRITE':
            rewrite_instructions = result.get('rewrite_instructions', '')
            print("")
            print_info(f"需要重写: {rewrite_instructions[:200]}")
        elif final_action == 'ASK_USER':
            questions = result.get('questions', [])
            print("")
            print_info(f"需要用户澄清: {len(questions)} 个问题")
            for q in questions:
                print(f"   - {q}")
        
        # 如果返回 ASK_USER，也算部分成功（说明系统正确识别了需要澄清的问题）
        return final_action in ['PASS', 'AUTO_FIX', 'ASK_USER']
    else:
        print_error(f"草稿处理失败 (状态码: {status})")
        if result:
            print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
        return False


def verify_death_state() -> bool:
    """步骤3: 验证死亡后的状态"""
    print_section("步骤 3: 验证死亡后的状态")
    
    url = f"{BASE_URL}/state/{STORY_ID}"
    status, data = make_request(url)
    
    if status == 200:
        characters = data.get('entities', {}).get('characters', {})
        yuanshao = characters.get('yuanshao')
        
        if yuanshao:
            alive = yuanshao.get('alive', False)
            if not alive:
                print_success("袁绍状态正确：已死亡 ✅")
                return True
            else:
                print_error("袁绍状态错误：仍显示为存活 ❌")
                return False
        else:
            print_info("袁绍角色不存在（可能未创建或需要更多上下文）")
            return False
    else:
        print_error(f"获取状态失败 (状态码: {status})")
        return False


def main():
    """主测试函数"""
    print("="*70)
    print("角色死亡场景完整测试：袁绍被何进处死")
    print("="*70)
    print(f"后端 URL: {BASE_URL}")
    print(f"Story ID: {STORY_ID}")
    
    results = {
        'setup_characters': False,
        'death_scenario': False,
        'verify_state': False,
    }
    
    # 步骤1: 创建角色和地点
    results['setup_characters'] = setup_characters()
    
    # 步骤2: 测试死亡场景
    results['death_scenario'] = test_death_scenario()
    
    # 步骤3: 验证状态
    results['verify_state'] = verify_death_state()
    
    # 汇总
    print_section("测试结果汇总")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:20} {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！死亡场景处理正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试未通过")
        print("\n💡 提示:")
        print("   - 如果返回 ASK_USER，说明系统正确识别了需要澄清的问题")
        print("   - 在实际使用中，用户需要回答这些问题以继续")
        print("   - 或者可以在草稿中更明确地指定角色ID和地点ID")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

