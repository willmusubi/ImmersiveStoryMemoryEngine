#!/usr/bin/env python3
"""
测试 RAG 索引和查询功能
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.world_bible_indexer import WorldBibleIndexer
from backend.rag import RAGService


def test_indexing():
    """测试索引功能"""
    print("=" * 60)
    print("测试索引功能")
    print("=" * 60)
    
    # 检查是否有测试文件
    script_file = project_root.parent / "剧本" / "三国演义.txt"
    if not script_file.exists():
        print(f"⚠️  测试文件不存在: {script_file}")
        print("请提供 notes_folder 路径进行测试")
        return False
    
    # 创建临时测试目录
    test_notes_dir = project_root / "data" / "test_notes"
    test_notes_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制测试文件（或创建符号链接）
    import shutil
    test_file = test_notes_dir / "三国演义.txt"
    if not test_file.exists():
        shutil.copy(script_file, test_file)
        print(f"✅ 已复制测试文件到: {test_file}")
    
    # 索引输出目录
    index_out_dir = project_root / "data" / "indices"
    index_out_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建索引器并执行索引
    try:
        indexer = WorldBibleIndexer()
        indexer.index_folder(
            notes_folder=test_notes_dir,
            index_out_dir=index_out_dir,
            story_id="sanguo_yanyi",
        )
        print("\n✅ 索引测试成功！")
        return True
    except Exception as e:
        print(f"\n❌ 索引测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query():
    """测试查询功能"""
    print("\n" + "=" * 60)
    print("测试查询功能")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        
        # 测试查询
        queries = [
            "曹操的武器是什么？",
            "吕布在哪里？",
            "三国的历史背景",
        ]
        
        for query in queries:
            print(f"\n查询: {query}")
            print("-" * 60)
            
            try:
                results = rag_service.query(
                    story_id="sanguo_yanyi",
                    query_text=query,
                    top_k=3,
                )
                
                print(f"找到 {len(results)} 个结果:")
                for i, result in enumerate(results, 1):
                    print(f"\n结果 {i}:")
                    print(f"  相似度分数: {result['score']:.4f}")
                    print(f"  文件: {result['metadata'].get('file', 'N/A')}")
                    print(f"  标题: {result['metadata'].get('heading', 'N/A')}")
                    print(f"  文本预览: {result['text'][:150]}...")
                    if result['metadata'].get('entities_guess'):
                        print(f"  实体: {', '.join(result['metadata']['entities_guess'][:5])}")
            except FileNotFoundError as e:
                print(f"❌ 索引文件不存在: {e}")
                print("请先运行索引功能")
                return False
            except Exception as e:
                print(f"❌ 查询失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        print("\n✅ 查询测试成功！")
        return True
    except Exception as e:
        print(f"\n❌ 查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("RAG 索引和查询功能测试")
    print("=" * 60)
    
    # 测试索引
    indexing_success = test_indexing()
    
    if not indexing_success:
        print("\n⚠️  索引测试失败，跳过查询测试")
        return
    
    # 测试查询
    query_success = test_query()
    
    if indexing_success and query_success:
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 部分测试失败")
        print("=" * 60)


if __name__ == "__main__":
    main()

