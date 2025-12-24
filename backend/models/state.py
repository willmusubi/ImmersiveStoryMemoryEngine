"""
Canonical State 数据模型定义
包含：meta, time, player, entities, quest, constraints
"""
from datetime import datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ==================== Meta Info ====================
class MetaInfo(BaseModel):
    """元信息：剧本ID、版本、轮次等"""
    story_id: str = Field(..., description="剧本ID，如 'sanguo_yanyi'")
    canon_version: str = Field(default="1.0.0", description="规范版本号")
    turn: int = Field(default=0, ge=0, description="当前轮次，从0开始")
    last_event_id: Optional[str] = Field(default=None, description="最后一个事件的ID")
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间")


# ==================== Time State ====================
class TimeAnchor(BaseModel):
    """时间锚点：用于时间线排序"""
    label: str = Field(..., description="时间标签，如 '建安三年春'")
    order: int = Field(..., ge=0, description="时间顺序值，用于排序")


class TimeState(BaseModel):
    """时间状态"""
    calendar: str = Field(..., description="当前日历时间，如 '建安三年春'")
    anchor: TimeAnchor = Field(..., description="时间锚点")


# ==================== Player State ====================
class PlayerState(BaseModel):
    """玩家状态"""
    id: str = Field(..., description="玩家角色ID")
    name: str = Field(..., description="玩家角色名称")
    location_id: str = Field(..., description="当前所在位置ID")
    party: List[str] = Field(default_factory=list, description="队伍成员ID列表")
    inventory: List[str] = Field(default_factory=list, description="物品ID列表")


# ==================== Entities ====================
class Character(BaseModel):
    """人物实体"""
    id: str = Field(..., description="人物ID")
    name: str = Field(..., description="人物名称")
    location_id: str = Field(..., description="当前所在位置ID")
    alive: bool = Field(default=True, description="是否存活")
    faction_id: Optional[str] = Field(default=None, description="所属阵营ID")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")


class Item(BaseModel):
    """物品实体"""
    id: str = Field(..., description="物品ID")
    name: str = Field(..., description="物品名称")
    owner_id: Optional[str] = Field(default=None, description="拥有者ID（人物ID或地点ID）")
    location_id: Optional[str] = Field(default=None, description="物品所在位置ID")
    unique: bool = Field(default=False, description="是否为唯一物品")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")

    @model_validator(mode='after')
    def validate_unique_item(self):
        """唯一物品必须指定 owner_id"""
        if self.unique and self.owner_id is None:
            raise ValueError(f"Unique item '{self.id}' must have owner_id")
        return self

    @model_validator(mode='after')
    def validate_location(self):
        """物品必须要么有 owner_id，要么有 location_id"""
        if self.owner_id is None and self.location_id is None:
            raise ValueError(f"Item '{self.id}' must have either owner_id or location_id")
        return self


class Location(BaseModel):
    """地点实体"""
    id: str = Field(..., description="地点ID")
    name: str = Field(..., description="地点名称")
    parent_location_id: Optional[str] = Field(default=None, description="父级地点ID")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")


class Faction(BaseModel):
    """阵营实体"""
    id: str = Field(..., description="阵营ID")
    name: str = Field(..., description="阵营名称")
    leader_id: Optional[str] = Field(default=None, description="首领ID")
    members: List[str] = Field(default_factory=list, description="成员ID列表")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")


class Entities(BaseModel):
    """实体集合"""
    characters: Dict[str, Character] = Field(default_factory=dict, description="人物字典")
    items: Dict[str, Item] = Field(default_factory=dict, description="物品字典")
    locations: Dict[str, Location] = Field(default_factory=dict, description="地点字典")
    factions: Dict[str, Faction] = Field(default_factory=dict, description="阵营字典")


# ==================== Quest State ====================
class Quest(BaseModel):
    """任务"""
    id: str = Field(..., description="任务ID")
    title: str = Field(..., description="任务标题")
    status: Literal["active", "completed", "failed"] = Field(..., description="任务状态")
    prerequisites: List[str] = Field(default_factory=list, description="前置任务ID列表")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")


class QuestState(BaseModel):
    """任务状态"""
    active: List[Quest] = Field(default_factory=list, description="进行中的任务列表")
    completed: List[Quest] = Field(default_factory=list, description="已完成的任务列表")


# ==================== Constraints ====================
class Constraint(BaseModel):
    """硬约束"""
    id: str = Field(..., description="约束ID")
    type: Literal["immutable_event", "unique_item", "entity_state", "relationship"] = Field(
        ..., description="约束类型"
    )
    description: str = Field(..., description="约束描述")
    entity_id: Optional[str] = Field(default=None, description="相关实体ID")
    value: Dict = Field(default_factory=dict, description="约束值（如状态、关系等）")


