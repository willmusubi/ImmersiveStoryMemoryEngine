"""
State Manager 测试
"""
import pytest
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.core.state_manager import apply_state_patch, apply_multiple_patches
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
    QuestState,
    Constraints,
    StatePatch,
    EntityUpdate,
    TimeUpdate,
    QuestUpdate,
    Quest,
    Constraint,
    Event,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
)


@pytest.fixture
def base_state():
    """创建基础状态"""
    luoyang = Location(id="luoyang", name="洛阳")
    xuchang = Location(id="xuchang", name="许昌")
    
    caocao = Character(
        id="caocao",
        name="曹操",
        location_id="luoyang",
        alive=True,
    )
    
    sword = Item(
        id="sword_001",
        name="青釭剑",
        owner_id="caocao",
        location_id="luoyang",
        unique=False,
    )
    
    return CanonicalState(
        meta=MetaInfo(story_id="test", turn=0),
        time=TimeState(
            calendar="建安三年春",
            anchor=TimeAnchor(label="建安三年春", order=10)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang",
            inventory=[],
        ),
        entities=Entities(
            characters={"caocao": caocao},
            items={"sword_001": sword},
            locations={"luoyang": luoyang, "xuchang": xuchang},
        ),
        quest=QuestState(),
        constraints=Constraints(),
    )


class TestStateManager:
    """State Manager 测试"""
    
    def test_apply_state_patch_entity_update(self, base_state):
        """测试：应用实体更新"""
        patch = StatePatch(
            entity_updates={
                "caocao": EntityUpdate(
                    entity_type="character",
                    entity_id="caocao",
                    updates={"location_id": "xuchang"}
                )
            }
        )
        
        updated_state = apply_state_patch(
            state=base_state,
            patch=patch,
            event_id="evt_1_001",
            turn=1,
        )
        
        assert updated_state.entities.characters["caocao"].location_id == "xuchang"
        assert updated_state.meta.turn == 1
        assert updated_state.meta.last_event_id == "evt_1_001"
    
    def test_apply_state_patch_player_inventory_add(self, base_state):
        """测试：添加物品到 inventory"""
        patch = StatePatch(
            player_updates={
                "inventory_add": ["sword_001"]
            }
        )
        
        updated_state = apply_state_patch(
            state=base_state,
            patch=patch,
            event_id="evt_1_001",
            turn=1,
        )
        
        assert "sword_001" in updated_state.player.inventory
    
    def test_apply_state_patch_player_inventory_remove(self, base_state):
        """测试：从 inventory 移除物品"""
        # 先添加物品
        base_state.player.inventory = ["sword_001"]
        
        patch = StatePatch(
            player_updates={
                "inventory_remove": ["sword_001"]
            }
        )
        
        updated_state = apply_state_patch(
            state=base_state,
            patch=patch,
            event_id="evt_1_001",
            turn=1,
        )
        
        assert "sword_001" not in updated_state.player.inventory
    
    def test_apply_state_patch_time_update(self, base_state):
        """测试：更新时间"""
        patch = StatePatch(
            time_update=TimeUpdate(
                calendar="建安三年夏",
                anchor=TimeAnchor(label="建安三年夏", order=11)
            )
        )
        
        updated_state = apply_state_patch(
            state=base_state,
            patch=patch,
            event_id="evt_1_001",
            turn=1,
        )
        
        assert updated_state.time.calendar == "建安三年夏"
        assert updated_state.time.anchor.order == 11
    
    def test_apply_state_patch_quest_update(self, base_state):
        """测试：更新任务"""
        patch = StatePatch(
            quest_updates=[
                QuestUpdate(
                    quest_id="quest_001",
                    status="active",
                    metadata={"title": "测试任务"}
                )
            ]
        )
        
        updated_state = apply_state_patch(
            state=base_state,
            patch=patch,
            event_id="evt_1_001",
            turn=1,
        )
        
        assert len(updated_state.quest.active) == 1
        assert updated_state.quest.active[0].id == "quest_001"
        assert updated_state.quest.active[0].status == "active"
    
    def test_apply_multiple_patches(self, base_state):
        """测试：应用多个补丁"""
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["player_001"]),
            type="OTHER",
            summary="事件1",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "caocao": EntityUpdate(
                        entity_type="character",
                        entity_id="caocao",
                        updates={"location_id": "xuchang"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        event2 = Event(
            event_id="evt_1_002",
            turn=1,
            time=EventTime(label="建安三年春", order=12),
            where=EventLocation(location_id="xuchang"),
            who=EventParticipants(actors=["player_001"]),
            type="OTHER",
            summary="事件2",
            payload={},
            state_patch=StatePatch(
                player_updates={
                    "inventory_add": ["sword_001"]
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        updated_state = apply_multiple_patches(base_state, [event1, event2])
        
        assert updated_state.entities.characters["caocao"].location_id == "xuchang"
        assert "sword_001" in updated_state.player.inventory
        assert updated_state.meta.turn == 1
        assert updated_state.meta.last_event_id == "evt_1_002"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

