# Consistency Gate（一致性闸门）

## 概述

Consistency Gate 是 Immersive Story Memory Engine 的核心校验模块，用于确保状态和事件的一致性。它实现了 10 条规则（R1-R10），**已全部完成**。

## 功能

### 输入
- `current_state: CanonicalState` - 当前唯一真相状态
- `draft_text: str` (可选) - LLM 生成的草稿文本（用于草稿校验）
- `pending_events: List[Event]` (可选) - 待写入的事件列表（用于事件补丁校验）

### 输出
- `action: Literal["PASS", "AUTO_FIX", "REWRITE", "ASK_USER"]` - 处理动作
- `reasons: List[str]` - 原因列表
- `violations: List[RuleViolation]` - 违反的规则列表
- `fixes: Optional[StatePatch]` - 自动修复补丁（AUTO_FIX 时提供）
- `questions: Optional[List[str]]` - 澄清问题（ASK_USER 时提供）

## 已实现的规则

### R1: 唯一物品不能多重归属

**规则描述**: 唯一物品在多个事件中不能被分配给不同的拥有者。

**检查逻辑**:
- 检查 `pending_events` 中是否有同一个唯一物品被分配给多个不同的 `owner_id`
- 如果检测到，返回 `REWRITE` 或 `ASK_USER`

**示例**:
```python
# ❌ 违反：同一个唯一物品在两个事件中被分配给不同的人
event1: seal_001 -> owner: liubei
event2: seal_001 -> owner: player_001

# ✅ 通过：唯一物品只在一个事件中转移
event1: seal_001 -> owner: liubei
```

### R2: 物品位置与归属一致

**规则描述**: 物品的 `location_id` 应该与 `owner_id` 的位置一致。

**规则细节**:
- 如果物品的 `owner_id` 是人物，`location_id` 应该等于人物的 `location_id`
- 如果物品的 `owner_id` 是地点，`location_id` 应该等于 `owner_id`
- **可自动修复**: 根据 `owner_id` 自动修正 `location_id`

**检查逻辑**:
- 检查 `temp_state` 中所有物品的 `location_id` 是否与 `owner_id` 一致
- 如果不一致，标记为 `warning` 级别，`fixable=True`

**示例**:
```python
# ❌ 违反：物品在人物A手中，但 location_id 指向地点B
item.owner_id = "caocao"  # 人物在 luoyang
item.location_id = "xuchang"  # 不一致

# ✅ 自动修复：将 location_id 修正为 caocao 的位置
fixes: item.location_id = "luoyang"
```

### R3: 死亡角色不能行动/说话

**规则描述**: 已死亡的角色不能作为事件的行动者（actors），也不能在没有 REVIVAL 事件的情况下被复活。

**检查逻辑**:
1. 检查 `pending_events` 中的 `actors` 列表，如果包含已死亡角色，则违反
2. 检查 `state_patch` 中是否有死亡角色被更新为 `alive=True`，但事件类型不是 `REVIVAL`
3. **例外**: `DEATH` 和 `REVIVAL` 事件中，死亡角色可以作为参与者

**示例**:
```python
# ❌ 违反：死亡角色作为行动者
dead_char.alive = False
event.who.actors = ["dead_char"]  # 违反 R3

# ❌ 违反：没有 REVIVAL 事件就复活
event.type = "OTHER"
event.state_patch.entity_updates["dead_char"].updates["alive"] = True  # 违反 R3

# ✅ 通过：REVIVAL 事件可以复活
event.type = "REVIVAL"
event.state_patch.entity_updates["dead_char"].updates["alive"] = True  # 通过
```

### R4: 生死/状态变更必须显式事件

**规则描述**: 角色的生死状态或重要状态（如阵营）变更必须有对应的事件类型。

**检查逻辑**:
- 如果角色的 `alive` 从 `True` 变为 `False`，事件类型必须是 `DEATH`
- 如果角色的 `alive` 从 `False` 变为 `True`，事件类型必须是 `REVIVAL`
- 如果角色的 `faction_id` 发生变化，事件类型必须是 `FACTION_CHANGE`

**示例**:
```python
# ❌ 违反：改变 alive 状态但没有 DEATH 事件
event.type = "OTHER"
event.state_patch.entity_updates["char"].updates["alive"] = False  # 违反 R4

# ✅ 通过：DEATH 事件可以改变 alive 状态
event.type = "DEATH"
event.state_patch.entity_updates["char"].updates["alive"] = False  # 通过
```

