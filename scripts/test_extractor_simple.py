"""
简单测试 Event Extractor（单个场景）
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
    luoyang = Location(id="luoyang", name="洛阳")
    caocao = Character(id="caocao", name="曹操", location_id="luoyang", alive=True)
    
    return CanonicalState(
        meta=MetaInfo(story_id="test", turn=0),
        time=TimeState(calendar="建安三年春", anchor=TimeAnchor(label="建安三年春", order=10)),
        player=PlayerState(id="player_001", name="玩家", location_id="luoyang", inventory=[], party=[]),
        entities=Entities(characters={"caocao": caocao}, items={}, locations={"luoyang": luoyang}),
        quest=QuestState(),
        constraints=Constraints(),
    )


async def test():
    """测试"""
    print("=" * 60)
    print("Event Extractor 简单测试")
    print("=" * 60)
    
    extractor = EventExtractor()
    state = create_test_state()
    
    user_message = "玩家向曹操打招呼"
    assistant_draft = "玩家向曹操打招呼，曹操点头回应。"
    
    print(f"\n用户消息: {user_message}")
    print(f"助手草稿: {assistant_draft}")
    print(f"\n正在调用 LLM...")
    
    try:
        result = await extractor.extract_events(
            canonical_state=state,
            user_message=user_message,
            assistant_draft=assistant_draft,
            turn=1,
        )
        
        print(f"\n✅ 提取成功!")
        print(f"   事件数量: {len(result.events)}")
        print(f"   需要用户输入: {result.requires_user_input}")
        
        if result.events:
            event = result.events[0]
            print(f"\n   事件详情:")
            print(f"     ID: {event.event_id}")
            print(f"     类型: {event.type}")
            print(f"     摘要: {event.summary}")
            print(f"     轮次: {event.turn}")
            print(f"     时间: {event.time.label} (order: {event.time.order})")
            print(f"     地点: {event.where.location_id}")
            print(f"     参与者: {', '.join(event.who.actors)}")
        
        if result.open_questions:
            print(f"\n   澄清问题:")
            for q in result.open_questions:
                print(f"     - {q}")
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())

