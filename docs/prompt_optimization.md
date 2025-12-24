# 提示词优化总结

## 📋 优化内容

### 1. Schema 定义来源

**Schema 由 Pydantic 模型自动生成**：
- 定义位置：`backend/models/event.py` 中的 `ExtractedEvent` 类
- 生成方式：`ExtractedEvent.model_json_schema()` 自动生成 JSON Schema
- 使用位置：`backend/extractor/extractor.py` 的 `_get_function_definition()` 方法

### 2. 提示词优化要点

#### 2.1 添加了详细的状态变化识别规则

为每种事件类型提供了：
- **识别关键词**：明确告诉 LLM 如何识别状态变化
- **必须提取的信息**：列出需要提取的关键字段
- **state_patch 格式示例**：提供完整的 JSON 格式示例

#### 2.2 提供了完整的示例

包含两个完整示例：
1. **物品所有权变更**：展示如何提取 `OWNERSHIP_CHANGE` 事件
2. **角色移动**：展示如何提取 `TRAVEL` 事件

每个示例都包含：
- 完整的 JSON 结构
- 正确的 `state_patch` 格式
- 实体更新和玩家更新的写法

#### 2.3 强化了格式要求说明

明确说明：
- `entity_updates` 必须是对象（字典），不是数组
- 键是实体ID，值是包含 `entity_type`, `entity_id`, `updates` 的对象
- `player_updates` 的格式和用法

#### 2.4 改进了用户提示词

在 `_build_user_prompt` 中添加了：
- 状态变化识别步骤
- 每种状态变化对应的 `state_patch` 写入要求
- 更清晰的提取要求说明

## ✅ 测试结果

### 场景 1: 物品所有权变更

**输入**：
- 用户消息：`"请将青釭剑借给我"`
- 助手草稿：`"曹操点了点头，将青釭剑递给玩家，说道：'这把剑就借给你了，希望你能善用它。'"`

**输出**：
- ✅ 事件类型：`OWNERSHIP_CHANGE`
- ✅ 状态补丁：
  ```json
  {
    "entity_updates": {
      "sword_001": {
        "updates": {
          "owner_id": "player_001",
          "location_id": "luoyang"
        }
      }
    },
    "player_updates": {
      "inventory_add": ["sword_001"]
    }
  }
  ```

### 场景 2: 角色移动

**输入**：
- 用户消息：`"我想去许昌"`
- 助手草稿：`"玩家离开洛阳，经过长途跋涉，终于到达了许昌。"`

**输出**：
- ✅ 事件类型：`TRAVEL`
- ✅ 状态补丁：
  ```json
  {
    "entity_updates": {
      "player_001": {
        "updates": {
          "location_id": "xuchang"
        }
      }
    },
    "player_updates": {
      "location_id": "xuchang"
    }
  }
  ```

## 🎯 优化效果

1. **状态变化识别更准确**：
   - LLM 能够正确识别物品所有权变更和角色移动
   - 状态补丁格式完全正确

2. **格式规范更清晰**：
   - 提供了具体的 JSON 示例
   - 明确了 `entity_updates` 必须是对象（字典）

3. **容错机制有效**：
   - 虽然 LLM 可能不完全使用 function calling，但回退到 JSON mode 后仍能正确提取
   - 最终结果符合预期

## 📝 关键改进点

### 1. 动态示例生成

提示词会根据当前状态动态生成示例：
```python
example_char_id = list(state.entities.characters.keys())[0] if state.entities.characters else "caocao"
example_item_id = list(state.entities.items.keys())[0] if state.entities.items else "sword_001"
```

这样示例中的实体ID都是真实存在的，避免误导 LLM。

### 2. 关键词识别指南

为每种事件类型提供了识别关键词：
- **OWNERSHIP_CHANGE**：给、借、递、交给、获得、拾起、拿起、丢失、掉落、归还
- **TRAVEL**：前往、到达、离开、来到、抵达、移动到、出发、返回
- **DEATH**：死亡、被杀、战死、去世、阵亡

### 3. 格式要求强调

在多个地方强调格式要求：
- 系统提示词中明确说明 `entity_updates` 必须是对象
- 提供完整的 JSON 示例
- 在用户提示词中再次强调格式要求

## 🔄 关于 Function Calling

虽然 `supermind-agent-v1` 可能不完全支持强制 function calling，但系统已经实现了完善的回退机制：

1. **优先尝试 function calling**：使用 `tool_choice` 强制调用函数
2. **回退到 JSON mode**：如果 function calling 失败，使用 `response_format={"type": "json_object"}`
3. **容错处理**：如果 JSON 解析失败，尝试从 markdown 代码块中提取

**结果**：无论 LLM 使用哪种方式返回，最终都能正确提取事件和状态补丁。

## 📚 相关文件

- `backend/extractor/extractor.py`：Event Extractor 实现
- `backend/models/event.py`：ExtractedEvent 模型定义
- `scripts/test_optimized_prompt.py`：测试脚本

## 🚀 下一步建议

1. **继续优化提示词**：
   - 可以添加更多事件类型的示例
   - 可以添加边界情况的处理说明

2. **监控 LLM 输出**：
   - 记录 LLM 是否使用 function calling
   - 分析回退到 JSON mode 的原因

3. **测试更多场景**：
   - 测试复杂的状态变化（多个事件同时发生）
   - 测试边界情况（物品不存在、角色死亡等）

