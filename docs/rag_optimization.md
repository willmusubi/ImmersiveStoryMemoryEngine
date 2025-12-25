# RAG 查询优化建议

## 当前问题

RAG 查询返回的结果相关性不够高，可能的原因：

1. **Embedding 模型对中文的支持**：`text-embedding-3-small` 可能对中文语义理解不够准确
2. **查询文本与文档文本的语义差异**：查询"曹操的武器是什么？"与文档中的"曹操有宝剑二口：一名'倚天'，一名'青釭'"在语义上可能不够接近
3. **Chunk 大小**：当前 chunk 大小（800-1200 tokens）可能将相关信息分散到不同 chunks

## 已实现的优化

### 1. 关键词重排序

在 `RAGService.query()` 中添加了关键词匹配分数，结合向量相似度进行重排序：

```python
# 计算关键词匹配分数
keyword_score = 0.0
for kw in keywords:
    if kw in text_lower:
        keyword_score += 1.0

# 综合分数
combined_score = distance - keyword_score * 0.1
```

### 2. 扩大搜索范围

搜索时先获取 `top_k * 3` 个候选结果，然后进行重排序，最后返回 `top_k` 个最佳结果。

## 进一步优化建议

### 1. 使用更适合中文的 Embedding 模型

如果 API 支持，可以尝试：
- `text-embedding-3-large`（更大的模型，可能对中文理解更好）
- 中文专用的 embedding 模型（如果有）

### 2. 查询扩展（Query Expansion）

在查询前扩展查询文本，添加同义词和相关词：

```python
def expand_query(query: str) -> str:
    """扩展查询，添加同义词"""
    expansions = {
        "武器": ["兵器", "剑", "刀", "枪"],
        "曹操": ["曹孟德", "曹公"],
    }
    # 实现查询扩展逻辑
    return expanded_query
```

### 3. 混合检索（Hybrid Search）

结合向量检索和关键词检索：

```python
# 1. 向量检索（语义相似度）
vector_results = faiss_search(query_embedding, top_k=20)

# 2. 关键词检索（精确匹配）
keyword_results = keyword_search(query_text, top_k=20)

# 3. 合并和重排序
combined_results = merge_and_rerank(vector_results, keyword_results)
```

### 4. 改进 Chunking 策略

- **重叠 Chunking**：相邻 chunks 之间有一定重叠，避免信息被分割
- **语义 Chunking**：按句子或段落边界分割，而不是固定长度
- **保留上下文**：每个 chunk 包含前后文信息

### 5. 后处理优化

- **相关性阈值**：过滤掉相似度分数过高的结果（距离过大）
- **去重**：合并内容相似的结果
- **摘要生成**：对多个相关 chunks 生成摘要

## 使用建议

### 查询优化

1. **使用具体的关键词**：
   - ❌ "曹操的武器是什么？"
   - ✅ "青釭剑" 或 "曹操 宝剑"

2. **尝试不同的查询方式**：
   - "曹操 武器"
   - "青釭剑"
   - "倚天剑"
   - "曹操佩剑"

3. **增加 top_k**：如果前 5 个结果不够相关，尝试 `top_k=10` 或更多

### 索引优化

1. **重新创建索引**：如果修改了 chunking 策略，需要重新创建索引
2. **检查 chunk 质量**：确保重要信息没有被分割到不同 chunks
3. **添加元数据**：在索引时添加更多元数据（如实体标签），便于后续过滤

## 示例代码

### 测试查询相关性

```python
from backend.rag import RAGService

rag = RAGService()

# 测试不同查询
queries = [
    "曹操的武器",
    "青釭剑",
    "曹操 宝剑",
]

for query in queries:
    results = rag.query('sanguo_test', query, top_k=5)
    print(f"\n查询: {query}")
    for i, r in enumerate(results, 1):
        has_keyword = '青釭' in r['text'] or '倚天' in r['text']
        print(f"  {i}. 分数={r['score']:.4f}, 相关={'是' if has_keyword else '否'}")
```

### 检查索引内容

```python
import json

# 读取元数据，查找包含特定关键词的 chunks
meta_path = 'data/indices/sanguo_test_world_bible_meta.jsonl'
with open(meta_path, 'r', encoding='utf-8') as f:
    for line in f:
        meta = json.loads(line)
        if '青釭' in meta.get('text_preview', ''):
            print(f"找到相关 chunk: {meta['chunk_id']}")
            print(f"预览: {meta['text_preview'][:200]}...")
```

