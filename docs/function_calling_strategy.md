# Function Calling 策略说明

## 关于 supermind-agent-v1 的 Function Call 支持

### 当前情况

`supermind-agent-v1` 是一个多工具代理模型，它可能：
- ✅ 支持部分 function calling（用于工具调用）
- ❌ 可能不支持强制 function calling（`tool_choice: {"type": "function"}`）
- ✅ 支持自动选择是否调用函数（`tool_choice: "auto"`）

### 我们的实现策略

我们采用了**混合策略**：

1. **优先尝试 Function Calling**
   - 定义 `extract_events` 函数
   - 尝试强制调用（`tool_choice: {"type": "function"}`）
   - 如果失败，回退到自动模式（`tool_choice: "auto"`）

2. **自动回退到 JSON 模式**
   - 如果 function calling 完全失败
   - 使用 `response_format: {"type": "json_object"}`
   - 从 `message.content` 中解析 JSON

3. **容错机制**
   - 如果 JSON 解析失败，生成默认事件
   - 确保系统始终可用

## 关于创建 Function Set 调用 State Machine

### 你的想法是对的！

**可以创建一个 function set 来让 LLM 查询和操作 state machine**，但需要注意：

### 适用场景

1. **查询状态**（推荐）
   - `get_current_state(story_id)` - 获取当前状态
   - `get_character_info(character_id)` - 获取角色信息
   - `get_location_info(location_id)` - 获取地点信息
   - `list_recent_events(story_id, limit)` - 获取最近事件

2. **验证一致性**（可选）
   - `validate_event(event_data)` - 验证事件是否符合规则
   - `check_constraints(constraint_type)` - 检查约束

3. **不建议的操作**
   - ❌ 直接修改状态（应该通过事件驱动）
   - ❌ 绕过 Consistency Gate（会破坏一致性）

### 实现建议

如果要在 Event Extractor 中添加查询功能，可以这样：

```python
def _get_function_set(self) -> List[Dict[str, Any]]:
    """获取完整的 Function Set（包括查询和提取）"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_state",
                "description": "获取当前游戏状态",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_events",
                "description": "提取事件",
                "parameters": {...}
            }
        }
    ]
```

### 当前架构的优势

**当前设计（LLM 只负责提取，不直接操作状态）的优势：**

1. ✅ **职责清晰**：LLM 只负责理解文本并提取事件
2. ✅ **安全性**：所有状态变更都经过 Consistency Gate 验证
3. ✅ **可追溯性**：所有变更都有对应的事件记录
4. ✅ **可测试性**：提取逻辑和状态管理分离

### 建议

**对于 Event Extractor：**
- 保持当前设计（LLM 只提取事件）
- 如果需要查询状态，可以在系统提示词中包含状态摘要（已实现）

**对于其他场景（如 RAG 增强的对话生成）：**
- 可以考虑添加查询函数
- 让 LLM 能够查询状态来生成更准确的回复

## 总结

1. ✅ Function calling 已实现，有完整的回退机制
2. ✅ 创建 function set 调用 state machine 是可行的
3. ⚠️ 但要注意：不要绕过 Consistency Gate 直接修改状态
4. 💡 建议：在需要查询的场景使用 function calling，在提取场景保持当前设计

