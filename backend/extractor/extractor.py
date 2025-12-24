"""
Event Extractor: 从对话草稿中提取结构化事件
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from openai import AsyncOpenAI

from ..models import (
    CanonicalState,
    Event,
    ExtractedEvent,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
    StatePatch,
)
from ..config import settings


class ExtractionResult(BaseModel):
    """提取结果"""
    events: List[Event] = Field(default_factory=list, description="提取的事件列表")
    open_questions: List[str] = Field(default_factory=list, description="需要用户澄清的问题")
    requires_user_input: bool = Field(default=False, description="是否需要用户输入")


class EventExtractor:
    """事件提取器：从对话草稿中提取结构化事件"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 Event Extractor
        
        Args:
            api_key: OpenAI API Key，如果为 None 则从 settings 读取
            base_url: OpenAI API Base URL，如果为 None 则从 settings 读取
            model: 使用的模型，如果为 None 则从 settings 读取
        """
        self.api_key = api_key or settings.super_mind_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        
        if not self.api_key:
            raise ValueError("API key is required. Set SUPER_MIND_API_KEY in .env or pass api_key parameter.")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    async def extract_events(
        self,
        canonical_state: CanonicalState,
        user_message: str,
        assistant_draft: str,
        turn: int,
    ) -> ExtractionResult:
        """
        从对话草稿中提取事件
        
        Args:
            canonical_state: 当前 Canonical State
            user_message: 用户消息
            assistant_draft: 助手生成的草稿
            turn: 当前轮次
            
        Returns:
            ExtractionResult: 提取结果
        """
        # 生成系统提示词
        system_prompt = self._build_system_prompt(canonical_state, turn)
        
        # 生成用户提示词
        user_prompt = self._build_user_prompt(user_message, assistant_draft)
        
        # 获取 JSON Schema
        json_schema = self._get_json_schema()
        
        # 调用 LLM（带重试机制）
        extracted_data = await self._call_llm_with_retry(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
        )
        
        # 解析并转换为 Event 对象
        events = []
        open_questions = []
        requires_user_input = False
        
        if extracted_data:
            # 检查是否有需要澄清的问题
            if "open_questions" in extracted_data and extracted_data["open_questions"]:
                open_questions = extracted_data["open_questions"]
                requires_user_input = True
            
            # 提取事件
            if "events" in extracted_data and extracted_data["events"]:
                for event_data in extracted_data["events"]:
                    try:
                        # 转换为 ExtractedEvent
                        extracted_event = ExtractedEvent.model_validate(event_data)
                        
                        # 转换为 Event（分配 event_id）
                        event = self._convert_to_event(extracted_event, turn, assistant_draft)
                        events.append(event)
                    except Exception as e:
                        # 如果解析失败，记录错误但继续处理其他事件
                        print(f"Warning: Failed to parse event: {e}")
                        continue
        
        # 如果没有提取到事件，创建一个默认事件
        if not events and not requires_user_input:
            events.append(self._create_default_event(canonical_state, turn, assistant_draft))
        
        return ExtractionResult(
            events=events,
            open_questions=open_questions,
            requires_user_input=requires_user_input,
        )
    
    def _build_system_prompt(self, state: CanonicalState, turn: int) -> str:
        """构建系统提示词"""
        # 格式化当前状态摘要
        state_summary = self._format_state_summary(state)
        
        prompt = f"""你是一个事件提取器，负责从对话草稿中提取结构化事件。

## 当前状态（Turn {turn}）

{state_summary}

## 核心规则

1. **任何状态变化必须写入 state_patch**
   - 如果角色位置改变，必须在 state_patch.entity_updates 中更新 location_id
   - 如果物品所有权改变，必须在 state_patch.entity_updates 中更新 owner_id
   - 如果角色生死状态改变，必须在 state_patch.entity_updates 中更新 alive
   - 如果时间推进，必须在 state_patch.time_update 中更新

2. **不可凭空出现物品/复活/瞬移**
   - 如果草稿中出现了当前状态中不存在的物品，必须标记为 open_questions
   - 如果草稿中描述了死亡角色的行动，必须标记为 open_questions
   - 如果角色位置改变但没有明确的移动描述，必须标记为 open_questions

