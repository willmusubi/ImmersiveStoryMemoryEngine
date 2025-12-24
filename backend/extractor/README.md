# Event Extractor（事件提取器）

## 概述

Event Extractor 负责从 LLM 生成的对话草稿中提取结构化事件。它使用 OpenAI API（支持自定义 base_url）调用 LLM，通过严格的 JSON Schema 强制输出结构化数据。

## 功能

### 输入
- `canonical_state: CanonicalState` - 当前唯一真相状态
- `user_message: str` - 用户消息
- `assistant_draft: str` - 助手生成的草稿
- `turn: int` - 当前轮次

### 输出
- `events: List[Event]` - 提取的事件列表（至少 1 个）
- `open_questions: List[str]` - 需要用户澄清的问题
- `requires_user_input: bool` - 是否需要用户输入

## 配置

### 环境变量

在 `.env` 文件中设置：

```bash
# OpenAI API 配置
SUPER_MIND_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://space.ai-builders.com/backend/v1
OPENAI_MODEL=gpt-4o-mini
```

### 初始化

```python
from backend.extractor import EventExtractor

# 使用默认配置（从环境变量读取）
extractor = EventExtractor()

# 或自定义配置
extractor = EventExtractor(
    api_key="custom_key",
    base_url="https://custom.api.com/v1",
    model="gpt-4"
)
```

## 使用方法

### 基本使用

```python
from backend.extractor import EventExtractor
from backend.models import CanonicalState

extractor = EventExtractor()
result = await extractor.extract_events(
    canonical_state=current_state,
    user_message="玩家向曹操打招呼",
    assistant_draft="玩家向曹操打招呼，曹操点头回应。",
    turn=1,
)

# 检查结果
if result.requires_user_input:
    print("需要用户澄清:")
    for question in result.open_questions:
        print(f"  - {question}")
else:
    print(f"提取到 {len(result.events)} 个事件:")
    for event in result.events:
        print(f"  - {event.summary} ({event.type})")
```

## 核心特性

### 1. 严格的 JSON Schema 输出

使用 OpenAI 的 `json_schema` response_format 强制输出结构化数据：

- 自动验证输出格式
- 解析失败时自动重试（最多 1 次）
- 支持从 markdown 代码块中提取 JSON

### 2. 系统提示词模板

系统提示词包含：

- **当前状态摘要**：时间、玩家、关键角色、物品、约束
- **核心规则**：
  - 任何状态变化必须写入 state_patch
  - 不可凭空出现物品/复活/瞬移
  - 事件类型必须准确
  - 必须输出至少 1 个事件

### 3. 自动问题检测

如果检测到以下情况，会在 `open_questions` 中列出：

- 草稿中出现了当前状态中不存在的物品
- 草稿中描述了死亡角色的行动
- 角色位置改变但没有明确的移动描述

### 4. 默认事件生成

如果没有提取到事件且没有需要澄清的问题，会自动创建一个默认的 `OTHER` 类型事件。

## 事件类型

支持的事件类型：

- `OWNERSHIP_CHANGE`: 物品所有权变更
- `DEATH`: 角色死亡
- `REVIVAL`: 角色复活
- `TRAVEL`: 角色移动
- `FACTION_CHANGE`: 阵营变更
- `QUEST_START/QUEST_COMPLETE/QUEST_FAIL`: 任务相关
- `ITEM_CREATE/ITEM_DESTROY`: 物品创建/销毁
- `TIME_ADVANCE`: 时间推进
- `OTHER`: 其他事件

## 错误处理

### JSON 解析失败

如果 LLM 返回的 JSON 无法解析：

1. 自动重试一次（添加更严格的指令）
2. 尝试从 markdown 代码块中提取 JSON
3. 如果仍然失败，抛出异常

### 事件验证失败

如果提取的事件无法通过 Pydantic 验证：

- 记录警告但继续处理其他事件
- 如果所有事件都失败，创建默认事件

## 测试

运行测试：

```bash
python -m pytest tests/unit/test_extractor.py -v
```

测试覆盖：
- ✅ 成功提取事件
- ✅ 提取到需要澄清的问题
- ✅ JSON 解析失败时的重试机制
- ✅ ExtractedEvent 转换为 Event
- ✅ 默认事件生成
- ✅ 状态摘要格式化

## 实现细节

### JSON Schema 生成

使用 `ExtractedEvent.model_json_schema()` 生成 JSON Schema，包装成包含 `events` 数组和 `open_questions` 的格式。

### 事件 ID 生成

格式：`evt_{turn}_{timestamp}_{hash}`

例如：`evt_1_1703123456_a1b2c3d4`

### 状态摘要格式化

包含以下信息：
- 时间信息（calendar, order）
- 玩家信息（位置、队伍、物品）
- 关键角色（前 10 个，显示状态和位置）
- 关键物品（前 10 个，显示所有权）
- 约束信息（唯一物品、不可变事件）

## 注意事项

1. **API Key 必须设置**：如果没有设置 `SUPER_MIND_API_KEY`，初始化会失败
2. **网络连接**：需要能够访问配置的 API endpoint
3. **成本考虑**：每次调用都会消耗 API 配额，建议在生产环境中添加缓存或批处理
4. **错误处理**：建议在生产环境中添加更完善的错误处理和日志记录

