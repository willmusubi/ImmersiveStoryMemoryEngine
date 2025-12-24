# 数据模型说明

## 概述

本模块定义了 Immersive Story Memory Engine 的核心数据模型，使用 Pydantic v2 实现严格的类型检查和验证。

## 核心模型

### CanonicalState（唯一真相状态）

包含以下部分：

- **meta**: 元信息（story_id, canon_version, turn, last_event_id, updated_at）
- **time**: 时间状态（calendar, anchor）
- **player**: 玩家状态（id, name, location_id, party, inventory）
- **entities**: 实体集合（characters, items, locations, factions）
- **quest**: 任务状态（active, completed）
- **constraints**: 约束集合（unique_item_ids, immutable_events, constraints）

### Event（事件）

驱动状态变更的最小单元，包含：

- **event_id**: 唯一标识符（格式：`evt_{turn}_{timestamp}_{hash}`）
- **turn**: 轮次
- **time**: 事件时间（label, order）
- **where**: 事件地点（location_id）
- **who**: 参与者（actors, witnesses）
- **type**: 事件类型（OWNERSHIP_CHANGE, DEATH, TRAVEL 等）
- **summary**: 事件摘要
- **payload**: 事件详情（类型相关）
- **state_patch**: 状态变更补丁
- **evidence**: 事件证据（source, text_span）

### StatePatch（状态补丁）

用于增量更新 Canonical State：

- **entity_updates**: 实体更新字典
- **time_update**: 时间更新
- **quest_updates**: 任务更新列表
- **constraint_additions**: 新增约束列表
- **player_updates**: 玩家状态更新

## 字段校验规则

### 严格校验

1. **唯一物品必须指定 owner_id**

   ```python
   # Item.unique = True 时，owner_id 必填
   Item(id="sword_001", name="青釭剑", unique=True, owner_id="player_001")  # ✅
   Item(id="sword_001", name="青釭剑", unique=True)  # ❌ ValueError
   ```

2. **物品必须指定 owner_id 或 location_id**

   ```python
   # 至少有一个
   Item(id="item_001", owner_id="char_001")  # ✅
   Item(id="item_001", location_id="loc_001")  # ✅
   Item(id="item_001")  # ❌ ValueError
   ```

3. **引用完整性验证**

   - player.location_id 必须在 locations 中存在
   - player.party 中的角色必须在 characters 中存在
   - player.inventory 中的物品必须在 items 中存在
   - 所有实体的引用必须有效

4. **事件类型相关的 payload 验证**

   - OWNERSHIP_CHANGE: 必须包含 item_id, old_owner_id, new_owner_id
   - DEATH: 必须包含 character_id
   - TRAVEL: 必须包含 character_id, from_location_id, to_location_id
   - FACTION_CHANGE: 必须包含 character_id, old_faction_id, new_faction_id
   - QUEST\_\*: 必须包含 quest_id
   - ITEM\_\*: 必须包含 item_id
   - TIME_ADVANCE: 必须包含 time_anchor

5. **事件可追溯性验证**
   - state_patch 必须包含至少一个更新项

## 使用示例

### 创建 CanonicalState

```python
from backend.models import CanonicalState, MetaInfo, TimeState, TimeAnchor, PlayerState, Entities, QuestState, Constraints

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
    entities=Entities(),
    quest=QuestState(),
    constraints=Constraints(),
)
```

### 创建 Event

```python
from backend.models import (
    Event, EventTime, EventLocation, EventParticipants,
    EventEvidence, StatePatch
)

event = Event(
    event_id="evt_1_1234567890_abc123",
    turn=1,
    time=EventTime(label="建安三年春", order=1),
    where=EventLocation(location_id="luoyang"),
    who=EventParticipants(actors=["player_001"], witnesses=[]),
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
```

## 导出 JSON Schema

运行以下命令生成 JSON Schema：

```bash
python scripts/export_schemas.py
```

生成的 Schema 文件位于 `schemas/` 目录。
