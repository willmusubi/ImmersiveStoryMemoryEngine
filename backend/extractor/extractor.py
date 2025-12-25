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
        
        # 尝试使用 function calling，如果失败则回退到 JSON 模式
        function_def = self._get_function_definition()
        json_schema = self._get_json_schema()
        
        extracted_data = None
        
        try:
            # 先尝试 function calling
            extracted_data = await self._call_llm_with_function_calling(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                function_def=function_def,
            )
        except Exception as e:
            print(f"Function calling failed: {e}, falling back to JSON mode...")
            try:
                # 回退到 JSON 模式
                extracted_data = await self._call_llm_with_retry(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=json_schema,
                )
            except Exception as e2:
                # 如果 JSON 模式也失败，记录错误但继续处理
                print(f"JSON mode also failed: {e2}")
                print("Will create default event to ensure workflow continues")
                extracted_data = None
        
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
        
        # 获取当前玩家位置和关键实体ID，用于示例
        player_location = state.player.location_id
        player_id = state.player.id
        example_char_id = list(state.entities.characters.keys())[0] if state.entities.characters else "caocao"
        example_item_id = list(state.entities.items.keys())[0] if state.entities.items else "sword_001"
        
        prompt = f"""你是一个事件提取器，负责从对话草稿中提取结构化事件并识别所有状态变化。

## 当前状态（Turn {turn}）

{state_summary}

## 核心任务

**你必须识别草稿中的所有状态变化，并在 state_patch 中准确记录！**

## 状态变化识别规则

### 1. 物品所有权变更（OWNERSHIP_CHANGE）
**识别关键词**：给、借、递、交给、获得、拾起、拿起、丢失、掉落、归还

**必须提取**：
- 物品ID（从当前状态中查找）
- 原拥有者ID
- 新拥有者ID

**state_patch 格式**：
```json
{{
  "entity_updates": {{
    "{example_item_id}": {{
      "entity_type": "item",
      "entity_id": "{example_item_id}",
      "updates": {{
        "owner_id": "新拥有者ID",
        "location_id": "新拥有者所在位置ID"
      }}
    }}
  }},
  "player_updates": {{
    "inventory_add": ["物品ID"]  // 如果新拥有者是玩家
  }}
}}
```

### 2. 角色移动（TRAVEL）
**识别关键词**：前往、到达、离开、来到、抵达、移动到、出发、返回

**必须提取**：
- 移动的角色ID
- 起始位置ID
- 目标位置ID

**state_patch 格式**：
```json
{{
  "entity_updates": {{
    "{player_id}": {{
      "entity_type": "character",
      "entity_id": "{player_id}",
      "updates": {{
        "location_id": "目标位置ID"
      }}
    }}
  }},
  "player_updates": {{
    "location_id": "目标位置ID"
  }}
}}
```

### 3. 角色死亡（DEATH）
**识别关键词**：死亡、被杀、战死、去世、阵亡

**state_patch 格式**：
```json
{{
  "entity_updates": {{
    "角色ID": {{
      "entity_type": "character",
      "entity_id": "角色ID",
      "updates": {{
        "alive": false
      }}
    }}
  }}
}}
```

### 4. 物品创建/获得（ITEM_CREATE）
**识别关键词**：发现、找到、获得（新物品）、拾到

**注意**：如果物品在当前状态中不存在，必须标记为 open_questions！

### 5. 时间推进（TIME_ADVANCE）
**识别关键词**：过了、之后、第二天、几日后、时间流逝

**state_patch 格式**：
```json
{{
  "time_update": {{
    "calendar": "新的日历时间",
    "anchor": {{
      "label": "新的时间标签",
      "order": 当前order + 1
    }}
  }}
}}
```

## 关键格式要求

### state_patch.entity_updates 格式（重要！）
**必须是对象（字典），不是数组！**

```json
{{
  "实体ID": {{
    "entity_type": "character|item|location|faction",
    "entity_id": "实体ID",
    "updates": {{
      "字段名": "新值"
    }}
  }}
}}
```

**常见更新字段**：
- character: location_id, alive, faction_id, metadata
- item: owner_id, location_id, metadata
- location: name, metadata
- faction: name, leader_id, members, metadata

### state_patch.player_updates 格式
```json
{{
  "location_id": "新位置ID",              // 直接更新位置
  "inventory_add": ["item_id1", ...],     // 添加物品到库存
  "inventory_remove": ["item_id1"],       // 从库存移除物品
  "party_add": ["char_id1"],              // 添加角色到队伍
  "party_remove": ["char_id1"]            // 从队伍移除角色
}}
```

## 完整示例

### 示例 1: 物品所有权变更
**草稿**："曹操将青釭剑递给玩家，说道：'这把剑就借给你了。'"

**正确提取**：
```json
{{
  "events": [
    {{
      "turn": {turn},
      "time": {{"label": "{state.time.calendar}", "order": {state.time.anchor.order + 1}}},
      "where": {{"location_id": "{player_location}"}},
      "who": {{"actors": ["{player_id}", "{example_char_id}"], "witnesses": []}},
      "type": "OWNERSHIP_CHANGE",
      "summary": "曹操将青釭剑借给玩家",
      "payload": {{
        "item_id": "{example_item_id}",
        "old_owner_id": "{example_char_id}",
        "new_owner_id": "{player_id}"
      }},
      "state_patch": {{
        "entity_updates": {{
          "{example_item_id}": {{
            "entity_type": "item",
            "entity_id": "{example_item_id}",
            "updates": {{
              "owner_id": "{player_id}",
              "location_id": "{player_location}"
            }}
          }}
        }},
        "player_updates": {{
          "inventory_add": ["{example_item_id}"]
        }},
        "time_update": null,
        "quest_updates": null,
        "constraint_additions": []
      }},
      "evidence": {{"source": "draft_turn_{turn}", "text_span": null}},
      "confidence": 1.0
    }}
  ],
  "open_questions": []
}}
```

### 示例 2: 角色移动
**草稿**："玩家离开洛阳，经过长途跋涉，终于到达了许昌。"

**正确提取**：
```json
{{
  "events": [
    {{
      "turn": {turn},
      "time": {{"label": "{state.time.calendar}", "order": {state.time.anchor.order + 1}}},
      "where": {{"location_id": "xuchang"}},
      "who": {{"actors": ["{player_id}"], "witnesses": []}},
      "type": "TRAVEL",
      "summary": "玩家从洛阳前往许昌",
      "payload": {{
        "character_id": "{player_id}",
        "from_location_id": "{player_location}",
        "to_location_id": "xuchang"
      }},
      "state_patch": {{
        "entity_updates": {{
          "{player_id}": {{
            "entity_type": "character",
            "entity_id": "{player_id}",
            "updates": {{
              "location_id": "xuchang"
            }}
          }}
        }},
        "player_updates": {{
          "location_id": "xuchang"
        }},
        "time_update": null,
        "quest_updates": null,
        "constraint_additions": []
      }},
      "evidence": {{"source": "draft_turn_{turn}", "text_span": null}},
      "confidence": 1.0
    }}
  ],
  "open_questions": []
}}
```

## 重要规则

1. **任何状态变化必须写入 state_patch**
   - 如果草稿中描述了状态变化，但没有写入 state_patch，这是错误的！

2. **不可凭空出现物品/复活/瞬移**
   - 如果物品不存在 → open_questions
   - 如果死亡角色行动 → open_questions
   - 如果位置改变但没有移动描述 → open_questions

3. **事件类型必须准确**
   - OWNERSHIP_CHANGE: 物品所有权变更
   - TRAVEL: 角色移动（必须有明确的移动描述）
   - DEATH: 角色死亡
   - REVIVAL: 角色复活
   - FACTION_CHANGE: 阵营变更
   - ITEM_CREATE/ITEM_DESTROY: 物品创建/销毁
   - TIME_ADVANCE: 时间推进
   - OTHER: 其他事件（没有明显状态变化时使用）

4. **必须输出至少 1 个事件**

## 必须调用 extract_events 函数

**重要**：你必须调用 extract_events 函数来返回结果，不要输出任何其他内容！

函数会自动验证格式，如果格式错误会导致提取失败。
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
        return f"""请从以下对话中提取事件，**必须调用 extract_events 函数返回结果**：

