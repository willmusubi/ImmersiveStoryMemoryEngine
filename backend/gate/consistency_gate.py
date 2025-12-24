"""
Consistency Gate: 一致性校验器
实现 10 条规则校验，确保状态一致性
"""
from typing import List, Optional, Literal, Dict, Set
from pydantic import BaseModel, Field

from ..models import (
    CanonicalState,
    Event,
    ExtractedEvent,
    StatePatch,
    EntityUpdate,
    Item,
    Character,
)


# ==================== 数据模型 ====================
class RuleViolation(BaseModel):
    """规则违反"""
    rule_id: str = Field(..., description="规则ID，如 'R1'")
    rule_name: str = Field(..., description="规则名称")
    severity: Literal["error", "warning"] = Field(default="error", description="严重程度")
    message: str = Field(..., description="违反信息")
    entity_id: Optional[str] = Field(default=None, description="相关实体ID")
    fixable: bool = Field(default=False, description="是否可自动修复")


class ValidationResult(BaseModel):
    """校验结果"""
    action: Literal["PASS", "AUTO_FIX", "REWRITE", "ASK_USER"] = Field(..., description="处理动作")
    reasons: List[str] = Field(default_factory=list, description="原因列表")
    violations: List[RuleViolation] = Field(default_factory=list, description="违反的规则列表")
    fixes: Optional[StatePatch] = Field(default=None, description="自动修复补丁（AUTO_FIX 时提供）")
    questions: Optional[List[str]] = Field(default=None, description="澄清问题（ASK_USER 时提供）")


