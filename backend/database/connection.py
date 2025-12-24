"""
SQLite 连接管理
"""
import aiosqlite
import json
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager


# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "databases" / "memory_engine.db"


async def init_database(db_path: Optional[Path] = None) -> None:
    """
    初始化数据库，创建表结构
    
    Args:
        db_path: 数据库文件路径，如果为 None 则使用默认路径
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    # 确保目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(db_path)) as db:
        # 创建 state 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS state (
                story_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 创建 events 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                story_id TEXT NOT NULL,
                event_id TEXT PRIMARY KEY,
                turn INT NOT NULL,
                time_order INT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (story_id) REFERENCES state(story_id)
            )
        """)
        
        # 创建索引以提高查询性能
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_story_turn 
            ON events(story_id, turn)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_story_time_order 
            ON events(story_id, time_order)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_story_id 
            ON events(story_id)
        """)
        
        await db.commit()
        print(f"✅ Database initialized at {db_path}")


@asynccontextmanager
async def get_db_connection(db_path: Optional[Path] = None):
    """
    获取数据库连接的上下文管理器
    
    Args:
        db_path: 数据库文件路径，如果为 None 则使用默认路径
        
    Yields:
        aiosqlite.Connection: 数据库连接
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    # 确保目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(db_path)) as db:
        # 启用外键约束
        await db.execute("PRAGMA foreign_keys = ON")
        yield db

