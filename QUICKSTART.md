# 快速启动指南

## 启动 FastAPI 服务

### 方式 1：使用 run_server.py（推荐）

```bash
cd /Users/liutong/Admin/Journey_to_AI/Ukiyo/Product/ImmersiveStoryMemoryEngine
source venv/bin/activate
python run_server.py
```

### 方式 2：使用 scripts/start_api.py

```bash
cd /Users/liutong/Admin/Journey_to_AI/Ukiyo/Product/ImmersiveStoryMemoryEngine
source venv/bin/activate
python scripts/start_api.py
```

### 方式 3：使用 uvicorn 命令

```bash
cd /Users/liutong/Admin/Journey_to_AI/Ukiyo/Product/ImmersiveStoryMemoryEngine
source venv/bin/activate
PYTHONPATH=. uvicorn backend.api.routes:app --host 0.0.0.0 --port 8000 --reload
```

## 访问测试界面

启动服务后，在浏览器中访问：

1. **测试页面**（推荐）：http://localhost:8000/
   - 友好的 UI 界面
   - 可以直接测试所有 API 端点

2. **Swagger UI**：http://localhost:8000/docs
   - 交互式 API 文档
   - 可以直接测试 API

3. **ReDoc**：http://localhost:8000/redoc
   - 另一种 API 文档格式

## 测试 API

### 使用测试页面

1. 打开 http://localhost:8000/
2. 在"获取状态"区域输入 `story_id`，点击"获取状态"
3. 在"处理草稿"区域输入信息，点击"处理草稿"

### 使用 curl

```bash
# 获取状态
curl http://localhost:8000/state/sanguo_test

# 处理草稿
curl -X POST http://localhost:8000/draft/process \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "sanguo_test",
    "user_message": "玩家向曹操打招呼",
    "assistant_draft": "玩家向曹操打招呼，曹操点头回应。"
  }'
```

## 常见问题

### ModuleNotFoundError: No module named 'backend'

**解决方案**：
- 确保在项目根目录运行
- 使用 `run_server.py`（推荐）
- 或者设置 `PYTHONPATH=.`

### 端口被占用

如果 8000 端口被占用，可以修改端口：

```python
# 在 run_server.py 中修改
uvicorn.run(app, host="0.0.0.0", port=8001, ...)
```

