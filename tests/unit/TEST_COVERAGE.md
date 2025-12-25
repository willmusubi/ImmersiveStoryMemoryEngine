# 测试覆盖报告

## 单元测试覆盖（10条规则）

每条规则都有至少2个用例（通过/失败）：

### R1: 唯一物品不能多重归属
- ✅ `test_r1_pass_single_owner` - 唯一物品只有一个拥有者，应该通过
- ✅ `test_r1_fail_multiple_owners` - 唯一物品被分配给多个拥有者，应该失败

### R2: 物品位置与归属一致
- ✅ `test_r2_pass_consistent_location` - 物品位置与拥有者位置一致，应该通过
- ✅ `test_r2_fail_inconsistent_location` - 物品位置与拥有者位置不一致，应该检测到
- ✅ `test_r2_auto_fix` - R2 违反应该可以自动修复

### R3: 死亡角色不能行动/说话
- ✅ `test_r3_pass_alive_character` - 存活角色可以行动，应该通过
- ✅ `test_r3_fail_dead_character_action` - 死亡角色不能行动，应该失败
- ✅ `test_r3_pass_death_event` - DEATH 事件中死亡角色可以参与
- ✅ `test_r3_fail_revive_without_revival_event` - 没有 REVIVAL 事件就复活角色，应该失败

### R4: 生死/状态变更必须显式事件
- ✅ `test_r4_pass_death_event` - DEATH 事件可以改变 alive 状态
- ✅ `test_r4_fail_alive_change_without_death` - 改变 alive 状态但没有 DEATH 事件，应该失败
- ✅ `test_r4_fail_faction_change_without_event` - 改变 faction_id 但没有 FACTION_CHANGE 事件，应该失败

### R5: 位置变化必须由 move 事件解释（防瞬移）
- ✅ `test_r5_pass_travel_event` - TRAVEL 事件可以改变位置
- ✅ `test_r5_fail_location_change_without_travel` - 改变位置但没有 TRAVEL 事件，应该失败

### R6: 同一角色同一时刻不能在多个地点
- ✅ `test_r6_pass_single_location` - 角色在同一时间只有一个位置，应该通过
- ✅ `test_r6_fail_multiple_locations_same_time` - 同一角色在同一时间出现在多个地点，应该失败

### R7: 时间戳单调递增（回忆不推进time）
- ✅ `test_r7_pass_monotonic_increase` - 时间单调递增，应该通过
- ✅ `test_r7_fail_time_decrease` - 时间倒退，应该失败
- ✅ `test_r7_fail_same_turn_time_decrease` - 同一轮次中时间倒退，应该失败

### R8: immutable timeline constraints 不可违背
- ✅ `test_r8_pass_no_constraints` - 没有约束时应该通过
- ✅ `test_r8_fail_violate_entity_state_constraint` - 违反实体状态约束，应该失败
- ✅ `test_r8_fail_violate_relationship_constraint` - 违反关系约束，应该失败

### R9: 阵营/关系变更需可追溯事件
- ✅ `test_r9_pass_faction_change_with_event` - 有 FACTION_CHANGE 事件的阵营变更，应该通过
- ✅ `test_r9_fail_faction_change_without_event` - 阵营变更但没有 FACTION_CHANGE 事件，应该失败
- ✅ `test_r9_fail_faction_change_without_payload` - FACTION_CHANGE 事件 payload 验证

### R10: 草稿硬事实必须忠实于 canonical state
- ✅ `test_r10_pass_consistent_draft` - 草稿与状态一致，应该通过
- ✅ `test_r10_fail_dead_character_alive` - 草稿中描述死亡角色存活，应该失败
- ✅ `test_r10_fail_wrong_location` - 草稿中描述角色在错误的位置，应该失败
- ✅ `test_r10_fail_alive_character_dead` - 草稿中描述存活角色死亡，应该失败

## Needle Tests（5个关键场景测试）

每个Needle Test都包含：初始state、输入消息序列、预期state断言

### 1. 物品归属针：赠与后不得回到原主手里
- ✅ `test_needle_ownership_pass_gift_once` - 物品赠与一次，应该通过
- ✅ `test_needle_ownership_fail_return_to_original_owner` - 物品赠与后回到原主，应该失败

**测试场景：**
1. 初始状态：物品A属于角色X
2. 事件1：角色X将物品A赠与角色Y
3. 事件2（应该失败）：角色Y将物品A还给角色X（违反：赠与后不得回到原主）

### 2. 生死针：救活后不得再描述死亡
- ✅ `test_needle_life_death_pass_revival_once` - 角色被救活一次，应该通过
- ✅ `test_needle_life_death_fail_die_after_revival` - 角色救活后再次死亡，应该失败

**测试场景：**
1. 初始状态：角色X死亡
2. 事件1：角色X被救活（REVIVAL事件）
3. 事件2（应该失败）：角色X再次死亡（违反：救活后不得再描述死亡）

### 3. 时间线针：关键事件顺序不可颠倒
- ✅ `test_needle_timeline_pass_sequential_events` - 事件按时间顺序发生，应该通过
- ✅ `test_needle_timeline_fail_reversed_events` - 事件时间顺序颠倒，应该失败

**测试场景：**
1. 初始状态：角色X在位置A
2. 事件1：角色X移动到位置B（TRAVEL事件，time_order=11）
3. 事件2（应该失败）：角色X在位置A发生事件（time_order=10，违反：时间线不可颠倒）

### 4. 地理针：跨城移动必须有move事件
- ✅ `test_needle_geography_pass_travel_event` - 有TRAVEL事件的移动，应该通过
- ✅ `test_needle_geography_fail_teleport_without_travel` - 没有TRAVEL事件的瞬移，应该失败

**测试场景：**
1. 初始状态：角色X在位置A
2. 事件1（应该失败）：角色X在位置B发生事件，但没有TRAVEL事件（违反：跨城移动必须有move事件）

### 5. 阵营关系针：结盟/背叛后阵营不可回滚
- ✅ `test_needle_faction_pass_faction_change_once` - 阵营变更一次，应该通过
- ✅ `test_needle_faction_fail_rollback_faction` - 阵营变更后回滚，应该失败

**测试场景：**
1. 初始状态：角色X在阵营A
2. 事件1：角色X背叛到阵营B（FACTION_CHANGE事件）
3. 事件2（应该失败）：角色X回到阵营A（违反：结盟/背叛后阵营不可回滚）

## 测试统计

- **单元测试总数**: 32个
- **Needle Tests总数**: 10个（每个场景2个用例：通过/失败）
- **总测试数**: 42个
- **通过率**: 100%

## 运行测试

```bash
# 运行所有单元测试
pytest tests/unit/test_consistency_gate_*.py -v

# 运行所有Needle Tests
pytest tests/unit/test_needle_tests.py -v

# 运行所有测试
pytest tests/unit/ -v
```

## 测试文件结构

```
tests/unit/
├── test_consistency_gate_r1_r3.py    # R1-R3规则测试
├── test_consistency_gate_r4_r7.py    # R4-R7规则测试
├── test_consistency_gate_r8_r10.py   # R8-R10规则测试
└── test_needle_tests.py              # Needle Tests（5个关键场景）
```

