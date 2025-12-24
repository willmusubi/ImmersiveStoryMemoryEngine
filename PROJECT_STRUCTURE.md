# Immersive Story Memory Engine - 项目结构设计

## 技术选型

### 后端技术栈

- **Python 3.11+**: 核心开发语言
- **FastAPI**: 异步 Web 框架，提供 RESTful API
- **SQLite**: 轻量级数据库，存储 Canonical State 和 Event Log
- **Pydantic v2**: 数据验证和序列化
- **FAISS**: 向量相似度搜索（用于 RAG）
- **OpenAI API**: Embeddings 生成（支持自定义 base_url）
- **pytest**: 单元测试框架
- **httpx**: 异步 HTTP 客户端（用于测试）

### 前端技术栈

- **TypeScript/JavaScript**: SillyTavern 扩展开发
- **原生 JS/TS**: 无需额外框架依赖，直接集成到 SillyTavern

### 开发工具

- **black**: 代码格式化
- **mypy**: 类型检查
- **ruff**: 快速 linting

---

## 项目目录结构

```
ImmersiveStoryMemoryEngine/
├── README.md                          # 项目说明文档
├── PROJECT_STRUCTURE.md              # 本文件：目录结构与模块说明
├── requirements.txt                   # Python 依赖
├── pyproject.toml                    # Python 项目配置（black, mypy, pytest）
├── .env.example                      # 环境变量模板
├── .gitignore                        # Git 忽略文件
│
├── backend/                          # 后端服务
│   ├── __init__.py
│   ├── main.py                       # FastAPI 应用入口
│   ├── config.py                     # 配置管理（环境变量、数据库路径等）
│   │
│   ├── core/                         # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── state.py                  # Canonical State 管理
│   │   ├── event.py                  # Event Log 管理
│   │   ├── extractor.py              # Event Extractor（LLM 抽取事件）
│   │   ├── consistency_gate.py       # Consistency Gate（10条规则校验）
│   │   └── rag.py                    # RAG 检索（World Bible）
│   │
│   ├── models/                       # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── state.py                  # State 相关模型
│   │   ├── event.py                  # Event 相关模型
│   │   └── api.py                    # API 请求/响应模型
│   │
│   ├── database/                     # 数据库层
│   │   ├── __init__.py
│   │   ├── connection.py             # SQLite 连接管理
│   │   ├── state_store.py            # State 持久化
│   │   └── event_store.py            # Event Log 持久化
│   │
│   ├── api/                          # API 路由
│   │   ├── __init__.py
│   │   ├── routes.py                 # 所有 API 端点
│   │   └── dependencies.py           # FastAPI 依赖注入
│   │
│   └── utils/                        # 工具函数
│       ├── __init__.py
│       ├── embeddings.py             # Embeddings 生成（OpenAI）
│       └── validators.py             # 辅助验证函数
│
├── frontend/                         # SillyTavern 扩展
│   ├── extension.json                # SillyTavern 扩展配置
│   ├── script.js                     # 主扩展脚本（或 script.ts）
│   ├── styles.css                    # 扩展样式
│   └── README.md                     # 扩展使用说明
│
├── tests/                            # 测试套件
│   ├── __init__.py
│   ├── conftest.py                   # pytest 配置和 fixtures
│   │
│   ├── unit/                         # 单元测试
│   │   ├── __init__.py
│   │   ├── test_state.py             # State 管理测试
│   │   ├── test_event.py             # Event 管理测试
│   │   ├── test_extractor.py        # Event Extractor 测试
│   │   ├── test_consistency_gate.py # Consistency Gate 测试（10条规则）
│   │   └── test_rag.py               # RAG 测试
│   │
│   ├── integration/                  # 集成测试
│   │   ├── __init__.py
│   │   ├── test_api.py               # API 端点测试
│   │   └── test_workflow.py          # 完整工作流测试
│   │
│   └── needle/                       # Needle 测试用例
│       ├── __init__.py
│       ├── test_ownership.py         # 物品所有权测试
│       ├── test_life_status.py       # 人物生死状态测试
│       ├── test_timeline.py          # 时间线测试
│       ├── test_location.py          # 地理位置测试
│       └── test_relationship.py      # 关系测试
│
├── scripts/                          # 辅助脚本
│   ├── index_world_bible.py          # 索引 World Bible（剧本文件）
│   └── init_database.py              # 初始化数据库
│
└── data/                             # 数据目录（不提交到 Git）
    ├── world_bible/                  # 原始剧本文件（.txt, .md）
    ├── indices/                      # FAISS 索引文件
    └── databases/                    # SQLite 数据库文件
```

---

