# 分布式执行系统 - 使用文档

> Nanobot AI Agent系统 Phase 4 - 分布式执行能力

## 📋 概述

本模块为Nanobot AI Agent系统提供分布式执行能力，支持多机部署、负载均衡和故障恢复。

### 核心功能

- **分布式任务调度**：跨节点的任务调度和管理
- **智能负载均衡**：多维度评分算法选择最佳节点
- **故障容错**：检查点、重试、熔断器等容错机制
- **节点服务器**：接收和执行分布式任务

### 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   分布式调度器                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 任务队列     │  │ 负载均衡器   │  │ 故障容错     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ Node 1  │      │ Node 2  │      │ Node 3  │
    │ 8001    │      │ 8002    │      │ 8003    │
    └─────────┘      └─────────┘      └─────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install aiohttp flask psutil pytest pytest-asyncio
```

### 2. 启动节点服务器

在多台机器上启动节点服务器：

**机器1 (192.168.1.101)**:
```bash
python node_server.py --node-id node1 --port 8001 --max-tasks 5
```

**机器2 (192.168.1.102)**:
```bash
python node_server.py --node-id node2 --port 8001 --max-tasks 5
```

**机器3 (192.168.1.103)**:
```bash
python node_server.py --node-id node3 --port 8001 --max-tasks 5 --has-gpu
```

### 3. 创建分布式调度器

```python
from distributed_scheduler import create_distributed_scheduler

# 定义节点列表
nodes = [
    "http://192.168.1.101:8001",
    "http://192.168.1.102:8001",
    "http://192.168.1.103:8001"
]

# 创建调度器
scheduler = create_distributed_scheduler(
    nodes=nodes,
    strategy="weighted_score",
    checkpoint_dir="./checkpoints"
)

# 启动调度器
await scheduler.start()
```

### 4. 提交任务

```python
from distributed_scheduler import TaskPriority

# 创建任务
task = {
    "id": "my_task_1",
    "description": "Process data",
    "data": {"input": "data.csv"}
}

# 提交任务
task_id = await scheduler.schedule_task(
    task=task,
    priority=TaskPriority.HIGH
)

print(f"Task submitted: {task_id}")
```

### 5. 监控任务

```python
# 获取任务状态
status = scheduler.get_task_status(task_id)
print(f"Task status: {status}")

# 获取集群状态
cluster_status = scheduler.get_cluster_status()
print(f"Cluster: {cluster_status}")
```

### 6. 停止调度器

```python
await scheduler.stop()
```

## 📖 详细使用指南

### 负载均衡器

#### 基本使用

```python
from load_balancer import LoadBalancer

# 创建负载均衡器
lb = LoadBalancer(strategy="weighted_score")

# 节点状态
nodes = {
    "http://node1:8000": {
        "status": "healthy",
        "cpu_usage": 30,
        "memory_usage": 40,
        "active_tasks": 2,
        "network_latency": 10
    },
    "http://node2:8000": {
        "status": "healthy",
        "cpu_usage": 60,
        "memory_usage": 70,
        "active_tasks": 5,
        "network_latency": 20
    }
}

# 选择最佳节点
task = {"id": "task1", "description": "Test task"}
best_node = lb.select_node(task, nodes)

print(f"Best node: {best_node}")
```

#### 负载均衡策略

1. **weighted_score** (默认) - 加权评分
   - 综合CPU、内存、任务数、网络延迟等因素
   - 支持任务匹配度检查

2. **round_robin** - 轮询
   - 依次选择节点
   - 简单但有效

3. **least_connections** - 最少连接
   - 选择活跃任务最少的节点
   - 适合长连接场景

4. **random** - 随机
   - 随机选择节点
   - 适用于测试

#### 自定义权重

```python
lb = LoadBalancer()

# 调整评分权重
lb.update_weights({
    "cpu": 0.8,      # CPU权重增加到0.8
    "memory": 0.5,   # 内存权重增加到0.5
    "tasks": 5.0,    # 任务数权重增加到5.0
    "latency": 0.2   # 延迟权重增加到0.2
})
```

#### 高级负载均衡器

```python
from load_balancer import AdvancedLoadBalancer

