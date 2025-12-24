# JSON Schema 导出说明

## 生成 JSON Schema

在安装依赖后，运行以下命令生成所有模型的 JSON Schema：

```bash
# 安装依赖
pip install -r requirements.txt

# 导出 JSON Schema
python scripts/export_schemas.py
```

或者使用 python3：

```bash
python3 scripts/export_schemas.py
```

## 导出的 Schema 文件

脚本会在 `schemas/` 目录下生成以下 JSON Schema 文件：

### 核心模型

- `CanonicalState.json` - 唯一真相状态
- `Event.json` - 事件模型
- `ExtractedEvent.json` - 抽取的事件模型
- `StatePatch.json` - 状态补丁

### State 子模型

- `MetaInfo.json` - 元信息
- `TimeState.json` - 时间状态
- `PlayerState.json` - 玩家状态
- `Entities.json` - 实体集合
- `QuestState.json` - 任务状态
- `Constraints.json` - 约束集合
- `Character.json` - 人物实体
- `Item.json` - 物品实体
- `Location.json` - 地点实体
- `Faction.json` - 阵营实体
- `Quest.json` - 任务
- `Constraint.json` - 硬约束

### Event 子模型

- `EventTime.json` - 事件时间
- `EventLocation.json` - 事件地点
- `EventParticipants.json` - 事件参与者
- `EventEvidence.json` - 事件证据

### Patch 子模型

- `EntityUpdate.json` - 实体更新
- `TimeUpdate.json` - 时间更新
- `QuestUpdate.json` - 任务更新

## 使用 JSON Schema

这些 Schema 可以用于：

1. API 文档生成（如 OpenAPI/Swagger）
2. 前端类型定义生成（TypeScript）
3. 数据验证
4. 客户端 SDK 生成
