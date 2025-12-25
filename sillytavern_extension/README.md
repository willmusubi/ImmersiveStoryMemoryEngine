# Immersive Story Memory Engine - SillyTavern Extension

这是一个为 SillyTavern 提供沉浸式小说记忆引擎支持的扩展。它能够自动管理故事状态、提取事件并校验一致性。

## 功能特性

1. **状态管理**
   - 在每轮用户发送消息前，自动获取当前故事状态
   - 将状态摘要注入到系统提示词中，帮助模型理解当前故事状态

2. **事件提取与验证**
   - 在模型生成回复后，自动提取事件并验证一致性
   - 根据验证结果自动处理（通过/自动修复/重写/询问用户）

3. **状态摘要面板**
   - 显示当前故事状态摘要（时间、地点、队伍、物品、任务等）
   - 显示最近事件列表

4. **可配置**
   - 支持配置后端API地址（默认：http://127.0.0.1:8000）
   - 支持配置故事ID

## 安装

1. 将整个 `sillytavern_extension` 文件夹复制到 SillyTavern 的扩展目录：
   ```
   SillyTavern/extensions/
   ```

2. 在 SillyTavern 中启用扩展：
   - 打开 SillyTavern
   - 进入扩展设置
   - 找到 "Immersive Story Memory Engine" 并启用

## 配置

### 后端API地址

默认后端地址为 `http://127.0.0.1:8000`。如果需要修改，可以在扩展设置中配置：

1. 打开扩展设置
2. 找到 "Immersive Story Memory Engine" 设置
3. 修改 "后端URL" 字段

### 故事ID

故事ID用于标识不同的故事会话。可以在扩展设置中配置，也可以从聊天元数据中自动获取。

## 使用方法

### 基本使用

1. **启动后端服务**
   ```bash
   cd /path/to/ImmersiveStoryMemoryEngine
   python run_server.py
   ```

2. **在 SillyTavern 中启用扩展**
   - 确保后端服务正在运行
   - 在扩展设置中启用 "Immersive Story Memory Engine"

3. **开始对话**
   - 扩展会自动在每轮对话前获取状态并注入到系统提示词
   - 模型生成回复后，扩展会自动处理并验证一致性

### 状态摘要

状态摘要会自动显示在侧栏面板中，包括：
- **时间**：当前故事时间
- **地点**：玩家当前位置
- **队伍**：队伍成员列表
- **物品**：玩家拥有的关键物品
- **生命状态**：队伍成员的存活状态
- **任务阶段**：当前进行中和已完成的任务
- **轮次**：当前对话轮次

### 事件处理

扩展会根据后端返回的结果自动处理：

- **PASS**：事件通过验证，正常继续
- **AUTO_FIX**：自动修复不一致，继续对话
- **REWRITE**：需要重写回复，扩展会自动触发重写
- **ASK_USER**：需要用户澄清，扩展会显示提示框

## API 要求

扩展需要后端提供以下API端点：

### GET /state/{story_id}

获取指定故事的状态。

**响应示例：**
```json
{
  "meta": {
    "story_id": "sanguo_yanyi",
    "turn": 5,
    ...
  },
  "time": {
    "calendar": "建安三年春",
    ...
  },
  "player": {
    "location_id": "luoyang",
    "party": ["caocao", "guanyu"],
    ...
  },
  ...
}
```

### POST /draft/process

处理助手生成的草稿。

**请求：**
```json
{
  "story_id": "sanguo_yanyi",
  "user_message": "用户消息",
  "assistant_draft": "助手生成的草稿"
}
```

**响应（PASS）：**
```json
{
  "final_action": "PASS",
  "state": {...},
  "recent_events": [...]
}
```

**响应（REWRITE）：**
```json
{
  "final_action": "REWRITE",
  "rewrite_instructions": "重写指令",
  "violations": [...]
}
```

**响应（ASK_USER）：**
```json
{
  "final_action": "ASK_USER",
  "questions": ["需要澄清的问题"],
  "violations": [...]
}
```

## 故障排除

### 扩展未加载

1. 检查扩展文件是否在正确的目录
2. 检查 `manifest.json` 格式是否正确
3. 查看浏览器控制台是否有错误信息

### 无法连接到后端

1. 检查后端服务是否正在运行
2. 检查后端URL配置是否正确
3. 检查网络连接和防火墙设置

### 状态未更新

1. 检查故事ID是否正确
2. 检查后端API是否正常响应
3. 查看浏览器控制台的错误信息

### 重写功能不工作

1. 检查 SillyTavern 版本是否支持相关API
2. 查看控制台是否有错误信息
3. 尝试手动触发重写

## 开发

### 文件结构

```
sillytavern_extension/
├── manifest.json      # 扩展元数据
├── index.js          # 主脚本文件
├── styles.css        # 样式文件
└── README.md         # 说明文档
```

### 主要函数

- `state_summary(state)`: 生成状态摘要
- `fetchState(storyId)`: 获取状态
- `processDraft(storyId, userMessage, assistantDraft)`: 处理草稿
- `injectStatePanel(summary)`: 注入状态到系统提示词
- `updateSidebarPanel(state, recentEvents)`: 更新侧栏面板

### 扩展点

扩展使用以下 SillyTavern 扩展点：

- `beforeUserMessage`: 用户发送消息前
- `afterAssistantDraft`: 助手生成草稿后

## 许可证

MIT License

## 贡献

欢迎提交问题和拉取请求！

## 相关链接

- [SillyTavern 文档](https://sillytavern.wiki/)
- [Immersive Story Memory Engine 项目](https://github.com/your-repo)

