"""
简单测试数据模型
"""
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.models import (
    CanonicalState,
    MetaInfo,
    TimeState,
    TimeAnchor,
    PlayerState,
    Entities,
    Character,
    Item,
    Location,
    Faction,
    QuestState,
    Constraints,
    Event,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
    StatePatch,
    EntityUpdate,
)


def test_basic_state_creation():
    """测试基本状态创建"""
    print("=" * 60)
    print("测试 1: 创建基本 CanonicalState（需要先创建地点）")
    print("=" * 60)
    
    try:
        # 先创建地点，因为 player.location_id 需要引用它
        luoyang = Location(id="luoyang", name="洛阳")
        
        state = CanonicalState(
            meta=MetaInfo(
                story_id="sanguo_yanyi",
                canon_version="1.0.0",
                turn=0,
            ),
            time=TimeState(
                calendar="建安三年春",
                anchor=TimeAnchor(label="建安三年春", order=1)
            ),
            player=PlayerState(
                id="player_001",
                name="玩家",
                location_id="luoyang",
            ),
            entities=Entities(
                locations={"luoyang": luoyang}
            ),
            quest=QuestState(),
            constraints=Constraints(),
        )
        print("✅ 基本状态创建成功")
        print(f"   Story ID: {state.meta.story_id}")
        print(f"   Turn: {state.meta.turn}")
        print(f"   Player: {state.player.name} @ {state.player.location_id}")
        return state
    except Exception as e:
        print(f"❌ 失败: {e}")
        return None


def test_entities_creation():
    """测试实体创建"""
    print("\n" + "=" * 60)
    print("测试 2: 创建实体（人物、物品、地点）")
    print("=" * 60)
    
    try:
        # 创建地点
        luoyang = Location(id="luoyang", name="洛阳")
        xuchang = Location(id="xuchang", name="许昌")
        
        # 创建人物
        caocao = Character(
            id="caocao",
            name="曹操",
            location_id="luoyang",
            alive=True,
        )
        
        # 创建物品（非唯一）
        sword = Item(
            id="sword_001",
            name="青釭剑",
            owner_id="caocao",
            unique=False,
        )
        
        # 创建唯一物品
        seal = Item(
            id="seal_001",
            name="传国玉玺",
            owner_id="caocao",
            unique=True,
        )
        
        entities = Entities(
            characters={"caocao": caocao},
            items={"sword_001": sword, "seal_001": seal},
            locations={"luoyang": luoyang, "xuchang": xuchang},
        )
        
        print("✅ 实体创建成功")
        print(f"   人物: {len(entities.characters)} 个")
        print(f"   物品: {len(entities.items)} 个")
        print(f"   地点: {len(entities.locations)} 个")
        return entities
    except Exception as e:
        print(f"❌ 失败: {e}")
        return None


def test_unique_item_validation():
    """测试唯一物品校验"""
    print("\n" + "=" * 60)
    print("测试 3: 唯一物品必须指定 owner_id")
    print("=" * 60)
    
    # 测试失败情况
    try:
        item = Item(
            id="seal_001",
            name="传国玉玺",
            unique=True,
            # 缺少 owner_id
        )
        print("❌ 应该失败但没有失败！")
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    # 测试成功情况
    try:
        item = Item(
            id="seal_001",
            name="传国玉玺",
            owner_id="caocao",
            unique=True,
        )
        print("✅ 唯一物品指定 owner_id 后创建成功")
    except Exception as e:
        print(f"❌ 不应该失败: {e}")


def test_item_location_validation():
    """测试物品 location 校验"""
    print("\n" + "=" * 60)
    print("测试 4: 物品必须指定 owner_id 或 location_id")
    print("=" * 60)
    
    # 测试失败情况
    try:
        item = Item(
            id="item_001",
            name="普通物品",
            # 既没有 owner_id 也没有 location_id
        )
        print("❌ 应该失败但没有失败！")
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    # 测试成功情况（有 owner_id）
    try:
        item = Item(id="item_001", name="物品", owner_id="caocao")
        print("✅ 指定 owner_id 后创建成功")
    except Exception as e:
        print(f"❌ 不应该失败: {e}")
    
    # 测试成功情况（有 location_id）
    try:
        item = Item(id="item_002", name="物品", location_id="luoyang")
        print("✅ 指定 location_id 后创建成功")
    except Exception as e:
        print(f"❌ 不应该失败: {e}")


