"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
# config.py 在 backend/config.py，所以需要回到项目根目录
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """应用配置"""
    
    def __init__(self):
        """初始化配置"""
        # OpenAI API 配置
        self.super_mind_api_key: Optional[str] = os.getenv("SUPER_MIND_API_KEY")
        self.openai_base_url: str = os.getenv(
            "OPENAI_BASE_URL",
            "https://space.ai-builders.com/backend/v1"
        )
        self.openai_model: str = os.getenv("OPENAI_MODEL", "supermind-agent-v1")
        
        # 数据库配置
        db_path_str = os.getenv("DB_PATH")
        self.db_path: Optional[Path] = Path(db_path_str) if db_path_str else None
        
        # RAG 索引配置
        index_base_dir_str = os.getenv("RAG_INDEX_BASE_DIR")
        if index_base_dir_str:
            self.rag_index_base_dir: Optional[Path] = Path(index_base_dir_str)
        else:
            # 默认：项目根目录/data/indices
            project_root = Path(__file__).parent.parent
            self.rag_index_base_dir = project_root / "data" / "indices"


# 全局配置实例
settings = Settings()
