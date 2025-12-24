"""
实际测试 Event Extractor 功能（使用真实 LLM）
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.extractor import EventExtractor
from backend.models import (
    CanonicalState,
    MetaInfo,
    TimeState,
    TimeAnchor,
    PlayerState,
    Entities,
    Character,
    Location,
    QuestState,
    Constraints,
)


def create_test_state():
    """创建测试用的 CanonicalState"""
    # 创建地点
    luoyang = Location(id="luoyang", name="洛阳")
    xuchang = Location(id="xuchang", name="许昌")
    
    # 创建角色
    caocao = Character(
        id="caocao",
        name="曹操",
        location_id="luoyang",
        alive=True,
    )
    
    liubei = Character(
        id="liubei",
        name="刘备",
        location_id="xuchang",
        alive=True,
    )
    
    # 创建状态
    state = CanonicalState(
        meta=MetaInfo(story_id="sanguo_test", turn=0),
        time=TimeState(
            calendar="建安三年春",
            anchor=TimeAnchor(label="建安三年春", order=10)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang",
            inventory=[],
            party=[],
        ),
        entities=Entities(
            characters={"caocao": caocao, "liubei": liubei},
            items={},
            locations={"luoyang": luoyang, "xuchang": xuchang},
        ),
        quest=QuestState(),
        constraints=Constraints(),
    )
    
    return state


async def test_extractor():
    """测试 Event Extractor"""
    print("=" * 60)
    print("Event Extractor 实际功能测试")
    print("=" * 60)
    
    # 初始化 Extractor
    try:
        extractor = EventExtractor()
        print(f"\n✅ EventExtractor 初始化成功")
        print(f"   Model: {extractor.model}")
        print(f"   Base URL: {extractor.base_url}")
    except Exception as e:
        print(f"\n❌ EventExtractor 初始化失败: {e}")
        return
    
    # 创建测试状态
    state = create_test_state()
    print(f"\n📋 测试状态:")
    print(f"   Story ID: {state.meta.story_id}")
    print(f"   Turn: {state.meta.turn}")
    print(f"   时间: {state.time.calendar}")
    print(f"   玩家位置: {state.player.location_id}")
    print(f"   角色: {', '.join([c.name for c in state.entities.characters.values()])}")
    
    # 测试场景 1: 简单的对话
    print(f"\n" + "-" * 60)
    print("测试场景 1: 玩家与曹操对话")
    print("-" * 60)
    
    user_message = "玩家向曹操打招呼"
    assistant_draft = "玩家向曹操打招呼，曹操点头回应，说道：'欢迎来到洛阳。'"
    
    print(f"\n用户消息: {user_message}")
    print(f"助手草稿: {assistant_draft}")
    print(f"\n正在调用 LLM 提取事件...")
    
    try:
        result = await extractor.extract_events(
            canonical_state=state,
            user_message=user_message,
            assistant_draft=assistant_draft,
            turn=1,
        )
        
        print(f"\n✅ 提取成功!")
        print(f"   需要用户输入: {result.requires_user_input}")
        print(f"   提取到 {len(result.events)} 个事件")
        
        if result.open_questions:
            print(f"   澄清问题: {len(result.open_questions)} 个")
            for q in result.open_questions:
                print(f"     - {q}")
        
        for i, event in enumerate(result.events, 1):
            print(f"\n   事件 {i}:")
            print(f"     ID: {event.event_id}")
            print(f"     类型: {event.type}")
            print(f"     摘要: {event.summary}")
            print(f"     轮次: {event.turn}")
            print(f"     时间: {event.time.label} (order: {event.time.order})")
            print(f"     地点: {event.where.location_id}")
            print(f"     参与者: {', '.join(event.who.actors)}")
            print(f"     状态补丁: {len(event.state_patch.entity_updates)} 个实体更新")
            
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试场景 2: 包含状态变化的事件
    print(f"\n" + "-" * 60)
    print("测试场景 2: 玩家获得物品")
    print("-" * 60)
    
    user_message = "玩家在地上发现了一把剑"
    assistant_draft = "玩家在地上发现了一把青釭剑，将其拾起放入背包。"
    
    print(f"\n用户消息: {user_message}")
    print(f"助手草稿: {assistant_draft}")
    print(f"\n正在调用 LLM 提取事件...")
    
    try:
        result = await extractor.extract_events(
            canonical_state=state,
            user_message=user_message,
            assistant_draft=assistant_draft,
            turn=2,
        )
        
        print(f"\n✅ 提取成功!")
        print(f"   需要用户输入: {result.requires_user_input}")
        print(f"   提取到 {len(result.events)} 个事件")
        
        if result.open_questions:
            print(f"   澄清问题: {len(result.open_questions)} 个")
            for q in result.open_questions:
                print(f"     - {q}")
        
        for i, event in enumerate(result.events, 1):
            print(f"\n   事件 {i}:")
            print(f"     ID: {event.event_id}")
            print(f"     类型: {event.type}")
            print(f"     摘要: {event.summary}")
            print(f"     状态补丁:")
            if event.state_patch.entity_updates:
                for entity_id, update in event.state_patch.entity_updates.items():
                    print(f"       - {update.entity_type} {entity_id}: {update.updates}")
            if event.state_patch.player_updates:
                print(f"       - player: {event.state_patch.player_updates}")
            
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试场景 3: 角色移动
    print(f"\n" + "-" * 60)
    print("测试场景 3: 角色移动")
    print("-" * 60)
    
    user_message = "玩家决定前往许昌"
    assistant_draft = "玩家离开洛阳，经过长途跋涉，终于到达了许昌。"
    
    print(f"\n用户消息: {user_message}")
    print(f"助手草稿: {assistant_draft}")
    print(f"\n正在调用 LLM 提取事件...")
    
    try:
        result = await extractor.extract_events(
            canonical_state=state,
            user_message=user_message,
            assistant_draft=assistant_draft,
            turn=3,
        )
        
        print(f"\n✅ 提取成功!")
        print(f"   需要用户输入: {result.requires_user_input}")
        print(f"   提取到 {len(result.events)} 个事件")
        
        if result.open_questions:
            print(f"   澄清问题: {len(result.open_questions)} 个")
            for q in result.open_questions:
                print(f"     - {q}")
        
        for i, event in enumerate(result.events, 1):
            print(f"\n   事件 {i}:")
            print(f"     ID: {event.event_id}")
            print(f"     类型: {event.type}")
            print(f"     摘要: {event.summary}")
            print(f"     状态补丁:")
            if event.state_patch.entity_updates:
                for entity_id, update in event.state_patch.entity_updates.items():
                    print(f"       - {update.entity_type} {entity_id}: {update.updates}")
            if event.state_patch.player_updates:
                print(f"       - player: {event.state_patch.player_updates}")
            
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n" + "=" * 60)
    print("✅ 所有测试场景完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_extractor())