# ==================== Consistency Gate ====================
class ConsistencyGate:
    """一致性闸门：校验状态和事件的一致性"""
    
    def __init__(self):
        """初始化 Consistency Gate"""
        self.rules = {
            "R1": self._check_r1_unique_item_ownership,
            "R2": self._check_r2_item_location_consistency,
            "R3": self._check_r3_dead_character_action,
            "R4": self._check_r4_explicit_state_change,
            "R5": self._check_r5_travel_event_required,
            "R6": self._check_r6_single_location_per_character,
            "R7": self._check_r7_monotonic_timeline,
            "R8": self._check_r8_immutable_constraints,
            "R9": self._check_r9_traceable_relationship_change,
            "R10": self._check_r10_draft_factual_consistency,
        }
    
    def validate_event_patch(
        self,
        current_state: CanonicalState,
        pending_events: List[Event],
    ) -> ValidationResult:
        """
        校验待写入的事件补丁
        
        Args:
            current_state: 当前 Canonical State
            pending_events: 待写入的事件列表
            
        Returns:
            ValidationResult: 校验结果
        """
        violations: List[RuleViolation] = []
        
        # 应用所有 pending_events 的 state_patch，构建临时状态用于校验
        temp_state = self._apply_patches_to_state(current_state, pending_events)
        
        # 执行所有规则检查
        for rule_id, check_func in self.rules.items():
            rule_violations = check_func(current_state, temp_state, pending_events)
            violations.extend(rule_violations)
        
        # 根据违反情况决定 action
        return self._determine_action(violations, current_state, temp_state)
    
    def validate_draft(
        self,
        current_state: CanonicalState,
        draft_text: str,
    ) -> ValidationResult:
        """
        校验生成草稿（从文本中检测硬事实冲突）
        
        Args:
            current_state: 当前 Canonical State
            draft_text: LLM 生成的草稿文本
            
        Returns:
            ValidationResult: 校验结果
        """
        violations: List[RuleViolation] = []
        
        # 从草稿中提取可能的事实（简化版：检查关键词）
        # 这里先实现基础版本，后续可以增强
        
        # R3: 检查死亡角色是否在草稿中出现为行动者
        dead_characters = {
            char_id: char.name
            for char_id, char in current_state.entities.characters.items()
            if not char.alive
        }
        
        for char_id, char_name in dead_characters.items():
            # 简单检查：如果死亡角色名称出现在动作相关词汇附近
            if self._check_character_action_in_text(draft_text, char_name):
                violations.append(RuleViolation(
                    rule_id="R3",
                    rule_name="死亡角色不能行动/说话",
                    severity="error",
                    message=f"死亡角色 '{char_name}' 在草稿中表现为行动或说话",
                    entity_id=char_id,
                    fixable=False,
                ))
        
        # R10: 检查草稿硬事实是否忠实于 canonical state
        # 在草稿检查中，需要从文本中提取硬事实
        r10_violations = self._extract_and_check_hard_facts(draft_text, current_state)
        violations.extend(r10_violations)
        
        # 根据违反情况决定 action
        return self._determine_action(violations, current_state, None)
    
    # ==================== R1: 唯一物品不能多重归属 ====================
    def _check_r1_unique_item_ownership(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R1: 唯一物品不能多重归属
        
        检查：
        1. 当前状态中唯一物品的 owner_id 是否唯一
        2. pending_events 中是否有唯一物品被分配给多个 owner
        """
        violations: List[RuleViolation] = []
        
        # 获取所有唯一物品ID
        unique_item_ids = set(current_state.constraints.unique_item_ids)
        
        # 检查当前状态中的唯一物品
        for item_id in unique_item_ids:
            if item_id in current_state.entities.items:
                item = current_state.entities.items[item_id]
                if item.unique and item.owner_id:
                    # 检查是否有其他唯一物品也有相同的 owner_id（对于唯一物品，这不应该发生）
                    # 但这里主要检查同一个物品是否被分配给多个 owner
                    pass  # 当前状态应该已经通过模型验证
        
        # 检查 pending_events 中的唯一物品归属变更
        # 对于每个唯一物品，收集所有事件中分配的新 owner_id
        unique_item_new_owners: Dict[str, List[str]] = {}  # item_id -> list of new_owner_ids from events
        
        for event in pending_events:
            # 检查 state_patch 中的物品更新
            for entity_id, entity_update in event.state_patch.entity_updates.items():
                if entity_update.entity_type == "item":
                    item_id = entity_update.entity_id
                    
                    # 检查是否是唯一物品
                    if item_id in unique_item_ids:
                        # 获取新的 owner_id
                        new_owner_id = entity_update.updates.get("owner_id")
                        if new_owner_id:
                            if item_id not in unique_item_new_owners:
                                unique_item_new_owners[item_id] = []
                            unique_item_new_owners[item_id].append(new_owner_id)
        
        # 检查是否有唯一物品在多个事件中被分配给不同的 owner
        for item_id, new_owner_list in unique_item_new_owners.items():
            # 如果同一个物品在多个事件中被分配给不同的 owner，则违反 R1
            unique_new_owners = set(new_owner_list)
            if len(unique_new_owners) > 1:
                # 安全获取物品名称
                if item_id in current_state.entities.items:
                    item_name = current_state.entities.items[item_id].name
                else:
                    item_name = item_id
                violations.append(RuleViolation(
                    rule_id="R1",
                    rule_name="唯一物品不能多重归属",
                    severity="error",
                    message=f"唯一物品 '{item_name}' ({item_id}) 在多个事件中被分配给不同的拥有者: {unique_new_owners}",
                    entity_id=item_id,
                    fixable=False,
                ))
        
        # 检查 temp_state 中唯一物品的最终状态
        for item_id in unique_item_ids:
            if item_id in temp_state.entities.items:
                item = temp_state.entities.items[item_id]
                if item.unique:
                    # 检查是否有其他唯一物品也指向同一个 owner（这不应该发生，但检查一下）
                    owner_id = item.owner_id
                    if owner_id:
                        # 检查是否有其他唯一物品也指向这个 owner
                        for other_item_id, other_item in temp_state.entities.items.items():
                            if other_item_id != item_id and other_item.unique and other_item.owner_id == owner_id:
                                # 这通常不应该发生，但如果是同一个物品的多次更新，应该已经在上面的检查中捕获
                                pass
        
        return violations
    
    # ==================== R2: 物品位置与归属一致 ====================
    def _check_r2_item_location_consistency(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R2: 物品位置与归属一致
        
        规则：
        - 如果物品有 owner_id（人物），location_id 应该与 owner 的 location_id 一致
        - 如果物品有 owner_id（地点），location_id 应该等于 owner_id
        - 可以 AUTO_FIX：根据 owner_id 自动修正 location_id
        """
        violations: List[RuleViolation] = []
        
        for item_id, item in temp_state.entities.items.items():
            if item.owner_id:
                # 检查 owner 是人物还是地点
                owner_is_character = item.owner_id in temp_state.entities.characters
                owner_is_location = item.owner_id in temp_state.entities.locations
                
                expected_location_id = None
                
                if owner_is_character:
                    # 如果 owner 是人物，物品应该在人物的 location_id
                    owner_char = temp_state.entities.characters[item.owner_id]
                    expected_location_id = owner_char.location_id
                elif owner_is_location:
                    # 如果 owner 是地点，物品的 location_id 应该等于 owner_id
                    expected_location_id = item.owner_id
                
                # 检查 location_id 是否一致
                if expected_location_id and item.location_id != expected_location_id:
                    item_name = item.name
                    violations.append(RuleViolation(
                        rule_id="R2",
                        rule_name="物品位置与归属一致",
                        severity="warning",  # 可以自动修复
                        message=f"物品 '{item_name}' ({item_id}) 的 location_id ({item.location_id}) "
                               f"与 owner ({item.owner_id}) 的位置 ({expected_location_id}) 不一致",
                        entity_id=item_id,
                        fixable=True,  # 可以自动修复
                    ))
                    
                    # fixable 已经在 RuleViolation 中设置为 True
        
        # 修复信息已经通过 fixable=True 标记在 violations 中
        return violations
    
    # ==================== R3: 死亡角色不能行动/说话 ====================
    def _check_r3_dead_character_action(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R3: 死亡角色不能行动/说话
        
        检查：
        1. 事件参与者（actors, witnesses）中是否有已死亡的角色
        2. state_patch 中是否有死亡角色被更新为 alive=True 但没有 DEATH/REVIVAL 事件
        """
        violations: List[RuleViolation] = []
        
        # 获取所有死亡角色ID
        dead_character_ids = {
            char_id
            for char_id, char in current_state.entities.characters.items()
            if not char.alive
        }
        
        # 检查 pending_events 中的参与者
        for event in pending_events:
            # 检查 actors
            for actor_id in event.who.actors:
                if actor_id in dead_character_ids:
                    char_name = current_state.entities.characters[actor_id].name
                    violations.append(RuleViolation(
                        rule_id="R3",
                        rule_name="死亡角色不能行动/说话",
                        severity="error",
                        message=f"死亡角色 '{char_name}' ({actor_id}) 在事件 '{event.summary}' 中作为行动者",
                        entity_id=actor_id,
                        fixable=False,
                    ))
            
            # 检查 witnesses（见证者通常可以，但如果是"说话"的行为，也应该检查）
            # 这里先只检查 actors，witnesses 可以根据需要调整
            
            # 检查事件类型：如果是 DEATH 或 REVIVAL，死亡角色可以作为参与者
            if event.type in ["DEATH", "REVIVAL"]:
                continue  # 这些事件中死亡角色可以参与
        
        # 检查 state_patch 中是否有死亡角色被"复活"但没有 REVIVAL 事件
        for event in pending_events:
            if event.type != "REVIVAL":
                for entity_id, entity_update in event.state_patch.entity_updates.items():
                    if entity_update.entity_type == "character":
                        char_id = entity_update.entity_id
                        if char_id in dead_character_ids:
                            # 检查是否被更新为 alive=True
                            if entity_update.updates.get("alive") is True:
                                char_name = current_state.entities.characters[char_id].name
                                violations.append(RuleViolation(
                                    rule_id="R3",
                                    rule_name="死亡角色不能行动/说话",
                                    severity="error",
                                    message=f"死亡角色 '{char_name}' ({char_id}) 被更新为 alive=True，但事件类型不是 REVIVAL",
                                    entity_id=char_id,
                                    fixable=False,
                                ))
        
        return violations
    
    # ==================== R4: 生死/状态变更必须显式事件 ====================
    def _check_r4_explicit_state_change(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R4: 生死/状态变更必须显式事件
        
        检查：
        1. 角色的 alive 状态变更必须有对应的 DEATH 或 REVIVAL 事件
        2. 其他重要状态变更（如 faction_id）应该有对应的事件类型
        """
        violations: List[RuleViolation] = []
        
        # 检查每个事件中的状态变更
        for event in pending_events:
            for entity_id, entity_update in event.state_patch.entity_updates.items():
                if entity_update.entity_type == "character":
                    char_id = entity_update.entity_id
                    
                    # 检查 alive 状态变更
                    if "alive" in entity_update.updates:
                        new_alive = entity_update.updates["alive"]
                        
                        # 获取当前状态
                        if char_id in current_state.entities.characters:
                            current_char = current_state.entities.characters[char_id]
                            current_alive = current_char.alive
                            
                            # 如果状态发生变化
                            if current_alive != new_alive:
                                char_name = current_char.name
                                
                                # 检查事件类型是否匹配
                                if new_alive is False and event.type != "DEATH":
                                    violations.append(RuleViolation(
                                        rule_id="R4",
                                        rule_name="生死/状态变更必须显式事件",
                                        severity="error",
                                        message=f"角色 '{char_name}' ({char_id}) 的 alive 状态从 True 变为 False，但事件类型不是 DEATH",
                                        entity_id=char_id,
                                        fixable=False,
                                    ))
                                elif new_alive is True and event.type != "REVIVAL":
                                    violations.append(RuleViolation(
                                        rule_id="R4",
                                        rule_name="生死/状态变更必须显式事件",
                                        severity="error",
                                        message=f"角色 '{char_name}' ({char_id}) 的 alive 状态从 False 变为 True，但事件类型不是 REVIVAL",
                                        entity_id=char_id,
                                        fixable=False,
                                    ))
                    
                    # 检查 faction_id 变更（应该有 FACTION_CHANGE 事件）
                    if "faction_id" in entity_update.updates:
                        if char_id in current_state.entities.characters:
                            current_char = current_state.entities.characters[char_id]
                            current_faction = current_char.faction_id
                            new_faction = entity_update.updates["faction_id"]
                            
                            if current_faction != new_faction and event.type != "FACTION_CHANGE":
                                char_name = current_char.name
                                violations.append(RuleViolation(
                                    rule_id="R4",
                                    rule_name="生死/状态变更必须显式事件",
                                    severity="error",
                                    message=f"角色 '{char_name}' ({char_id}) 的 faction_id 从 '{current_faction}' 变为 '{new_faction}'，但事件类型不是 FACTION_CHANGE",
                                    entity_id=char_id,
                                    fixable=False,
                                ))
        
        return violations
    
    # ==================== R5: 位置变化必须由 move 事件解释（防瞬移）====================
    def _check_r5_travel_event_required(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R5: 位置变化必须由 move 事件解释（防瞬移）
        
        检查：
        1. 角色的 location_id 变更必须有对应的 TRAVEL 事件
        2. 物品的 location_id 变更（如果 owner 是人物）应该跟随 owner 的位置
        """
        violations: List[RuleViolation] = []
        
        # 检查每个事件中的位置变更
        for event in pending_events:
            for entity_id, entity_update in event.state_patch.entity_updates.items():
                if entity_update.entity_type == "character":
                    char_id = entity_update.entity_id
                    
                    # 检查 location_id 变更
                    if "location_id" in entity_update.updates:
                        new_location_id = entity_update.updates["location_id"]
                        
                        # 获取当前状态
                        if char_id in current_state.entities.characters:
                            current_char = current_state.entities.characters[char_id]
                            current_location_id = current_char.location_id
                            
                            # 如果位置发生变化
                            if current_location_id != new_location_id:
                                char_name = current_char.name
                                
                                # 检查事件类型是否是 TRAVEL
                                if event.type != "TRAVEL":
                                    violations.append(RuleViolation(
                                        rule_id="R5",
                                        rule_name="位置变化必须由 move 事件解释（防瞬移）",
                                        severity="error",
                                        message=f"角色 '{char_name}' ({char_id}) 的位置从 '{current_location_id}' 变为 '{new_location_id}'，但事件类型不是 TRAVEL",
                                        entity_id=char_id,
                                        fixable=False,
                                    ))
                                else:
                                    # 验证 TRAVEL 事件的 payload 是否匹配
                                    if "character_id" in event.payload:
                                        if event.payload["character_id"] != char_id:
                                            violations.append(RuleViolation(
                                                rule_id="R5",
                                                rule_name="位置变化必须由 move 事件解释（防瞬移）",
                                                severity="error",
                                                message=f"TRAVEL 事件的 character_id ({event.payload.get('character_id')}) 与更新的角色 ({char_id}) 不匹配",
                                                entity_id=char_id,
                                                fixable=False,
                                            ))
                
                elif entity_update.entity_type == "item":
                    # 物品的位置变更通常跟随 owner，这里主要检查是否有不合理的独立位置变更
                    item_id = entity_update.entity_id
                    if "location_id" in entity_update.updates and "owner_id" not in entity_update.updates:
                        # 如果只更新 location_id 而不更新 owner_id，可能是问题
                        # 但这不是强制性的，因为物品可能被放在某个地点
                        pass  # 暂时不检查物品的独立位置变更
        
        return violations
    
    # ==================== R6: 同一角色同一时刻不能在多个地点 ====================
    def _check_r6_single_location_per_character(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R6: 同一角色同一时刻不能在多个地点
        
        检查：
        1. temp_state 中每个角色只能有一个 location_id
        2. pending_events 中同一角色在同一时间（time_order）不能出现在不同地点
        """
        violations: List[RuleViolation] = []
        
        # 检查 temp_state 中角色的位置（应该已经在模型验证中检查，但这里再确认）
        character_locations: Dict[str, str] = {}  # char_id -> location_id
        
        for char_id, char in temp_state.entities.characters.items():
            if char_id in character_locations:
                # 这不应该发生，因为每个角色只有一个 location_id
                char_name = char.name
                violations.append(RuleViolation(
                    rule_id="R6",
                    rule_name="同一角色同一时刻不能在多个地点",
                    severity="error",
                    message=f"角色 '{char_name}' ({char_id}) 在状态中有多个位置定义",
                    entity_id=char_id,
                    fixable=False,
                ))
            character_locations[char_id] = char.location_id
        
        # 检查 pending_events 中同一角色在同一时间出现在不同地点
        # 按时间分组事件
        events_by_time: Dict[int, List[Event]] = {}  # time_order -> events
        
        for event in pending_events:
            time_order = event.time.order
            if time_order not in events_by_time:
                events_by_time[time_order] = []
            events_by_time[time_order].append(event)
        
        # 检查每个时间点的角色位置
        for time_order, events in events_by_time.items():
            char_locations_at_time: Dict[str, Set[str]] = {}  # char_id -> set of location_ids
            
            for event in events:
                # 检查 state_patch 中的位置更新（这是角色的最终位置）
                for entity_id, entity_update in event.state_patch.entity_updates.items():
                    if entity_update.entity_type == "character":
                        char_id = entity_update.entity_id
                        if "location_id" in entity_update.updates:
                            new_location = entity_update.updates["location_id"]
                            if char_id not in char_locations_at_time:
                                char_locations_at_time[char_id] = set()
                            char_locations_at_time[char_id].add(new_location)
                
                # 对于没有位置更新的角色，检查事件发生地点（但只对参与者）
                # 注意：对于 TRAVEL 事件，角色的位置已经在 state_patch 中更新，不需要再检查 where
                if event.type != "TRAVEL":
                    for actor_id in event.who.actors:
                        # 如果这个角色没有在 state_patch 中更新位置，使用事件发生地点
                        if actor_id not in char_locations_at_time:
                            char_locations_at_time[actor_id] = set()
                            char_locations_at_time[actor_id].add(event.where.location_id)
            
            # 检查是否有角色在同一时间出现在多个地点
            for char_id, locations in char_locations_at_time.items():
                if len(locations) > 1:
                    if char_id in current_state.entities.characters:
                        char_name = current_state.entities.characters[char_id].name
                    else:
                        char_name = char_id
                    violations.append(RuleViolation(
                        rule_id="R6",
                        rule_name="同一角色同一时刻不能在多个地点",
                        severity="error",
                        message=f"角色 '{char_name}' ({char_id}) 在时间点 {time_order} 同时出现在多个地点: {locations}",
                        entity_id=char_id,
                        fixable=False,
                    ))
        
        return violations
    
    # ==================== R7: 时间戳单调递增（回忆不推进time）====================
    def _check_r7_monotonic_timeline(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R7: 时间戳单调递增（回忆不推进time）
        
        检查：
        1. pending_events 的 time.order 应该单调递增
        2. temp_state 的 time.anchor.order 应该 >= current_state 的 time.anchor.order
        3. 如果事件是"回忆"类型，不应该推进时间
        """
        violations: List[RuleViolation] = []
        
        # 检查 pending_events 的时间顺序
        if pending_events:
            # 按 turn 和 time_order 排序
            sorted_events = sorted(pending_events, key=lambda e: (e.turn, e.time.order))
            
            # 检查时间是否单调递增
            current_time_order = current_state.time.anchor.order
            
            for event in sorted_events:
                event_time_order = event.time.order
                
                # 时间应该 >= 当前时间
                if event_time_order < current_time_order:
                    violations.append(RuleViolation(
                        rule_id="R7",
                        rule_name="时间戳单调递增（回忆不推进time）",
                        severity="error",
                        message=f"事件 '{event.summary}' (event_id: {event.event_id}) 的时间顺序值 ({event_time_order}) 小于当前时间 ({current_time_order})",
                        entity_id=None,
                        fixable=False,
                    ))
                
                # 更新当前时间（用于检查后续事件）
                current_time_order = max(current_time_order, event_time_order)
            
            # 检查事件之间的时间顺序（在排序之前检查原始顺序）
            # 按原始顺序检查，而不是排序后的顺序
            for i in range(len(pending_events) - 1):
                for j in range(i + 1, len(pending_events)):
                    prev_event = pending_events[i]
                    next_event = pending_events[j]
                    
                    # 如果 turn 相同，time_order 应该递增
                    if prev_event.turn == next_event.turn:
                        if prev_event.time.order > next_event.time.order:
                            violations.append(RuleViolation(
                                rule_id="R7",
                                rule_name="时间戳单调递增（回忆不推进time）",
                                severity="error",
                                message=f"同一轮次 ({prev_event.turn}) 中，事件 '{prev_event.summary}' 的时间顺序值 ({prev_event.time.order}) "
                                       f"大于后续事件 '{next_event.summary}' 的时间顺序值 ({next_event.time.order})",
                                entity_id=None,
                                fixable=False,
                            ))
                            break  # 每个事件只报告一次违反
        
        # 检查 temp_state 的时间是否 >= current_state 的时间
        if temp_state.time.anchor.order < current_state.time.anchor.order:
            violations.append(RuleViolation(
                rule_id="R7",
                rule_name="时间戳单调递增（回忆不推进time）",
                severity="error",
                message=f"临时状态的时间顺序值 ({temp_state.time.anchor.order}) 小于当前状态的时间顺序值 ({current_state.time.anchor.order})",
                entity_id=None,
                fixable=False,
            ))
        
        return violations
    
    # ==================== R8: immutable timeline constraints 不可违背 ====================
    def _check_r8_immutable_constraints(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R8: immutable timeline constraints 不可违背（除非进入架空模式）
        
        检查：
        1. immutable_events 中的事件不能被修改或删除
        2. constraints 中的硬约束不能被违反
        3. 检查是否有"架空模式"标记（如果进入架空模式，可以放宽约束）
        """
        violations: List[RuleViolation] = []
        
        # 检查是否进入架空模式（通过 constraints 或其他标记）
        # 这里简化处理：检查 constraints 中是否有"架空模式"标记
        is_alternate_mode = False
        for constraint in current_state.constraints.constraints:
            if constraint.type == "entity_state" and constraint.description and "架空" in constraint.description:
                is_alternate_mode = True
                break
        
        if is_alternate_mode:
            # 架空模式下，某些约束可以放宽，但核心约束仍然需要检查
            pass
        
        # 检查 immutable_events
        immutable_event_ids = set(current_state.constraints.immutable_events)
        
        # 检查 pending_events 中是否有试图修改或删除不可变事件的
        for event in pending_events:
            # 如果事件试图修改已发生的历史事件，应该检查
            # 这里简化处理：检查是否有事件试图改变已记录为不可变的状态
            if event.event_id in immutable_event_ids:
                violations.append(RuleViolation(
                    rule_id="R8",
                    rule_name="immutable timeline constraints 不可违背",
                    severity="error",
                    message=f"事件 '{event.event_id}' 已被标记为不可变事件，不能修改或删除",
                    entity_id=None,
                    fixable=False,
                ))
        
        # 检查 constraints 中的硬约束
        for constraint in current_state.constraints.constraints:
            constraint_id = constraint.id
            constraint_type = constraint.type
            entity_id = constraint.entity_id
            constraint_value = constraint.value
            
            # 根据约束类型检查
            if constraint_type == "entity_state":
                # 检查实体状态约束
                if entity_id:
                    # 检查 temp_state 中该实体的状态是否违反约束
                    if entity_id in temp_state.entities.characters:
                        char = temp_state.entities.characters[entity_id]
                        # 检查约束值
                        if "alive" in constraint_value:
                            if char.alive != constraint_value["alive"]:
                                char_name = char.name
                                violations.append(RuleViolation(
                                    rule_id="R8",
                                    rule_name="immutable timeline constraints 不可违背",
                                    severity="error",
                                    message=f"硬约束违反：角色 '{char_name}' ({entity_id}) 的状态违反约束 '{constraint.description}'",
                                    entity_id=entity_id,
                                    fixable=False,
                                ))
            
            elif constraint_type == "relationship":
                # 检查关系约束
                if entity_id:
                    # 检查关系是否被改变
                    if entity_id in temp_state.entities.characters:
                        char = temp_state.entities.characters[entity_id]
                        if "faction_id" in constraint_value:
                            if char.faction_id != constraint_value["faction_id"]:
                                char_name = char.name
                                violations.append(RuleViolation(
                                    rule_id="R8",
                                    rule_name="immutable timeline constraints 不可违背",
                                    severity="error",
                                    message=f"硬约束违反：角色 '{char_name}' ({entity_id}) 的阵营关系违反约束 '{constraint.description}'",
                                    entity_id=entity_id,
                                    fixable=False,
                                ))
            
            elif constraint_type == "unique_item":
                # 检查唯一物品约束（这个在 R1 中已经检查，但这里可以额外验证）
                if entity_id and entity_id in temp_state.entities.items:
                    item = temp_state.entities.items[entity_id]
                    if "owner_id" in constraint_value:
                        if item.owner_id != constraint_value["owner_id"]:
                            item_name = item.name
                            violations.append(RuleViolation(
                                rule_id="R8",
                                rule_name="immutable timeline constraints 不可违背",
                                severity="error",
                                message=f"硬约束违反：物品 '{item_name}' ({entity_id}) 的所有权违反约束 '{constraint.description}'",
                                entity_id=entity_id,
                                fixable=False,
                            ))
        
        return violations
    
    # ==================== R9: 阵营/关系变更需可追溯事件 ====================
    def _check_r9_traceable_relationship_change(
        self,
        current_state: CanonicalState,
        temp_state: CanonicalState,
        pending_events: List[Event],
    ) -> List[RuleViolation]:
        """
        R9: 阵营/关系变更需可追溯事件
        
        检查：
        1. faction_id 变更必须有 FACTION_CHANGE 事件（这个在 R4 中已经检查，但这里更详细）
        2. 关系变更（如角色之间的关系）应该有对应的事件
        3. 所有关系变更都应该有可追溯的 event_id
        """
        violations: List[RuleViolation] = []
        
        # 检查 faction_id 变更（R4 已经检查了事件类型，这里检查可追溯性）
        for event in pending_events:
            for entity_id, entity_update in event.state_patch.entity_updates.items():
                if entity_update.entity_type == "character":
                    char_id = entity_update.entity_id
                    
                    # 检查 faction_id 变更
                    if "faction_id" in entity_update.updates:
                        if char_id in current_state.entities.characters:
                            current_char = current_state.entities.characters[char_id]
                            current_faction = current_char.faction_id
                            new_faction = entity_update.updates["faction_id"]
                            
                            if current_faction != new_faction:
                                # 检查事件类型
                                if event.type != "FACTION_CHANGE":
                                    char_name = current_char.name
                                    violations.append(RuleViolation(
                                        rule_id="R9",
                                        rule_name="阵营/关系变更需可追溯事件",
                                        severity="error",
                                        message=f"角色 '{char_name}' ({char_id}) 的阵营从 '{current_faction}' 变为 '{new_faction}'，但事件类型不是 FACTION_CHANGE",
                                        entity_id=char_id,
                                        fixable=False,
                                    ))
                                else:
                                    # 验证 FACTION_CHANGE 事件的 payload
                                    if "character_id" not in event.payload:
                                        char_name = current_char.name
                                        violations.append(RuleViolation(
                                            rule_id="R9",
                                            rule_name="阵营/关系变更需可追溯事件",
                                            severity="error",
                                            message=f"FACTION_CHANGE 事件缺少 character_id 字段，无法追溯",
                                            entity_id=char_id,
                                            fixable=False,
                                        ))
                    
                    # 检查其他关系变更（如角色之间的关系，存储在 metadata 中）
                    # 这里简化处理，主要检查是否有明确的事件类型
                    if "metadata" in entity_update.updates:
                        metadata = entity_update.updates["metadata"]
                        # 如果 metadata 中包含关系变更（如 relationship_changes），应该有对应的事件
                        if "relationship_changes" in metadata:
                            # 关系变更应该有 RELATIONSHIP_CHANGE 事件
                            if event.type != "RELATIONSHIP_CHANGE":
                                char_name = current_state.entities.characters.get(char_id, Character(id=char_id, name=char_id, location_id="unknown")).name
                                violations.append(RuleViolation(
                                    rule_id="R9",
                                    rule_name="阵营/关系变更需可追溯事件",
                                    severity="error",
                                    message=f"角色 '{char_name}' ({char_id}) 的关系发生变更，但事件类型不是 RELATIONSHIP_CHANGE",
                                    entity_id=char_id,
                                    fixable=False,
                                ))
        
        return violations
    
    # ==================== R10: 草稿硬事实必须忠实于 canonical state ====================
    def _check_r10_draft_factual_consistency(
        self,
        current_state: CanonicalState,
        temp_state: Optional[CanonicalState],
        pending_events: Optional[List[Event]],
    ) -> List[RuleViolation]:
        """
        R10: 草稿硬事实必须忠实于 canonical state
        
        注意：这个方法主要在 validate_draft 中调用
        检查草稿文本中的硬事实是否与当前状态一致
        
        检查：
        1. 角色生死状态
        2. 角色位置
        3. 物品所有权
        4. 时间线信息
        """
        violations: List[RuleViolation] = []
        
        # 这个方法主要在 validate_draft 中使用
        # 如果是从 validate_event_patch 调用，则不需要检查（因为事件已经通过其他规则验证）
        if pending_events is not None:
            # 从 validate_event_patch 调用，不需要检查草稿
            return violations
        
        # 这里返回空列表，实际的草稿检查在 validate_draft 中实现
        return violations
    
    # ==================== 辅助方法 ====================
    def _apply_patches_to_state(
        self,
        current_state: CanonicalState,
        pending_events: List[Event],
    ) -> CanonicalState:
        """
        应用所有 pending_events 的 state_patch 到当前状态，构建临时状态
        
        注意：这是一个简化的实现，主要用于检查 pending_events 中的更新
        实际完整实现应该深度复制并应用所有更新
        """
        import copy
        temp_state = copy.deepcopy(current_state)
        
        # 应用每个事件的 state_patch（简化版，只更新 entities）
        for event in pending_events:
            patch = event.state_patch
            
            # 应用 entity_updates
            for entity_id, entity_update in patch.entity_updates.items():
                if entity_update.entity_type == "item":
                    if entity_id in temp_state.entities.items:
                        item = temp_state.entities.items[entity_id]
                        for key, value in entity_update.updates.items():
                            setattr(item, key, value)
                elif entity_update.entity_type == "character":
                    if entity_id in temp_state.entities.characters:
                        char = temp_state.entities.characters[entity_id]
                        for key, value in entity_update.updates.items():
                            setattr(char, key, value)
                # 其他类型类似处理...
            
            # 应用 player_updates
            if patch.player_updates:
                for key, value in patch.player_updates.items():
                    setattr(temp_state.player, key, value)
            
            # 应用 time_update
            if patch.time_update:
                if patch.time_update.calendar:
                    temp_state.time.calendar = patch.time_update.calendar
                if patch.time_update.anchor:
                    temp_state.time.anchor = patch.time_update.anchor
        
        return temp_state
    
    def _determine_action(
        self,
        violations: List[RuleViolation],
        current_state: CanonicalState,
        temp_state: Optional[CanonicalState],
    ) -> ValidationResult:
        """
        根据违反情况决定处理动作
        """
        if not violations:
            return ValidationResult(
                action="PASS",
                reasons=[],
                violations=[],
            )
        
        # 分类违反
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        fixable = [v for v in violations if v.fixable]
        
        reasons = [f"{v.rule_id}: {v.message}" for v in violations]
        
        # 如果有错误，需要 REWRITE 或 ASK_USER
        if errors:
            # 检查是否有需要用户澄清的情况
            needs_clarification = any(
                "多重归属" in v.message or "死亡角色" in v.message
                for v in errors
            )
            
            if needs_clarification:
                questions = [
                    f"规则 {v.rule_id} 违反: {v.message}。请确认如何处理？"
                    for v in errors
                ]
                return ValidationResult(
                    action="ASK_USER",
                    reasons=reasons,
                    violations=violations,
                    questions=questions,
                )
            else:
                return ValidationResult(
                    action="REWRITE",
                    reasons=reasons,
                    violations=violations,
                )
        
        # 如果只有警告且都可以修复，则 AUTO_FIX
        if warnings and len(fixable) == len(warnings):
            # 构建修复补丁
            fixes = self._build_fix_patch(violations, temp_state or current_state)
            return ValidationResult(
                action="AUTO_FIX",
                reasons=reasons,
                violations=violations,
                fixes=fixes,
            )
        
        # 其他情况需要 REWRITE
        return ValidationResult(
            action="REWRITE",
            reasons=reasons,
            violations=violations,
        )
    
    def _build_fix_patch(
        self,
        violations: List[RuleViolation],
        state: CanonicalState,
    ) -> Optional[StatePatch]:
        """
        构建自动修复补丁
        """
        entity_updates: Dict[str, EntityUpdate] = {}
        
        for violation in violations:
            if violation.fixable and violation.entity_id:
                entity_id = violation.entity_id
                
                # R2: 物品位置修复
                if violation.rule_id == "R2":
                    if entity_id in state.entities.items:
                        item = state.entities.items[entity_id]
                        if item.owner_id:
                            # 确定正确的 location_id
                            if item.owner_id in state.entities.characters:
                                owner_char = state.entities.characters[item.owner_id]
                                correct_location_id = owner_char.location_id
                            elif item.owner_id in state.entities.locations:
                                correct_location_id = item.owner_id
                            else:
                                continue
                            
                            if entity_id not in entity_updates:
                                entity_updates[entity_id] = EntityUpdate(
                                    entity_type="item",
                                    entity_id=entity_id,
                                    updates={},
                                )
                            entity_updates[entity_id].updates["location_id"] = correct_location_id
        
        if entity_updates:
            return StatePatch(entity_updates=entity_updates)
        
        return None
    
    def _check_character_action_in_text(self, text: str, character_name: str) -> bool:
        """
        检查角色是否在文本中表现为行动或说话（简化版）
        
        这是一个简化的实现，实际应该使用更复杂的 NLP 方法
        """
        # 简单的关键词检查
        action_keywords = ["说", "道", "做", "行动", "前往", "拿起", "放下", "使用"]
        
        # 检查角色名称附近是否有动作关键词
        char_index = text.find(character_name)
        if char_index == -1:
            return False
        
        # 检查角色名称前后一定范围内是否有动作关键词
        context_start = max(0, char_index - 20)
        context_end = min(len(text), char_index + len(character_name) + 20)
        context = text[context_start:context_end]
        
        return any(keyword in context for keyword in action_keywords)
    
    def _extract_and_check_hard_facts(self, draft_text: str, current_state: CanonicalState) -> List[RuleViolation]:
        """
        从草稿文本中提取硬事实并与当前状态对比
        
        这是一个简化的实现，实际应该使用更复杂的 NLP 方法
        """
        violations: List[RuleViolation] = []
        
        # 检查角色生死状态
        for char_id, char in current_state.entities.characters.items():
            char_name = char.name
            is_alive = char.alive
            
            # 检查文本中是否提到角色死亡（如果角色实际是活的）
            if is_alive:
                death_keywords = ["死亡", "死了", "去世", "逝世", "被杀", "被斩"]
                for keyword in death_keywords:
                    if keyword in draft_text and char_name in draft_text:
                        # 检查关键词和角色名称是否在相近位置
                        char_index = draft_text.find(char_name)
                        keyword_index = draft_text.find(keyword)
                        if char_index != -1 and keyword_index != -1:
                            distance = abs(char_index - keyword_index)
                            if distance < 50:  # 在50个字符内
                                violations.append(RuleViolation(
                                    rule_id="R10",
                                    rule_name="草稿硬事实必须忠实于 canonical state",
                                    severity="error",
                                    message=f"草稿中描述角色 '{char_name}' ({char_id}) 死亡，但当前状态中该角色是存活的",
                                    entity_id=char_id,
                                    fixable=False,
                                ))
                                break
        
        # 检查角色位置（简化版：检查是否提到角色在不正确的位置）
        # 使用句子分割来更准确地检测
        import re
        
        # 简单的句子分割（按句号、问号、感叹号）
        sentences = re.split(r'[。！？]', draft_text)
        
        for char_id, char in current_state.entities.characters.items():
            char_name = char.name
            current_location_id = char.location_id
            
            # 获取当前地点名称
            if current_location_id in current_state.entities.locations:
                current_location_name = current_state.entities.locations[current_location_id].name
                
                # 检查每个句子
                for sentence in sentences:
                    if char_name in sentence:
                        # 检查句子中是否提到错误的地点
                        for loc_id, location in current_state.entities.locations.items():
                            if loc_id != current_location_id:
                                location_name = location.name
                                if location_name in sentence:
                                    # 检查是否有位置相关的关键词
                                    location_keywords = ["在", "位于", "到达", "来到", "到了"]
                                    if any(kw in sentence for kw in location_keywords):
                                        # 检查角色名称和地点名称的相对位置
                                        char_pos = sentence.find(char_name)
                                        loc_pos = sentence.find(location_name)
                                        if char_pos != -1 and loc_pos != -1:
                                            # 检查是否有位置关键词在两者之间或附近
                                            between_text = sentence[min(char_pos, loc_pos):max(char_pos, loc_pos) + len(max(char_name, location_name, key=len))]
                                            if any(kw in between_text for kw in location_keywords):
                                                violations.append(RuleViolation(
                                                    rule_id="R10",
                                                    rule_name="草稿硬事实必须忠实于 canonical state",
                                                    severity="error",
                                                    message=f"草稿中描述角色 '{char_name}' ({char_id}) 在 '{location_name}'，但当前状态中该角色在 '{current_location_name}'",
                                                    entity_id=char_id,
                                                    fixable=False,
                                                ))
                                                break
        
        return violations