## 模块职责与接口设计

### 1. Core Module: `core/state.py`

**职责**: Canonical State 的读取、更新、查询

**主要函数签名**:

```python
class StateManager:
    async def get_current_state() -> CanonicalState
    async def apply_state_patch(patch: StatePatch, event_id: str) -> CanonicalState
    async def get_entity(entity_id: str) -> Optional[Entity]
    async def get_entities_by_type(entity_type: str) -> List[Entity]
    async def validate_state(state: CanonicalState) -> ValidationResult
```

**输入/输出**:

- `get_current_state()`: 无输入 → `CanonicalState` (包含 meta/time/player/entities/quest/constraints)
- `apply_state_patch()`: `StatePatch` + `event_id` → 更新后的 `CanonicalState`
- `get_entity()`: `entity_id: str` → `Optional[Entity]`

---

### 2. Core Module: `core/event.py`

**职责**: Event Log 的写入、查询、追溯

**主要函数签名**:

```python
class EventManager:
    async def create_event(event: Event) -> Event
    async def get_event(event_id: str) -> Optional[Event]
    async def get_events_by_turn(turn: int) -> List[Event]
    async def get_events_by_entity(entity_id: str) -> List[Event]
    async def trace_state_change(entity_id: str, field: str) -> Optional[Event]
```

**输入/输出**:

- `create_event()`: `Event` → 持久化后的 `Event` (含 event_id)
- `trace_state_change()`: `entity_id` + `field` → 导致该变化的 `Event` (可追溯性)

---

### 3. Core Module: `core/extractor.py`

**职责**: 从 LLM 生成的剧情草稿中抽取结构化事件

**主要函数签名**:

```python
class EventExtractor:
    async def extract_events(
        draft_text: str,
        current_state: CanonicalState,
        turn: int
    ) -> List[ExtractedEvent]

    async def extract_state_patch(
        events: List[ExtractedEvent],
        current_state: CanonicalState
    ) -> StatePatch
```

**输入/输出**:

- `extract_events()`: `draft_text` + `current_state` + `turn` → `List[ExtractedEvent]`
- `extract_state_patch()`: `events` + `current_state` → `StatePatch` (状态变更补丁)

---

### 4. Core Module: `core/consistency_gate.py`

**职责**: 10 条规则校验，决定 AUTO_FIX / REWRITE / ASK_USER

**主要函数签名**:

```python
class ConsistencyGate:
    async def validate(
        events: List[ExtractedEvent],
        state_patch: StatePatch,
        current_state: CanonicalState
    ) -> ValidationResult

    async def check_rule_ownership(...) -> RuleResult
    async def check_rule_alive(...) -> RuleResult
    async def check_rule_timeline(...) -> RuleResult
    async def check_rule_location(...) -> RuleResult
    async def check_rule_faction(...) -> RuleResult
    async def check_rule_traceability(...) -> RuleResult
    # ... 其他 4 条规则
```

**输入/输出**:

- `validate()`: `events` + `state_patch` + `current_state` → `ValidationResult`
  - `ValidationResult`: `status: Literal["PASS", "AUTO_FIX", "REWRITE", "ASK_USER"]`, `violations: List[Violation]`, `fixed_patch: Optional[StatePatch]`

**10 条规则**:

1. **Ownership**: 物品所有权变更必须可追溯
2. **Alive**: 人物生死状态不能矛盾
3. **Timeline**: 时间线必须单调递增
4. **Location**: 地理位置变更必须合理（不能瞬移）
5. **Faction**: 阵营关系变更必须可追溯
6. **Traceability**: 所有状态变更必须有 event_id
7. **Quest**: 任务状态变更必须符合前置条件
8. **Constraint**: 不能违反硬约束（如"吕布已死"）
9. **Entity Existence**: 引用的实体必须存在
10. **State Consistency**: 状态内部一致性（如"持有物品"与"物品位置"一致）

---

### 5. Core Module: `core/rag.py`

**职责**: World Bible 检索（仅用于背景与设定，不用于裁定硬事实）

**主要函数签名**:

```python
class RAGEngine:
    async def query_world_bible(
        query: str,
        top_k: int = 5
    ) -> List[RetrievalResult]

    async def index_documents(
        documents: List[str],
        metadata: List[Dict]
    ) -> None
```

**输入/输出**:

- `query_world_bible()`: `query: str` + `top_k: int` → `List[RetrievalResult]` (chunk + score + metadata)
- `index_documents()`: `documents` + `metadata` → 无返回值（更新 FAISS 索引）

---

### 6. Database Module: `database/state_store.py`

**职责**: Canonical State 的 SQLite 持久化

