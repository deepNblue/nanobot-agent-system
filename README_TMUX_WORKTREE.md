# Tmux + Worktree + Monitor 功能

基于OpenClaw文章实现的Agent任务管理系统，支持任务隔离、监控和干预。

## 🎯 核心功能

### 1. Git Worktree管理
- ✅ 每个任务创建独立的worktree
- ✅ 保证隔离性，互不干扰
- ✅ 自动创建分支和管理
- ✅ 自动安装依赖

### 2. Tmux会话管理
- ✅ 每个Agent任务在独立的tmux会话中运行
- ✅ 允许中途发指令调整方向（可干预）
- ✅ 监控会话状态（是否还在运行）
- ✅ 捕获会话输出

### 3. 任务记录系统
- ✅ JSON格式记录任务状态
- ✅ 包含：tmuxSession、worktree、branch、status等
- ✅ 持久化存储

### 4. 自动监控
- ✅ 检查git分支是否有提交
- ✅ 检查CI是否通过
- ✅ 检查tmux会话是否存活
- ✅ 生成监控报告

## 📦 模块说明

```
agent-system/
├── worktree_manager.py          # Git Worktree管理器
├── tmux_manager.py              # Tmux会话管理器
├── task_monitor.py              # 任务监控器
├── nanobot_scheduler_enhanced.py # 增强版编排器
├── agent_cli.py                 # CLI工具
├── example_usage.py             # 使用示例
└── test_tmux_worktree.py        # 测试脚本
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 确保已安装tmux和git
sudo apt-get install tmux git  # Ubuntu/Debian
# 或
brew install tmux git          # macOS
```

### 2. 运行测试

```bash
cd /home/dudu/.nanobot/workspace/skills/agent-system
python test_tmux_worktree.py
```

### 3. 使用CLI工具

```bash
# 创建任务
python agent_cli.py create feat-xxx "实现新功能" --agent codex

# 查看所有任务
python agent_cli.py status

# 捕获任务输出
python agent_cli.py capture feat-xxx --lines 100

# 干预任务
python agent_cli.py intervene feat-xxx "调整方向"

# 完成任务
python agent_cli.py complete feat-xxx --cleanup

# 生成报告
python agent_cli.py report --output report.md

# 列出tmux会话
python agent_cli.py sessions

# 连接到会话
python agent_cli.py attach codex-feat-xxx
```

## 📝 代码示例

### 创建任务

```python
from nanobot_scheduler_enhanced import get_orchestrator_enhanced

async def create_task():
    orchestrator = get_orchestrator_enhanced(base_repo="/path/to/repo")
    
    result = await orchestrator.create_agent_task(
        task_id="feat-custom-templates",
        description="实现自定义模板功能",
        agent_type="codex",
        priority="high",
        base_branch="main"
    )
    
    print(f"任务创建成功: {result}")
```

### 监控任务

```python
status = await orchestrator.monitor_task("feat-custom-templates")
print(f"任务状态: {status['overall_status']}")
```

### 干预任务

```python
result = await orchestrator.intervene_task(
    task_id="feat-custom-templates",
    command="echo '请优先处理性能优化'"
)
```

### 捕获输出

```python
output = await orchestrator.capture_task_output(
    task_id="feat-custom-templates",
    lines=100
)
print(output["output"])
```

## 📊 任务记录格式

```json
{
  "id": "feat-custom-templates",
  "tmuxSession": "codex-templates",
  "agent": "codex",
  "worktree": "/path/to/worktrees/feat-custom-templates",
  "branch": "agent/feat-custom-templates",
  "baseBranch": "main",
  "startedAt": 1740268800000,
  "status": "running",
  "checkCI": true,
  "notifyOnComplete": true,
  "retryCount": 0,
  "interventions": [
    {
      "timestamp": "2026-03-04T10:30:00",
      "command": "调整方向",
      "result": {"success": true}
    }
  ]
}
```

## 🔧 配置选项

### WorktreeManager

```python
worktree_manager = WorktreeManager(
    base_repo="/path/to/repo"  # 基础仓库路径
)

# 创建worktree
result = worktree_manager.create_worktree(
    task_id="task-123",
    branch_name="feat/new-feature",  # 可选，自动生成
    base_branch="main",
    description="任务描述"
)

# 移除worktree
result = worktree_manager.remove_worktree(
    task_id="task-123",
    force=False  # 强制移除
)
```

### TmuxManager

```python
tmux_manager = TmuxManager()

# 创建会话
result = tmux_manager.create_session(
    session_name="my-session",
    working_dir="/path/to/worktree",
    command="echo 'Starting'"
)

# 发送命令
tmux_manager.send_command(
    session_name="my-session",
    command="echo 'Hello'",
    enter=True
)

# 捕获输出
result = tmux_manager.capture_pane(
    session_name="my-session",
    lines=100
)
```

### TaskMonitor

```python
task_monitor = TaskMonitor(tasks_dir="/path/to/tasks")

# 检查任务状态
status = task_monitor.check_task_status("task-123")

# 监控所有任务
all_tasks = task_monitor.monitor_all_tasks()

# 生成报告
report = task_monitor.generate_report()
```

## 🎨 架构设计

```
┌─────────────────────────────────────────────────────────┐
│              NanobotOrchestratorEnhanced                 │
│                 (增强版编排层)                            │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌───────────┐ ┌──────────┐ ┌──────────┐
│ Worktree  │ │  Tmux    │ │ Monitor  │
│ Manager   │ │ Manager  │ │          │
└───────────┘ └──────────┘ └──────────┘
     │             │             │
     │             │             │
     ▼             ▼             ▼
┌───────────┐ ┌──────────┐ ┌──────────┐
│ Git Repo  │ │ Sessions │ │ Task DB  │
│ Worktrees │ │  (CLI)   │ │  (JSON)  │
└───────────┘ └──────────┘ └──────────┘
```

## 🔍 监控指标

### 1. Tmux会话状态
- 会话是否存在
- 会话是否运行中
- 窗口数量
- 是否已连接

### 2. Git提交状态
- 是否有新提交
- 提交数量
- 是否已推送到远程
- ahead/behind状态

### 3. CI状态（可选）
- CI是否运行
- CI是否成功
- CI是否失败
- 构建详情

### 4. 进程状态
- 进程是否存活
- 进程PID

## ⚙️ 高级功能

### 1. 自动重试

```python
# 在任务监控中自动检测失败任务
failed_tasks = task_monitor.get_failed_tasks()

# 重试失败任务
for task in failed_tasks:
    result = task_monitor.retry_task(task["task_id"])
```

### 2. 通知系统

```python
# 在任务完成时发送通知
async def _send_notification(task_id, status):
    # TODO: 实现邮件、webhook等通知
    pass
```

### 3. 自定义命令模板

```python
result = await orchestrator.create_agent_task(
    task_id="custom-task",
    description="自定义任务",
    agent_type="custom",
    command_template="python run.py --task {task_id} --dir {worktree_path}"
)
```

## 🧪 测试

```bash
# 运行完整测试套件
python test_tmux_worktree.py

# 测试单个模块
python -c "from worktree_manager import *; print('✅ WorktreeManager OK')"
python -c "from tmux_manager import *; print('✅ TmuxManager OK')"
python -c "from task_monitor import *; print('✅ TaskMonitor OK')"
```

## 📚 参考资料

- [OpenClaw文章](https://example.com/openclaw) - 原始设计思路
- [Git Worktree文档](https://git-scm.com/docs/git-worktree)
- [Tmux手册](https://man7.org/linux/man-pages/man1/tmux.1.html)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License
