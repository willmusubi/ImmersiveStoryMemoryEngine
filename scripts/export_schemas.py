"""
导出 Pydantic 模型为 JSON Schema
"""
import json
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.models import (
    CanonicalState,
    Event,
    ExtractedEvent,
    StatePatch,
    MetaInfo,
    TimeState,
    PlayerState,
    Entities,
    QuestState,
    Constraints,
    Character,
    Item,
    Location,
    Faction,
    Quest,
    Constraint,
    EventTime,
    EventLocation,
    EventParticipants,
    EventEvidence,
    EntityUpdate,
    TimeUpdate,
    QuestUpdate,
)


def export_schema(model_class, output_dir: Path):
    """导出单个模型的 JSON Schema"""
    schema = model_class.model_json_schema(mode='serialization')
    schema_file = output_dir / f"{model_class.__name__}.json"
    
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print(f"Exported: {schema_file}")


def main():
    """导出所有模型的 JSON Schema"""
    # 创建 schemas 目录
    schemas_dir = Path(__file__).parent.parent / "schemas"
    schemas_dir.mkdir(exist_ok=True)
    
    # 定义要导出的模型
    models = [
        # 核心模型
        CanonicalState,
        Event,
        ExtractedEvent,
        StatePatch,
        # State 子模型
        MetaInfo,
        TimeState,
        PlayerState,
        Entities,
        QuestState,
        Constraints,
        Character,
        Item,
        Location,
        Faction,
        Quest,
        Constraint,
        # Event 子模型
        EventTime,
        EventLocation,
        EventParticipants,
        EventEvidence,
        # Patch 子模型
        EntityUpdate,
        TimeUpdate,
        QuestUpdate,
    ]
    
    print(f"Exporting JSON Schemas to {schemas_dir}...")
    for model in models:
        export_schema(model, schemas_dir)
    
    print(f"\n✅ Exported {len(models)} schemas successfully!")


if __name__ == "__main__":
    main()

