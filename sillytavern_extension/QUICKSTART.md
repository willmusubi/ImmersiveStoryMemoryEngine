# 快速开始指南

## 前置要求

1. 已安装并运行 SillyTavern
2. 后端服务正在运行（默认：http://127.0.0.1:8000）

## 安装步骤

### 1. 复制扩展文件

将 `sillytavern_extension` 文件夹复制到 SillyTavern 的扩展目录：

**Windows:**
```
C:\Users\<YourUsername>\AppData\Roaming\SillyTavern\public\extensions\
```

**macOS/Linux:**
```
~/.local/share/SillyTavern/public/extensions/
```

或者如果使用便携版：
```
<SillyTavern安装目录>/public/extensions/
```

### 2. 启动后端服务

在项目根目录运行：

```bash
python run_server.py
```

确保后端服务在 `http://127.0.0.1:8000` 上运行。

### 3. 在 SillyTavern 中启用扩展

1. 打开 SillyTavern
2. 点击左侧菜单的 "Extensions" 或 "扩展"
3. 找到 "Immersive Story Memory Engine"
4. 点击启用开关

### 4. 配置扩展

1. 在扩展设置中找到 "Immersive Story Memory Engine"
2. 配置以下选项：
   - **后端URL**: 默认为 `http://127.0.0.1:8000`，如果后端运行在其他地址，请修改
   - **故事ID**: 用于标识不同的故事会话，可以留空使用默认值

### 5. 开始使用

1. 创建一个新的聊天或打开现有聊天
2. 开始对话，扩展会自动：
   - 在每轮对话前获取状态并注入到系统提示词
   - 在模型生成回复后验证一致性
   - 在侧栏显示状态摘要和最近事件

## 验证安装

### 检查扩展是否加载

1. 打开浏览器开发者工具（F12）
2. 查看控制台，应该看到：
   ```
   [Memory Engine] 扩展已加载
   [Memory Engine] 已注册事件监听器
   ```

### 检查后端连接

1. 发送一条消息
2. 查看控制台，应该看到：
   ```
   [Memory Engine] 状态摘要已生成
   [Memory Engine] 状态摘要已注入到system prompt
   ```

### 检查侧栏面板

1. 查看右侧边栏（如果可见）
2. 应该看到 "故事状态" 面板
3. 面板中显示状态摘要和最近事件

## 常见问题

### Q: 扩展未显示在扩展列表中

**A:** 检查：
- 扩展文件夹是否在正确的目录
- `manifest.json` 文件是否存在且格式正确
- 刷新 SillyTavern 页面

### Q: 无法连接到后端

**A:** 检查：
- 后端服务是否正在运行
- 后端URL配置是否正确
- 防火墙是否阻止了连接
- 查看浏览器控制台的错误信息

### Q: 状态未更新

**A:** 检查：
- 故事ID是否正确
- 后端API是否正常响应
- 查看控制台的错误信息

### Q: 侧栏面板未显示

**A:** 检查：
- 浏览器控制台是否有错误
- 尝试刷新页面
- 检查CSS文件是否加载

## 下一步

- 阅读 [README.md](README.md) 了解详细功能
- 查看后端API文档了解如何自定义
- 根据需要调整配置

## 获取帮助

如果遇到问题：
1. 查看浏览器控制台的错误信息
2. 检查后端服务的日志
3. 查看 [README.md](README.md) 的故障排除部分