3. **事件类型必须准确**
   - OWNERSHIP_CHANGE: 物品所有权变更
   - DEATH: 角色死亡
   - REVIVAL: 角色复活
   - TRAVEL: 角色移动
   - FACTION_CHANGE: 阵营变更
   - QUEST_START/QUEST_COMPLETE/QUEST_FAIL: 任务相关
   - ITEM_CREATE/ITEM_DESTROY: 物品创建/销毁
   - TIME_ADVANCE: 时间推进
   - OTHER: 其他事件

4. **必须输出至少 1 个事件**
   - 即使没有明显的事件，也要创建一个描述当前对话的 OTHER 类型事件

## 输出格式

严格按照 JSON Schema 输出，包含：
- events: 事件列表（至少 1 个）
- open_questions: 需要用户澄清的问题列表（如果有）

如果检测到需要澄清的情况（如凭空出现物品、死亡角色行动等），在 open_questions 中列出问题，并设置 requires_user_input=true。
"""
        return prompt
    
    def _format_state_summary(self, state: CanonicalState) -> str:
        """格式化状态摘要"""
        lines = []
        
        # 时间信息
        lines.append(f"时间: {state.time.calendar} (order: {state.time.anchor.order})")
        
        # 玩家信息
        lines.append(f"\n玩家: {state.player.name} @ {state.player.location_id}")
        if state.player.party:
            lines.append(f"  队伍: {', '.join(state.player.party)}")
        if state.player.inventory:
            lines.append(f"  物品: {', '.join(state.player.inventory)}")
        
        # 关键角色
        lines.append("\n关键角色:")
        for char_id, char in list(state.entities.characters.items())[:10]:  # 限制显示数量
            status = "存活" if char.alive else "死亡"
            location = state.entities.locations.get(char.location_id, None)
            location_name = location.name if location else char.location_id
            lines.append(f"  - {char.name} ({char_id}): {status}, 位置: {location_name}")
        
        # 关键物品
        if state.entities.items:
            lines.append("\n关键物品:")
            for item_id, item in list(state.entities.items.items())[:10]:
                owner_info = f"拥有者: {item.owner_id}" if item.owner_id else f"位置: {item.location_id}"
                lines.append(f"  - {item.name} ({item_id}): {owner_info}")
        
        # 约束
        if state.constraints.unique_item_ids:
            lines.append(f"\n唯一物品: {', '.join(state.constraints.unique_item_ids)}")
        if state.constraints.immutable_events:
            lines.append(f"不可变事件: {len(state.constraints.immutable_events)} 个")
        
        return "\n".join(lines)
    
    def _build_user_prompt(self, user_message: str, assistant_draft: str) -> str:
        """构建用户提示词"""
        return f"""请从以下对话中提取事件：

## 用户消息
{user_message}

## 助手草稿
{assistant_draft}

