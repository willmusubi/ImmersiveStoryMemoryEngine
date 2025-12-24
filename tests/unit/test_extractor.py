"""
Event Extractor 测试
"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.extractor import EventExtractor, ExtractionResult
from backend.models import (
    CanonicalState,
    MetaInfo,
    TimeState,
    TimeAnchor,
    PlayerState,
    Entities,
    Character,
    Location,
    QuestState,
    Constraints,
    Event,
    ExtractedEvent,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
    StatePatch,
)


@pytest.fixture
def base_state():
    """创建基础状态"""
    luoyang = Location(id="luoyang", name="洛阳")
    
    caocao = Character(
        id="caocao",
        name="曹操",
        location_id="luoyang",
        alive=True,
    )
    
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
            characters={"caocao": caocao},
            items={},
            locations={"luoyang": luoyang},
        ),
        quest=QuestState(),
        constraints=Constraints(),
    )


@pytest.fixture
def mock_extractor():
    """创建模拟的 EventExtractor（不实际调用 API）"""
    with patch('backend.extractor.extractor.AsyncOpenAI'):
        extractor = EventExtractor(
            api_key="test_key",
            base_url="https://test.api.com/v1",
            model="test-model"
        )
        return extractor


class TestEventExtractor:
    """Event Extractor 测试"""
    
    @pytest.mark.asyncio
    async def test_extract_events_success(self, base_state, mock_extractor):
        """测试：成功提取事件"""
        # 模拟 LLM 响应
        mock_response_data = {
            "events": [
                {
                    "turn": 1,
                    "time": {
                        "label": "建安三年春",
                        "order": 11
                    },
                    "where": {
                        "location_id": "luoyang"
                    },
                    "who": {
                        "actors": ["player_001"],
                        "witnesses": []
                    },
                    "type": "OTHER",
                    "summary": "玩家与曹操对话",
                    "payload": {},
                    "state_patch": {
                        "entity_updates": {
                            "player_001": {
                                "entity_type": "character",
                                "entity_id": "player_001",
                                "updates": {"metadata": {"action": "speak"}}
                            }
                        },
                        "constraint_additions": []
                    },
                    "evidence": {
                        "source": "draft_turn_1",
                        "text_span": None
                    },
                    "confidence": 1.0
                }
            ],
            "open_questions": []
        }
        
        # 模拟 API 调用
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_response_data)
        
        mock_extractor.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # 执行提取
        result = await mock_extractor.extract_events(
            canonical_state=base_state,
            user_message="你好",
            assistant_draft="玩家向曹操打招呼。",
            turn=1,
        )
        
        # 验证结果
        assert isinstance(result, ExtractionResult)
        assert len(result.events) == 1
        assert result.events[0].type == "OTHER"
        assert result.events[0].summary == "玩家与曹操对话"
        assert not result.requires_user_input
    
    @pytest.mark.asyncio
    async def test_extract_events_with_open_questions(self, base_state, mock_extractor):
        """测试：提取到需要澄清的问题"""
        # 模拟 LLM 响应（包含 open_questions）
        mock_response_data = {
            "events": [
                {
                    "turn": 1,
                    "time": {
                        "label": "建安三年春",
                        "order": 11
                    },
                    "where": {
                        "location_id": "luoyang"
                    },
                    "who": {
                        "actors": ["player_001"],
                        "witnesses": []
                    },
                    "type": "OTHER",
                    "summary": "玩家发现了一个物品",
                    "payload": {},
                    "state_patch": {
                        "entity_updates": {
                            "player_001": {
                                "entity_type": "character",
                                "entity_id": "player_001",
                                "updates": {"metadata": {"action": "speak"}}
                            }
                        },
                        "constraint_additions": []
                    },
                    "evidence": {
                        "source": "draft_turn_1",
                        "text_span": None
                    },
                    "confidence": 0.8
                }
            ],
            "open_questions": [
                "草稿中提到了一件物品，但当前状态中不存在。请确认这是什么物品？"
            ]
        }
        
        # 模拟 API 调用
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_response_data)
        
        mock_extractor.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # 执行提取
        result = await mock_extractor.extract_events(
            canonical_state=base_state,
            user_message="我发现了一个物品",
            assistant_draft="玩家在地上发现了一把剑。",
            turn=1,
        )
        
        # 验证结果
        assert result.requires_user_input
        assert len(result.open_questions) > 0
    
    @pytest.mark.asyncio
    async def test_extract_events_retry_on_parse_error(self, base_state, mock_extractor):
        """测试：JSON 解析失败时重试"""
        # 第一次返回无效 JSON
        invalid_response = MagicMock()
        invalid_response.choices = [MagicMock()]
        invalid_response.choices[0].message.content = "这不是有效的 JSON"
        
        # 第二次返回有效 JSON
        valid_response_data = {
            "events": [
                {
                    "turn": 1,
                    "time": {"label": "建安三年春", "order": 11},
                    "where": {"location_id": "luoyang"},
                    "who": {"actors": ["player_001"], "witnesses": []},
                    "type": "OTHER",
                    "summary": "对话继续",
                    "payload": {},
                    "state_patch": {"entity_updates": {}, "constraint_additions": []},
                    "evidence": {"source": "draft_turn_1", "text_span": None},
                    "confidence": 1.0
                }
            ],
            "open_questions": []
        }
        valid_response = MagicMock()
        valid_response.choices = [MagicMock()]
        valid_response.choices[0].message.content = json.dumps(valid_response_data)
        
        # 模拟重试
        mock_extractor.client.chat.completions.create = AsyncMock(
            side_effect=[invalid_response, valid_response]
        )
        
        # 执行提取
        result = await mock_extractor.extract_events(
            canonical_state=base_state,
            user_message="测试",
            assistant_draft="测试草稿",
            turn=1,
        )
        
        # 验证重试成功
        assert len(result.events) == 1
        assert mock_extractor.client.chat.completions.create.call_count == 2
    
    def test_convert_to_event(self, mock_extractor):
        """测试：ExtractedEvent 转换为 Event"""
        from backend.models import EntityUpdate
        
        extracted_event = ExtractedEvent(
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
            confidence=1.0,
        )
        
        event = mock_extractor._convert_to_event(extracted_event, turn=1, assistant_draft="测试")
        
        assert isinstance(event, Event)
        assert event.event_id.startswith("evt_")
        assert event.turn == 1
        assert event.type == "OTHER"
        assert event.summary == "测试事件"
    
    def test_create_default_event(self, base_state, mock_extractor):
        """测试：创建默认事件"""
        event = mock_extractor._create_default_event(
            state=base_state,
            turn=1,
            assistant_draft="测试草稿",
        )
        
        assert isinstance(event, Event)
        assert event.event_id.startswith("evt_")
        assert event.turn == 1
        assert event.type == "OTHER"
        assert event.summary == "对话继续"
    
    def test_format_state_summary(self, base_state, mock_extractor):
        """测试：格式化状态摘要"""
        summary = mock_extractor._format_state_summary(base_state)
        
        assert "时间:" in summary
        assert "玩家:" in summary
        assert "关键角色:" in summary
        assert "曹操" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