## 用户消息
{user_message}

## 助手草稿
{assistant_draft}

## 提取要求

1. **仔细分析草稿，识别所有状态变化**：
   - 物品所有权是否改变？（给、借、递等关键词）
   - 角色位置是否改变？（前往、到达、离开等关键词）
   - 角色生死状态是否改变？（死亡、复活等关键词）
   - 时间是否推进？（过了、之后等关键词）

2. **对于每个状态变化，必须写入 state_patch**：
   - 物品所有权变更 → entity_updates[物品ID].updates.owner_id + player_updates.inventory_add/remove
   - 角色移动 → entity_updates[角色ID].updates.location_id + player_updates.location_id
   - 角色死亡 → entity_updates[角色ID].updates.alive = false
   - 时间推进 → time_update

3. **如果检测到需要澄清的情况，在 open_questions 中列出**：
   - 物品不存在
   - 死亡角色行动
   - 位置改变但没有明确移动描述

4. **至少输出 1 个事件**（即使没有明显状态变化，也要创建 OTHER 类型事件）

**重要：必须调用 extract_events 函数，不要输出任何其他内容！**
"""
    
    def _get_function_definition(self) -> Dict[str, Any]:
        """获取 Function Calling 的函数定义"""
        # 获取 ExtractedEvent 的 JSON Schema
        extracted_event_schema = ExtractedEvent.model_json_schema()
        
        # 定义 function calling 的工具
        return {
            "type": "function",
            "function": {
                "name": "extract_events",
                "description": "从对话草稿中提取结构化事件。必须调用此函数来返回提取结果。",
                "parameters": {
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
                            "description": "需要用户澄清的问题列表（如果有）",
                            "default": []
                        }
                    },
                    "required": ["events"]
                }
            }
        }
    
    def _get_json_schema(self) -> Dict[str, Any]:
        """获取 JSON Schema（用于回退模式）"""
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
    
    async def _call_llm_with_function_calling(
        self,
        system_prompt: str,
        user_prompt: str,
        function_def: Dict[str, Any],
        max_retries: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        使用 Function Calling 调用 LLM，带重试机制
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            function_def: Function definition
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
                        "content": "⚠️ 重要：上次调用失败。请务必调用 extract_events 函数来返回结果，不要输出其他内容。"
                    })
                
                # 调用 API，使用 function calling
                # 注意：某些模型可能不支持强制 tool_choice，先尝试可选模式
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=[function_def],
                        tool_choice={"type": "function", "function": {"name": "extract_events"}},  # 强制调用函数
                        temperature=0.2,
                    )
                except Exception as e:
                    # 如果强制调用失败，尝试可选模式
                    if "tool_choice" in str(e).lower() or "function" in str(e).lower():
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            tools=[function_def],
                            tool_choice="auto",  # 让模型自己决定
                            temperature=0.2,
                        )
                    else:
                        raise
                
                # 从 tool_calls 中提取结果
                message = response.choices[0].message
                
                # 检查是否有 tool_calls
                if message.tool_calls and len(message.tool_calls) > 0:
                    tool_call = message.tool_calls[0]
                    if tool_call.function.name == "extract_events":
                        # 解析 function arguments
                        arguments_str = tool_call.function.arguments
                        try:
                            data = json.loads(arguments_str)
                            return data
                        except json.JSONDecodeError as e:
                            raise ValueError(f"Failed to parse function arguments: {e}")
                    else:
                        raise ValueError(f"Unexpected function call: {tool_call.function.name}")
                else:
                    # 如果没有 tool_calls，尝试从 content 中解析（后备方案）
                    if message.content:
                        # 尝试解析 JSON
                        try:
                            data = json.loads(message.content)
                            return data
                        except json.JSONDecodeError:
                            raise ValueError(f"Model did not call function and content is not valid JSON: {message.content[:200]}")
                    else:
                        raise ValueError("Model did not call function and has no content")
                        
            except Exception as e:
                if attempt < max_retries:
                    print(f"Attempt {attempt + 1} failed: {e}, retrying...")
                    continue
                else:
                    print(f"All attempts failed: {e}")
                    raise
        
        return None
    
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
                        "content": """⚠️ 重要：上次解析失败。请严格按照以下要求：

