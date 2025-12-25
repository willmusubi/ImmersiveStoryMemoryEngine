# World Bible Indexer 使用指南

## 概述

World Bible Indexer 用于索引背景设定文档（剧本、设定集等），支持 RAG（Retrieval Augmented Generation）查询。

## 功能特性

1. **文件扫描**：递归扫描 `.md` 和 `.txt` 文件
2. **智能分块**：按标题/空行分段，控制 chunk 长度（800-1200 tokens）
3. **向量化**：使用 OpenAI Embeddings API 生成向量
4. **FAISS 索引**：构建高效的向量索引
5. **元数据保存**：保存文件、标题、chunk_id、文本预览等信息

## 使用方法

### 1. 创建索引

```bash
python scripts/world_bible_indexer.py \
    --notes_folder /path/to/notes \
    --index_out_dir /path/to/index \
    --story_id sanguo_yanyi
```

**参数说明**：
- `--notes_folder`: 笔记文件夹路径（递归扫描 .md 和 .txt 文件）
- `--index_out_dir`: 索引输出目录
- `--story_id`: 故事ID（用于标识索引）
- `--embedding_model`: Embedding 模型名称（可选，默认：text-embedding-3-small）

**示例**：
```bash
# 使用项目内的剧本文件
python scripts/world_bible_indexer.py \
    --notes_folder ../剧本 \
    --index_out_dir data/indices \
    --story_id sanguo_yanyi
```

### 2. 输出文件

索引完成后，会在 `index_out_dir` 目录下生成：

- `{story_id}_world_bible.index`: FAISS 索引文件
- `{story_id}_world_bible_meta.jsonl`: 元数据文件（JSON Lines 格式）

**元数据格式**：
```json
{
  "chunk_id": "sanguo_yanyi_a1b2c3d4",
  "file": "三国演义.txt",
  "file_full_path": "/path/to/三国演义.txt",
  "heading": "第一章 桃园三结义",
  "text_preview": "话说天下大势，分久必合，合久必分...",
  "entities_guess": ["刘备", "关羽", "张飞"],
  "text_length": 2500
}
```

## Chunk 策略

### 分段规则

1. **按标题分割**：Markdown 标题（`#`, `##`, `###` 等）作为分段点
2. **按空行分割**：连续空行作为分段点
3. **长度控制**：
   - 最小长度：约 2400 字符（800 tokens）
   - 最大长度：约 3600 字符（1200 tokens）
   - 超过最大长度时，在最后一个空行处强制分割

### 实体提取

自动提取可能的实体（角色名、地名等）：
- 匹配常见的中文姓名模式
- 限制每个 chunk 最多提取 10 个实体

## RAG 查询

### API 端点

```bash
POST /rag/query
Content-Type: application/json

{
  "story_id": "sanguo_yanyi",
  "query": "曹操的武器是什么？",
  "top_k": 5
}
```

**响应**：
```json
{
  "query": "曹操的武器是什么？",
  "results": [
    {
      "text": "曹操手持青釭剑，威风凛凛...",
      "score": 0.1234,
      "metadata": {
        "chunk_id": "sanguo_yanyi_a1b2c3d4",
        "file": "三国演义.txt",
        "heading": "第一章",
        "text_preview": "...",
        "entities_guess": ["曹操", "青釭剑"]
      }
    }
  ]
}
```

### Python 代码示例

```python
from backend.rag import RAGService

# 创建 RAG 服务
rag_service = RAGService()

# 查询
results = rag_service.query(
    story_id="sanguo_yanyi",
    query_text="曹操的武器是什么？",
    top_k=5,
)

# 处理结果
for result in results:
    print(f"相似度: {result['score']:.4f}")
    print(f"文件: {result['metadata']['file']}")
    print(f"文本: {result['text'][:200]}...")
```

## 配置

### 环境变量

在 `.env` 文件中设置：

```bash
# OpenAI API 配置
SUPER_MIND_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://space.ai-builders.com/backend/v1

# RAG 索引目录（可选）
RAG_INDEX_BASE_DIR=/path/to/indices
```

### 默认路径

- 索引目录：`项目根目录/data/indices`
- 数据库目录：`项目根目录/data/databases`

## 测试

运行测试脚本：

```bash
python scripts/test_rag_indexing.py
```

测试包括：
1. 索引功能测试
2. 查询功能测试

## 注意事项

1. **API Key**：必须设置 `SUPER_MIND_API_KEY` 环境变量
2. **文件编码**：确保文件使用 UTF-8 编码
3. **索引大小**：大型文档集可能需要较长时间和较多 API 调用
4. **缓存**：RAGService 会缓存已加载的索引，提高查询性能
5. **相似度分数**：使用 L2 距离，**越小越相似**

## 故障排除

### 索引文件不存在

```
FileNotFoundError: 索引文件不存在
```

**解决方案**：先运行 `world_bible_indexer.py` 创建索引

### API Key 未设置

```
ValueError: API key 未设置
```

**解决方案**：在 `.env` 文件中设置 `SUPER_MIND_API_KEY`

### Embedding 模型不支持

如果使用的 API 不支持 `text-embedding-3-small`，可以：
1. 检查 API 支持的模型列表
2. 使用 `--embedding_model` 参数指定其他模型

## 性能优化

1. **批量处理**：索引器会显示进度，每 10 个 chunks 输出一次
2. **缓存机制**：RAGService 会缓存索引和元数据，避免重复加载
3. **索引类型**：使用 `IndexFlatL2`（L2 距离），适合小到中等规模的索引

对于大规模索引（>100K chunks），可以考虑：
- 使用 `IndexIVFFlat`（倒排索引）
- 使用 `IndexHNSW`（分层导航小世界图）

