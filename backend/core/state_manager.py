"""
State Manager: 状态管理核心逻辑
包含 apply_state_patch 等状态操作函数
"""
import copy
from datetime import datetime
from typing import List, Set

from ..models import (
    CanonicalState,
    StatePatch,
    EntityUpdate,
    TimeUpdate,
    QuestUpdate,
    Character,
    Item,
    Location,
    Faction,
    Quest,
)


def _ensure_location_references(state: CanonicalState) -> None:
    """
    确保所有引用的location都存在，如果不存在则创建默认location
    
    Args:
        state: CanonicalState 对象（会被修改）
    """
    # 收集所有需要的location_id
    required_locations: Set[str] = set()
    
    # Player的location_id
    if state.player.location_id:
        required_locations.add(state.player.location_id)
    
    # 所有角色的location_id
    for char in state.entities.characters.values():
        if char.location_id:
            required_locations.add(char.location_id)
    
    # 所有物品的location_id和owner_id（如果owner是location）
    for item in state.entities.items.values():
        if item.location_id:
            required_locations.add(item.location_id)
        if item.owner_id and item.owner_id in state.entities.locations:
            # owner_id是location，已经存在
            pass
        elif item.owner_id and item.owner_id not in state.entities.characters:
            # owner_id可能是location但不存在，需要创建
            required_locations.add(item.owner_id)
    
    # 创建缺失的location
    for loc_id in required_locations:
        if loc_id not in state.entities.locations:
            # 创建默认location
            state.entities.locations[loc_id] = Location(
                id=loc_id,
                name=loc_id,  # 使用id作为name（可以后续更新）
                parent_location_id=None,
                metadata={}
            )