1. **只输出 JSON，不要输出任何其他文字、解释或说明**
2. 输出必须是纯 JSON 格式，可以直接用 json.loads() 解析
3. 每个事件必须包含所有必需字段：turn, time, where, who, type, summary, payload, state_patch, evidence, confidence
4. state_patch.entity_updates 必须是对象（字典），键为实体ID
5. 不要输出任何 markdown、代码块标记或其他格式"""
                    })
                
                # 调用 API
                # 注意：某些 API 可能不支持 json_schema，使用 json_object 作为后备
                try:
                    # 先尝试使用 json_object（更通用）
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.2,  # 降低温度以提高一致性
                    )
                except Exception as e:
                    # 如果失败，尝试 json_schema
                    try:
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            response_format={"type": "json_schema", "json_schema": {
                                "name": "event_extraction",
                                "strict": True,
                                "schema": json_schema
                            }},
                            temperature=0.2,
                        )
                    except Exception as e2:
                        raise e2
                
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
                    # 有些模型会在 JSON 外包裹 markdown 代码块或其他文本
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
                    
                    # 尝试找到第一个 { 和最后一个 }
                    if "{" in cleaned_content and "}" in cleaned_content:
                        first_brace = cleaned_content.find("{")
                        last_brace = cleaned_content.rfind("}")
                        if first_brace < last_brace:
                            cleaned_content = cleaned_content[first_brace:last_brace + 1]
                    
                    # 再次尝试解析
                    try:
                        data = json.loads(cleaned_content)
                        return data
                    except json.JSONDecodeError:
                        raise ValueError(f"Failed to parse JSON after cleaning: {e}. Content preview: {content[:500]}")
                    
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

