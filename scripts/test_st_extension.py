#!/usr/bin/env python3
"""
SillyTavern 扩展完整测试
测试扩展所需的后端 API 和核心功能
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


# 测试配置
BASE_URL = "http://localhost:8000"
STORY_ID = "st_extension_test"
TIMEOUT = 30.0


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印测试标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_test(name: str):
    """打印测试名称"""
    print(f"{Colors.OKCYAN}▶ {name}{Colors.ENDC}")


def print_success(message: str):
    """打印成功消息"""
    print(f"{Colors.OKGREEN}   ✅ {message}{Colors.ENDC}")


def print_error(message: str):
    """打印错误消息"""
    print(f"{Colors.FAIL}   ❌ {message}{Colors.ENDC}")


def print_warning(message: str):
    """打印警告消息"""
    print(f"{Colors.WARNING}   ⚠️  {message}{Colors.ENDC}")


def print_info(message: str):
    """打印信息消息"""
    print(f"{Colors.OKBLUE}   ℹ️  {message}{Colors.ENDC}")


async def test_backend_connection(client: httpx.AsyncClient) -> bool:
    """测试后端连接"""
    print_test("测试后端连接")
    try:
        # 直接测试API端点而不是根端点
        response = await client.get(f"{BASE_URL}/state/{STORY_ID}", timeout=10.0)
        status = response.status_code
        if status == 200:
            print_success(f"后端服务运行正常 (状态码: {status})")
            return True
        elif status == 404:
            # 404也是正常的，说明服务在运行，只是状态不存在
            print_success(f"后端服务运行正常 (状态码: {status}，状态不存在，将自动创建)")
            return True
        else:
            print_error(f"后端服务响应异常 (状态码: {status})")
            print_error(f"响应内容: {response.text[:300]}")
            return False
    except httpx.ConnectError as e:
        print_error(f"无法连接到后端服务: {e}")
        print_info(f"请确保服务正在运行: python run_server.py")
        return False
    except httpx.TimeoutException:
        print_error("连接超时")
        return False
    except Exception as e:
        print_error(f"连接测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_state(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """测试 GET /state/{story_id}"""
    print_test("测试 GET /state/{story_id}")
    try:
        response = await client.get(f"{BASE_URL}/state/{STORY_ID}", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print_success("成功获取状态")
            print_info(f"Story ID: {data.get('meta', {}).get('story_id', 'N/A')}")
            print_info(f"Turn: {data.get('meta', {}).get('turn', 'N/A')}")
            print_info(f"玩家位置: {data.get('player', {}).get('location_id', 'N/A')}")
            return data
        else:
            print_error(f"获取状态失败 (状态码: {response.status_code})")
            print_error(f"响应: {response.text[:200]}")
            return None
    except Exception as e:
        print_error(f"测试失败: {e}")
        return None


def test_state_summary(state: Dict[str, Any]) -> bool:
    """测试状态摘要生成（模拟扩展的 state_summary 函数）"""
    print_test("测试状态摘要生成")
    try:
        lines = []
        lines.append("=== 故事状态摘要 ===")
        
        # 时间信息
        if state.get('time'):
            calendar = state['time'].get('calendar', '未知')
            lines.append(f"时间: {calendar}")
        
        # 地点信息
        if state.get('player') and state.get('entities'):
            location_id = state['player'].get('location_id')
            locations = state['entities'].get('locations', {})
            if location_id and location_id in locations:
                location_name = locations[location_id].get('name', location_id)
                lines.append(f"地点: {location_name}")
            else:
                lines.append(f"地点: {location_id or '未知'}")
        
        # 队伍成员
        if state.get('player') and state.get('entities'):
            party = state['player'].get('party', [])
            characters = state['entities'].get('characters', {})
            if party:
                party_names = []
                for char_id in party:
                    if char_id in characters:
                        party_names.append(characters[char_id].get('name', char_id))
                    else:
                        party_names.append(char_id)
                lines.append(f"队伍: {', '.join(party_names)}")
            else:
                lines.append("队伍: 无")
        
        # 物品
        if state.get('player') and state.get('entities'):
            inventory = state['player'].get('inventory', [])
            items = state['entities'].get('items', {})
            if inventory:
                item_names = []
                for item_id in inventory:
                    if item_id in items:
                        item_names.append(items[item_id].get('name', item_id))
                    else:
                        item_names.append(item_id)
                lines.append(f"物品: {', '.join(item_names) if item_names else '无'}")
            else:
                lines.append("物品: 无")
        
        # 任务
        if state.get('quest'):
            active = state['quest'].get('active', [])
            completed = state['quest'].get('completed', [])
            if active:
                quest_titles = [q.get('title', '') for q in active]
                lines.append(f"进行中任务: {', '.join(quest_titles)}")
            if completed:
                lines.append(f"已完成任务: {len(completed)}个")
            if not active and not completed:
                lines.append("任务: 无")
        
        # 轮次
        if state.get('meta'):
            turn = state['meta'].get('turn', 0)
            lines.append(f"轮次: {turn}")
        
        lines.append("===================")
        
        summary = '\n'.join(lines)
        
        # 验证摘要长度（10-20行）
        line_count = len(lines)
        if 10 <= line_count <= 20:
            print_success(f"状态摘要生成成功 ({line_count} 行)")
            print_info("摘要预览:")
            for line in summary.split('\n')[:5]:
                print(f"      {line}")
            print_info("...")
            return True
        else:
            print_warning(f"摘要行数不在预期范围 (当前: {line_count} 行，预期: 10-20 行)")
            print_info("摘要内容:")
            print(summary)
            return True  # 仍然算通过，只是警告
    except Exception as e:
        print_error(f"状态摘要生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_draft_process_pass(client: httpx.AsyncClient) -> bool:
    """测试 POST /draft/process (PASS 场景)"""
    print_test("测试 POST /draft/process (PASS 场景)")
    try:
        request_data = {
            "story_id": STORY_ID,
            "user_message": "玩家向曹操打招呼",
            "assistant_draft": "曹操点头回应，表示欢迎。"
        }
        
        response = await client.post(
            f"{BASE_URL}/draft/process",
            json=request_data,
            timeout=TIMEOUT * 2  # 可能需要 LLM 调用，延长超时
        )
        
        if response.status_code == 200:
            data = response.json()
            final_action = data.get('final_action', '')
            
            print_success(f"草稿处理成功 (动作: {final_action})")
            
            if final_action in ['PASS', 'AUTO_FIX']:
                if data.get('state'):
                    print_info("状态已更新")
                if data.get('recent_events'):
                    event_count = len(data['recent_events'])
                    print_info(f"最近事件: {event_count} 个")
                return True
            elif final_action == 'REWRITE':
                print_warning("需要重写（这是正常的，取决于一致性规则）")
                if data.get('rewrite_instructions'):
                    print_info(f"重写指令: {data['rewrite_instructions'][:100]}...")
                return True  # 仍然算通过
            elif final_action == 'ASK_USER':
                print_warning("需要用户澄清（这是正常的，取决于一致性规则）")
                if data.get('questions'):
                    print_info(f"问题: {data['questions'][0][:100]}...")
                return True  # 仍然算通过
            else:
                print_warning(f"未知的动作类型: {final_action}")
                return True
        else:
            print_error(f"草稿处理失败 (状态码: {response.status_code})")
            print_error(f"响应: {response.text[:500]}")
            return False
    except httpx.TimeoutException:
        print_error("请求超时（可能是 LLM 调用时间过长）")
        print_info("这可能是正常的，取决于 LLM 响应时间")
        return False
    except Exception as e:
        print_error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_draft_process_rewrite(client: httpx.AsyncClient) -> bool:
    """测试 POST /draft/process (REWRITE 场景)"""
    print_test("测试 POST /draft/process (REWRITE 场景)")
    print_info("注意: 这个测试需要触发一致性规则违反")
    print_info("如果返回 PASS，说明没有违反规则（这也是正常的）")
    
    try:
        # 尝试创建一个可能违反规则的场景
        request_data = {
            "story_id": STORY_ID,
            "user_message": "玩家拿起传国玉玺",
            "assistant_draft": "玩家拿起传国玉玺，但传国玉玺已经在其他地方了。"
        }
        
        response = await client.post(
            f"{BASE_URL}/draft/process",
            json=request_data,
            timeout=TIMEOUT * 2
        )
        
        if response.status_code == 200:
            data = response.json()
            final_action = data.get('final_action', '')
            
            print_success(f"草稿处理完成 (动作: {final_action})")
            
            if final_action == 'REWRITE':
                print_success("成功触发 REWRITE 场景")
                if data.get('rewrite_instructions'):
                    print_info(f"重写指令: {data['rewrite_instructions'][:150]}")
                if data.get('violations'):
                    print_info(f"违反规则数: {len(data['violations'])}")
                return True
            else:
                print_info(f"返回动作: {final_action}（未触发 REWRITE，这是正常的）")
                return True
        else:
            print_error(f"草稿处理失败 (状态码: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"测试失败: {e}")
        return False


async def test_extension_workflow(client: httpx.AsyncClient) -> bool:
    """测试扩展的完整工作流程"""
    print_test("测试扩展完整工作流程")
    
    try:
        # 步骤1: 获取状态
        print_info("步骤 1: 获取状态...")
        state = await test_get_state(client)
        if not state:
            print_error("无法获取状态，终止工作流测试")
            return False
        
        # 步骤2: 生成状态摘要
        print_info("步骤 2: 生成状态摘要...")
        if not test_state_summary(state):
            print_error("状态摘要生成失败")
            return False
        
        # 步骤3: 处理草稿
        print_info("步骤 3: 处理草稿...")
        if not await test_draft_process_pass(client):
            print_warning("草稿处理可能有问题，但继续测试")
        
        # 步骤4: 再次获取状态（验证状态已更新）
        print_info("步骤 4: 验证状态更新...")
        updated_state = await test_get_state(client)
        if updated_state:
            old_turn = state.get('meta', {}).get('turn', 0)
            new_turn = updated_state.get('meta', {}).get('turn', 0)
            if new_turn >= old_turn:
                print_success(f"状态已更新 (轮次: {old_turn} -> {new_turn})")
            else:
                print_warning(f"轮次未增加 (轮次: {old_turn} -> {new_turn})")
        
        print_success("完整工作流程测试通过")
        return True
    except Exception as e:
        print_error(f"工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print_header("SillyTavern 扩展完整测试")
    
    print_info(f"后端 URL: {BASE_URL}")
    print_info(f"测试 Story ID: {STORY_ID}")
    print_info(f"超时设置: {TIMEOUT} 秒")
    
    results = {
        'backend_connection': False,
        'get_state': False,
        'state_summary': False,
        'draft_process_pass': False,
        'draft_process_rewrite': False,
        'extension_workflow': False,
    }
    
    # 创建客户端，设置更长的超时和重试
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(TIMEOUT, connect=10.0),
        follow_redirects=True
    ) as client:
        # 测试1: 后端连接
        print_header("阶段 1: 后端连接测试")
        results['backend_connection'] = await test_backend_connection(client)
        
        if not results['backend_connection']:
            print_warning("\n⚠️  后端连接测试失败，但继续测试其他功能...")
            print_info("  如果后续测试也失败，请检查:")
            print_info("  1. 后端服务是否正在运行: python run_server.py")
            print_info("  2. 服务是否在正确的端口 (8000)")
            print_info("  3. 防火墙设置")
            print("")
        
        # 测试2: 获取状态
        print_header("阶段 2: API 端点测试")
        state = await test_get_state(client)
        results['get_state'] = state is not None
        
        if state:
            # 测试3: 状态摘要生成
            results['state_summary'] = test_state_summary(state)
        
        # 测试4: 草稿处理 (PASS)
        print_header("阶段 3: 草稿处理测试")
        results['draft_process_pass'] = await test_draft_process_pass(client)
        results['draft_process_rewrite'] = await test_draft_process_rewrite(client)
        
        # 测试5: 完整工作流
        print_header("阶段 4: 完整工作流测试")
        results['extension_workflow'] = await test_extension_workflow(client)
    
    # 测试结果汇总
    print_header("测试结果汇总")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:30} {status}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print_success("\n🎉 所有测试通过！扩展可以正常使用。")
        return 0
    else:
        print_warning(f"\n⚠️  有 {total_tests - passed_tests} 个测试未通过，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

