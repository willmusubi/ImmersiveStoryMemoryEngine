# Immersive Story Memory Engine

**从剧本数据到沉浸魔法：用"状态机 + 事件日志 + 一致性闸门"解决长期记忆混淆**

## 📋 目录

- [快速开始](#快速开始)
- [安装依赖](#安装依赖)
- [配置](#配置)
- [运行后端服务](#运行后端服务)
- [创建索引](#创建索引)
- [安装 SillyTavern 扩展](#安装-sillytavern-扩展)
- [运行测试](#运行测试)
- [失败恢复策略](#失败恢复策略)
- [项目结构](#项目结构)
- [系统设计](#系统设计)

---

## 🚀 快速开始

1. **安装依赖**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **配置环境变量**

   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的 API Key 等配置
   ```

3. **初始化数据库**

   ```bash
   python scripts/init_database.py
   ```

4. **创建索引（可选，用于 RAG 查询）**

   ```bash
   python scripts/world_bible_indexer.py \
     --notes_folder data/test_notes \
     --index_out_dir data/indices \
     --story_id sanguo_test
   ```

5. **启动后端服务**

   ```bash
   python run_server.py
   ```

6. **访问测试界面**
   - 打开浏览器访问：http://localhost:8000/
   - 或查看 API 文档：http://localhost:8000/docs

---

## 📦 安装依赖

### 系统要求

- Python 3.10 或更高版本
- 已安装 pip 和 venv

### 安装步骤

1. **创建虚拟环境**

   ```bash
   python -m venv venv
   ```

2. **激活虚拟环境**

   ```bash
   # macOS/Linux
   source venv/bin/activate

   # Windows
   venv\Scripts\activate
   ```

3. **安装依赖包**
   ```bash
   pip install -r requirements.txt
   ```

### 依赖说明

- **FastAPI**: Web 框架
- **SQLite (aiosqlite)**: 数据库
- **FAISS**: 向量检索
- **OpenAI**: LLM API 客户端
- **Pydantic**: 数据验证

---

## ⚙️ 配置

### 环境变量配置

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

### 必需配置项

- `SUPER_MIND_API_KEY`: OpenAI API Key（必需）
- `OPENAI_BASE_URL`: API 基础 URL（默认：https://space.ai-builders.com/backend/v1）
- `OPENAI_MODEL`: 使用的模型（默认：supermind-agent-v1）

### 可选配置项

- `DB_PATH`: 数据库文件路径（默认：`data/databases/memory_engine.db`）
- `RAG_INDEX_BASE_DIR`: RAG 索引目录（默认：`data/indices`）
- `STORY_ID`: 默认故事 ID（用于测试）

### 配置示例

详见 `.env.example` 文件。

---

## 🖥️ 运行后端服务

### 方式 1：使用 run_server.py（推荐）

```bash
python run_server.py
```

服务将在 `http://0.0.0.0:8000` 启动。

### 方式 2：使用 uvicorn 命令

```bash
PYTHONPATH=. uvicorn backend.api.routes:app --host 0.0.0.0 --port 8000 --reload
```

### 方式 3：使用 scripts/start_api.py

```bash
python scripts/start_api.py
```

### 访问服务

- **测试页面**: http://localhost:8000/
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📚 创建索引

索引用于 RAG 查询，从 World Bible 文档中检索相关信息。

### 准备文档

将你的背景设定文档（`.txt` 或 `.md` 格式）放在一个文件夹中，例如：

```
data/test_notes/
  ├── 三国演义_白话文_第一章.txt
  ├── 三国演义_白话文_第二章.txt
  └── ...
```

### 运行索引脚本

```bash
python scripts/world_bible_indexer.py \
  --notes_folder data/test_notes \
  --index_out_dir data/indices \
  --story_id sanguo_test
```

### 参数说明

- `--notes_folder`: 笔记文件夹路径（必需）
- `--index_out_dir`: 索引输出目录（必需）
- `--story_id`: 故事 ID（必需，用于标识索引）
- `--embedding_model`: Embedding 模型（可选，默认：text-embedding-3-small）

### 输出文件

索引脚本会生成两个文件：

- `{story_id}_world_bible.index`: FAISS 索引文件
- `{story_id}_world_bible_meta.jsonl`: 元数据文件

---

## 🎮 安装 SillyTavern 扩展

### 步骤 1：复制扩展文件

将 `sillytavern_extension` 文件夹复制到 SillyTavern 的扩展目录：

```bash
# 找到你的 SillyTavern 安装目录
# 通常位于：
# - macOS/Linux: ~/SillyTavern/extensions/
# - Windows: C:\Users\YourName\SillyTavern\extensions\

# 复制扩展文件夹
cp -r sillytavern_extension /path/to/SillyTavern/extensions/
```

### 步骤 2：启用扩展

1. 启动 SillyTavern
2. 进入 **扩展设置**（Extensions）
3. 找到 **"Immersive Story Memory Engine"**
4. 点击 **启用**（Enable）

### 步骤 3：配置扩展

在扩展设置中配置：

- **后端 URL**: 默认 `http://127.0.0.1:8000`（如果后端运行在其他地址，请修改）
- **故事 ID**: 用于标识不同的故事会话

### 步骤 4：开始使用

1. 确保后端服务正在运行（见 [运行后端服务](#运行后端服务)）
2. 在 SillyTavern 中开始对话
3. 扩展会自动：
   - 在每轮对话前获取状态并注入到系统提示词
   - 在模型生成回复后提取事件并验证一致性
   - 在侧栏显示状态摘要和最近事件

### 详细说明

更多信息请参考 `sillytavern_extension/README.md`。

---

## 🧪 运行测试

### 运行所有测试

```bash
# 使用测试脚本（推荐）
bash scripts/run_all_tests.sh

# 或手动运行
pytest tests/ -v
```

### 运行特定测试

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 特定测试文件
pytest tests/unit/test_extractor.py -v
```

### 运行完整工作流测试（需要 LLM）

```bash
# 这会调用真实的 LLM API，会消耗配额
python scripts/test_full_workflow.py
```

### 测试覆盖率

查看测试覆盖率报告：

```bash
pytest --cov=backend --cov-report=html
```

---

## 🛡️ 失败恢复策略

系统内置了多种失败恢复策略，确保在异常情况下能够优雅降级或自动修复。

### 1. Extractor JSON 解析失败

**问题**: LLM 返回的 JSON 格式不正确，无法解析。

**恢复策略**:

1. **自动重试**: 如果解析失败，会自动重试（最多 1 次）
2. **回退到 JSON 模式**: Function calling 失败时，自动回退到 JSON 模式
3. **清理 JSON**: 自动移除 markdown 代码块标记，提取纯 JSON
4. **创建默认事件**: 如果所有重试都失败，创建一个默认的 `OTHER` 类型事件，确保流程继续

**代码位置**: `backend/extractor/extractor.py`

### 2. FAISS 索引不存在

**问题**: 尝试查询 RAG 索引时，索引文件不存在。

**恢复策略**:

1. **友好错误提示**: 返回详细的错误信息，包含创建索引的命令
2. **自动创建目录**: 如果索引目录不存在，自动创建
3. **优雅降级**: 如果索引不存在，RAG 查询会失败，但不影响其他功能

**代码位置**: `backend/rag/rag_service.py`

**示例错误信息**:

```
索引文件不存在: /path/to/index
请先运行以下命令创建索引:
  python scripts/world_bible_indexer.py \
    --notes_folder <笔记文件夹> \
    --index_out_dir /path/to/index \
    --story_id <story_id>
```

### 3. State 损坏

**问题**: 数据库中的 state JSON 损坏或格式不正确。

**恢复策略**:

1. **自动修复缺失的 Location**: 如果 state 中引用了不存在的 location，自动创建默认 location
2. **JSON 验证前修复**: 在 Pydantic 验证之前，先修复常见的 JSON 结构问题
3. **初始化默认状态**: 如果 state 完全无法恢复，自动初始化一个默认状态
4. **从事件日志重建**: 如果 state 损坏但事件日志完整，可以从事件日志重建 state（未来功能）

**代码位置**:

- `backend/database/repository.py` - `_fix_missing_locations_in_json()`
- `backend/core/state_manager.py` - `_ensure_location_references()`

### 4. 数据库连接失败

**问题**: 无法连接到数据库或数据库文件损坏。

**恢复策略**:

1. **自动创建目录**: 如果数据库目录不存在，自动创建
2. **自动初始化**: 如果数据库文件不存在，自动初始化表结构
3. **事务回滚**: 如果操作失败，自动回滚事务，确保数据一致性

**代码位置**: `backend/database/connection.py`

### 5. API 调用失败

**问题**: LLM API 调用失败（网络错误、API 错误等）。

**恢复策略**:

1. **重试机制**: 自动重试失败的 API 调用（最多 1 次）
2. **错误处理**: 捕获并记录详细的错误信息
3. **优雅降级**: 如果 API 调用失败，返回友好的错误信息，不导致整个系统崩溃

**代码位置**: `backend/extractor/extractor.py`, `backend/rag/rag_service.py`

---

## 📁 项目结构

```
ImmersiveStoryMemoryEngine/
├── backend/              # 后端代码
│   ├── api/              # FastAPI 路由
│   ├── core/             # 核心逻辑（状态管理）
│   ├── database/         # 数据库访问
│   ├── extractor/        # 事件提取器
│   ├── gate/             # 一致性闸门
│   ├── models/           # 数据模型
│   └── rag/              # RAG 服务
├── data/                 # 数据目录
│   ├── databases/        # SQLite 数据库
│   ├── embeddings/       # Embeddings 缓存（可选）
│   ├── indices/          # FAISS 索引
│   └── test_notes/        # 测试文档
├── docs/                 # 文档
├── scripts/              # 工具脚本
├── sillytavern_extension/ # SillyTavern 扩展
├── tests/                # 测试代码
├── .env.example          # 环境变量示例
├── requirements.txt      # Python 依赖
├── run_server.py         # 启动脚本
└── README.md             # 本文档
```

---

## 🏗️ 系统设计

## Phase 1：Product Definition Brief（产品定义简报）

### North Star（北极星）

把小说/剧本（《三国演义》《天龙八部》等）做成沉浸式互动游戏，并确保：

- 世界观长期稳定：物品归属、人物生死、时间线、地理位置持续一致
- 玩家历史可追溯：每个“事实变化”都能追溯到一个事件
- 可评测：能用 Needle tests 和长对话压力测试量化一致性

### Core Problem（核心问题）

LLM 很会写，但不擅长维护“可验证的事实状态”。常见崩坏：

1. **物品所有权错误（Ownership）**

   - 貂蝉给了“定情信物”，后面信物又出现在貂蝉手里

2. **人物生死/状态错误（Life/Status）**

   - 白门楼救了吕布，但后续仍被描述“吕布已死”

3. **时间线错误（Timeline）**

   - 下邳之战出现在剿灭袁术之后（顺序颠倒）

4. **地理位置错误（Location/Travel）**

   - 人物瞬移、城市归属错、场景连续性断裂

   **本质：缺乏唯一真相来源（single source of truth）+ 缺乏硬约束校验机制。**

### MVP（最小可行产品）

做一个“单剧本可长期游玩不崩”的 Demo（强烈建议先三国某一段）：

**MVP 必须具备：**

1. **World Bible（静态知识）RAG**：原著/设定检索（只负责背景，不负责决定事实）
2. **Canonical State（唯一真相状态）**：结构化 JSON/SQLite 保存当前世界事实
3. **Event Log（事件日志）**：每轮写入结构化事件，驱动状态更新
4. **Consistency Gate（闸门）**：生成前/写入前做 10 条规则校验，冲突就重写/追问/自动修

**UI（最简）**

- 聊天窗口 + 右侧状态面板（时间、地点、队伍、关键物品、生死状态、任务阶段、最近事件）

### OKRs（指标）

- **KR1 一致性错误率**：长对话压力（至少 15–30 轮/段，20 段）硬矛盾 < 2%
- **KR2 Needle Tests 100%**：至少 5 个（物品/生死/时间/地理/关系）全通过
- **KR3 可追溯性**：任何 state 变化必须能指向 event_id
- **KR4 可用性**：单轮含检索+校验延迟可控（本地可放宽，但要稳定）

---

## Phase 2：System Design（系统设计）

### 核心原则（最重要）

- **状态只存事实，不存故事文本**
- **任何状态变化必须由事件驱动**
- **RAG 用于补充描写/背景，不用于裁定硬事实**
- **生成必须服从 Canonical State；若要改变事实，先写事件再更新 state**

### 模块拆分（建议就这四块）

1. **World Bible Indexer（Python）**

   - 扫描剧本文件 → chunk → embeddings → FAISS 索引

2. **State Store（SQLite + JSON）**

   - 保存 canonical state + event log（可追溯）

3. **Event Extractor（LLM）**

   - 将本轮剧情草稿抽取成结构化 events + state_patch

4. **Consistency Gate（规则引擎）**

   - 校验 10 条规则，决定 AUTO_FIX / REWRITE / ASK_USER

### 数据结构（直接采用你要的最小版）

- Canonical State JSON：包含 meta/time/player/entities/quest/constraints
- Event JSON：包含 event_id/turn/time/where/who/type/summary/payload/state_patch/evidence
- 10 条规则：ownership / alive / timeline / location / faction/traceability 等

---

## Phase 3：Integration Plan（与 SillyTavern 结合的落地方案）

### 推荐落地路径：SillyTavern 扩展 + 本地后端服务

- **后端服务（FastAPI）**：负责 state / event log / validate / rag query
- **SillyTavern 扩展（JS）**：
  - 每轮：拿到用户输入 → 调用后端 get_state + 可选 query_world_bible
  - 把“状态摘要”注入 prompt 固定位置
  - LLM 生成草稿后：调用后端 extract_events → validate → apply_events
  - 如果 validate 要 REWRITE/ASK_USER：扩展执行相应流程
  - UI：展示状态面板 & 最近事件列表
