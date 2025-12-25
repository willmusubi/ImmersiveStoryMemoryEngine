#!/bin/bash
# 快速测试死亡场景（使用curl，超时时间更长）

BASE_URL="http://127.0.0.1:8000"
STORY_ID="sanguo_test_baihua"

echo "======================================================================"
echo "角色死亡场景测试：袁绍被何进处死"
echo "======================================================================"
echo "后端 URL: $BASE_URL"
echo "Story ID: $STORY_ID"
echo ""

# 步骤1: 获取当前状态
echo "======================================================================"
echo "步骤 1: 获取当前状态"
echo "======================================================================"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/state/$STORY_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✅ 成功获取状态"
    characters=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('entities', {}).get('characters', {})))" 2>/dev/null)
    echo "   当前角色数量: $characters"
    echo ""
else
    echo "❌ 获取状态失败 (状态码: $http_code)"
    exit 1
fi

# 步骤2: 测试死亡场景
echo "======================================================================"
echo "步骤 2: 测试死亡场景 - 袁绍被何进处死"
echo "======================================================================"
echo "用户消息: 何进下令处死袁绍"
echo "助手草稿: 何进下令处死袁绍。士兵们将袁绍押到刑场，执行了死刑。袁绍倒在地上，再也没有起来。"
echo ""

draft_response=$(curl -s -w "\n%{http_code}" --max-time 120 -X POST "$BASE_URL/draft/process" \
    -H "Content-Type: application/json" \
    -d "{
        \"story_id\": \"$STORY_ID\",
        \"user_message\": \"何进下令处死袁绍\",
        \"assistant_draft\": \"何进下令处死袁绍。士兵们将袁绍押到刑场，执行了死刑。袁绍倒在地上，再也没有起来。\"
    }")

draft_http_code=$(echo "$draft_response" | tail -n1)
draft_body=$(echo "$draft_response" | sed '$d')

if [ "$draft_http_code" = "200" ]; then
    echo "✅ 草稿处理成功"
    
    # 解析结果
    final_action=$(echo "$draft_body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('final_action', 'N/A'))" 2>/dev/null)
    echo "   最终动作: $final_action"
    echo ""
    
    # 检查事件
    event_count=$(echo "$draft_body" | python3 -c "import sys, json; data=json.load(sys.stdin); events=data.get('recent_events', []); print(len(events))" 2>/dev/null)
    echo "   提取事件数: $event_count"
    
    # 检查是否有DEATH事件
    death_events=$(echo "$draft_body" | python3 -c "import sys, json; data=json.load(sys.stdin); events=data.get('recent_events', []); death=[e for e in events if e.get('type')=='DEATH']; print(len(death))" 2>/dev/null)
    if [ "$death_events" -gt 0 ]; then
        echo "   ✅ 检测到 $death_events 个死亡事件"
    else
        echo "   ⚠️  未检测到DEATH类型事件"
    fi
    echo ""
    
    # 显示事件详情
    echo "   事件列表:"
    echo "$draft_body" | python3 <<'PYTHON'
import sys
import json

data = json.load(sys.stdin)
events = data.get('recent_events', [])

for i, event in enumerate(events[:5], 1):
    event_type = event.get('type', 'UNKNOWN')
    summary = event.get('summary', 'N/A')
    actors = ', '.join(event.get('who', {}).get('actors', []))
    print(f"      {i}. [{event_type}] {summary}")
    print(f"         参与者: {actors}")
    if event_type == 'DEATH':
        char_id = event.get('payload', {}).get('character_id', 'N/A')
        print(f"         ✅ 死亡角色: {char_id}")
PYTHON
    echo ""
    
    # 检查状态更新
    yuanshao_alive=$(echo "$draft_body" | python3 -c "import sys, json; data=json.load(sys.stdin); state=data.get('state', {}); chars=state.get('entities', {}).get('characters', {}); yuanshao=chars.get('yuanshao', {}); print('False' if not yuanshao.get('alive', True) else 'True')" 2>/dev/null)
    
    if [ "$yuanshao_alive" = "False" ]; then
        echo "   ✅ 袁绍状态已更新为: 已死亡"
    elif [ "$yuanshao_alive" = "True" ]; then
        echo "   ⚠️  袁绍状态仍为: 存活"
    else
        echo "   ℹ️  袁绍角色不存在（可能需要在事件中创建）"
    fi
    
    # 检查是否需要澄清
    if [ "$final_action" = "ASK_USER" ]; then
        echo ""
        echo "   ℹ️  需要用户澄清:"
        echo "$draft_body" | python3 -c "import sys, json; data=json.load(sys.stdin); questions=data.get('questions', []); [print(f'      - {q}') for q in questions]" 2>/dev/null
    fi
    
    # 检查规则违反
    violations=$(echo "$draft_body" | python3 -c "import sys, json; data=json.load(sys.stdin); v=data.get('violations', []); print(len(v))" 2>/dev/null)
    if [ "$violations" -gt 0 ]; then
        echo ""
        echo "   ⚠️  检测到 $violations 个规则违反"
    else
        echo ""
        echo "   ✅ 无规则违反"
    fi
    
else
    echo "❌ 草稿处理失败 (状态码: $draft_http_code)"
    echo "$draft_body" | head -20
fi

echo ""
echo "======================================================================"
echo "测试完成"
echo "======================================================================"

