"""
测试 SQLite 存储层
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.database import Repository, init_database
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
    Event,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
    StatePatch,
    EntityUpdate,
)


async def test_database_init():
    """测试数据库初始化"""
    print("=" * 60)
    print("测试 1: 数据库初始化")
    print("=" * 60)
    
    # 使用临时数据库
    test_db = Path(__file__).parent.parent / "data" / "databases" / "test.db"
    test_db.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果存在则删除
    if test_db.exists():
        test_db.unlink()
    
    await init_database(test_db)
    print("✅ 数据库初始化成功")
    return test_db


async def test_state_operations(test_db: Path):
    """测试状态操作"""
    print("\n" + "=" * 60)
    print("测试 2: 状态操作（get_state, save_state）")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "test_story"
    
    # 创建初始状态
    luoyang = Location(id="luoyang", name="洛阳")
    
    state = CanonicalState(
        meta=MetaInfo(story_id=story_id, turn=0),
        time=TimeState(
            calendar="建安三年春",
            anchor=TimeAnchor(label="建安三年春", order=1)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang",
        ),
        entities=Entities(locations={"luoyang": luoyang}),
        quest=QuestState(),
        constraints=Constraints(),
    )
    
    # 保存状态
    await repo.save_state(story_id, state)
    print("✅ 状态保存成功")
    
    # 读取状态
    loaded_state = await repo.get_state(story_id)
    assert loaded_state is not None, "状态应该存在"
    assert loaded_state.meta.story_id == story_id, "story_id 应该匹配"
    assert loaded_state.player.name == "玩家", "玩家名称应该匹配"
    print("✅ 状态读取成功")
    
    # 更新状态
    state.meta.turn = 1
    state.player.name = "玩家（已更新）"
    await repo.save_state(story_id, state)
    
    # 验证更新
    updated_state = await repo.get_state(story_id)
    assert updated_state.meta.turn == 1, "turn 应该更新为 1"
    assert updated_state.player.name == "玩家（已更新）", "玩家名称应该更新"
    print("✅ 状态更新成功")


async def test_initialize_state(test_db: Path):
    """测试初始化状态"""
    print("\n" + "=" * 60)
    print("测试 3: 初始化状态（如果不存在则创建）")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "new_story"
    
    # 第一次调用应该创建默认状态
    state = await repo.initialize_state(story_id)
    assert state is not None, "应该返回状态"
    assert state.meta.story_id == story_id, "story_id 应该匹配"
    print("✅ 自动创建默认状态成功")
    
    # 第二次调用应该返回已存在的状态
    existing_state = await repo.initialize_state(story_id)
    assert existing_state.meta.story_id == story_id, "应该返回已存在的状态"
    print("✅ 返回已存在状态成功")


async def test_event_operations(test_db: Path):
    """测试事件操作"""
    print("\n" + "=" * 60)
    print("测试 4: 事件操作（append_event, list_recent_events）")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "test_story"
    
    # 创建事件
    event1 = Event(
        event_id="evt_1_001",
        turn=1,
        time=EventTime(label="建安三年春", order=1),
        where=EventLocation(location_id="luoyang"),
        who=EventParticipants(actors=["player_001"]),
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
        evidence=EventEvidence(source="draft_turn_1"),
    )
    
    # 追加事件
    await repo.append_event(story_id, event1)
    print("✅ 事件追加成功")
    
    # 创建第二个事件（时间顺序更晚）
    event2 = Event(
        event_id="evt_1_002",
        turn=1,
        time=EventTime(label="建安三年春", order=2),
        where=EventLocation(location_id="luoyang"),
        who=EventParticipants(actors=["player_001"]),
        type="TRAVEL",
        summary="玩家前往许昌",
        payload={
            "character_id": "player_001",
            "from_location_id": "luoyang",
            "to_location_id": "xuchang"
        },
        state_patch=StatePatch(
            entity_updates={
                "player_001": EntityUpdate(
                    entity_type="character",
                    entity_id="player_001",
                    updates={"location_id": "xuchang"}
                )
            }
        ),
        evidence=EventEvidence(source="draft_turn_1"),
    )
    
    await repo.append_event(story_id, event2)
    print("✅ 第二个事件追加成功")
    
    # 列出最近事件
    events = await repo.list_recent_events(story_id, limit=10)
    assert len(events) == 2, f"应该有 2 个事件，实际有 {len(events)}"
    # 应该按 time_order 降序排列
    assert events[0].time.order == 2, "第一个事件应该是 time_order=2"
    assert events[1].time.order == 1, "第二个事件应该是 time_order=1"
    print("✅ 列出最近事件成功（按时间顺序降序）")


async def test_event_id_uniqueness(test_db: Path):
    """测试 event_id 唯一性"""
    print("\n" + "=" * 60)
    print("测试 5: event_id 唯一性约束")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "test_story"
    
    event = Event(
        event_id="evt_duplicate",
        turn=2,
        time=EventTime(label="建安三年春", order=3),
        where=EventLocation(location_id="luoyang"),
        who=EventParticipants(actors=["player_001"]),
        type="OTHER",
        summary="测试事件",
        payload={},
        state_patch=StatePatch(
            entity_updates={
                "player_001": EntityUpdate(
                    entity_type="character",
                    entity_id="player_001",
                    updates={"metadata": {"test": True}}
                )
            }
        ),
        evidence=EventEvidence(source="test"),
    )
    
    # 第一次追加应该成功
    await repo.append_event(story_id, event)
    print("✅ 第一次追加事件成功")
    
    # 第二次追加应该失败
    try:
        await repo.append_event(story_id, event)
        print("❌ 应该失败但没有失败！")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        print(f"✅ 正确捕获重复 event_id 错误: {e}")


async def test_get_event(test_db: Path):
    """测试根据 event_id 获取事件"""
    print("\n" + "=" * 60)
    print("测试 6: 根据 event_id 获取事件")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "test_story"
    
    # 获取存在的事件
    event = await repo.get_event("evt_1_001")
    assert event is not None, "事件应该存在"
    assert event.event_id == "evt_1_001", "event_id 应该匹配"
    assert event.summary == "玩家获得了青釭剑", "摘要应该匹配"
    print("✅ 获取存在的事件成功")
    
    # 获取不存在的事件
    nonexistent = await repo.get_event("evt_nonexistent")
    assert nonexistent is None, "不存在的事件应该返回 None"
    print("✅ 获取不存在的事件返回 None")


async def test_get_events_by_turn(test_db: Path):
    """测试根据轮次获取事件"""
    print("\n" + "=" * 60)
    print("测试 7: 根据轮次获取事件")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "test_story"
    
    # 获取 turn=1 的所有事件
    events = await repo.get_events_by_turn(story_id, turn=1)
    assert len(events) == 2, f"turn=1 应该有 2 个事件，实际有 {len(events)}"
    assert all(e.turn == 1 for e in events), "所有事件都应该是 turn=1"
    print("✅ 根据轮次获取事件成功")


async def test_transaction_safety(test_db: Path):
    """测试事务安全性"""
    print("\n" + "=" * 60)
    print("测试 8: 事务安全性（状态和事件的一致性）")
    print("=" * 60)
    
    repo = Repository(test_db)
    story_id = "transaction_test"
    
    # 创建状态
    luoyang = Location(id="luoyang", name="洛阳")
    state = CanonicalState(
        meta=MetaInfo(story_id=story_id, turn=0),
        time=TimeState(
            calendar="建安三年春",
            anchor=TimeAnchor(label="建安三年春", order=1)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang",
        ),
        entities=Entities(locations={"luoyang": luoyang}),
        quest=QuestState(),
        constraints=Constraints(),
    )
    
    await repo.save_state(story_id, state)
    
    # 创建事件并更新状态
    state.meta.turn = 1
    state.meta.last_event_id = "evt_trans_001"
    
    event = Event(
        event_id="evt_trans_001",
        turn=1,
        time=EventTime(label="建安三年春", order=1),
        where=EventLocation(location_id="luoyang"),
        who=EventParticipants(actors=["player_001"]),
        type="OTHER",
        summary="事务测试事件",
        payload={},
        state_patch=StatePatch(
            entity_updates={
                "player_001": EntityUpdate(
                    entity_type="character",
                    entity_id="player_001",
                    updates={"metadata": {"transaction_test": True}}
                )
            }
        ),
        evidence=EventEvidence(source="test"),
    )
    
    # 保存状态和事件
    await repo.save_state(story_id, state)
    await repo.append_event(story_id, event)
    
    # 验证一致性
    loaded_state = await repo.get_state(story_id)
    loaded_event = await repo.get_event("evt_trans_001")
    
    assert loaded_state.meta.last_event_id == "evt_trans_001", "状态应该记录最后的事件ID"
    assert loaded_event is not None, "事件应该存在"
    assert loaded_event.turn == loaded_state.meta.turn, "事件轮次应该与状态一致"
    print("✅ 事务安全性验证通过")


async def main():
    """运行所有测试"""
    print("\n" + "🚀 开始测试 SQLite 存储层" + "\n")
    
    # 初始化数据库
    test_db = await test_database_init()
    
    # 运行测试
    await test_state_operations(test_db)
    await test_initialize_state(test_db)
    await test_event_operations(test_db)
    await test_event_id_uniqueness(test_db)
    await test_get_event(test_db)
    await test_get_events_by_turn(test_db)
    await test_transaction_safety(test_db)
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60 + "\n")
    
    # 清理测试数据库
    if test_db.exists():
        test_db.unlink()
        print(f"🧹 已清理测试数据库: {test_db}")


if __name__ == "__main__":
    asyncio.run(main())

