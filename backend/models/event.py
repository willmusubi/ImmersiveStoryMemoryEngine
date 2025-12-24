"""
Event 数据模型定义
包含：event_id, turn, time, where, who, type, summary, payload, state_patch, evidence
"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime

from .state import TimeAnchor, StatePatch


# ==================== Event Type ====================
EventType = Literal[
    "OWNERSHIP_CHANGE",  # 物品所有权变更
    "DEATH",             # 人物死亡
    "REVIVAL",           # 人物复活（特殊事件）
    "TRAVEL",            # 旅行/位置变更
    "FACTION_CHANGE",    # 阵营关系变更
    "QUEST_START",       # 任务开始
    "QUEST_COMPLETE",    # 任务完成
    "QUEST_FAIL",        # 任务失败
    "ITEM_CREATE",       # 物品创建
    "ITEM_DESTROY",      # 物品销毁
    "RELATIONSHIP_CHANGE", # 关系变更
    "TIME_ADVANCE",      # 时间推进
    "OTHER"              # 其他事件
]


# ==================== Event Location ====================
class EventLocation(BaseModel):
    """事件发生地点"""
    location_id: str = Field(..., description="地点ID")


# ==================== Event Participants ====================
class EventParticipants(BaseModel):
    """事件参与者"""
    actors: List[str] = Field(default_factory=list, description="主要参与者ID列表（执行动作的角色）")
    witnesses: List[str] = Field(default_factory=list, description="见证者ID列表（在场但未直接参与的角色）")


# ==================== Event Evidence ====================
class EventEvidence(BaseModel):
    """事件证据：来自原始文本"""
    source: str = Field(..., description="证据来源，如 'draft_turn_5'")
    text_span: Optional[str] = Field(default=None, description="相关文本片段")


# ==================== Event Time ====================
class EventTime(BaseModel):
    """事件时间"""
    label: str = Field(..., description="时间标签，如 '建安三年春'")
    order: int = Field(..., ge=0, description="时间顺序值，用于排序")


# ==================== Event ====================
class Event(BaseModel):
    """事件：驱动状态变更的最小单元"""
    event_id: str = Field(..., description="事件ID，格式：'evt_{turn}_{timestamp}_{hash}'")
    turn: int = Field(..., ge=0, description="事件发生的轮次")
    time: EventTime = Field(..., description="事件时间")
    where: EventLocation = Field(..., description="事件发生地点")
    who: EventParticipants = Field(..., description="事件参与者")
    type: EventType = Field(..., description="事件类型")
    summary: str = Field(..., min_length=1, description="事件摘要")
    payload: Dict = Field(default_factory=dict, description="事件详情（类型相关的额外信息）")
    state_patch: StatePatch = Field(..., description="状态变更补丁")
    evidence: EventEvidence = Field(..., description="事件证据")
    created_at: datetime = Field(default_factory=datetime.now, description="事件创建时间")

    @field_validator('event_id')
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """验证 event_id 格式"""
        if not v.startswith('evt_'):
            raise ValueError("event_id must start with 'evt_'")
        return v

    @model_validator(mode='after')
    def validate_payload_by_type(self):
        """根据事件类型验证 payload"""
        if self.type == "OWNERSHIP_CHANGE":
            required_fields = ["item_id", "old_owner_id", "new_owner_id"]
            for field in required_fields:
                if field not in self.payload:
                    raise ValueError(f"OWNERSHIP_CHANGE event must have '{field}' in payload")
        
        elif self.type == "DEATH":
            if "character_id" not in self.payload:
                raise ValueError("DEATH event must have 'character_id' in payload")
        
        elif self.type == "TRAVEL":
            required_fields = ["character_id", "from_location_id", "to_location_id"]
            for field in required_fields:
                if field not in self.payload:
                    raise ValueError(f"TRAVEL event must have '{field}' in payload")
        
        elif self.type == "FACTION_CHANGE":
            required_fields = ["character_id", "old_faction_id", "new_faction_id"]
            for field in required_fields:
                if field not in self.payload:
                    raise ValueError(f"FACTION_CHANGE event must have '{field}' in payload")
        
        elif self.type in ["QUEST_START", "QUEST_COMPLETE", "QUEST_FAIL"]:
            if "quest_id" not in self.payload:
                raise ValueError(f"{self.type} event must have 'quest_id' in payload")
        
        elif self.type in ["ITEM_CREATE", "ITEM_DESTROY"]:
            if "item_id" not in self.payload:
                raise ValueError(f"{self.type} event must have 'item_id' in payload")
        
        elif self.type == "TIME_ADVANCE":
            if "time_anchor" not in self.payload:
                raise ValueError("TIME_ADVANCE event must have 'time_anchor' in payload")
        
        return self

    @model_validator(mode='after')
    def validate_traceability(self):
        """验证可追溯性：state_patch 必须包含变更"""
        # 至少应该有一些更新
        has_updates = (
            bool(self.state_patch.entity_updates) or
            self.state_patch.time_update is not None or
            self.state_patch.quest_updates is not None or
            bool(self.state_patch.constraint_additions) or
            self.state_patch.player_updates is not None
        )
        
        if not has_updates:
            raise ValueError("Event state_patch must contain at least one update")
        
        return self


# ==================== Extracted Event ====================
class ExtractedEvent(BaseModel):
    """从 LLM 草稿中抽取的事件（尚未分配 event_id）"""
    turn: int = Field(..., ge=0, description="事件发生的轮次")
    time: EventTime = Field(..., description="事件时间")
    where: EventLocation = Field(..., description="事件发生地点")
    who: EventParticipants = Field(..., description="事件参与者")
    type: EventType = Field(..., description="事件类型")
    summary: str = Field(..., min_length=1, description="事件摘要")
    payload: Dict = Field(default_factory=dict, description="事件详情")
    state_patch: StatePatch = Field(..., description="状态变更补丁")
    evidence: EventEvidence = Field(..., description="事件证据")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="抽取置信度")

