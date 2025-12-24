"""
FastAPI 路由定义
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from pathlib import Path

from ..database import Repository
from ..extractor import EventExtractor
from ..gate import ConsistencyGate
from ..core.state_manager import apply_multiple_patches
from ..models import CanonicalState
from .models import (
    RAGQueryRequest,
    RAGQueryResponse,
    DraftProcessRequest,
    DraftProcessResponse,
)


# 创建 FastAPI 应用
app = FastAPI(
    title="Immersive Story Memory Engine API",
    description="沉浸式小说记忆引擎 API",
    version="1.0.0",
)

# 挂载静态文件（用于测试页面）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# 依赖注入：获取 Repository
def get_repository() -> Repository:
    """获取 Repository 实例"""
    return Repository()


# 依赖注入：获取 EventExtractor
def get_extractor() -> EventExtractor:
    """获取 EventExtractor 实例"""
    return EventExtractor()


# 依赖注入：获取 ConsistencyGate
def get_gate() -> ConsistencyGate:
    """获取 ConsistencyGate 实例"""
    return ConsistencyGate()


# ==================== 端点 ====================

@app.get("/state/{story_id}", response_model=CanonicalState)
async def get_state(
    story_id: str,
    repo: Repository = Depends(get_repository),
):
    """
    获取指定 story_id 的状态
    
    Args:
        story_id: 剧本ID
        
    Returns:
        CanonicalState: 当前状态
    """
    state = await repo.get_state(story_id)
    
    if state is None:
        # 如果状态不存在，初始化一个默认状态
        state = await repo.initialize_state(story_id)
    
    return state


@app.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
):
    """
    RAG 查询（占位实现）
    
    Args:
        request: RAG 查询请求
        
    Returns:
        RAGQueryResponse: 检索结果
    """
    # TODO: 实现 RAG 查询逻辑
    # 这里先返回占位响应
    return RAGQueryResponse(
        query=request.query,
        results=[
            {
                "text": f"检索结果占位（查询：{request.query}）",
                "score": 0.9,
                "metadata": {}
            }
        ]
    )


@app.post("/draft/process", response_model=DraftProcessResponse)
async def process_draft(
    request: DraftProcessRequest,
    repo: Repository = Depends(get_repository),
    extractor: EventExtractor = Depends(get_extractor),
    gate: ConsistencyGate = Depends(get_gate),
):
    """
    处理草稿：提取事件、校验一致性、应用更新
    
    流程：
    1. load state
    2. （可选）rag query（由外部调用控制）
    3. call extractor -> events
    4. run consistency gate on (state, draft, events)
    5. 根据 action 处理
    
    Args:
        request: 草稿处理请求
        
    Returns:
        DraftProcessResponse: 处理结果
    """
    try:
        # 1. Load state
        state = await repo.get_state(request.story_id)
        if state is None:
            state = await repo.initialize_state(request.story_id)
        
        # 当前轮次应该是 state.meta.turn + 1（新的一轮）
        current_turn = state.meta.turn + 1
        
        # 2. （可选）rag query - 由外部调用控制，本端点不强制
        
        # 3. Call extractor -> events
        extraction_result = await extractor.extract_events(
            canonical_state=state,
            user_message=request.user_message,
            assistant_draft=request.assistant_draft,
            turn=current_turn,
        )
        
        # 如果提取器要求用户输入，直接返回
        if extraction_result.requires_user_input:
            return DraftProcessResponse(
                final_action="ASK_USER",
                questions=extraction_result.open_questions,
            )
        
        events = extraction_result.events
        
        # 4. Run consistency gate on (state, draft, events)
        validation_result = gate.validate_event_patch(
            current_state=state,
            pending_events=events,
        )
        
        # 5. 根据 action 处理
        if validation_result.action == "PASS":
            # PASS: append events + apply patches -> save state
            # 应用所有事件的 state_patch
            updated_state = apply_multiple_patches(state, events)
            
            # 保存事件
            for event in events:
                await repo.append_event(request.story_id, event)
            
            # 保存状态
            await repo.save_state(request.story_id, updated_state)
            
            # 获取最近事件
            recent_events = await repo.list_recent_events(request.story_id, limit=10)
            
            return DraftProcessResponse(
                final_action="PASS",
                state=updated_state,
                recent_events=recent_events,
            )
        
        elif validation_result.action == "AUTO_FIX":
            # AUTO_FIX: apply fixes -> save
            if validation_result.fixes:
                # 应用修复补丁
                # 先应用原始 events 的 patch
                updated_state = apply_multiple_patches(state, events)
                
                # 然后应用 fixes（创建一个修复事件来应用 fixes）
                # 注意：fixes 是一个 StatePatch，我们需要将其应用到状态
                from ..core.state_manager import apply_state_patch
                from ..models import Event, EventTime, EventLocation, EventParticipants, EventEvidence
                import uuid
                from datetime import datetime
                
                # 创建修复事件（用于应用 fixes）
                fix_event_id = f"evt_fix_{current_turn}_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}"
                fix_event = Event(
                    event_id=fix_event_id,
                    turn=current_turn,
                    time=EventTime(
                        label=updated_state.time.calendar,
                        order=updated_state.time.anchor.order,
                    ),
                    where=EventLocation(location_id=updated_state.player.location_id),
                    who=EventParticipants(actors=[updated_state.player.id]),
                    type="OTHER",
                    summary="自动修复",
                    payload={"fix_type": "auto_fix"},
                    state_patch=validation_result.fixes,
                    evidence=EventEvidence(
                        source=f"auto_fix_turn_{current_turn}",
                        text_span=None,
                    ),
                )
                
                # 应用修复补丁
                updated_state = apply_state_patch(
                    updated_state,
                    validation_result.fixes,
                    fix_event_id,
                    current_turn,
                )
                
                # 保存原始事件
                for event in events:
                    await repo.append_event(request.story_id, event)
                
                # 保存修复事件
                await repo.append_event(request.story_id, fix_event)
                
                # 保存状态
                await repo.save_state(request.story_id, updated_state)
                
                # 获取最近事件
                recent_events = await repo.list_recent_events(request.story_id, limit=10)
                
                return DraftProcessResponse(
                    final_action="AUTO_FIX",
                    state=updated_state,
                    recent_events=recent_events,
                    violations=[v.model_dump() for v in validation_result.violations],
                )
            else:
                # 如果没有 fixes，当作 PASS 处理
                updated_state = apply_multiple_patches(state, events)
                for event in events:
                    await repo.append_event(request.story_id, event)
                await repo.save_state(request.story_id, updated_state)
                recent_events = await repo.list_recent_events(request.story_id, limit=10)
                
                return DraftProcessResponse(
                    final_action="PASS",
                    state=updated_state,
                    recent_events=recent_events,
                )
        
        elif validation_result.action == "REWRITE":
            # REWRITE: 返回重写指令
            rewrite_instructions = "\n".join(validation_result.reasons)
            
            return DraftProcessResponse(
                final_action="REWRITE",
                rewrite_instructions=rewrite_instructions,
                violations=[v.model_dump() for v in validation_result.violations],
            )
        
        elif validation_result.action == "ASK_USER":
            # ASK_USER: 返回问题
            questions = validation_result.questions or [
                f"规则 {v.rule_id} 违反: {v.message}"
                for v in validation_result.violations
            ]
            
            return DraftProcessResponse(
                final_action="ASK_USER",
                questions=questions,
                violations=[v.model_dump() for v in validation_result.violations],
            )
        
        else:
            # 未知 action，当作 REWRITE 处理
            return DraftProcessResponse(
                final_action="REWRITE",
                rewrite_instructions="未知的处理动作",
                violations=[v.model_dump() for v in validation_result.violations],
            )
    
    except Exception as e:
        # 错误处理
        raise HTTPException(
            status_code=500,
            detail=f"处理草稿时发生错误: {str(e)}"
        )


@app.get("/")
async def root():
    """根端点 - 返回测试页面"""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return {
        "name": "Immersive Story Memory Engine API",
        "version": "1.0.0",
        "endpoints": {
            "GET /state/{story_id}": "获取状态",
            "POST /rag/query": "RAG 查询",
            "POST /draft/process": "处理草稿",
        },
        "docs": "/docs",
        "test_page": "/static/index.html" if static_file.exists() else None
    }

