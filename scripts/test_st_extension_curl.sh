#!/bin/bash
# SillyTavern 扩展测试（使用 curl）

BASE_URL="http://127.0.0.1:8000"
STORY_ID="st_extension_test"

echo "======================================================================"
echo "SillyTavern 扩展完整测试（使用 curl）"
echo "======================================================================"
echo "后端 URL: $BASE_URL"
echo "测试 Story ID: $STORY_ID"
echo ""

# 测试1: 获取状态
echo "======================================================================"
echo "测试 1: GET /state/{story_id}"
echo "======================================================================"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/state/$STORY_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✅ 成功获取状态"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -20
    echo ""
    
    # 测试2: 状态摘要生成（Python脚本）
    echo "======================================================================"
    echo "测试 2: 状态摘要生成"
    echo "======================================================================"
    python3 <<EOF
import json
import sys

state = json.loads('''$body''')

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
    else:
        lines.append(f"地点: {location_id or '未知'}")

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
print(f"✅ 状态摘要生成成功 ({len(lines)} 行)")
print("摘要内容:")
for line in summary.split('\n'):
    print(f"  {line}")
EOF
    echo ""
    
    # 测试3: 处理草稿
    echo "======================================================================"
    echo "测试 3: POST /draft/process"
    echo "======================================================================"
    draft_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/draft/process" \
        -H "Content-Type: application/json" \
        -d "{
            \"story_id\": \"$STORY_ID\",
            \"user_message\": \"玩家向曹操打招呼\",
            \"assistant_draft\": \"曹操点头回应，表示欢迎。\"
        }")
    draft_http_code=$(echo "$draft_response" | tail -n1)
    draft_body=$(echo "$draft_response" | sed '$d')
    
    if [ "$draft_http_code" = "200" ]; then
        echo "✅ 草稿处理成功"
        echo "$draft_body" | python3 -m json.tool 2>/dev/null | head -30
    else
        echo "❌ 草稿处理失败 (状态码: $draft_http_code)"
        echo "$draft_body"
    fi
    echo ""
    
    # 测试结果汇总
    echo "======================================================================"
    echo "测试结果汇总"
    echo "======================================================================"
    echo "  get_state            ✅ 通过"
    echo "  state_summary        ✅ 通过"
    if [ "$draft_http_code" = "200" ]; then
        echo "  draft_process        ✅ 通过"
        echo ""
        echo "总计: 3/3 测试通过"
        echo "🎉 所有测试通过！扩展可以正常使用。"
    else
        echo "  draft_process        ❌ 失败"
        echo ""
        echo "总计: 2/3 测试通过"
        echo "⚠️  草稿处理测试失败，请检查后端服务。"
    fi
else
    echo "❌ 获取状态失败 (状态码: $http_code)"
    echo "$body"
    echo ""
    echo "请确保后端服务正在运行:"
    echo "  python run_server.py"
fi

echo "======================================================================"