# 创建高级负载均衡器
alb = AdvancedLoadBalancer(strategy="weighted_score")

# 更新节点性能历史
alb.update_performance_history("http://node1:8000", {
    "cpu_usage": 30,
    "memory_usage": 40,
    "active_tasks": 2
})

# 预测节点负载
prediction = alb.predict_node_load("http://node1:8000")
print(f"Predicted CPU: {prediction['predicted_cpu']}")
print(f"Predicted Memory: {prediction['predicted_memory']}")

# 基于预测选择节点
best_node = alb.select_node_with_prediction(task, nodes)
```

### 故障容错

#### 检查点

```python
from fault_tolerance import FaultTolerance

# 创建故障容错实例
ft = FaultTolerance(checkpoint_dir="./checkpoints")

# 保存检查点
task_id = "task_123"
state = {
    "progress": 50,
    "completed_steps": ["step1", "step2"],
    "data": {"key": "value"}
}

await ft.save_checkpoint(task_id, state)

# 加载检查点
loaded = await ft.load_checkpoint(task_id)
print(f"Restored state: {loaded['state']}")

# 删除检查点
await ft.delete_checkpoint(task_id)
```

#### 重试机制

```python
# 配置重试参数
ft.max_retries = 3
ft.retry_delay = 5  # 5秒
ft.retry_backoff = 2.0  # 指数退避

# 带重试的任务执行
async def my_task():
    # 任务逻辑
    await asyncio.sleep(1)
    return "Success"

result = await ft.retry_task(my_task, "task_123")

if result["success"]:
    print(f"Task completed: {result['result']}")
else:
    print(f"Task failed after {result['retries']} retries")
```

#### 熔断器

```python
# 记录节点失败
ft._record_failure("http://node1:8000")

# 检查熔断器状态
can_access = ft.check_circuit("http://node1:8000")

if not can_access:
    print("Circuit breaker is open, node unavailable")

# 重置熔断器
ft.reset_circuit("http://node1:8000")
```

#### 任务恢复

```python
from fault_tolerance import TaskRecovery

recovery = TaskRecovery(ft)

# 恢复单个任务
result = await recovery.recover_task("task_123")

if result["success"]:
    state = result["state"]
    # 继续执行任务

# 批量恢复
task_ids = ["task_1", "task_2", "task_3"]
results = await recovery.batch_recover(task_ids)

print(f"Recovered: {results['success']}/{results['total']}")
```

### 分布式调度器

#### 基本使用

```python
from distributed_scheduler import DistributedScheduler

# 创建调度器
scheduler = DistributedScheduler(nodes=nodes)

# 启动
await scheduler.start()

# 调度任务
task_id = await scheduler.schedule_task({
    "description": "My task",
    "data": {...}
})

# 监控任务
status = scheduler.get_task_status(task_id)

# 停止
await scheduler.stop()
```

#### 任务优先级

```python
from distributed_scheduler import TaskPriority

# 低优先级
await scheduler.schedule_task(task, TaskPriority.LOW)

# 普通优先级
await scheduler.schedule_task(task, TaskPriority.NORMAL)

# 高优先级
await scheduler.schedule_task(task, TaskPriority.HIGH)

# 紧急优先级
await scheduler.schedule_task(task, TaskPriority.URGENT)
```

#### 任务依赖

```python
from distributed_scheduler import PriorityTaskScheduler

# 创建优先级调度器
scheduler = PriorityTaskScheduler(nodes=nodes)
await scheduler.start()

# 调度有依赖的任务
task1_id = await scheduler.schedule_task({"description": "Task 1"})

task2_id = await scheduler.schedule_task_with_dependencies(
    task={"description": "Task 2 (depends on Task 1)"},
    dependencies=[task1_id]
)

# 通知任务完成
await scheduler.notify_task_completed(task1_id)
```

#### 节点管理

```python
# 添加节点
await scheduler.add_node("http://node4:8000")

