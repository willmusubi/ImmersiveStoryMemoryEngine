#!/usr/bin/env python3
"""
测试优化后的提示词
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.extractor import EventExtractor
from backend.models import (
    CanonicalState,
    MetaInfo,
    TimeState,
    TimeAnchor,
    PlayerState,
    Entities,
    Location,
    Character,
    Item,
    QuestState,
    Constraints,
)


async def test_optimized_prompt():
    """测试优化后的提示词"""
    print("=" * 60)
    print("测试优化后的提示词")
    print("=" * 60)
    
    # 创建测试状态
    state = CanonicalState(
        meta=MetaInfo(story_id="test_story", turn=1),
        time=TimeState(
            calendar="建安三年春",
            anchor=TimeAnchor(label="建安三年春", order=10)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang"
        ),
        entities=Entities(
            locations={
                "luoyang": Location(id="luoyang", name="洛阳"),
                "xuchang": Location(id="xuchang", name="许昌"),
            },
            characters={
                "caocao": Character(
                    id="caocao",
                    name="曹操",
                    location_id="luoyang",
                    alive=True
                ),
            },
            items={
                "sword_001": Item(
                    id="sword_001",
                    name="青釭剑",
                    owner_id="caocao",
                    location_id="luoyang",
                    unique=True
                ),
            }
        ),
        quest=QuestState(),
        constraints=Constraints(unique_item_ids=["sword_001"])
    )
    
    # 创建提取器
    extractor = EventExtractor()
    
    # 测试场景 1: 物品所有权变更
    print("\n" + "=" * 60)
    print("场景 1: 物品所有权变更")
    print("=" * 60)
    
    user_message = "请将青釭剑借给我"
    assistant_draft = "曹操点了点头，将青釭剑递给玩家，说道：'这把剑就借给你了，希望你能善用它。'"
    
    print(f"\n用户消息: {user_message}")
    print(f"助手草稿: {assistant_draft}")
    
    try:
        result = await extractor.extract_events(
            canonical_state=state,
            user_message=user_message,
            assistant_draft=assistant_draft,
            turn=2
        )
        
        print(f"\n✅ 提取成功！")
        print(f"事件数量: {len(result.events)}")
        print(f"需要用户输入: {result.requires_user_input}")
        if result.open_questions:
            print(f"开放问题: {result.open_questions}")
        
        for i, event in enumerate(result.events, 1):
            print(f"\n事件 {i}:")
            print(f"  类型: {event.type}")
            print(f"  摘要: {event.summary}")
            print(f"  状态补丁: {len(event.state_patch.entity_updates)} 个实体更新")
            if event.state_patch.entity_updates:
                for entity_id, update in event.state_patch.entity_updates.items():
                    print(f"    - {entity_id}: {update.updates}")
            if event.state_patch.player_updates:
                print(f"  玩家更新: {event.state_patch.player_updates}")
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试场景 2: 角色移动
    print("\n" + "=" * 60)
    print("场景 2: 角色移动")
    print("=" * 60)
    
    user_message = "我想去许昌"
    assistant_draft = "玩家离开洛阳，经过长途跋涉，终于到达了许昌。"
    
    print(f"\n用户消息: {user_message}")
    print(f"助手草稿: {assistant_draft}")
    
    try:
        result = await extractor.extract_events(
            canonical_state=state,
            user_message=user_message,
            assistant_draft=assistant_draft,
            turn=3
        )
        
        print(f"\n✅ 提取成功！")
        print(f"事件数量: {len(result.events)}")
        print(f"需要用户输入: {result.requires_user_input}")
        if result.open_questions:
            print(f"开放问题: {result.open_questions}")
        
        for i, event in enumerate(result.events, 1):
            print(f"\n事件 {i}:")
            print(f"  类型: {event.type}")
            print(f"  摘要: {event.summary}")
            print(f"  状态补丁: {len(event.state_patch.entity_updates)} 个实体更新")
            if event.state_patch.entity_updates:
                for entity_id, update in event.state_patch.entity_updates.items():
                    print(f"    - {entity_id}: {update.updates}")
            if event.state_patch.player_updates:
                print(f"  玩家更新: {event.state_patch.player_updates}")
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_optimized_prompt())

