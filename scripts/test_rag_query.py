#!/usr/bin/env python3
"""
测试 RAG 查询功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.rag import RAGService


def test_rag_query():
    """测试 RAG 查询"""
    print("=" * 60)
    print("测试 RAG 查询")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        
        # 检查索引文件
        story_id = "sanguo_yanyi"
        index_path = rag_service._get_index_path(story_id)
        meta_path = rag_service._get_meta_path(story_id)
        
        print(f"\n检查索引文件:")
        print(f"  索引文件: {index_path}")
        print(f"  存在: {index_path.exists()}")
        print(f"  元数据文件: {meta_path}")
        print(f"  存在: {meta_path.exists()}")
        
        if not index_path.exists() or not meta_path.exists():
            print("\n❌ 索引文件不存在，请先创建索引")
            return
        
        # 加载索引信息
        try:
            import faiss
            index = faiss.read_index(str(index_path))
            print(f"\n索引信息:")
            print(f"  向量维度: {index.d}")
            print(f"  向量数量: {index.ntotal}")
        except Exception as e:
            print(f"\n❌ 无法读取索引: {e}")
            return
        
        # 读取元数据
        import json
        metadata = []
        with open(meta_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))
        
        print(f"  元数据条目: {len(metadata)}")
        if metadata:
            print(f"\n前 3 个 chunk 预览:")
            for i, meta in enumerate(metadata[:3], 1):
                print(f"  {i}. {meta.get('file', 'N/A')} - {meta.get('heading', 'N/A')}")
                print(f"     预览: {meta.get('text_preview', '')[:100]}...")
        
        # 测试查询
        queries = [
            "曹操的武器是什么？",
            "曹操",
            "武器",
            "青釭剑",
        ]
        
        for query in queries:
            print(f"\n{'='*60}")
            print(f"查询: {query}")
            print(f"{'='*60}")
            
            try:
                results = rag_service.query(
                    story_id=story_id,
                    query_text=query,
                    top_k=5,
                )
                
                print(f"找到 {len(results)} 个结果")
                
                if results:
                    for i, result in enumerate(results, 1):
                        print(f"\n结果 {i}:")
                        print(f"  相似度分数: {result['score']:.4f}")
                        print(f"  文件: {result['metadata'].get('file', 'N/A')}")
                        print(f"  标题: {result['metadata'].get('heading', 'N/A')}")
                        print(f"  文本: {result['text'][:200]}...")
                else:
                    print("  未找到相关结果")
                    print("\n可能的原因:")
                    print("  1. 索引内容与查询不匹配")
                    print("  2. 需要重新创建索引")
                    print("  3. 查询文本需要调整")
                    
            except Exception as e:
                print(f"❌ 查询失败: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_rag_query()