### R5: 位置变化必须由 move 事件解释（防瞬移）

**规则描述**: 角色的 `location_id` 变更必须有对应的 `TRAVEL` 事件，防止角色瞬移。

**检查逻辑**:
- 检查 `state_patch` 中是否有角色的 `location_id` 变更
- 如果有变更，事件类型必须是 `TRAVEL`
- 验证 `TRAVEL` 事件的 `payload.character_id` 是否匹配

**示例**:
```python
# ❌ 违反：改变位置但没有 TRAVEL 事件
event.type = "OTHER"
event.state_patch.entity_updates["char"].updates["location_id"] = "xuchang"  # 违反 R5

# ✅ 通过：TRAVEL 事件可以改变位置
event.type = "TRAVEL"
event.payload = {"character_id": "char", "from_location_id": "luoyang", "to_location_id": "xuchang"}
event.state_patch.entity_updates["char"].updates["location_id"] = "xuchang"  # 通过
```

### R6: 同一角色同一时刻不能在多个地点

**规则描述**: 同一角色在同一时间点（`time_order`）不能同时出现在多个地点。

**检查逻辑**:
- 检查 `pending_events` 中同一角色在同一 `time_order` 是否出现在不同地点
- 对于 `TRAVEL` 事件，只考虑 `state_patch` 中的最终位置，不考虑事件发生地点

**示例**:
```python
# ❌ 违反：同一角色在同一时间出现在两个地点
event1.time.order = 11
event1.who.actors = ["char"]
event1.state_patch.entity_updates["char"].updates["location_id"] = "luoyang"

event2.time.order = 11  # 同一时间
event2.who.actors = ["char"]  # 同一角色
event2.state_patch.entity_updates["char"].updates["location_id"] = "xuchang"  # 违反 R6
```

### R7: 时间戳单调递增（回忆不推进time）

**规则描述**: 时间顺序值（`time.order`）必须单调递增，不能倒退。

**检查逻辑**:
- 检查 `pending_events` 的 `time.order` 是否 >= 当前状态的 `time.anchor.order`
- 检查同一轮次中事件的 `time.order` 是否单调递增
- 检查 `temp_state` 的时间是否 >= `current_state` 的时间

**示例**:
```python
# ❌ 违反：时间倒退
current_state.time.anchor.order = 10
event.time.order = 5  # 违反 R7

# ❌ 违反：同一轮次中时间倒退
event1.time.order = 12
event2.time.order = 11  # 违反 R7

# ✅ 通过：时间单调递增
event1.time.order = 11
event2.time.order = 12  # 通过
```

### R8: immutable timeline constraints 不可违背

**规则描述**: 硬约束（immutable constraints）不能被违反，除非进入架空模式。

**检查逻辑**:
- 检查 `constraints.immutable_events` 中的事件是否被修改或删除
- 检查 `constraints.constraints` 中的硬约束是否被违反
  - `entity_state`: 检查实体状态约束（如角色必须存活）
  - `relationship`: 检查关系约束（如阵营关系）
  - `unique_item`: 检查唯一物品约束

**示例**:
```python
# ❌ 违反：试图杀死被约束为必须存活的角色
constraint = Constraint(
    type="entity_state",
    entity_id="caocao",
    value={"alive": True}
)
event.type = "DEATH"
event.state_patch.entity_updates["caocao"].updates["alive"] = False  # 违反 R8
```

### R9: 阵营/关系变更需可追溯事件

**规则描述**: 阵营和关系变更必须有对应的事件类型，且事件 payload 必须包含可追溯信息。

**检查逻辑**:
- 检查 `faction_id` 变更是否有 `FACTION_CHANGE` 事件
- 验证 `FACTION_CHANGE` 事件的 `payload.character_id` 是否匹配
- 检查关系变更（metadata 中的 relationship_changes）是否有 `RELATIONSHIP_CHANGE` 事件

**示例**:
```python
# ❌ 违反：FACTION_CHANGE 事件缺少 character_id
event.type = "FACTION_CHANGE"
event.payload = {}  # 缺少 character_id，无法追溯
```

### R10: 草稿硬事实必须忠实于 canonical state

**规则描述**: LLM 生成的草稿文本中的硬事实必须与当前状态一致。

**检查逻辑**:
- 检查草稿中是否描述死亡角色为存活状态
- 检查草稿中是否描述存活角色为死亡状态
- 检查草稿中是否描述角色在错误的位置
- 使用句子分割和关键词匹配来检测硬事实冲突

