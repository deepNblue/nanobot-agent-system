# Nanobot Agent Dashboard - 使用文档

## 概述

Nanobot Agent Dashboard是Phase 3新增的实时可视化监控界面，提供：
- 实时任务状态监控
- WebSocket实时更新
- 统计数据展示
- 性能指标分析
- 错误日志追踪
- 响应式Web界面

## 快速开始

### 1. 启动Dashboard

Dashboard会随Orchestrator自动启动：

```python
from nanobot_scheduler_enhanced import get_orchestrator_enhanced

# 创建Orchestrator实例（Dashboard会自动启动）
orchestrator = get_orchestrator_enhanced()

# Dashboard访问地址
# http://localhost:5000
```

### 2. 手动启动Dashboard

也可以单独启动Dashboard：

```python
from dashboard import start_dashboard

# 启动Dashboard（在后台线程运行）
dashboard = start_dashboard(port=5000)

# 访问地址
# http://localhost:5000
```

### 3. 直接运行Dashboard

```bash
cd /home/dudu/.nanobot/workspace/skills/agent-system
python dashboard.py --port 5000
```

## 功能特性

### 1. 实时监控

#### 任务状态卡片
- **运行中**: 显示当前正在执行的任务数量
- **已完成**: 显示已成功完成的任务数量
- **失败**: 显示执行失败的任务数量
- **等待中**: 显示待执行的任务数量

#### 性能指标
- **平均执行时间**: 任务平均完成时间（分钟）
- **成功率**: 任务成功完成的百分比
- **代码质量**: 代码审查平均分数（0-100）
- **今日完成**: 今天完成的任务数量
- **平均重试次数**: CI失败后的平均重试次数
- **总任务数**: 系统中的总任务数

### 2. 实时更新

Dashboard使用WebSocket实现实时更新：

- **任务创建**: 新任务创建时自动更新
- **状态变化**: 任务状态改变时实时推送
- **错误警告**: 错误发生时立即显示
- **统计更新**: 每10秒自动更新统计数据

### 3. 历史趋势图

显示最近7天的任务趋势：
- 每日创建任务数
- 每日完成任务数
- 成功率变化

### 4. Agent分布图

显示不同Agent类型的任务分布：
- codex
- claude
- opencode
- 其他

### 5. 错误日志

显示最近的错误信息：
- 错误时间
- 错误消息
- 关联任务ID

### 6. 任务列表

显示所有任务详情：
- 任务描述
- Agent类型
- 创建时间
- 分支名称
- 执行时间
- 进度条（运行中任务）

## API接口

Dashboard提供以下REST API：

### 1. 获取任务列表

```http
GET /api/tasks
```

响应：
```json
{
  "success": true,
  "tasks": [...],
  "count": 10
}
```

### 2. 获取统计数据

```http
GET /api/stats
```

响应：
```json
{
  "success": true,
  "stats": {
    "total": 100,
    "running": 2,
    "completed": 85,
    "failed": 3,
    "pending": 10,
    "performance": {
      "avg_execution_time": 5.2,
      "success_rate": 96.6,
      "avg_code_quality": 85.3
    },
    "today": {
      "tasks_created": 5,
      "tasks_completed": 3,
      "errors": 1
    }
  }
}
```

### 3. 获取任务详情

```http
GET /api/task/<task_id>
```

响应：
```json
{
  "success": true,
  "task": {
    "id": "task-123",
    "description": "实现用户登录功能",
    "status": "completed",
    "agent": "opencode",
    ...
  }
}
```

### 4. 获取错误日志

```http
GET /api/errors?limit=10
```

响应：
```json
{
  "success": true,
  "errors": [...],
  "count": 10,
  "total": 25
}
```

### 5. 获取历史数据

```http
GET /api/history?days=7
```

响应：
```json
{
  "success": true,
  "history": {
    "dates": ["2024-01-01", "2024-01-02", ...],
    "tasks_created": [5, 3, ...],
    "tasks_completed": [4, 6, ...],
    "tasks_failed": [0, 1, ...],
    "success_rates": [100.0, 85.7, ...]
  }
}
```

### 6. 健康检查

```http
GET /api/health
```

响应：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "uptime": 3600
}
```

## WebSocket事件

### 客户端事件

#### 1. 连接
```javascript
socket.on('connect', function() {
    console.log('Connected to Dashboard');
});
```

#### 2. 请求更新
```javascript
socket.emit('request_update', {task_id: 'task-123'});
```

#### 3. 请求统计
```javascript
socket.emit('request_stats');
```

#### 4. 订阅任务
```javascript
socket.emit('subscribe_task', {task_id: 'task-123'});
```

### 服务端事件

#### 1. 任务更新
```javascript
socket.on('task_update', function(data) {
    console.log('Task update:', data);
});
```

#### 2. 统计更新
```javascript
socket.on('stats_update', function(stats) {
    console.log('Stats update:', stats);
});
```

#### 3. 错误警告
```javascript
socket.on('error_alert', function(error) {
    console.error('Error:', error);
});
```

## 编程接口

### 1. 广播任务更新

```python
from nanobot_scheduler_enhanced import get_orchestrator_enhanced

