"""
Repository 类：统一的数据访问接口
提供 state 和 events 的 CRUD 操作
"""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from pathlib import Path

from ..models import CanonicalState, Event, MetaInfo, TimeState, TimeAnchor, PlayerState, Entities, QuestState, Constraints, Location
from .connection import get_db_connection, init_database
from ..core.state_manager import _ensure_location_references


def _fix_missing_locations_in_json(state_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    在JSON数据中修复缺失的location引用（在Pydantic验证之前）
    
    Args:
        state_json: 状态的JSON字典
        
    Returns:
        修复后的JSON字典
    """
    if "entities" not in state_json:
        return state_json
    
    entities = state_json["entities"]
    if "locations" not in entities:
        entities["locations"] = {}
    
    locations = entities["locations"]
    required_locations: Set[str] = set()
    
    # Player的location_id
    if "player" in state_json and state_json["player"].get("location_id"):
        required_locations.add(state_json["player"]["location_id"])
    
    # 所有角色的location_id
    if "characters" in entities:
        for char in entities["characters"].values():
            if isinstance(char, dict) and char.get("location_id"):
                required_locations.add(char["location_id"])
    
    # 所有物品的location_id和owner_id（如果owner是location）
    if "items" in entities:
        for item in entities["items"].values():
            if isinstance(item, dict):
                if item.get("location_id"):
                    required_locations.add(item["location_id"])
                owner_id = item.get("owner_id")
                if owner_id:
                    # 如果owner_id不在characters中，可能是location
                    characters = entities.get("characters", {})
                    if owner_id not in characters:
                        required_locations.add(owner_id)
    
    # 创建缺失的location
    for loc_id in required_locations:
        if loc_id not in locations:
            locations[loc_id] = {
                "id": loc_id,
                "name": loc_id,  # 使用id作为name（可以后续更新）
                "parent_location_id": None,
                "metadata": {}
            }
    
    return state_json


class Repository:
    """数据仓库：管理 State 和 Event 的持久化"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化 Repository
        
        Args:
            db_path: 数据库文件路径，如果为 None 则使用默认路径
        """
        self.db_path = db_path
    
    async def get_state(self, story_id: str) -> Optional[CanonicalState]:
        """
        获取指定 story_id 的状态
        
        Args:
            story_id: 剧本ID
            
        Returns:
            CanonicalState 对象，如果不存在则返回 None
            
        Raises:
            ValueError: 如果 state JSON 损坏且无法恢复
        """
        async with get_db_connection(self.db_path) as db:
            async with db.execute(
                "SELECT state_json FROM state WHERE story_id = ?",
                (story_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                
                try:
                    state_json = json.loads(row[0])
                except json.JSONDecodeError as e:
                    # JSON 解析失败，state 可能损坏
                    raise ValueError(
                        f"State JSON 损坏，无法解析 (story_id: {story_id}): {str(e)}\n"
                        f"建议：删除损坏的状态并重新初始化，或从事件日志重建状态"
                    ) from e
                
                # 在验证之前修复缺失的location（避免Pydantic验证失败）
                state_json = _fix_missing_locations_in_json(state_json)
                
                try:
                    state = CanonicalState.model_validate(state_json)
                except Exception as e:
                    # Pydantic 验证失败，state 结构可能损坏
                    raise ValueError(
                        f"State 结构损坏，无法验证 (story_id: {story_id}): {str(e)}\n"
                        f"建议：删除损坏的状态并重新初始化，或从事件日志重建状态"
                    ) from e
                
                return state
    
    async def save_state(self, story_id: str, state: CanonicalState) -> None:
        """
        保存状态（使用事务，确保原子性）
        
        Args:
            story_id: 剧本ID
            state: CanonicalState 对象
        """
        async with get_db_connection(self.db_path) as db:
            # 确保所有引用的location都存在（修复引用完整性）
            _ensure_location_references(state)
            
            # 更新 state 的 meta 信息
            state.meta.updated_at = datetime.now()
            
            state_json = state.model_dump_json()
            updated_at = state.meta.updated_at.isoformat()
            
            # 使用 INSERT OR REPLACE 确保事务安全
            await db.execute(
                """
                INSERT OR REPLACE INTO state (story_id, state_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (story_id, state_json, updated_at)
            )
            await db.commit()
    
    async def append_event(self, story_id: str, event: Event) -> None:
        """
        追加事件（使用事务，确保 event_id 唯一性）
        
        Args:
            story_id: 剧本ID
            event: Event 对象
            
        Raises:
            ValueError: 如果 event_id 已存在
        """
        async with get_db_connection(self.db_path) as db:
            # 检查 event_id 是否已存在
            async with db.execute(
                "SELECT event_id FROM events WHERE event_id = ?",
                (event.event_id,)
            ) as cursor:
                existing = await cursor.fetchone()
                if existing is not None:
                    raise ValueError(f"Event with event_id '{event.event_id}' already exists")
            
            # 插入事件
            event_json = event.model_dump_json()
            created_at = event.created_at.isoformat()
            
            await db.execute(
                """
                INSERT INTO events (story_id, event_id, turn, time_order, event_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    story_id,
                    event.event_id,
                    event.turn,
                    event.time.order,
                    event_json,
                    created_at
                )
            )
            await db.commit()
    
    async def list_recent_events(
        self, 
        story_id: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[Event]:
        """
        列出最近的事件（按 time_order 降序）
        
        Args:
            story_id: 剧本ID
            limit: 返回的最大事件数量
            offset: 偏移量（用于分页）
            
        Returns:
            Event 对象列表，按时间顺序降序排列
        """
        async with get_db_connection(self.db_path) as db:
            async with db.execute(
                """
                SELECT event_json FROM events
                WHERE story_id = ?
                ORDER BY time_order DESC, turn DESC, created_at DESC
                LIMIT ? OFFSET ?
                """,
                (story_id, limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
                
                events = []
                for row in rows:
                    event_json = json.loads(row[0])
                    events.append(Event.model_validate(event_json))
                
                return events
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """
        根据 event_id 获取事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            Event 对象，如果不存在则返回 None
        """
        async with get_db_connection(self.db_path) as db:
            async with db.execute(
                "SELECT event_json FROM events WHERE event_id = ?",
                (event_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                
                event_json = json.loads(row[0])
                return Event.model_validate(event_json)
    
    async def get_events_by_turn(self, story_id: str, turn: int) -> List[Event]:
        """
        获取指定轮次的所有事件
        
        Args:
            story_id: 剧本ID
            turn: 轮次
            
        Returns:
            Event 对象列表
        """
        async with get_db_connection(self.db_path) as db:
            async with db.execute(
                """
                SELECT event_json FROM events
                WHERE story_id = ? AND turn = ?
                ORDER BY time_order ASC, created_at ASC
                """,
                (story_id, turn)
            ) as cursor:
                rows = await cursor.fetchall()
                
                events = []
                for row in rows:
                    event_json = json.loads(row[0])
                    events.append(Event.model_validate(event_json))
                
                return events
    
    async def get_events_by_time_range(
        self,
        story_id: str,
        min_time_order: Optional[int] = None,
        max_time_order: Optional[int] = None
    ) -> List[Event]:
        """
        根据时间范围获取事件
        
        Args:
            story_id: 剧本ID
            min_time_order: 最小时间顺序值
            max_time_order: 最大时间顺序值
            
        Returns:
            Event 对象列表
        """
        async with get_db_connection(self.db_path) as db:
            query = "SELECT event_json FROM events WHERE story_id = ?"
            params = [story_id]
            
            if min_time_order is not None:
                query += " AND time_order >= ?"
                params.append(min_time_order)
            
            if max_time_order is not None:
                query += " AND time_order <= ?"
                params.append(max_time_order)
            
            query += " ORDER BY time_order ASC, turn ASC, created_at ASC"
            
            async with db.execute(query, tuple(params)) as cursor:
                rows = await cursor.fetchall()
                
                events = []
                for row in rows:
                    event_json = json.loads(row[0])
                    events.append(Event.model_validate(event_json))
                
                return events
    
    async def initialize_state(
        self,
        story_id: str,
        initial_state: Optional[CanonicalState] = None
    ) -> CanonicalState:
        """
        初始化状态（如果不存在则创建）
        
        Args:
            story_id: 剧本ID
            initial_state: 初始状态，如果为 None 则创建默认状态
            
        Returns:
            CanonicalState 对象
        """
        existing = await self.get_state(story_id)
        if existing is not None:
            return existing
        
        if initial_state is None:
            # 创建默认状态（需要包含一个默认地点以满足引用验证）
            from ..models import Location
            unknown_location = Location(id="unknown", name="未知地点")
            
            initial_state = CanonicalState(
                meta=MetaInfo(
                    story_id=story_id,
                    canon_version="1.0.0",
                    turn=0,
                ),
                time=TimeState(
                    calendar="初始时间",
                    anchor=TimeAnchor(label="初始时间", order=0)
                ),
                player=PlayerState(
                    id="player_001",
                    name="玩家",
                    location_id="unknown",
                ),
                entities=Entities(
                    locations={"unknown": unknown_location}
                ),
                quest=QuestState(),
                constraints=Constraints(),
            )
        
        await self.save_state(story_id, initial_state)
        return initial_state