class Constraints(BaseModel):
    """约束集合"""
    unique_item_ids: List[str] = Field(default_factory=list, description="唯一物品ID列表")
    immutable_events: List[str] = Field(default_factory=list, description="不可变事件ID列表（已发生的历史事件）")
    constraints: List[Constraint] = Field(default_factory=list, description="其他约束列表")


# ==================== Canonical State ====================
class CanonicalState(BaseModel):
    """Canonical State：唯一真相状态"""
    meta: MetaInfo = Field(..., description="元信息")
    time: TimeState = Field(..., description="时间状态")
    player: PlayerState = Field(..., description="玩家状态")
    entities: Entities = Field(..., description="实体集合")
    quest: QuestState = Field(..., description="任务状态")
    constraints: Constraints = Field(..., description="约束集合")

    @model_validator(mode='after')
    def validate_references(self):
        """验证引用完整性"""
        errors = []
        
        # 验证 player.location_id 存在
        if self.player.location_id not in self.entities.locations:
            errors.append(f"Player location_id '{self.player.location_id}' not found in locations")
        
        # 验证 player.party 中的角色存在
        for char_id in self.player.party:
            if char_id not in self.entities.characters:
                errors.append(f"Party member '{char_id}' not found in characters")
        
        # 验证 player.inventory 中的物品存在
        for item_id in self.player.inventory:
            if item_id not in self.entities.items:
                errors.append(f"Inventory item '{item_id}' not found in items")
        
        # 验证所有角色的 location_id 存在
        for char_id, char in self.entities.characters.items():
            if char.location_id not in self.entities.locations:
                errors.append(f"Character '{char_id}' location_id '{char.location_id}' not found")
            if char.faction_id and char.faction_id not in self.entities.factions:
                errors.append(f"Character '{char_id}' faction_id '{char.faction_id}' not found")
        
        # 验证所有物品的 owner_id 和 location_id
        for item_id, item in self.entities.items.items():
            if item.owner_id:
                # owner_id 可能是角色ID或地点ID
                if item.owner_id not in self.entities.characters and item.owner_id not in self.entities.locations:
                    errors.append(f"Item '{item_id}' owner_id '{item.owner_id}' not found")
            if item.location_id and item.location_id not in self.entities.locations:
                errors.append(f"Item '{item_id}' location_id '{item.location_id}' not found")
        
        # 验证地点的 parent_location_id
        for loc_id, loc in self.entities.locations.items():
            if loc.parent_location_id and loc.parent_location_id not in self.entities.locations:
                errors.append(f"Location '{loc_id}' parent_location_id '{loc.parent_location_id}' not found")
        
        # 验证阵营的 leader_id 和 members
        for faction_id, faction in self.entities.factions.items():
            if faction.leader_id and faction.leader_id not in self.entities.characters:
                errors.append(f"Faction '{faction_id}' leader_id '{faction.leader_id}' not found")
            for member_id in faction.members:
                if member_id not in self.entities.characters:
                    errors.append(f"Faction '{faction_id}' member '{member_id}' not found")
        
        if errors:
            raise ValueError("Reference validation failed:\n" + "\n".join(errors))
        
        return self


# ==================== State Patch ====================
class EntityUpdate(BaseModel):
    """实体更新"""
    entity_type: Literal["character", "item", "location", "faction"] = Field(..., description="实体类型")
    entity_id: str = Field(..., description="实体ID")
    updates: Dict = Field(..., description="更新字段字典")


class TimeUpdate(BaseModel):
    """时间更新"""
    calendar: Optional[str] = Field(default=None, description="新的日历时间")
    anchor: Optional[TimeAnchor] = Field(default=None, description="新的时间锚点")


class QuestUpdate(BaseModel):
    """任务更新"""
    quest_id: str = Field(..., description="任务ID")
    status: Literal["active", "completed", "failed"] = Field(..., description="新状态")
    metadata: Optional[Dict] = Field(default=None, description="额外元数据")


class StatePatch(BaseModel):
    """状态补丁：用于增量更新 Canonical State"""
    entity_updates: Dict[str, EntityUpdate] = Field(default_factory=dict, description="实体更新字典")
    time_update: Optional[TimeUpdate] = Field(default=None, description="时间更新")
    quest_updates: Optional[List[QuestUpdate]] = Field(default=None, description="任务更新列表")
    constraint_additions: List[Constraint] = Field(default_factory=list, description="新增约束列表")
    player_updates: Optional[Dict] = Field(default=None, description="玩家状态更新（location_id, party, inventory等）")

