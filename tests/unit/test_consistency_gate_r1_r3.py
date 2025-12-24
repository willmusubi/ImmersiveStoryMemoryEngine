"""
Consistency Gate R1-R3 规则测试
"""
import pytest
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.gate import ConsistencyGate, ValidationResult, RuleViolation
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
    Event,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
    StatePatch,
    EntityUpdate,
)


@pytest.fixture
def gate():
    """创建 ConsistencyGate 实例"""
    return ConsistencyGate()


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
    
    liubei = Character(
        id="liubei",
        name="刘备",
        location_id="xuchang",
        alive=True,
    )
    
    # 创建唯一物品
    seal = Item(
        id="seal_001",
        name="传国玉玺",
        owner_id="caocao",
        location_id="luoyang",
        unique=True,
    )
    
    # 创建普通物品
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
            anchor=TimeAnchor(label="建安三年春", order=1)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang",
        ),
        entities=Entities(
            characters={"caocao": caocao, "liubei": liubei},
            items={"seal_001": seal, "sword_001": sword},
            locations={"luoyang": luoyang, "xuchang": xuchang},
        ),
        quest=QuestState(),
        constraints=Constraints(unique_item_ids=["seal_001"]),
    )


# ==================== R1 测试 ====================
class TestR1UniqueItemOwnership:
    """R1: 唯一物品不能多重归属"""
    
    def test_r1_pass_single_owner(self, gate, base_state):
        """测试：唯一物品只有一个拥有者，应该通过"""
        # 创建一个事件，将唯一物品转移给新拥有者
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao", "liubei"]),
            type="OWNERSHIP_CHANGE",
            summary="曹操将传国玉玺交给刘备",
            payload={
                "item_id": "seal_001",
                "old_owner_id": "caocao",
                "new_owner_id": "liubei",
            },
            state_patch=StatePatch(
                entity_updates={
                    "seal_001": EntityUpdate(
                        entity_type="item",
                        entity_id="seal_001",
                        updates={"owner_id": "liubei", "location_id": "xuchang"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action == "PASS"
        assert len([v for v in result.violations if v.rule_id == "R1"]) == 0
    
    def test_r1_fail_multiple_owners(self, gate, base_state):
        """测试：唯一物品被分配给多个拥有者，应该失败"""
        # 创建两个事件，将同一个唯一物品分配给不同的人
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OWNERSHIP_CHANGE",
            summary="曹操将传国玉玺交给刘备",
            payload={
                "item_id": "seal_001",
                "old_owner_id": "caocao",
                "new_owner_id": "liubei",
            },
            state_patch=StatePatch(
                entity_updates={
                    "seal_001": EntityUpdate(
                        entity_type="item",
                        entity_id="seal_001",
                        updates={"owner_id": "liubei"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        event2 = Event(
            event_id="evt_1_002",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OWNERSHIP_CHANGE",
            summary="曹操将传国玉玺交给玩家",
            payload={
                "item_id": "seal_001",
                "old_owner_id": "caocao",
                "new_owner_id": "player_001",
            },
            state_patch=StatePatch(
                entity_updates={
                    "seal_001": EntityUpdate(
                        entity_type="item",
                        entity_id="seal_001",
                        updates={"owner_id": "player_001"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event1, event2])
        assert result.action in ["REWRITE", "ASK_USER"]
        r1_violations = [v for v in result.violations if v.rule_id == "R1"]
        assert len(r1_violations) > 0
        assert "不同的拥有者" in r1_violations[0].message or "多个" in r1_violations[0].message


# ==================== R2 测试 ====================
class TestR2ItemLocationConsistency:
    """R2: 物品位置与归属一致"""
    
    def test_r2_pass_consistent_location(self, gate, base_state):
        """测试：物品位置与拥有者位置一致，应该通过"""
        # 物品在拥有者的位置，应该通过
        result = gate.validate_event_patch(base_state, [])
        assert result.action == "PASS"
        assert len([v for v in result.violations if v.rule_id == "R2"]) == 0
    
    def test_r2_fail_inconsistent_location(self, gate, base_state):
        """测试：物品位置与拥有者位置不一致，应该检测到"""
        # 创建一个事件，更新物品的 owner 但不更新 location
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao", "liubei"]),
            type="OWNERSHIP_CHANGE",
            summary="曹操将青釭剑交给刘备",
            payload={
                "item_id": "sword_001",
                "old_owner_id": "caocao",
                "new_owner_id": "liubei",
            },
            state_patch=StatePatch(
                entity_updates={
                    "sword_001": EntityUpdate(
                        entity_type="item",
                        entity_id="sword_001",
                        updates={"owner_id": "liubei"}  # 只更新 owner，不更新 location
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        r2_violations = [v for v in result.violations if v.rule_id == "R2"]
        assert len(r2_violations) > 0
        assert r2_violations[0].fixable is True  # 应该可以自动修复
    
    def test_r2_auto_fix(self, gate, base_state):
        """测试：R2 违反应该可以自动修复"""
        # 创建一个事件，更新物品的 owner 但不更新 location
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao", "liubei"]),
            type="OWNERSHIP_CHANGE",
            summary="曹操将青釭剑交给刘备",
            payload={
                "item_id": "sword_001",
                "old_owner_id": "caocao",
                "new_owner_id": "liubei",
            },
            state_patch=StatePatch(
                entity_updates={
                    "sword_001": EntityUpdate(
                        entity_type="item",
                        entity_id="sword_001",
                        updates={"owner_id": "liubei"}  # 只更新 owner
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        r2_violations = [v for v in result.violations if v.rule_id == "R2"]
        
        if len(r2_violations) > 0 and r2_violations[0].fixable:
            # 如果只有 R2 违反且可修复，应该是 AUTO_FIX
            if len([v for v in result.violations if v.rule_id != "R2"]) == 0:
                assert result.action == "AUTO_FIX"
                assert result.fixes is not None
                assert "sword_001" in result.fixes.entity_updates


# ==================== R3 测试 ====================
class TestR3DeadCharacterAction:
    """R3: 死亡角色不能行动/说话"""
    
    def test_r3_pass_alive_character(self, gate, base_state):
        """测试：存活角色可以行动，应该通过"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="曹操说话",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "caocao": EntityUpdate(
                        entity_type="character",
                        entity_id="caocao",
                        updates={"metadata": {"action": "speak"}}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action == "PASS"
        assert len([v for v in result.violations if v.rule_id == "R3"]) == 0
    
    def test_r3_fail_dead_character_action(self, gate, base_state):
        """测试：死亡角色不能行动，应该失败"""
        # 先将角色设置为死亡
        dead_char = Character(
            id="dead_char",
            name="已死角色",
            location_id="luoyang",
            alive=False,
        )
        base_state.entities.characters["dead_char"] = dead_char
        
        # 创建事件，死亡角色作为行动者
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["dead_char"]),  # 死亡角色作为行动者
            type="OTHER",
            summary="已死角色说话",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "dead_char": EntityUpdate(
                        entity_type="character",
                        entity_id="dead_char",
                        updates={"metadata": {"action": "speak"}}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action in ["REWRITE", "ASK_USER"]
        r3_violations = [v for v in result.violations if v.rule_id == "R3"]
        assert len(r3_violations) > 0
        assert "死亡角色" in r3_violations[0].message
    
    def test_r3_pass_death_event(self, gate, base_state):
        """测试：DEATH 事件中死亡角色可以参与（作为事件对象）"""
        # 创建 DEATH 事件
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"], witnesses=["liubei"]),
            type="DEATH",
            summary="刘备死亡",
            payload={"character_id": "liubei"},
            state_patch=StatePatch(
                entity_updates={
                    "liubei": EntityUpdate(
                        entity_type="character",
                        entity_id="liubei",
                        updates={"alive": False}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        # DEATH 事件中，死亡角色可以作为参与者（见证者），不应该违反 R3
        r3_violations = [v for v in result.violations if v.rule_id == "R3"]
        # 注意：这里 liubei 在事件发生时还是活的，所以不应该违反 R3
        # 如果 liubei 在事件前已经死亡，才会违反 R3
        assert len(r3_violations) == 0
    
    def test_r3_fail_revive_without_revival_event(self, gate, base_state):
        """测试：没有 REVIVAL 事件就复活角色，应该失败"""
        # 先将角色设置为死亡
        dead_char = Character(
            id="dead_char",
            name="已死角色",
            location_id="luoyang",
            alive=False,
        )
        base_state.entities.characters["dead_char"] = dead_char
        
        # 创建事件，试图复活角色但没有 REVIVAL 类型
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",  # 不是 REVIVAL
            summary="复活角色",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "dead_char": EntityUpdate(
                        entity_type="character",
                        entity_id="dead_char",
                        updates={"alive": True}  # 试图复活
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action in ["REWRITE", "ASK_USER"]
        r3_violations = [v for v in result.violations if v.rule_id == "R3"]
        assert len(r3_violations) > 0
        assert any("alive=True" in v.message or "REVIVAL" in v.message for v in r3_violations)


# ==================== 综合测试 ====================
class TestMultipleRules:
    """测试多条规则同时违反"""
    
    def test_multiple_violations(self, gate, base_state):
        """测试：同时违反多条规则"""
        # 创建死亡角色
        dead_char = Character(
            id="dead_char",
            name="已死角色",
            location_id="luoyang",
            alive=False,
        )
        base_state.entities.characters["dead_char"] = dead_char
        
        # 创建两个事件：一个违反 R1，一个违反 R3
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OWNERSHIP_CHANGE",
            summary="将传国玉玺给刘备",
            payload={
                "item_id": "seal_001",
                "old_owner_id": "caocao",
                "new_owner_id": "liubei",
            },
            state_patch=StatePatch(
                entity_updates={
                    "seal_001": EntityUpdate(
                        entity_type="item",
                        entity_id="seal_001",
                        updates={"owner_id": "liubei"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        event2 = Event(
            event_id="evt_1_002",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OWNERSHIP_CHANGE",
            summary="将传国玉玺给玩家",
            payload={
                "item_id": "seal_001",
                "old_owner_id": "caocao",
                "new_owner_id": "player_001",
            },
            state_patch=StatePatch(
                entity_updates={
                    "seal_001": EntityUpdate(
                        entity_type="item",
                        entity_id="seal_001",
                        updates={"owner_id": "player_001"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        event3 = Event(
            event_id="evt_1_003",
            turn=1,
            time=EventTime(label="建安三年春", order=2),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["dead_char"]),  # 死亡角色行动
            type="OTHER",
            summary="已死角色说话",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "dead_char": EntityUpdate(
                        entity_type="character",
                        entity_id="dead_char",
                        updates={"metadata": {"action": "speak"}}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event1, event2, event3])
        assert result.action in ["REWRITE", "ASK_USER"]
        assert len(result.violations) >= 2  # 至少应该有 R1 和 R3 的违反


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