orchestrator = get_orchestrator_enhanced()

# 广播任务更新
orchestrator._broadcast_task_update('task-123', {
    'status': 'running',
    'progress': 50,
    'description': '正在执行任务'
})
```

### 2. 广播错误

```python
# 广播错误
orchestrator._broadcast_error('任务执行失败', task_id='task-123')
```

### 3. 获取Dashboard实例

```python
from dashboard import get_dashboard

dashboard = get_dashboard()

if dashboard:
    # 手动广播统计更新
    dashboard.broadcast_stats_update()
```

## 配置选项

### 1. Orchestrator配置

```python
orchestrator = NanobotOrchestratorEnhanced()

# Dashboard配置
orchestrator.dashboard_enabled = True  # 启用Dashboard
orchestrator.dashboard_port = 5000     # Dashboard端口
```

### 2. Dashboard配置

```python
from dashboard import Dashboard

dashboard = Dashboard(
    port=5000,                           # 监听端口
    tasks_dir="/path/to/tasks"           # 任务目录
)

# 缓存配置
dashboard.cache_timeout = 5              # 缓存超时（秒）
dashboard.max_error_log = 100            # 最大错误日志数
```

## 性能优化

### 1. 数据缓存

Dashboard实现了智能缓存机制：
- 统计数据缓存5秒
- 避免频繁的文件读取
- 后台定期更新

### 2. WebSocket优化

- 使用threading模式提高兼容性
- 自动重连机制
- 批量更新减少网络开销

### 3. 前端优化

- 每5秒自动刷新数据
- 使用Chart.js高效渲染图表
- 响应式设计减少重排

## 故障排查

### 1. Dashboard无法启动

**问题**: 端口被占用

**解决**:
```bash
# 检查端口占用
lsof -i :5000

# 更改端口
orchestrator.dashboard_port = 5001
```

### 2. WebSocket连接失败

**问题**: CORS配置问题

**解决**: Dashboard已配置允许所有来源，如果仍有问题，检查浏览器控制台

### 3. 数据不更新

**问题**: 文件权限或路径问题

**解决**:
```python
# 检查任务目录
import os
tasks_dir = Path.home() / ".nanobot" / "workspace" / "agent_tasks"
print(f"Tasks dir exists: {tasks_dir.exists()}")
print(f"Tasks dir permission: {oct(os.stat(tasks_dir).st_mode)}")
```

### 4. 图表不显示

**问题**: Chart.js加载失败

**解决**: 检查网络连接，确保能访问CDN资源

## 安全考虑

### 1. 访问控制

Dashboard默认监听所有接口（0.0.0.0），建议：
- 仅在内网环境使用
- 使用反向代理添加认证
- 配置防火墙规则

### 2. 数据安全

- 任务数据存储在本地文件系统
- 不包含敏感凭据信息
- 建议定期备份任务数据

## 未来扩展

### 计划功能

1. **用户认证**: 添加登录系统
2. **自定义Dashboard**: 允许用户自定义布局
3. **告警规则**: 配置自定义告警条件
4. **数据导出**: 导出任务数据为CSV/Excel
5. **移动端优化**: 专门的移动端界面
6. **多语言支持**: i18n国际化

### 插件系统

计划支持插件扩展：
- 自定义图表类型
- 第三方集成（Slack、钉钉等）
- 自定义数据源

## 常见问题

### Q1: Dashboard支持多少并发连接？

A: 使用Flask-SocketIO的threading模式，支持数十个并发连接。如需更高性能，可切换到eventlet或gevent模式。

### Q2: 历史数据保留多久？

A: Dashboard不限制历史数据，但建议定期清理旧任务文件以保持性能。

### Q3: 可以同时运行多个Dashboard吗？

A: 可以，但需要使用不同端口。建议每个Orchestrator实例对应一个Dashboard。

### Q4: Dashboard会影响Agent性能吗？

A: 影响很小。Dashboard在后台线程运行，数据读取有缓存，不会阻塞Agent执行。

## 技术栈

- **后端**: Python 3.11, Flask, Flask-SocketIO
- **前端**: HTML5, CSS3, JavaScript ES6
- **UI框架**: Bootstrap 5
- **图表**: Chart.js 3.7
- **实时通信**: Socket.IO 4.0
- **图标**: Font Awesome 6.0

## 贡献指南

欢迎贡献代码和建议！

1. Fork项目
2. 创建功能分支
3. 提交变更
4. 创建Pull Request

## 许可证

MIT License

## 联系方式

- 项目地址: `/home/dudu/.nanobot/workspace/skills/agent-system/`
- 文档更新: 2024-01-01
- 版本: v3.0 (Phase 3)