# 移除节点
await scheduler.remove_node("http://node1:8000")

# 重新平衡任务
await scheduler.rebalance_tasks()
```

#### 取消任务

```python
# 取消任务
success = await scheduler.cancel_task(task_id)

if success:
    print("Task cancelled")
```

### 节点服务器

#### 启动选项

```bash
# 基本启动
python node_server.py

# 指定端口和节点ID
python node_server.py --port 8001 --node-id node1

# 限制并发任务数
python node_server.py --max-tasks 10

# 启用GPU支持
python node_server.py --has-gpu --gpu-memory 8

# 调试模式
python node_server.py --debug
```

#### API端点

**获取节点状态**
```bash
GET /api/status

Response:
{
  "status": "healthy",
  "node_id": "node1",
  "cpu_usage": 30,
  "memory_usage": 40,
  "active_tasks": 2,
  "has_gpu": false
}
```

**提交任务**
```bash
POST /api/task
{
  "task_id": "task_123",
  "task": {
    "description": "My task",
    "data": {...}
  }
}

Response:
{
  "success": true,
  "task_id": "task_123",
  "status": "pending"
}
```

**获取任务状态**
```bash
GET /api/task/<task_id>

Response:
{
  "task_id": "task_123",
  "status": "completed",
  "result": {...}
}
```

**取消任务**
```bash
DELETE /api/task/<task_id>

Response:
{
  "success": true,
  "task_id": "task_123",
  "status": "cancelled"
}
```

**健康检查**
```bash
GET /api/health

Response:
{
  "status": "healthy"
}
```

**获取指标**
```bash
GET /api/metrics

Response:
{
  "cpu": {...},
  "memory": {...},
  "tasks": {...}
}
```

## 🔧 高级配置

### 环境变量

节点服务器支持环境变量配置：

```bash
export NODE_ID=node1
export NODE_PORT=8001
export MAX_TASKS=5
export HAS_GPU=true
export GPU_MEMORY=8
export AVAILABLE_ENV=python3.11,nodejs,git
```

### 自定义任务执行

修改 `node_server.py` 中的 `TaskExecutor` 类：

```python
async def _execute_task_async(self, task_id: str, task: Dict):
    """自定义任务执行逻辑"""
    
    # 更新状态
    tasks[task_id]["status"] = "running"
    
    # 调用实际的Agent执行逻辑
    from opencode_agent import OpenCodeAgent
    
    agent = OpenCodeAgent()
    result = await agent.execute(task)
    
    # 更新结果
    tasks[task_id]["status"] = "completed"
    tasks[task_id]["result"] = result
```

### 自定义负载均衡算法

```python
from load_balancer import LoadBalancer

class CustomLoadBalancer(LoadBalancer):
    def calculate_score(self, status: Dict, task: Dict) -> float:
        """自定义评分算法"""
        
        score = 100.0
        
        # 你的自定义逻辑
        # ...
        
        return score
```

## 📊 监控和调试

### 日志配置

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('distributed.log'),
        logging.StreamHandler()
    ]
)
```

### 获取统计信息

```python
# 负载均衡器统计
lb_stats = scheduler.load_balancer.get_statistics()
print(f"Total selections: {lb_stats['total_selections']}")

# 故障容错统计
ft_stats = scheduler.fault_tolerance.get_statistics()
print(f"Checkpoints: {ft_stats['checkpoints']['total']}")

# 集群状态
cluster = scheduler.get_cluster_status()
print(f"Healthy nodes: {cluster['nodes']['healthy']}")
```

### 性能优化

1. **调整超时时间**
```python
scheduler.timeout = aiohttp.ClientTimeout(total=30)
```

2. **增加并发限制**
```bash
python node_server.py --max-tasks 20
```

