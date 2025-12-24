# 指导文件 v2：Immersive Story Memory Engine

**从剧本数据到沉浸魔法：用“状态机 + 事件日志 + 一致性闸门”解决长期记忆混淆**

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
