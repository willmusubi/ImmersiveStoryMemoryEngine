#!/usr/bin/env python3
"""
World Bible Indexer: 索引背景设定文档，支持 RAG 查询

用法:
    python scripts/world_bible_indexer.py \
        --notes_folder /path/to/notes \
        --index_out_dir /path/to/index \
        --story_id sanguo_yanyi
"""
import argparse
import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import numpy as np
import faiss
from openai import OpenAI

from backend.config import settings


class WorldBibleIndexer:
    """World Bible 索引器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化索引器
        
        Args:
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
        
        # 字符长度到 token 的近似比例（中文约 1.5 字符/token，英文约 4 字符/token）
        # 使用保守估计：1 token ≈ 3 字符
        self.chars_per_token = 3
        # 降低最小chunk长度，确保重要信息不被丢弃
        self.min_chunk_chars = 400 * self.chars_per_token  # 约 1200 字符（降低以包含更多内容）
        self.max_chunk_chars = 1200 * self.chars_per_token  # 约 3600 字符
    
    def scan_files(self, notes_folder: Path) -> List[Path]:
        """
        递归扫描 .md 和 .txt 文件
        
        Args:
            notes_folder: 笔记文件夹路径
            
        Returns:
            文件路径列表
        """
        files = []
        for ext in ['*.md', '*.txt']:
            files.extend(notes_folder.rglob(ext))
        return sorted(files)
    
    def chunk_text(
        self,
        text: str,
        file_path: Path,
        current_heading: str = "",
    ) -> List[Dict[str, Any]]:
        """
        按标题/空行分段，控制 chunk 长度
        
        Args:
            text: 文本内容
            file_path: 文件路径
            current_heading: 当前标题（用于上下文）
            
        Returns:
            Chunk 列表，每个包含 text, heading, chunk_id
        """
        chunks = []
        
        # 按空行和标题分割
        # 匹配 Markdown 标题 (# ## ### 等)
        lines = text.split('\n')
        current_chunk_lines = []
        current_heading = ""
        chunk_id = 0
        
        for line in lines:
            # 检查是否是标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if heading_match:
                # 如果当前 chunk 有内容，先保存
                if current_chunk_lines:
                    chunk_text = '\n'.join(current_chunk_lines).strip()
                    # 即使小于最小长度也保存（避免丢失重要信息）
                    if len(chunk_text) > 0:
                        chunks.append({
                            'text': chunk_text,
                            'heading': current_heading,
                            'chunk_id': chunk_id,
                            'file': str(file_path.relative_to(file_path.parents[-1])),
                        })
                        chunk_id += 1
                    current_chunk_lines = []
                
                # 更新当前标题
                current_heading = heading_match.group(2).strip()
                continue
            
            # 添加到当前 chunk
            current_chunk_lines.append(line)
            
            # 检查是否需要分割（达到最大长度）
            current_text = '\n'.join(current_chunk_lines)
            if len(current_text) >= self.max_chunk_chars:
                # 尝试在最后一个空行处分割
                last_empty = -1
                for i in range(len(current_chunk_lines) - 1, -1, -1):
                    if not current_chunk_lines[i].strip():
                        last_empty = i
                        break
                
                if last_empty > 0:
                    # 在空行处分割
                    chunk_text = '\n'.join(current_chunk_lines[:last_empty]).strip()
                    if len(chunk_text) >= self.min_chunk_chars:
                        chunks.append({
                            'text': chunk_text,
                            'heading': current_heading,
                            'chunk_id': chunk_id,
                            'file': str(file_path.relative_to(file_path.parents[-1])),
                        })
                        chunk_id += 1
                    current_chunk_lines = current_chunk_lines[last_empty + 1:]
                else:
                    # 强制分割
                    chunk_text = '\n'.join(current_chunk_lines).strip()
                    if len(chunk_text) >= self.min_chunk_chars:
                        chunks.append({
                            'text': chunk_text,
                            'heading': current_heading,
                            'chunk_id': chunk_id,
                            'file': str(file_path.relative_to(file_path.parents[-1])),
                        })
                        chunk_id += 1
                    current_chunk_lines = []
        
        # 处理最后一个 chunk
        if current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines).strip()
            # 即使小于最小长度也保存（可能是文件末尾的重要信息）
            if len(chunk_text) > 0:
                chunks.append({
                    'text': chunk_text,
                    'heading': current_heading,
                    'chunk_id': chunk_id,
                    'file': str(file_path.relative_to(file_path.parents[-1])),
                })
        
        return chunks
    
    def extract_entities_guess(self, text: str) -> List[str]:
        """
        简单提取可能的实体（角色名、地名等）
        
        Args:
            text: 文本内容
            
        Returns:
            实体列表（可选，用于 metadata）
        """
        # 简单的实体提取：查找常见的中文姓名模式
        # 这里只是示例，可以后续优化
        entities = []
        
        # 匹配常见的中文姓名（2-4 个字符，可能包含常见姓氏）
        name_pattern = r'[张王李刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龥]{1,3}'
        matches = re.findall(name_pattern, text)
        entities.extend(matches[:10])  # 限制数量
        
        return list(set(entities))  # 去重
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        获取文本的 embedding
        
        Args:
            text: 文本内容
            
        Returns:
            Embedding 向量
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            print(f"获取 embedding 失败: {e}")
            raise
    
    def index_folder(
        self,
        notes_folder: Path,
        index_out_dir: Path,
        story_id: str,
    ) -> None:
        """
        索引文件夹
        
        Args:
            notes_folder: 笔记文件夹路径
            index_out_dir: 索引输出目录
            story_id: 故事ID
        """
        print(f"开始索引: {notes_folder}")
        print(f"输出目录: {index_out_dir}")
        print(f"故事ID: {story_id}")
        
        # 创建输出目录
        index_out_dir.mkdir(parents=True, exist_ok=True)
        
        # 扫描文件
        files = self.scan_files(notes_folder)
        print(f"找到 {len(files)} 个文件")
        
        # 处理所有文件，生成 chunks
        all_chunks = []
        for file_path in files:
            print(f"处理文件: {file_path}")
            try:
                # 尝试多种编码
                text = None
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin1']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            text = f.read()
                        print(f"  使用编码: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if text is None:
                    raise ValueError(f"无法使用常见编码读取文件: {file_path}")
                
                chunks = self.chunk_text(text, file_path)
                print(f"  生成 {len(chunks)} 个 chunks")
                
                for chunk in chunks:
                    # 添加完整文件路径
                    chunk['file_full_path'] = str(file_path)
                    # 提取实体（可选）
                    chunk['entities_guess'] = self.extract_entities_guess(chunk['text'])
                    # 生成文本预览（保存完整文本，不截断）
                    # 对于小文件，保存完整文本；对于大文件，保存前2000字符
                    if len(chunk['text']) > 2000:
                        chunk['text_preview'] = chunk['text'][:2000] + "..."
                    else:
                        chunk['text_preview'] = chunk['text']
                    # 生成唯一 chunk_id
                    chunk_hash = hashlib.md5(
                        f"{chunk['file']}:{chunk['chunk_id']}".encode()
                    ).hexdigest()[:8]
                    chunk['chunk_id'] = f"{story_id}_{chunk_hash}"
                
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"  处理文件失败: {e}")
                continue
        
        print(f"\n总共生成 {len(all_chunks)} 个 chunks")
        
        if len(all_chunks) == 0:
            raise ValueError("没有生成任何 chunks，请检查文件内容和编码")
        
        # 生成 embeddings 并构建 FAISS 索引
        print("生成 embeddings...")
        embeddings = []
        for i, chunk in enumerate(all_chunks):
            if (i + 1) % 10 == 0:
                print(f"  进度: {i + 1}/{len(all_chunks)}")
            
            embedding = self.get_embedding(chunk['text'])
            embeddings.append(embedding)
        
        # 构建 FAISS 索引
        print("构建 FAISS 索引...")
        embeddings_array = np.array(embeddings, dtype=np.float32)
        if embeddings_array.size == 0:
            raise ValueError("没有生成任何 embeddings")
        dimension = embeddings_array.shape[1]
        
        # 使用 L2 距离的 IndexFlatIP（内积，适合归一化后的向量）
        # 或者使用 IndexFlatL2（L2 距离）
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        # 保存索引
        index_path = index_out_dir / f"{story_id}_world_bible.index"
        faiss.write_index(index, str(index_path))
        print(f"索引已保存: {index_path}")
        
        # 保存 metadata
        meta_path = index_out_dir / f"{story_id}_world_bible_meta.jsonl"
        with open(meta_path, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                # 只保存 metadata，不保存完整文本（文本在原始文件中）
                meta = {
                    'chunk_id': chunk['chunk_id'],
                    'file': chunk['file'],
                    'file_full_path': chunk['file_full_path'],
                    'heading': chunk['heading'],
                    'text_preview': chunk['text_preview'],
                    'entities_guess': chunk['entities_guess'],
                    'text_length': len(chunk['text']),
                }
                f.write(json.dumps(meta, ensure_ascii=False) + '\n')
        
        print(f"Metadata 已保存: {meta_path}")
        print(f"\n✅ 索引完成！")
        print(f"  - 索引文件: {index_path}")
        print(f"  - Metadata 文件: {meta_path}")
        print(f"  - 总 chunks: {len(all_chunks)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="World Bible Indexer")
    parser.add_argument(
        '--notes_folder',
        type=str,
        required=True,
        help='笔记文件夹路径'
    )
    parser.add_argument(
        '--index_out_dir',
        type=str,
        required=True,
        help='索引输出目录'
    )
    parser.add_argument(
        '--story_id',
        type=str,
        required=True,
        help='故事ID'
    )
    parser.add_argument(
        '--embedding_model',
        type=str,
        default='text-embedding-3-small',
        help='Embedding 模型名称（默认: text-embedding-3-small）'
    )
    
    args = parser.parse_args()
    
    # 创建索引器
    indexer = WorldBibleIndexer(embedding_model=args.embedding_model)
    
    # 执行索引
    indexer.index_folder(
        notes_folder=Path(args.notes_folder),
        index_out_dir=Path(args.index_out_dir),
        story_id=args.story_id,
    )


if __name__ == "__main__":
    main()