**主要函数签名**:

```python
class StateStore:
    async def save_state(state: CanonicalState) -> None
    async def load_state() -> Optional[CanonicalState]
    async def save_state_snapshot(state: CanonicalState, event_id: str) -> None
```

---

### 7. Database Module: `database/event_store.py`

**职责**: Event Log 的 SQLite 持久化

**主要函数签名**:

```python
class EventStore:
    async def save_event(event: Event) -> None
    async def load_event(event_id: str) -> Optional[Event]
    async def query_events(
        filters: EventFilters
    ) -> List[Event]
```

---

### 8. API Module: `api/routes.py`

**职责**: FastAPI 路由定义

**主要端点**:

```python
# State 相关
GET    /api/v1/state                    # 获取当前状态
POST   /api/v1/state/patch              # 应用状态补丁（内部使用）

# Event 相关
POST   /api/v1/events                  # 创建事件
GET    /api/v1/events/{event_id}        # 获取事件
GET    /api/v1/events/trace/{entity_id} # 追溯实体变更

# 工作流相关
POST   /api/v1/extract                  # 抽取事件
POST   /api/v1/validate                 # 校验一致性
POST   /api/v1/apply                    # 应用事件（extract + validate + apply）

# RAG 相关
POST   /api/v1/rag/query                # 查询 World Bible
```

---

### 9. Frontend Module: `frontend/script.js`

**职责**: SillyTavern 扩展，与后端 API 交互

**主要函数**:

```javascript
// 每轮对话前
async function injectStateSummary() {
    const state = await fetch('/api/v1/state');
    // 注入到 prompt 固定位置
}

// LLM 生成后
async function processDraft(draftText) {
    const result = await fetch('/api/v1/apply', {
        method: 'POST',
        body: JSON.stringify({ draft_text: draftText, turn: currentTurn })
    });
    // 处理 ValidationResult
}

// UI 更新
function updateStatePanel(state) { ... }
function updateEventList(events) { ... }
```

---

## 数据模型（Pydantic）

### CanonicalState

```python
class CanonicalState(BaseModel):
    meta: MetaInfo              # 剧本ID、版本等
    time: TimeState             # 当前时间、时间线
    player: PlayerState         # 玩家角色状态
    entities: Dict[str, Entity] # 实体字典（人物、物品、地点等）
    quest: QuestState           # 任务状态
    constraints: List[Constraint] # 硬约束列表
```

### Event

```python
class Event(BaseModel):
    event_id: str
    turn: int
    time: TimeInfo
    where: str                  # 地点ID
    who: List[str]              # 参与者ID列表
    type: EventType             # 枚举：OWNERSHIP_CHANGE, DEATH, TRAVEL, etc.
    summary: str
    payload: Dict               # 事件详情
    state_patch: StatePatch     # 状态变更补丁
    evidence: str               # 证据文本（来自 draft）
```

### StatePatch

```python
class StatePatch(BaseModel):
    entity_updates: Dict[str, EntityUpdate]
    time_update: Optional[TimeUpdate]
    quest_updates: Optional[QuestUpdate]
    constraint_additions: List[Constraint]
```

---

## 测试覆盖要求

### 单元测试（`tests/unit/`）

- **test_consistency_gate.py**: 至少覆盖 10 条规则，每条规则至少 3 个测试用例（正常、边界、异常）
- **test_state.py**: State 的 CRUD 操作
- **test_event.py**: Event 的创建、查询、追溯
- **test_extractor.py**: 事件抽取准确性
- **test_rag.py**: RAG 检索准确性

### Needle 测试（`tests/needle/`）

至少 5 个测试脚本：

1. **test_ownership.py**: 物品所有权一致性（如：物品 A 给了 B，后续不能出现在 A 手中）
2. **test_life_status.py**: 人物生死状态（如：救了某人，后续不能描述为"已死"）
3. **test_timeline.py**: 时间线顺序（如：事件必须按时间顺序发生）
4. **test_location.py**: 地理位置（如：不能瞬移，位置变更必须合理）
5. **test_relationship.py**: 关系一致性（如：阵营关系、人物关系）

每个 Needle 测试应包含：

- 初始状态设置
- 多轮对话模拟（15-30 轮）
- 硬事实检查点
- 断言：错误率 < 2%

---

## 下一步

等待进一步指令后，将按以下顺序实现：

1. 数据模型定义（Pydantic）
2. 数据库层（SQLite）
3. 核心业务逻辑（State, Event, Extractor, Consistency Gate, RAG）
4. API 层（FastAPI）
5. 前端扩展（SillyTavern）
6. 测试套件（单元测试 + Needle 测试）
