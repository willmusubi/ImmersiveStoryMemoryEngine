"""
Consistency Gate R4-R7 规则测试
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
    TimeUpdate,
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
    
    wei = Faction(id="wei", name="魏")
    shu = Faction(id="shu", name="蜀")
    
    caocao = Character(
        id="caocao",
        name="曹操",
        location_id="luoyang",
        alive=True,
        faction_id="wei",
    )
    
    liubei = Character(
        id="liubei",
        name="刘备",
        location_id="xuchang",
        alive=True,
        faction_id="shu",
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
        ),
        entities=Entities(
            characters={"caocao": caocao, "liubei": liubei},
            items={},
            locations={"luoyang": luoyang, "xuchang": xuchang},
            factions={"wei": wei, "shu": shu},
        ),
        quest=QuestState(),
        constraints=Constraints(),
    )


# ==================== R4 测试 ====================
class TestR4ExplicitStateChange:
    """R4: 生死/状态变更必须显式事件"""
    
    def test_r4_pass_death_event(self, gate, base_state):
        """测试：DEATH 事件可以改变 alive 状态"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
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
        assert result.action == "PASS"
        assert len([v for v in result.violations if v.rule_id == "R4"]) == 0
    
    def test_r4_fail_alive_change_without_death(self, gate, base_state):
        """测试：改变 alive 状态但没有 DEATH 事件，应该失败"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="刘备死亡",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "liubei": EntityUpdate(
                        entity_type="character",
                        entity_id="liubei",
                        updates={"alive": False}  # 改变状态但没有 DEATH 事件
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action in ["REWRITE", "ASK_USER"]
        r4_violations = [v for v in result.violations if v.rule_id == "R4"]
        assert len(r4_violations) > 0
        assert "DEATH" in r4_violations[0].message
    
    def test_r4_fail_faction_change_without_event(self, gate, base_state):
        """测试：改变 faction_id 但没有 FACTION_CHANGE 事件，应该失败"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["liubei"]),
            type="OTHER",
            summary="刘备改变阵营",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "liubei": EntityUpdate(
                        entity_type="character",
                        entity_id="liubei",
                        updates={"faction_id": "wei"}  # 改变阵营但没有 FACTION_CHANGE 事件
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action in ["REWRITE", "ASK_USER"]
        r4_violations = [v for v in result.violations if v.rule_id == "R4"]
        assert len(r4_violations) > 0
        assert "FACTION_CHANGE" in r4_violations[0].message


# ==================== R5 测试 ====================
class TestR5TravelEventRequired:
    """R5: 位置变化必须由 move 事件解释（防瞬移）"""
    
    def test_r5_pass_travel_event(self, gate, base_state):
        """测试：TRAVEL 事件可以改变位置"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="TRAVEL",
            summary="曹操前往许昌",
            payload={
                "character_id": "caocao",
                "from_location_id": "luoyang",
                "to_location_id": "xuchang",
            },
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
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action == "PASS"
        assert len([v for v in result.violations if v.rule_id == "R5"]) == 0
    
    def test_r5_fail_location_change_without_travel(self, gate, base_state):
        """测试：改变位置但没有 TRAVEL 事件，应该失败"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="曹操瞬移到许昌",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "caocao": EntityUpdate(
                        entity_type="character",
                        entity_id="caocao",
                        updates={"location_id": "xuchang"}  # 改变位置但没有 TRAVEL 事件
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event])
        assert result.action in ["REWRITE", "ASK_USER"]
        r5_violations = [v for v in result.violations if v.rule_id == "R5"]
        assert len(r5_violations) > 0
        assert "TRAVEL" in r5_violations[0].message


# ==================== R6 测试 ====================
class TestR6SingleLocationPerCharacter:
    """R6: 同一角色同一时刻不能在多个地点"""
    
    def test_r6_pass_single_location(self, gate, base_state):
        """测试：角色在同一时间只有一个位置，应该通过"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="曹操在洛阳",
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
        assert len([v for v in result.violations if v.rule_id == "R6"]) == 0
    
    def test_r6_fail_multiple_locations_same_time(self, gate, base_state):
        """测试：同一角色在同一时间出现在多个地点，应该失败"""
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="曹操在洛阳",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "caocao": EntityUpdate(
                        entity_type="character",
                        entity_id="caocao",
                        updates={"location_id": "luoyang"}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        event2 = Event(
            event_id="evt_1_002",
            turn=1,
            time=EventTime(label="建安三年春", order=11),  # 同一时间
            where=EventLocation(location_id="xuchang"),
            who=EventParticipants(actors=["caocao"]),  # 同一角色
            type="OTHER",
            summary="曹操在许昌",
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
        
        result = gate.validate_event_patch(base_state, [event1, event2])
        assert result.action in ["REWRITE", "ASK_USER"]
        r6_violations = [v for v in result.violations if v.rule_id == "R6"]
        assert len(r6_violations) > 0
        assert "多个地点" in r6_violations[0].message or "同时出现" in r6_violations[0].message


# ==================== R7 测试 ====================
class TestR7MonotonicTimeline:
    """R7: 时间戳单调递增（回忆不推进time）"""
    
    def test_r7_pass_monotonic_increase(self, gate, base_state):
        """测试：时间单调递增，应该通过"""
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="事件1",
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
        
        event2 = Event(
            event_id="evt_1_002",
            turn=1,
            time=EventTime(label="建安三年春", order=12),  # 时间递增
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="事件2",
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
        
        result = gate.validate_event_patch(base_state, [event1, event2])
        assert result.action == "PASS"
        assert len([v for v in result.violations if v.rule_id == "R7"]) == 0
    
    def test_r7_fail_time_decrease(self, gate, base_state):
        """测试：时间倒退，应该失败"""
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=5),  # 小于当前时间 10
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="时间倒退的事件",
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
        assert result.action in ["REWRITE", "ASK_USER"]
        r7_violations = [v for v in result.violations if v.rule_id == "R7"]
        assert len(r7_violations) > 0
        assert "小于当前时间" in r7_violations[0].message or "时间顺序值" in r7_violations[0].message
    
    def test_r7_fail_same_turn_time_decrease(self, gate, base_state):
        """测试：同一轮次中时间倒退，应该失败"""
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=12),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="事件1",
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
        
        event2 = Event(
            event_id="evt_1_002",
            turn=1,  # 同一轮次
            time=EventTime(label="建安三年春", order=11),  # 时间倒退
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="事件2",
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
        
        result = gate.validate_event_patch(base_state, [event1, event2])
        assert result.action in ["REWRITE", "ASK_USER"]
        r7_violations = [v for v in result.violations if v.rule_id == "R7"]
        assert len(r7_violations) > 0
        assert "时间顺序值" in r7_violations[0].message or "大于后续事件" in r7_violations[0].message


# ==================== 综合测试 ====================
class TestMultipleRulesR4R7:
    """测试多条规则同时违反"""
    
    def test_multiple_violations_r4_r5(self, gate, base_state):
        """测试：同时违反 R4 和 R5"""
        event1 = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["caocao"]),
            type="OTHER",
            summary="改变位置和状态",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "caocao": EntityUpdate(
                        entity_type="character",
                        entity_id="caocao",
                        updates={
                            "location_id": "xuchang",  # 违反 R5
                            "alive": False,  # 违反 R4
                        }
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        
        result = gate.validate_event_patch(base_state, [event1])
        assert result.action in ["REWRITE", "ASK_USER"]
        violations = result.violations
        rule_ids = {v.rule_id for v in violations}
        assert "R4" in rule_ids
        assert "R5" in rule_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