**示例**:
```python
# ❌ 违反：草稿中描述角色在错误的位置
current_state: caocao.location_id = "luoyang"
draft_text = "曹操在许昌说话。"  # 违反 R10

# ❌ 违反：草稿中描述存活角色死亡
current_state: caocao.alive = True
draft_text = "曹操死亡了。"  # 违反 R10
```

## 使用方法

### 校验事件补丁

```python
from backend.gate import ConsistencyGate
from backend.models import CanonicalState, Event

gate = ConsistencyGate()
current_state = ...  # 当前状态
pending_events = [...]  # 待写入的事件列表

result = gate.validate_event_patch(current_state, pending_events)

if result.action == "PASS":
    # 可以写入
    pass
elif result.action == "AUTO_FIX":
    # 自动修复，应用 result.fixes
    pass
elif result.action == "REWRITE":
    # 需要重写事件
    pass
elif result.action == "ASK_USER":
    # 需要用户澄清，查看 result.questions
    pass
```

### 校验草稿文本

```python
result = gate.validate_draft(current_state, draft_text)

# 检查是否有硬事实冲突
if result.action != "PASS":
    print("草稿中存在硬事实冲突:")
    for violation in result.violations:
        print(f"  - {violation.message}")
```

## 处理动作说明

### PASS
所有规则校验通过，可以继续处理。

### AUTO_FIX
检测到可自动修复的违反（目前主要是 R2），系统会自动生成修复补丁。

```python
if result.action == "AUTO_FIX":
    # 应用修复补丁
    fixed_patch = result.fixes
    # 合并到事件或状态中
```

### REWRITE
检测到需要重写的违反，建议重新生成事件或草稿。

### ASK_USER
检测到需要用户澄清的违反（如 R1 多重归属），系统会生成澄清问题。

```python
if result.action == "ASK_USER":
    for question in result.questions:
        print(question)
    # 等待用户输入
```

## 测试

运行单元测试：

```bash
# R1-R3 测试
python -m pytest tests/unit/test_consistency_gate_r1_r3.py -v

# R4-R7 测试
python -m pytest tests/unit/test_consistency_gate_r4_r7.py -v

# R8-R10 测试
python -m pytest tests/unit/test_consistency_gate_r8_r10.py -v

# 所有测试
python -m pytest tests/unit/test_consistency_gate_*.py -v
```

测试覆盖：
- ✅ R1: 唯一物品多重归属检测
- ✅ R2: 物品位置一致性检测和自动修复
- ✅ R3: 死亡角色行动检测
- ✅ R4: 生死/状态变更显式事件检测
- ✅ R5: 位置变化 TRAVEL 事件检测
- ✅ R6: 同一角色同一时刻多地点检测
- ✅ R7: 时间戳单调递增检测
- ✅ R8: immutable timeline constraints 检测
- ✅ R9: 阵营/关系变更可追溯性检测
- ✅ R10: 草稿硬事实一致性检测
- ✅ 多条规则同时违反的处理

## 规则总结

所有 10 条规则已实现并测试通过：

1. ✅ **R1**: 唯一物品不能多重归属
2. ✅ **R2**: 物品位置与归属一致（支持 AUTO_FIX）
3. ✅ **R3**: 死亡角色不能行动/说话
4. ✅ **R4**: 生死/状态变更必须显式事件
5. ✅ **R5**: 位置变化必须由 move 事件解释（防瞬移）
6. ✅ **R6**: 同一角色同一时刻不能在多个地点
7. ✅ **R7**: 时间戳单调递增（回忆不推进time）
8. ✅ **R8**: immutable timeline constraints 不可违背
9. ✅ **R9**: 阵营/关系变更需可追溯事件
10. ✅ **R10**: 草稿硬事实必须忠实于 canonical state

## 架构设计

### 规则注册
规则通过 `self.rules` 字典注册，键为规则ID（如 "R1"），值为检查函数。

### 临时状态构建
`_apply_patches_to_state()` 方法将 `pending_events` 的 `state_patch` 应用到当前状态，构建临时状态用于校验。

### 动作决策
`_determine_action()` 方法根据违反的规则类型和严重程度决定处理动作：
- 有 `error` 级别违反 → `REWRITE` 或 `ASK_USER`
- 只有 `warning` 级别且可修复 → `AUTO_FIX`
- 无违反 → `PASS`

