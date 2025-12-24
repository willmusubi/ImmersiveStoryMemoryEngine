"""
API 集成测试
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from fastapi.testclient import TestClient
from backend.api.routes import app
from backend.database import Repository
from backend.extractor import EventExtractor
from backend.gate import ConsistencyGate


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_repository():
    """模拟 Repository"""
    with patch('backend.api.routes.Repository') as mock_repo_class:
        mock_repo = AsyncMock(spec=Repository)
        mock_repo_class.return_value = mock_repo
        yield mock_repo


@pytest.fixture
def mock_extractor():
    """模拟 EventExtractor"""
    with patch('backend.api.routes.EventExtractor') as mock_extractor_class:
        mock_ext = AsyncMock(spec=EventExtractor)
        mock_extractor_class.return_value = mock_ext
        yield mock_ext


@pytest.fixture
def mock_gate():
    """模拟 ConsistencyGate"""
    with patch('backend.api.routes.ConsistencyGate') as mock_gate_class:
        mock_g = MagicMock(spec=ConsistencyGate)
        mock_gate_class.return_value = mock_g
        yield mock_g


@pytest.fixture
def base_state():
    """创建基础状态"""
    from backend.models import (
        CanonicalState,
        MetaInfo,
        TimeState,
        TimeAnchor,
        PlayerState,
        Entities,
        Location,
        QuestState,
        Constraints,
    )
    
    luoyang = Location(id="luoyang", name="洛阳")
    
    return CanonicalState(
        meta=MetaInfo(story_id="test", turn=0),
        time=TimeState(
            calendar="建安三年春",
            anchor=TimeAnchor(label="建安三年春", order=10)
        ),
        player=PlayerState(
            id="player_001",
            name="玩家",
            location_id="luoyang",
        ),
        entities=Entities(
            locations={"luoyang": luoyang},
        ),
        quest=QuestState(),
        constraints=Constraints(),
    )


class TestAPIEndpoints:
    """API 端点测试"""
    
    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        # 根端点现在返回 HTML 测试页面
        assert response.headers["content-type"].startswith("text/html") or "html" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_get_state(self, client, mock_repository, base_state):
        """测试 GET /state/{story_id}"""
        # 模拟 Repository
        mock_repository.get_state = AsyncMock(return_value=base_state)
        
        # 注意：TestClient 是同步的，但我们的路由是异步的
        # 这里需要特殊处理，或者使用 httpx.AsyncClient
        # 简化测试：直接测试路由函数
        from backend.api.routes import get_state
        from backend.database import Repository
        
        with patch('backend.api.routes.get_repository', return_value=mock_repository):
            result = await get_state("test", repo=mock_repository)
            assert result.meta.story_id == "test"
    
    @pytest.mark.asyncio
    async def test_rag_query(self, client):
        """测试 POST /rag/query"""
        response = client.post(
            "/rag/query",
            json={
                "story_id": "test",
                "query": "测试查询",
                "top_k": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
    
    @pytest.mark.asyncio
    async def test_draft_process_pass(self, client, mock_repository, mock_extractor, mock_gate, base_state):
        """测试 POST /draft/process - PASS 场景"""
        from backend.models import Event, EventTime, EventLocation, EventParticipants, EventEvidence, StatePatch, EntityUpdate
        from backend.gate import ValidationResult
        
        # 模拟 Repository
        mock_repository.get_state = AsyncMock(return_value=base_state)
        mock_repository.append_event = AsyncMock()
        mock_repository.save_state = AsyncMock()
        mock_repository.list_recent_events = AsyncMock(return_value=[])
        
        # 模拟 Extractor
        from backend.extractor import ExtractionResult
        event = Event(
            event_id="evt_1_001",
            turn=1,
            time=EventTime(label="建安三年春", order=11),
            where=EventLocation(location_id="luoyang"),
            who=EventParticipants(actors=["player_001"]),
            type="OTHER",
            summary="测试事件",
            payload={},
            state_patch=StatePatch(
                entity_updates={
                    "player_001": EntityUpdate(
                        entity_type="character",
                        entity_id="player_001",
                        updates={"metadata": {"test": True}}
                    )
                }
            ),
            evidence=EventEvidence(source="test"),
        )
        mock_extractor.extract_events = AsyncMock(return_value=ExtractionResult(
            events=[event],
            open_questions=[],
            requires_user_input=False,
        ))
        
        # 模拟 Gate
        mock_gate.validate_event_patch = MagicMock(return_value=ValidationResult(
            action="PASS",
            reasons=[],
            violations=[],
        ))
        
        # 测试路由（简化版，直接调用函数）
        from backend.api.routes import process_draft
        from backend.api.models import DraftProcessRequest
        
        request = DraftProcessRequest(
            story_id="test",
            user_message="测试",
            assistant_draft="测试草稿",
        )
        
        with patch('backend.api.routes.get_repository', return_value=mock_repository), \
             patch('backend.api.routes.get_extractor', return_value=mock_extractor), \
             patch('backend.api.routes.get_gate', return_value=mock_gate):
            result = await process_draft(request, repo=mock_repository, extractor=mock_extractor, gate=mock_gate)
            
            assert result.final_action == "PASS"
            assert result.state is not None
            assert mock_repository.append_event.called
            assert mock_repository.save_state.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