def test_complete_state_with_entities():
    """测试完整状态（包含实体和引用）"""
    print("\n" + "=" * 60)
    print("测试 5: 创建完整状态（包含实体和引用验证）")
    print("=" * 60)
    
    try:
        # 创建地点
        luoyang = Location(id="luoyang", name="洛阳")
        
        # 创建人物
        caocao = Character(
            id="caocao",
            name="曹操",
            location_id="luoyang",
            alive=True,
        )
        
        # 创建物品
        sword = Item(
            id="sword_001",
            name="青釭剑",
            owner_id="caocao",
            unique=False,
        )
        
        state = CanonicalState(
            meta=MetaInfo(story_id="sanguo_yanyi", turn=0),
            time=TimeState(
                calendar="建安三年春",
                anchor=TimeAnchor(label="建安三年春", order=1)
            ),
            player=PlayerState(
                id="player_001",
                name="玩家",
                location_id="luoyang",
                party=["caocao"],
                inventory=["sword_001"],
            ),
            entities=Entities(
                characters={"caocao": caocao},
                items={"sword_001": sword},
                locations={"luoyang": luoyang},
            ),
            quest=QuestState(),
            constraints=Constraints(),
        )
        
        print("✅ 完整状态创建成功（引用验证通过）")
        print(f"   玩家位置: {state.player.location_id}")
        print(f"   队伍成员: {state.player.party}")
        print(f"   物品列表: {state.player.inventory}")
        return state
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_event_creation():
    """测试事件创建"""
    print("\n" + "=" * 60)
    print("测试 6: 创建 Event")
    print("=" * 60)
    
    try:
        event = Event(
            event_id="evt_1_1234567890_abc123",
            turn=1,
            time=EventTime(label="建安三年春", order=1),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["player_001"], witnesses=["caocao"]),
            type="OWNERSHIP_CHANGE",
            summary="玩家获得了青釭剑",
            payload={
                "item_id": "sword_001",
                "old_owner_id": None,
                "new_owner_id": "player_001"
            },
            state_patch=StatePatch(
                entity_updates={
                    "sword_001": EntityUpdate(
                        entity_type="item",
                        entity_id="sword_001",
                        updates={"owner_id": "player_001"}
                    )
                }
            ),
            evidence=EventEvidence(
                source="draft_turn_1",
                text_span="玩家在洛阳城中发现了青釭剑"
            )
        )
        
        print("✅ 事件创建成功")
        print(f"   事件ID: {event.event_id}")
        print(f"   类型: {event.type}")
        print(f"   摘要: {event.summary}")
        print(f"   参与者: {event.who.actors}")
        return event
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_event_payload_validation():
    """测试事件 payload 校验"""
    print("\n" + "=" * 60)
    print("测试 7: 事件类型相关的 payload 验证")
    print("=" * 60)
    
    # 测试 OWNERSHIP_CHANGE 缺少字段
    try:
        event = Event(
            event_id="evt_1_1234567890_abc123",
            turn=1,
            time=EventTime(label="建安三年春", order=1),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["player_001"]),
            type="OWNERSHIP_CHANGE",
            summary="测试",
            payload={},  # 缺少必需字段
            state_patch=StatePatch(),
            evidence=EventEvidence(source="test"),
        )
        print("❌ 应该失败但没有失败！")
    except ValueError as e:
        print(f"✅ OWNERSHIP_CHANGE 正确捕获错误: {e}")
    
    # 测试 DEATH 缺少字段
    try:
        event = Event(
            event_id="evt_1_1234567890_abc123",
            turn=1,
            time=EventTime(label="建安三年春", order=1),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["player_001"]),
            type="DEATH",
            summary="测试",
            payload={},  # 缺少 character_id
            state_patch=StatePatch(),
            evidence=EventEvidence(source="test"),
        )
        print("❌ 应该失败但没有失败！")
    except ValueError as e:
        print(f"✅ DEATH 正确捕获错误: {e}")


def test_state_reference_validation():
    """测试状态引用验证"""
    print("\n" + "=" * 60)
    print("测试 8: 状态引用完整性验证")
    print("=" * 60)
    
    # 测试玩家 location_id 不存在
    try:
        state = CanonicalState(
            meta=MetaInfo(story_id="test", turn=0),
            time=TimeState(
                calendar="建安三年春",
                anchor=TimeAnchor(label="建安三年春", order=1)
            ),
            player=PlayerState(
                id="player_001",
                name="玩家",
                location_id="nonexistent_location",  # 不存在的地点
            ),
            entities=Entities(),  # 空实体
            quest=QuestState(),
            constraints=Constraints(),
        )
        print("❌ 应该失败但没有失败！")
    except ValueError as e:
        print(f"✅ 正确捕获引用错误: {str(e)[:100]}...")


def main():
    """运行所有测试"""
    print("\n" + "🚀 开始测试数据模型" + "\n")
    
    # 运行测试
    test_basic_state_creation()
    test_entities_creation()
    test_unique_item_validation()
    test_item_location_validation()
    test_complete_state_with_entities()
    test_event_creation()
    test_event_payload_validation()
    test_state_reference_validation()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

