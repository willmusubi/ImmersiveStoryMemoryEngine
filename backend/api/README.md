# FastAPI 服务文档

## 概述

FastAPI 服务提供 RESTful API，用于管理 Canonical State 和处理对话草稿。

## 启动服务

```bash
# 方式1：使用 uvicorn
uvicorn backend.api.routes:app --host 0.0.0.0 --port 8000 --reload

# 方式2：使用 main.py
python -m backend.main
```

## API 端点

### GET /state/{story_id}

获取指定 story_id 的状态。

**路径参数**:
- `story_id` (str): 剧本ID

**响应**:
```json
{
  "meta": {
    "story_id": "sanguo_yanyi",
    "canon_version": "1.0.0",
    "turn": 0,
    "last_event_id": null,
    "updated_at": "2024-01-01T00:00:00"
  },
  "time": {...},
  "player": {...},
  "entities": {...},
  "quest": {...},
  "constraints": {...}
}
```

**示例**:
```bash
curl http://localhost:8000/state/sanguo_yanyi
```

### POST /rag/query

RAG 查询（占位实现）。

**请求体**:
```json
{
  "story_id": "sanguo_yanyi",
  "query": "曹操的武器是什么？",
  "top_k": 5
}
```

**响应**:
```json
{
  "query": "曹操的武器是什么？",
  "results": [
    {
      "text": "检索结果",
      "score": 0.9,
      "metadata": {}
    }
  ]
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "sanguo_yanyi",
    "query": "曹操的武器",
    "top_k": 5
  }'
```

### POST /draft/process

处理草稿：提取事件、校验一致性、应用更新。

**完整流程**:
1. Load state
2. （可选）rag query（由外部调用控制）
3. Call extractor -> events
4. Run consistency gate on (state, draft, events)
5. 根据 action 处理

**请求体**:
```json
{
  "story_id": "sanguo_yanyi",
  "user_message": "玩家向曹操打招呼",
  "assistant_draft": "玩家向曹操打招呼，曹操点头回应。"
}
```

**响应（PASS）**:
```json
{
  "final_action": "PASS",
  "state": {...},
  "recent_events": [...],
  "violations": null,
  "rewrite_instructions": null,
  "questions": null
}
```

**响应（AUTO_FIX）**:
```json
{
  "final_action": "AUTO_FIX",
  "state": {...},
  "recent_events": [...],
  "violations": [...]
}
```

**响应（REWRITE）**:
```json
{
  "final_action": "REWRITE",
  "rewrite_instructions": "规则 R2 违反: ...",
  "violations": [...]
}
```

**响应（ASK_USER）**:
```json
{
  "final_action": "ASK_USER",
  "questions": [
    "规则 R1 违反: 唯一物品 '传国玉玺' 被分配给多个拥有者。请确认如何处理？"
  ],
  "violations": [...]
}
```

**示例**:
```bash
curl -X POST http://localhost:8000/draft/process \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "sanguo_yanyi",
    "user_message": "玩家向曹操打招呼",
    "assistant_draft": "玩家向曹操打招呼，曹操点头回应。"
  }'
```

## 处理流程详解

### /draft/process 流程

1. **Load state**: 从数据库加载当前状态，如果不存在则初始化
2. **（可选）RAG query**: 由外部调用控制，本端点不强制
3. **Call extractor**: 调用 EventExtractor 提取事件
   - 如果 `requires_user_input=true`，直接返回 ASK_USER
4. **Run consistency gate**: 校验事件一致性
   - 检查 10 条规则
   - 返回 ValidationResult
5. **根据 action 处理**:
   - **PASS**: 应用所有事件的 state_patch，保存事件和状态
   - **AUTO_FIX**: 应用修复补丁，保存事件和状态
   - **REWRITE**: 返回重写指令和违反的规则
   - **ASK_USER**: 返回澄清问题

## 状态更新

所有状态更新都会：
- 更新 `meta.turn`（使用事件的最大 turn）
- 更新 `meta.last_event_id`（使用最后一个事件的 event_id）
- 更新 `meta.updated_at`（当前时间）

## 错误处理

API 使用 HTTP 状态码表示错误：
- `200`: 成功
- `404`: 资源不存在
- `500`: 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误信息"
}
```

## 测试

运行 API 测试：

```bash
python -m pytest tests/integration/test_api.py -v
python -m pytest tests/integration/test_state_manager.py -v
```

## 开发

### 本地开发

1. 设置环境变量（`.env` 文件）:
```bash
SUPER_MIND_API_KEY=your_api_key
OPENAI_BASE_URL=https://space.ai-builders.com/backend/v1
```

2. 启动服务:
```bash
uvicorn backend.api.routes:app --reload
```

3. 访问 API 文档:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