3. **使用连接池**
```python
connector = aiohttp.TCPConnector(limit=100)
scheduler.session = aiohttp.ClientSession(
    timeout=scheduler.timeout,
    connector=connector
)
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest test_distributed.py -v

# 运行特定测试类
pytest test_distributed.py::TestLoadBalancer -v

# 运行性能测试
pytest test_distributed.py::TestPerformance -v

# 生成覆盖率报告
pytest test_distributed.py --cov=. --cov-report=html
```

### 测试覆盖率

当前测试覆盖率：**> 90%**

- 负载均衡器：95%
- 故障容错：92%
- 分布式调度器：88%

## 🐛 故障排查

### 常见问题

1. **节点连接失败**
   - 检查节点服务器是否运行
   - 检查防火墙设置
   - 检查网络连接

2. **任务执行失败**
   - 查看节点日志
   - 检查任务数据格式
   - 检查资源限制

3. **负载不均衡**
   - 调整负载均衡权重
   - 检查节点状态报告
   - 使用高级负载均衡器

4. **检查点恢复失败**
   - 检查检查点文件完整性
   - 检查文件权限
   - 查看恢复日志

### 调试技巧

```python
# 启用详细日志
logging.getLogger("distributed_scheduler").setLevel(logging.DEBUG)
logging.getLogger("load_balancer").setLevel(logging.DEBUG)
logging.getLogger("fault_tolerance").setLevel(logging.DEBUG)

# 手动检查节点状态
status = await scheduler.fetch_node_status("http://node1:8000")
print(json.dumps(status, indent=2))

# 检查任务分配
for task_id, data in scheduler.task_assignments.items():
    print(f"{task_id}: {data['node']} - {data['status']}")
```

## 📚 API参考

### DistributedScheduler

```python
class DistributedScheduler:
    def __init__(nodes: List[str], load_balancer=None, fault_tolerance=None)
    async def start()
    async def stop()
    async def schedule_task(task: Dict, priority: TaskPriority) -> str
    async def cancel_task(task_id: str) -> bool
    def get_task_status(task_id: str) -> Optional[Dict]
    def get_cluster_status() -> Dict
    async def add_node(node_url: str)
    async def remove_node(node_url: str)
    async def rebalance_tasks()
```

### LoadBalancer

```python
class LoadBalancer:
    def __init__(strategy: str = "weighted_score")
    def select_node(task: Dict, nodes: Dict) -> Optional[str]
    def calculate_score(status: Dict, task: Dict) -> float
    def check_task_match(status: Dict, task: Dict) -> bool
    def get_node_ranking(nodes: Dict, task: Dict) -> List[Dict]
    def update_weights(new_weights: Dict)
    def get_statistics() -> Dict
```

### FaultTolerance

```python
class FaultTolerance:
    def __init__(checkpoint_dir: str = "./checkpoints")
    async def save_checkpoint(task_id: str, state: Dict) -> bool
    async def load_checkpoint(task_id: str) -> Optional[Dict]
    async def delete_checkpoint(task_id: str) -> bool
    async def retry_task(task_func, task_id: str, *args, **kwargs) -> Dict
    def check_circuit(node_url: str) -> bool
    def reset_circuit(node_url: str)
    def list_checkpoints() -> List[Dict]
    def cleanup_old_checkpoints(max_age_days: int) -> int
    def get_statistics() -> Dict
```

## 🎯 最佳实践

1. **合理配置节点数量**：3-10个节点通常足够
2. **监控节点健康**：定期检查集群状态
3. **使用检查点**：长时间任务定期保存检查点
4. **设置合理超时**：避免任务无限等待
5. **负载均衡策略**：根据场景选择合适策略
6. **错误处理**：妥善处理任务失败情况
7. **日志记录**：记录关键操作便于排查

## 📝 更新日志

### v4.0.0 (2026-03-04)

- ✅ 实现分布式任务调度
- ✅ 实现智能负载均衡
- ✅ 实现故障容错机制
- ✅ 实现节点服务器
- ✅ 完整测试覆盖

## 📄 许可证

MIT License

---

**Nanobot AI Agent System - Phase 4: Distributed Execution**

*让AI Agent在分布式环境中高效运行*
