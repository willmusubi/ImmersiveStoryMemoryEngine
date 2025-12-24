# SQLite 存储层说明

## 概述

本模块实现了 SQLite 数据库存储层，用于持久化 Canonical State 和 Event Log。

## 数据库结构

### 表1: state
存储 Canonical State（每个 story_id 一条记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| story_id | TEXT PRIMARY KEY | 剧本ID |
| state_json | TEXT NOT NULL | 状态的 JSON 序列化 |
| updated_at | TEXT NOT NULL | 最后更新时间（ISO 格式） |

### 表2: events
存储事件日志（每个 event_id 一条记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| story_id | TEXT NOT NULL | 剧本ID（外键） |
| event_id | TEXT PRIMARY KEY | 事件ID（唯一） |
| turn | INT NOT NULL | 轮次 |
| time_order | INT NOT NULL | 时间顺序值（用于排序） |
| event_json | TEXT NOT NULL | 事件的 JSON 序列化 |
| created_at | TEXT NOT NULL | 创建时间（ISO 格式） |

### 索引

- `idx_events_story_turn`: (story_id, turn) - 按轮次查询
- `idx_events_story_time_order`: (story_id, time_order) - 按时间顺序查询
- `idx_events_story_id`: (story_id) - 按剧本ID查询

## Repository 类

### 初始化

```python
from backend.database import Repository
from pathlib import Path

# 使用默认数据库路径
repo = Repository()

# 或指定自定义路径
custom_db = Path("/path/to/custom.db")
repo = Repository(custom_db)
```

### 状态操作

#### get_state(story_id) -> Optional[CanonicalState]
获取指定 story_id 的状态

```python
state = await repo.get_state("sanguo_yanyi")
if state is None:
    print("状态不存在")
```

#### save_state(story_id, CanonicalState)
保存状态（使用事务，确保原子性）

```python
from backend.models import CanonicalState, MetaInfo, TimeState, TimeAnchor, PlayerState, Entities, QuestState, Constraints, Location

# 创建状态
luoyang = Location(id="luoyang", name="洛阳")
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
    ),
    entities=Entities(locations={"luoyang": luoyang}),
    quest=QuestState(),
    constraints=Constraints(),
)

# 保存
await repo.save_state("sanguo_yanyi", state)
```

#### initialize_state(story_id, initial_state=None) -> CanonicalState
初始化状态（如果不存在则创建）

```python
# 使用默认状态
state = await repo.initialize_state("sanguo_yanyi")

# 或提供自定义初始状态
custom_state = CanonicalState(...)
state = await repo.initialize_state("sanguo_yanyi", custom_state)
```

### 事件操作

#### append_event(story_id, Event)
追加事件（使用事务，确保 event_id 唯一性）

```python
from backend.models import (
    Event, EventTime, EventLocation, EventParticipants,
    EventEvidence, StatePatch, EntityUpdate
)

event = Event(
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

await repo.append_event("sanguo_yanyi", event)
```

**注意**: 如果 event_id 已存在，会抛出 `ValueError`。

#### list_recent_events(story_id, limit=20, offset=0) -> List[Event]
列出最近的事件（按 time_order 降序）

```python
events = await repo.list_recent_events("sanguo_yanyi", limit=10)
for event in events:
    print(f"{event.event_id}: {event.summary}")
```

#### get_event(event_id) -> Optional[Event]
根据 event_id 获取事件

```python
event = await repo.get_event("evt_1_001")
if event:
    print(event.summary)
```

#### get_events_by_turn(story_id, turn) -> List[Event]
获取指定轮次的所有事件

```python
events = await repo.get_events_by_turn("sanguo_yanyi", turn=1)
```

#### get_events_by_time_range(story_id, min_time_order=None, max_time_order=None) -> List[Event]
根据时间范围获取事件

```python
# 获取 time_order >= 10 的所有事件
events = await repo.get_events_by_time_range("sanguo_yanyi", min_time_order=10)

# 获取 time_order 在 10-20 之间的事件
events = await repo.get_events_by_time_range(
    "sanguo_yanyi",
    min_time_order=10,
    max_time_order=20
)
```

## 特性

### 1. 事务安全
所有写操作（`save_state`, `append_event`）都使用事务，确保原子性。

### 2. event_id 唯一性
`append_event` 会检查 event_id 是否已存在，如果存在则抛出 `ValueError`。

### 3. 索引优化
- `turn` 和 `time_order` 字段都有索引，支持高效查询
- 支持按轮次、时间顺序、时间范围查询

### 4. 外键约束
events 表的 `story_id` 有外键约束（虽然 SQLite 默认不强制，但代码中已启用）。

## 数据库初始化

### 使用脚本初始化

```bash
python scripts/init_database.py
```

### 在代码中初始化

```python
from backend.database import init_database

await init_database()  # 使用默认路径
# 或
await init_database(Path("/path/to/custom.db"))
```

## 完整示例

```python
import asyncio
from backend.database import Repository, init_database
from backend.models import (
    CanonicalState, MetaInfo, TimeState, TimeAnchor,
    PlayerState, Entities, Location, QuestState, Constraints,
    Event, EventTime, EventLocation, EventParticipants,
    EventEvidence, StatePatch, EntityUpdate
)

async def main():
    # 初始化数据库
    await init_database()
    
    # 创建 Repository
    repo = Repository()
    story_id = "sanguo_yanyi"
    
    # 初始化状态
    state = await repo.initialize_state(story_id)
    print(f"初始状态: turn={state.meta.turn}")
    
    # 创建事件
    event = Event(
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
    await repo.append_event(story_id, event)
    
    # 更新状态
    state.meta.turn = 1
    state.meta.last_event_id = "evt_1_001"
    await repo.save_state(story_id, state)
    
    # 查询最近事件
    events = await repo.list_recent_events(story_id, limit=10)
    print(f"最近 {len(events)} 个事件:")
    for e in events:
        print(f"  - {e.summary}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 测试

运行存储层测试：

```bash
python scripts/test_storage.py
```

测试覆盖：
- ✅ 数据库初始化
- ✅ 状态操作（保存、读取、更新）
- ✅ 状态初始化
- ✅ 事件操作（追加、列表查询）
- ✅ event_id 唯一性约束
- ✅ 根据 event_id 获取事件
- ✅ 根据轮次获取事件
- ✅ 事务安全性

