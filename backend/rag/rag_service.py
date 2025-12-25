"""
RAG Service: 提供向量检索功能
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from openai import OpenAI

from ..config import settings


class RAGService:
    """RAG 服务：加载索引并提供查询接口"""
    
    def __init__(
        self,
        index_base_dir: Optional[Path] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化 RAG 服务
        
        Args:
            index_base_dir: 索引文件基础目录（默认：项目根目录/data/indices）
            api_key: OpenAI API key（默认从 settings 读取）
            base_url: OpenAI API base URL（默认从 settings 读取）
            embedding_model: Embedding 模型名称
        """
        self.api_key = api_key or settings.super_mind_api_key
        self.base_url = base_url or settings.openai_base_url
        self.embedding_model = embedding_model
        
        if not self.api_key:
            raise ValueError("API key 未设置，请设置 SUPER_MIND_API_KEY 环境变量")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # 设置索引基础目录
        if index_base_dir is None:
            # 优先使用 settings 中的配置
            if hasattr(settings, 'rag_index_base_dir'):
                index_base_dir = settings.rag_index_base_dir
            else:
                project_root = Path(__file__).parent.parent.parent
                index_base_dir = project_root / "data" / "indices"
        self.index_base_dir = Path(index_base_dir)
        
        # 缓存已加载的索引
        self._index_cache: Dict[str, faiss.Index] = {}
        self._meta_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def _get_index_path(self, story_id: str) -> Path:
        """获取索引文件路径"""
        return self.index_base_dir / f"{story_id}_world_bible.index"
    
    def _get_meta_path(self, story_id: str) -> Path:
        """获取 metadata 文件路径"""
        return self.index_base_dir / f"{story_id}_world_bible_meta.jsonl"
    
    def _load_index(self, story_id: str) -> faiss.Index:
        """
        加载 FAISS 索引（带缓存）
        
        Args:
            story_id: 故事ID
            
        Returns:
            FAISS 索引对象
        """
        if story_id in self._index_cache:
            return self._index_cache[story_id]
        
        index_path = self._get_index_path(story_id)
        if not index_path.exists():
            raise FileNotFoundError(
                f"索引文件不存在: {index_path}\n"
                f"请先运行以下命令创建索引:\n"
                f"  python scripts/world_bible_indexer.py \\\n"
                f"    --notes_folder <笔记文件夹> \\\n"
                f"    --index_out_dir {self.index_base_dir} \\\n"
                f"    --story_id {story_id}"
            )
        
        index = faiss.read_index(str(index_path))
        self._index_cache[story_id] = index
        return index
    
    def _load_metadata(self, story_id: str) -> List[Dict[str, Any]]:
        """
        加载 metadata（带缓存）
        
        Args:
            story_id: 故事ID
            
        Returns:
            Metadata 列表
        """
        if story_id in self._meta_cache:
            return self._meta_cache[story_id]
        
        meta_path = self._get_meta_path(story_id)
        if not meta_path.exists():
            raise FileNotFoundError(
                f"Metadata 文件不存在: {meta_path}\n"
                f"请先运行 world_bible_indexer.py 创建索引"
            )
        
        metadata = []
        with open(meta_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))
        
        self._meta_cache[story_id] = metadata
        return metadata
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        获取文本的 embedding
        
        Args:
            text: 文本内容
            
        Returns:
            Embedding 向量
        """
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    
    def query(
        self,
        story_id: str,
        query_text: str,
        top_k: int = 5,
        use_rerank: bool = True,
        use_keyword_search: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        查询索引，返回最相关的 chunks
        
        Args:
            story_id: 故事ID
            query_text: 查询文本
            top_k: 返回结果数量
            use_rerank: 是否使用关键词重排序（提高相关性）
            
        Returns:
            检索结果列表，每个包含：
            - text: chunk 文本（从原始文件读取）
            - score: 相似度分数（距离，越小越相似）
            - metadata: 包含 file, heading, chunk_id, text_preview, entities_guess 等
        """
        # 加载索引和 metadata
        index = self._load_index(story_id)
        metadata = self._load_metadata(story_id)
        
        # 混合检索：结合向量检索和关键词检索
        candidate_indices = set()
        
        # 1. 向量检索
        query_embedding = self._get_embedding(query_text)
        query_embedding = query_embedding.reshape(1, -1)
        search_k = min(top_k * 3, index.ntotal) if use_rerank else top_k
        distances, indices = index.search(query_embedding, search_k)
        
        # 添加向量检索的结果
        for idx in indices[0]:
            if idx >= 0 and idx < len(metadata):
                candidate_indices.add(idx)
        
        # 2. 关键词检索（如果启用）
        if use_keyword_search:
            import re
            # 提取查询中的关键词（中文字符和英文单词）
            keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query_text)
            
            for i, meta in enumerate(metadata):
                text = meta.get('text_preview', '').lower()
                # 检查是否包含任何关键词
                for keyword in keywords:
                    if keyword.lower() in text:
                        candidate_indices.add(i)
                        break
        
        # 如果没有候选结果，使用向量检索的结果
        if not candidate_indices:
            candidate_indices = set(indices[0][:search_k])
        
        # 构建候选结果
        candidate_results = []
        for idx in candidate_indices:
            if idx < 0 or idx >= len(metadata):
                continue
            
            meta = metadata[idx].copy()
            text = meta.get('text_preview', '')
            
            # 计算向量距离（如果在向量检索结果中）
            vector_distance = None
            if idx in indices[0]:
                pos = list(indices[0]).index(idx)
                vector_distance = float(distances[0][pos])
            else:
                # 如果不在向量检索结果中，使用一个较大的默认距离
                vector_distance = 2.0
            
            # 计算关键词匹配分数
            keyword_score = 0.0
            keywords = []
            if use_rerank and query_text:
                query_lower = query_text.lower()
                text_lower = text.lower()
                
                # 提取关键词
                import re
                keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query_text)
                
                if keywords:
                    # 计算匹配的关键词数量
                    matched_keywords = sum(1 for kw in keywords if kw.lower() in text_lower)
                    total_keywords = len(keywords)
                    
                    # 按匹配比例给分（部分匹配也给予分数）
                    if matched_keywords > 0:
                        # 完全匹配所有关键词：3.0分
                        # 匹配一半关键词：1.5分
                        # 匹配部分关键词：按比例给分
                        keyword_score = (matched_keywords / total_keywords) * 3.0
                    
                    # 检查完整查询文本匹配（更高权重）
                    if query_lower in text_lower:
                        keyword_score += 2.0
            
            # 综合分数
            combined_score = vector_distance - keyword_score * 0.15
            
            # 如果没有任何关键词匹配，但有多个关键词，降低排名
            if keyword_score == 0 and len(keywords) > 1:
                combined_score += 0.3  # 增加距离，降低排名
            
            candidate_results.append({
                'idx': idx,
                'text': text,
                'vector_score': vector_distance,
                'keyword_score': keyword_score,
                'combined_score': combined_score,
                'meta': meta,
            })
        
        # 按综合分数排序
        candidate_results.sort(key=lambda x: x['combined_score'])
        
        # 构建最终结果
        results = []
        for candidate in candidate_results[:top_k]:
            results.append({
                'text': candidate['text'],
                'score': candidate['vector_score'],
                'combined_score': candidate['combined_score'],
                'keyword_matches': candidate['keyword_score'],
                'metadata': {
                    'chunk_id': candidate['meta'].get('chunk_id'),
                    'file': candidate['meta'].get('file'),
                    'heading': candidate['meta'].get('heading'),
                    'text_preview': candidate['meta'].get('text_preview'),
                    'entities_guess': candidate['meta'].get('entities_guess', []),
                }
            })
        
        return results
        
        # 构建结果
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0 or idx >= len(metadata):
                continue
            
            meta = metadata[idx].copy()
            
            # 使用 text_preview 作为返回文本
            text = meta.get('text_preview', '')
            
            # 计算关键词匹配分数（用于重排序）
            keyword_score = 0.0
            if use_rerank and query_text:
                import re
                query_lower = query_text.lower()
                text_lower = text.lower()
                
                # 提取中文词汇（连续的中文字符）
                chinese_words = re.findall(r'[\u4e00-\u9fff]+', query_text)
                for word in chinese_words:
                    if len(word) >= 2:  # 至少2个字符的词汇
                        if word in text:
                            keyword_score += 2.0  # 完整词汇匹配，更高权重
                        elif len(word) > 2:
                            # 对于长词，也检查部分匹配
                            for i in range(len(word) - 1):
                                subword = word[i:i+2]
                                if subword in text:
                                    keyword_score += 0.5
                                    break
                
                # 检查英文单词匹配
                english_words = re.findall(r'[a-zA-Z]+', query_text)
                for word in english_words:
                    if len(word) > 2 and word.lower() in text_lower:
                        keyword_score += 1.0
            
            # 综合分数：距离越小越好，关键词匹配越多越好
            # 将距离转换为相似度分数（距离越小，相似度越高）
            # 然后结合关键词匹配
            combined_score = distance - keyword_score * 0.1  # 关键词匹配可以降低分数
            
            results.append({
                'text': text,
                'score': float(distance),  # 原始 L2 距离
                'combined_score': float(combined_score),  # 综合分数
                'keyword_matches': keyword_score,  # 关键词匹配数
                'metadata': {
                    'chunk_id': meta.get('chunk_id'),
                    'file': meta.get('file'),
                    'heading': meta.get('heading'),
                    'text_preview': meta.get('text_preview'),
                    'entities_guess': meta.get('entities_guess', []),
                }
            })
        
        # 如果使用重排序，按综合分数排序
        if use_rerank:
            results.sort(key=lambda x: x['combined_score'])
        
        # 只返回 top_k 个结果
        return results[:top_k]
    
    def clear_cache(self, story_id: Optional[str] = None):
        """
        清除缓存
        
        Args:
            story_id: 如果指定，只清除该 story_id 的缓存；否则清除所有缓存
        """
        if story_id:
            self._index_cache.pop(story_id, None)
            self._meta_cache.pop(story_id, None)
        else:
            self._index_cache.clear()
            self._meta_cache.clear()


# 全局单例（可选）
_global_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """获取全局 RAG 服务实例"""
    global _global_rag_service
    if _global_rag_service is None:
        _global_rag_service = RAGService()
    return _global_rag_service