请提取所有状态变化相关的事件，并确保：
1. 每个事件都有对应的 state_patch
2. 如果检测到需要澄清的情况，在 open_questions 中列出
3. 至少输出 1 个事件
"""
    
    def _get_json_schema(self) -> Dict[str, Any]:
        """获取 JSON Schema"""
        # 使用 ExtractedEvent 的 JSON Schema
        # 但需要包装成包含 events 数组和 open_questions 的格式
        
        # 获取 ExtractedEvent 的 schema
        extracted_event_schema = ExtractedEvent.model_json_schema()
        
        # OpenAI 的 JSON schema 格式需要特定的结构
        return {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": extracted_event_schema,
                    "minItems": 1,
                    "description": "提取的事件列表，至少包含 1 个事件"
                },
                "open_questions": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "需要用户澄清的问题列表"
                }
            },
            "required": ["events"]
        }
    
    async def _call_llm_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Dict[str, Any],
        max_retries: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        调用 LLM，带重试机制
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            json_schema: JSON Schema
            max_retries: 最大重试次数
            
        Returns:
            解析后的 JSON 数据，如果失败则返回 None
        """
        for attempt in range(max_retries + 1):
            try:
                # 构建消息
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # 如果是重试，添加更严格的指令
                if attempt > 0:
                    messages.append({
                        "role": "system",
                        "content": "⚠️ 重要：上次解析失败。请严格按照 JSON Schema 输出，确保所有字段都符合要求。"
                    })
                
                # 调用 API
                # 注意：某些 API 可能不支持 json_schema，使用 json_object 作为后备
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "json_schema", "json_schema": {
                            "name": "event_extraction",
                            "strict": True,
                            "schema": json_schema
                        }},
                        temperature=0.3,  # 降低温度以提高一致性
                    )
                except Exception as e:
                    # 如果不支持 json_schema，尝试使用 json_object
                    if "json_schema" in str(e).lower() or "response_format" in str(e).lower():
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            response_format={"type": "json_object"},
                            temperature=0.3,
                        )
                    else:
                        raise
                
                # 解析响应
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM")
                
                # 尝试解析 JSON
                try:
                    data = json.loads(content)
                    return data
                except json.JSONDecodeError as e:
                    # 如果 JSON 解析失败，尝试提取 JSON 部分
                    # 有些模型会在 JSON 外包裹 markdown 代码块
                    cleaned_content = content.strip()
                    
                    # 尝试提取 markdown 代码块中的 JSON
                    if "```json" in cleaned_content:
                        json_start = cleaned_content.find("```json") + 7
                        json_end = cleaned_content.find("```", json_start)
                        if json_end > json_start:
                            cleaned_content = cleaned_content[json_start:json_end].strip()
                    elif "```" in cleaned_content:
                        # 尝试提取普通代码块
                        json_start = cleaned_content.find("```") + 3
                        json_end = cleaned_content.find("```", json_start)
                        if json_end > json_start:
                            cleaned_content = cleaned_content[json_start:json_end].strip()
                    
                    # 再次尝试解析
                    try:
                        data = json.loads(cleaned_content)
                        return data
                    except json.JSONDecodeError:
                        raise ValueError(f"Failed to parse JSON after cleaning: {e}. Content: {content[:200]}")
                    
            except Exception as e:
                if attempt < max_retries:
                    print(f"Attempt {attempt + 1} failed: {e}, retrying...")
                    continue
                else:
                    print(f"All attempts failed: {e}")
                    raise
        
        return None
    
    def _convert_to_event(
        self,
        extracted_event: ExtractedEvent,
        turn: int,
        assistant_draft: str,
    ) -> Event:
        """
        将 ExtractedEvent 转换为 Event（分配 event_id）
        
        Args:
            extracted_event: 提取的事件
            turn: 当前轮次
            assistant_draft: 助手草稿（作为证据）
            
        Returns:
            Event 对象
        """
        # 生成 event_id
        timestamp = int(datetime.now().timestamp())
        hash_suffix = str(uuid.uuid4())[:8]
        event_id = f"evt_{turn}_{timestamp}_{hash_suffix}"
        
        # 构建 Event
        event = Event(
            event_id=event_id,
            turn=extracted_event.turn,
            time=extracted_event.time,
            where=extracted_event.where,
            who=extracted_event.who,
            type=extracted_event.type,
            summary=extracted_event.summary,
            payload=extracted_event.payload,
            state_patch=extracted_event.state_patch,
            evidence=EventEvidence(
                source=f"draft_turn_{turn}",
                text_span=assistant_draft[:200] if assistant_draft else None,  # 限制长度
            ),
        )
        
        return event
    
    def _create_default_event(
        self,
        state: CanonicalState,
        turn: int,
        assistant_draft: str,
    ) -> Event:
        """
        创建默认事件（当没有提取到事件时）
        
        Args:
            state: 当前状态
            turn: 当前轮次
            assistant_draft: 助手草稿
            
        Returns:
            默认 Event 对象
        """
        timestamp = int(datetime.now().timestamp())
        hash_suffix = str(uuid.uuid4())[:8]
        event_id = f"evt_{turn}_{timestamp}_{hash_suffix}"
        
        # Event 要求 state_patch 必须包含至少一个更新
        # 创建一个最小的更新（更新玩家的 metadata）
        from ..models import EntityUpdate
        state_patch = StatePatch(
            entity_updates={
                state.player.id: EntityUpdate(
                    entity_type="character",
                    entity_id=state.player.id,
                    updates={"metadata": {"last_turn": turn}}
                )
            }
        )
        
        return Event(
            event_id=event_id,
            turn=turn,
            time=EventTime(
                label=state.time.calendar,
                order=state.time.anchor.order,
            ),
            where=EventLocation(location_id=state.player.location_id),
            who=EventParticipants(actors=[state.player.id]),
            type="OTHER",
            summary="对话继续",
            payload={},
            state_patch=state_patch,
            evidence=EventEvidence(
                source=f"draft_turn_{turn}",
                text_span=assistant_draft[:200] if assistant_draft else None,
            ),
        )