def apply_state_patch(
    state: CanonicalState,
    patch: StatePatch,
    event_id: str,
    turn: int,
) -> CanonicalState:
    """
    应用状态补丁到 Canonical State
    
    Args:
        state: 当前 Canonical State
        patch: 状态补丁
        event_id: 事件ID（用于记录）
        turn: 当前轮次
        
    Returns:
        更新后的 Canonical State
    """
    # 深度复制状态
    new_state = copy.deepcopy(state)
    
    # 应用 entity_updates
    for entity_id, entity_update in patch.entity_updates.items():
        if entity_update.entity_type == "character":
            if entity_id in new_state.entities.characters:
                char = new_state.entities.characters[entity_id]
                for key, value in entity_update.updates.items():
                    setattr(char, key, value)
            else:
                # 如果角色不存在，创建新角色（简化处理）
                # 实际应该从 updates 中提取完整信息
                pass
        
        elif entity_update.entity_type == "item":
            if entity_id in new_state.entities.items:
                item = new_state.entities.items[entity_id]
                for key, value in entity_update.updates.items():
                    setattr(item, key, value)
            else:
                # 如果物品不存在，创建新物品
                # 需要从 updates 中提取信息
                if "name" in entity_update.updates:
                    new_item = Item(
                        id=entity_id,
                        name=entity_update.updates["name"],
                        owner_id=entity_update.updates.get("owner_id"),
                        location_id=entity_update.updates.get("location_id"),
                        unique=entity_update.updates.get("unique", False),
                        metadata=entity_update.updates.get("metadata", {}),
                    )
                    new_state.entities.items[entity_id] = new_item
        
        elif entity_update.entity_type == "location":
            if entity_id in new_state.entities.locations:
                loc = new_state.entities.locations[entity_id]
                for key, value in entity_update.updates.items():
                    setattr(loc, key, value)
            else:
                # 创建新地点
                if "name" in entity_update.updates:
                    new_location = Location(
                        id=entity_id,
                        name=entity_update.updates["name"],
                        parent_location_id=entity_update.updates.get("parent_location_id"),
                        metadata=entity_update.updates.get("metadata", {}),
                    )
                    new_state.entities.locations[entity_id] = new_location
        
        elif entity_update.entity_type == "faction":
            if entity_id in new_state.entities.factions:
                faction = new_state.entities.factions[entity_id]
                for key, value in entity_update.updates.items():
                    setattr(faction, key, value)
            else:
                # 创建新阵营
                if "name" in entity_update.updates:
                    new_faction = Faction(
                        id=entity_id,
                        name=entity_update.updates["name"],
                        leader_id=entity_update.updates.get("leader_id"),
                        members=entity_update.updates.get("members", []),
                        metadata=entity_update.updates.get("metadata", {}),
                    )
                    new_state.entities.factions[entity_id] = new_faction
    
    # 应用 player_updates
    if patch.player_updates:
        for key, value in patch.player_updates.items():
            if key == "inventory_add":
                # 添加物品到 inventory
                if isinstance(value, list):
                    for item_id in value:
                        if item_id not in new_state.player.inventory:
                            new_state.player.inventory.append(item_id)
            elif key == "inventory_remove":
                # 从 inventory 移除物品
                if isinstance(value, list):
                    new_state.player.inventory = [
                        item_id for item_id in new_state.player.inventory
                        if item_id not in value
                    ]
            elif key == "party_add":
                # 添加角色到 party
                if isinstance(value, list):
                    for char_id in value:
                        if char_id not in new_state.player.party:
                            new_state.player.party.append(char_id)
            elif key == "party_remove":
                # 从 party 移除角色
                if isinstance(value, list):
                    new_state.player.party = [
                        char_id for char_id in new_state.player.party
                        if char_id not in value
                    ]
            else:
                # 直接更新其他字段
                setattr(new_state.player, key, value)
    
    # 应用 time_update
    if patch.time_update:
        if patch.time_update.calendar:
            new_state.time.calendar = patch.time_update.calendar
        if patch.time_update.anchor:
            new_state.time.anchor = patch.time_update.anchor
    
    # 应用 quest_updates
    if patch.quest_updates:
        for quest_update in patch.quest_updates:
            # 查找任务
            quest_found = False
            
            # 在 active 中查找
            for quest in new_state.quest.active:
                if quest.id == quest_update.quest_id:
                    quest.status = quest_update.status
                    if quest_update.metadata:
                        quest.metadata.update(quest_update.metadata)
                    quest_found = True
                    break
            
            # 在 completed 中查找
            if not quest_found:
                for quest in new_state.quest.completed:
                    if quest.id == quest_update.quest_id:
                        quest.status = quest_update.status
                        if quest_update.metadata:
                            quest.metadata.update(quest_update.metadata)
                        quest_found = True
                        break
            
            # 如果任务不存在，创建新任务
            if not quest_found:
                new_quest = Quest(
                    id=quest_update.quest_id,
                    title=quest_update.metadata.get("title", quest_update.quest_id) if quest_update.metadata else quest_update.quest_id,
                    status=quest_update.status,
                    metadata=quest_update.metadata or {},
                )
                
                if quest_update.status == "completed":
                    new_state.quest.completed.append(new_quest)
                elif quest_update.status == "failed":
                    # 失败的任务也可以移到 completed（或创建 failed 列表）
                    new_state.quest.completed.append(new_quest)
                else:
                    new_state.quest.active.append(new_quest)
            
            # 如果状态变为 completed 或 failed，从 active 移到 completed
            if quest_update.status in ["completed", "failed"]:
                new_state.quest.active = [
                    q for q in new_state.quest.active
                    if q.id != quest_update.quest_id
                ]
                # 确保在 completed 中
                if not any(q.id == quest_update.quest_id for q in new_state.quest.completed):
                    quest = next(
                        (q for q in new_state.quest.active + new_state.quest.completed if q.id == quest_update.quest_id),
                        None
                    )
                    if quest:
                        quest.status = quest_update.status
                        new_state.quest.completed.append(quest)
    
    # 应用 constraint_additions
    if patch.constraint_additions:
        for constraint in patch.constraint_additions:
            new_state.constraints.constraints.append(constraint)
            
            # 如果是 unique_item 类型，添加到 unique_item_ids
            if constraint.type == "unique_item" and constraint.entity_id:
                if constraint.entity_id not in new_state.constraints.unique_item_ids:
                    new_state.constraints.unique_item_ids.append(constraint.entity_id)
    
    # 更新 meta 信息
    new_state.meta.turn = turn
    new_state.meta.last_event_id = event_id
    new_state.meta.updated_at = datetime.now()
    
    # 确保所有引用的location都存在（修复引用完整性）
    _ensure_location_references(new_state)
    
    return new_state


def apply_multiple_patches(
    state: CanonicalState,
    events: List,
) -> CanonicalState:
    """
    应用多个事件的 state_patch
    
    Args:
        state: 当前 Canonical State
        events: 事件列表（必须有序）
        
    Returns:
        更新后的 Canonical State
    """
    if not events:
        return state
    
    current_state = state
    max_turn = state.meta.turn
    last_event_id = state.meta.last_event_id
    
    for event in events:
        max_turn = max(max_turn, event.turn)
        last_event_id = event.event_id
        current_state = apply_state_patch(
            current_state,
            event.state_patch,
            event.event_id,
            event.turn,
        )
    
    # 确保最终状态记录正确的 turn 和 last_event_id
    current_state.meta.turn = max_turn
    current_state.meta.last_event_id = last_event_id
    current_state.meta.updated_at = datetime.now()
    
    # 确保所有引用的location都存在（修复引用完整性）
    _ensure_location_references(current_state)
    
    return current_state

