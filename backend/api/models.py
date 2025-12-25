"""
API 请求/响应模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ..models import CanonicalState, Event


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""
    story_id: str = Field(..., description="剧本ID")
    query: str = Field(..., description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""
    results: List[Dict[str, Any]] = Field(default_factory=list, description="检索结果")
    query: str = Field(..., description="查询文本")
    error: Optional[str] = Field(default=None, description="错误信息（如果有）")
    warning: Optional[str] = Field(default=None, description="警告信息（如果有）")


class DraftProcessRequest(BaseModel):
    """草稿处理请求"""
    story_id: str = Field(..., description="剧本ID")
    user_message: str = Field(..., description="用户消息")
    assistant_draft: str = Field(..., description="助手生成的草稿")


class DraftProcessResponse(BaseModel):
    """草稿处理响应"""
    final_action: str = Field(..., description="最终动作：PASS, AUTO_FIX, REWRITE, ASK_USER")
    state: Optional[CanonicalState] = Field(default=None, description="更新后的状态（PASS/AUTO_FIX 时提供）")
    recent_events: Optional[List[Event]] = Field(default=None, description="最近的事件列表（PASS/AUTO_FIX 时提供）")
    rewrite_instructions: Optional[str] = Field(default=None, description="重写指令（REWRITE 时提供）")
    questions: Optional[List[str]] = Field(default=None, description="澄清问题（ASK_USER 时提供）")
    violations: Optional[List[Dict[str, Any]]] = Field(default=None, description="违反的规则列表（用于调试）")

