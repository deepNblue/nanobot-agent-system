"""
分布式任务调度器 - 跨节点的任务调度和执行

功能：
- 多节点任务调度
- 节点状态监控
- 任务分配和跟踪
- 与负载均衡器和故障容错集成
- 支持任务优先级和依赖
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import uuid

from load_balancer import LoadBalancer, create_load_balancer
from fault_tolerance import FaultTolerance, TaskStatus, create_fault_tolerance

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class DistributedScheduler:
    """分布式任务调度器"""
    
    def __init__(
        self,
        nodes: List[str],
        load_balancer: LoadBalancer = None,
        fault_tolerance: FaultTolerance = None
    ):
        """
        初始化分布式调度器
        
        Args:
            nodes: 节点URL列表 ["http://node1:8000", "http://node2:8000"]
            load_balancer: 负载均衡器实例
            fault_tolerance: 故障容错实例
        """
        self.nodes = nodes
        self.node_status = {}
        self.task_assignments = {}
        
        # 组件
        self.load_balancer = load_balancer or create_load_balancer()
        self.fault_tolerance = fault_tolerance or create_fault_tolerance()
        
        # 任务队列
        self.task_queue = asyncio.PriorityQueue()
        self.pending_tasks = {}
        
        # HTTP客户端配置
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.session = None
        
        # 后台任务
        self._monitor_task = None
        self._health_check_task = None
        self._running = False
    
    async def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        
        # 创建HTTP会话
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        # 启动后台任务
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Distributed scheduler started with {len(self.nodes)} nodes")
    
    async def stop(self):
        """停止调度器"""
        self._running = False
        
        # 取消后台任务
        if self._monitor_task:
            self._monitor_task.cancel()
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # 关闭HTTP会话
        if self.session:
            await self.session.close()
        
        logger.info("Distributed scheduler stopped")
    
    async def schedule_task(
        self,
        task: Dict,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """
        调度任务到最佳节点
        
        Args:
            task: 任务信息
            priority: 任务优先级
        
        Returns:
            任务ID
        """
        # 生成任务ID
        task_id = task.get("id") or f"task_{uuid.uuid4().hex[:12]}"
        task["id"] = task_id
        task["priority"] = priority.value
        task["created_at"] = datetime.now().isoformat()
        
        logger.info(f"Scheduling task {task_id} with priority {priority.name}")
        
        # 1. 更新节点状态
        await self.update_node_status()
        
        # 2. 选择最佳节点
        best_node = self.load_balancer.select_node(
            task=task,
            nodes=self.node_status
        )
        
        if not best_node:
            # 没有可用节点，加入队列
            logger.warning(f"No available nodes, queuing task {task_id}")
            await self.task_queue.put((priority.value, task_id, task))
            self.pending_tasks[task_id] = task
            return task_id
        
        # 3. 检查熔断器
        if not self.fault_tolerance.check_circuit(best_node):
            logger.warning(f"Circuit breaker open for {best_node}, trying another node")
            
            # 尝试其他节点
            healthy_nodes = {
                k: v for k, v in self.node_status.items()
                if self.fault_tolerance.check_circuit(k)
            }
            
            best_node = self.load_balancer.select_node(task, healthy_nodes)
            
            if not best_node:
                logger.warning(f"No available nodes after circuit breaker check")
                await self.task_queue.put((priority.value, task_id, task))
                self.pending_tasks[task_id] = task
                return task_id
        
        # 4. 分配任务
        success = await self.assign_task_to_node(best_node, task_id, task)
        
        if success:
            # 5. 记录分配
            self.task_assignments[task_id] = {
                "node": best_node,
                "task": task,
                "priority": priority.value,
                "assigned_at": datetime.now().isoformat(),
                "status": TaskStatus.RUNNING.value
            }
            
            # 6. 启动任务监控
            asyncio.create_task(self.monitor_task(task_id, best_node))
            
            logger.info(f"Task {task_id} assigned to {best_node}")
            
            return task_id
        else:
            # 分配失败，加入队列
            logger.error(f"Failed to assign task {task_id} to {best_node}")
            await self.task_queue.put((priority.value, task_id, task))
            self.pending_tasks[task_id] = task
            
            # 记录失败
            self.fault_tolerance._record_failure(best_node)
            
            return task_id
    
    async def update_node_status(self):
        """更新所有节点状态"""
        tasks = []
        for node in self.nodes:
            tasks.append(self.fetch_node_status(node))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for node, result in zip(self.nodes, results):
            if isinstance(result, Exception):
                self.node_status[node] = {
                    "status": "unhealthy",
                    "error": str(result),
                    "node_url": node,
                    "last_check": datetime.now().isoformat()
                }
            else:
                self.node_status[node] = result
    
    async def fetch_node_status(self, node: str) -> Dict:
        """
        获取单个节点状态
        
        Args:
            node: 节点URL
        
        Returns:
            节点状态
        """
        try:
            async with self.session.get(f"{node}/api/status") as response:
                if response.status == 200:
                    data = await response.json()
                    data["node_url"] = node
                    data["last_check"] = datetime.now().isoformat()
                    return data
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}",
                        "node_url": node,
                        "last_check": datetime.now().isoformat()
                    }
        
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Timeout",
                "node_url": node,
                "last_check": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "node_url": node,
                "last_check": datetime.now().isoformat()
            }
    
    async def assign_task_to_node(
        self,
        node: str,
        task_id: str,
        task: Dict
    ) -> bool:
        """
        分配任务到节点
        
        Args:
            node: 节点URL
            task_id: 任务ID
            task: 任务信息
        
        Returns:
            是否成功
        """
        try:
            payload = {
                "task_id": task_id,
                "task": task
            }
            
            async with self.session.post(
                f"{node}/api/task",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.debug(f"Task {task_id} assigned to {node}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to assign task: {error_text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error assigning task to {node}: {e}")
            return False
    
    async def monitor_task(self, task_id: str, node: str):
        """
        监控任务执行
        
        Args:
            task_id: 任务ID
            node: 节点URL
        """
        max_checks = 100  # 最多检查100次
        check_interval = 10  # 每10秒检查一次
        
        for _ in range(max_checks):
            if not self._running:
                break
            
            await asyncio.sleep(check_interval)
            
            try:
                # 检查任务状态
                async with self.session.get(f"{node}/api/task/{task_id}") as response:
                    if response.status == 200:
                        task_status = await response.json()
                        
                        status = task_status.get("status")
                        
                        # 更新任务状态
                        if task_id in self.task_assignments:
                            self.task_assignments[task_id]["status"] = status
                            self.task_assignments[task_id]["last_check"] = datetime.now().isoformat()
                        
                        # 检查是否完成
                        if status == "completed":
                            logger.info(f"Task {task_id} completed")
                            
                            # 保存最终状态
                            await self.fault_tolerance.save_checkpoint(
                                task_id,
                                {"status": "completed", "result": task_status}
                            )
                            
                            # 重置熔断器
                            self.fault_tolerance.reset_circuit(node)
                            break
                        
                        elif status == "failed":
                            logger.error(f"Task {task_id} failed")
                            
                            # 记录失败
                            self.fault_tolerance._record_failure(node)
                            
                            # 尝试重新调度
                            if task_id in self.task_assignments:
                                task_data = self.task_assignments[task_id]
                                task = task_data.get("task")
                                
                                # 重试
                                await self.schedule_task(task, TaskPriority(task_data.get("priority", 2)))
                            
                            break
                        
                        # 保存检查点
                        if "checkpoint" in task_status:
                            await self.fault_tolerance.save_checkpoint(
                                task_id,
                                task_status["checkpoint"]
                            )
                    
                    elif response.status == 404:
                        logger.warning(f"Task {task_id} not found on {node}")
                        break
            
            except Exception as e:
                logger.error(f"Error monitoring task {task_id}: {e}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        # 检查任务是否在待处理队列
        if task_id in self.pending_tasks:
            del self.pending_tasks[task_id]
            logger.info(f"Cancelled pending task {task_id}")
            return True
        
        # 检查任务是否已分配
        if task_id not in self.task_assignments:
            logger.warning(f"Task {task_id} not found")
            return False
        
        task_data = self.task_assignments[task_id]
        node = task_data["node"]
        
        try:
            # 调用节点API取消任务
            async with self.session.delete(f"{node}/api/task/{task_id}") as response:
                if response.status == 200:
                    # 更新状态
                    self.task_assignments[task_id]["status"] = TaskStatus.CANCELLED.value
                    
                    logger.info(f"Cancelled task {task_id}")
                    return True
                else:
                    logger.error(f"Failed to cancel task {task_id}")
                    return False
        
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        if task_id in self.task_assignments:
            return self.task_assignments[task_id]
        
        if task_id in self.pending_tasks:
            return {
                "status": "pending",
                "task": self.pending_tasks[task_id]
            }
        
        return None
    
    def get_cluster_status(self) -> Dict:
        """获取集群状态"""
        # 统计节点状态
        total_nodes = len(self.nodes)
        healthy_nodes = sum(
            1 for s in self.node_status.values()
            if s.get("status") == "healthy"
        )
        
        # 统计任务状态
        active_tasks = sum(
            1 for t in self.task_assignments.values()
            if t.get("status") == TaskStatus.RUNNING.value
        )
        
        completed_tasks = sum(
            1 for t in self.task_assignments.values()
            if t.get("status") == "completed"
        )
        
        failed_tasks = sum(
            1 for t in self.task_assignments.values()
            if t.get("status") == "failed"
        )
        
        # 节点排名
        node_ranking = self.load_balancer.get_node_ranking(self.node_status)
        
        return {
            "nodes": {
                "total": total_nodes,
                "healthy": healthy_nodes,
                "unhealthy": total_nodes - healthy_nodes,
                "details": self.node_status
            },
            "tasks": {
                "active": active_tasks,
                "pending": len(self.pending_tasks),
                "completed": completed_tasks,
                "failed": failed_tasks
            },
            "node_ranking": node_ranking[:5],  # 前5个节点
            "fault_tolerance": self.fault_tolerance.get_statistics(),
            "load_balancer": self.load_balancer.get_statistics()
        }
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 处理待处理任务队列
                while not self.task_queue.empty():
                    try:
                        priority, task_id, task = self.task_queue.get_nowait()
                        
                        # 尝试调度
                        await self.schedule_task(task, TaskPriority(priority))
                        
                        # 从待处理列表移除
                        if task_id in self.pending_tasks:
                            del self.pending_tasks[task_id]
                    
                    except asyncio.QueueEmpty:
                        break
                
                await asyncio.sleep(5)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                # 更新节点状态
                await self.update_node_status()
                
                # 检查故障节点
                for node_url, status in self.node_status.items():
                    if status.get("status") != "healthy":
                        # 处理节点故障
                        await self.fault_tolerance.handle_node_failure(self, node_url)
                
                await asyncio.sleep(30)  # 每30秒检查一次
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def add_node(self, node_url: str):
        """添加节点"""
        if node_url not in self.nodes:
            self.nodes.append(node_url)
            logger.info(f"Added node: {node_url}")
    
    async def remove_node(self, node_url: str):
        """移除节点"""
        if node_url in self.nodes:
            # 处理该节点上的任务
            await self.fault_tolerance.handle_node_failure(self, node_url)
            
            # 移除节点
            self.nodes.remove(node_url)
            
            if node_url in self.node_status:
                del self.node_status[node_url]
            
            logger.info(f"Removed node: {node_url}")
    
    async def rebalance_tasks(self):
        """重新平衡任务"""
        logger.info("Rebalancing tasks...")
        
        # 找出负载不均衡的节点
        node_loads = {}
        
        for node_url in self.nodes:
            if self.node_status.get(node_url, {}).get("status") == "healthy":
                node_loads[node_url] = self.node_status[node_url].get("active_tasks", 0)
        
        if not node_loads:
            return
        
        avg_load = sum(node_loads.values()) / len(node_loads)
        
        # 找出高负载节点
        high_load_nodes = [
            node for node, load in node_loads.items()
            if load > avg_load * 1.5
        ]
        
        # 迁移任务
        for node_url in high_load_nodes:
            # 找到该节点上的任务
            tasks_to_migrate = [
                (task_id, data)
                for task_id, data in self.task_assignments.items()
                if data.get("node") == node_url
            ]
            
            # 迁移部分任务
            for task_id, task_data in tasks_to_migrate[:len(tasks_to_migrate) // 2]:
                # 找到低负载节点
                low_load_nodes = [
                    node for node, load in node_loads.items()
                    if load < avg_load * 0.8 and node != node_url
                ]
                
                if low_load_nodes:
                    target_node = min(low_load_nodes, key=lambda n: node_loads[n])
                    
                    # 迁移任务
                    success = await self.fault_tolerance.migrate_task(
                        self, task_id, node_url, target_node
                    )
                    
                    if success:
                        node_loads[node_url] -= 1
                        node_loads[target_node] += 1


class PriorityTaskScheduler(DistributedScheduler):
    """优先级任务调度器 - 支持任务依赖"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 任务依赖关系
        self.task_dependencies = {}
        
        # 已完成任务
        self.completed_tasks = set()
    
    async def schedule_task_with_dependencies(
        self,
        task: Dict,
        dependencies: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """
        调度带依赖的任务
        
        Args:
            task: 任务信息
            dependencies: 依赖的任务ID列表
            priority: 任务优先级
        
        Returns:
            任务ID
        """
        task_id = await self.schedule_task(task, priority)
        
        if dependencies:
            # 检查依赖是否满足
            unmet_dependencies = [
                dep_id for dep_id in dependencies
                if dep_id not in self.completed_tasks
            ]
            
            if unmet_dependencies:
                # 记录依赖关系
                self.task_dependencies[task_id] = unmet_dependencies
                
                # 暂停任务
                await self.cancel_task(task_id)
                
                logger.info(
                    f"Task {task_id} waiting for dependencies: {unmet_dependencies}"
                )
        
        return task_id
    
    async def check_dependencies(self, task_id: str) -> bool:
        """检查任务依赖是否满足"""
        if task_id not in self.task_dependencies:
            return True
        
        dependencies = self.task_dependencies[task_id]
        
        for dep_id in dependencies:
            if dep_id not in self.completed_tasks:
                return False
        
        return True
    
    async def notify_task_completed(self, task_id: str):
        """通知任务完成"""
        self.completed_tasks.add(task_id)
        
        # 检查是否有任务在等待这个任务
        for waiting_task_id, dependencies in self.task_dependencies.items():
            if task_id in dependencies:
                # 检查是否所有依赖都满足
                if await self.check_dependencies(waiting_task_id):
                    # 重新调度等待的任务
                    task_data = self.task_assignments.get(waiting_task_id)
                    
                    if task_data:
                        await self.schedule_task(
                            task_data["task"],
                            TaskPriority(task_data.get("priority", 2))
                        )
                        
                        # 清除依赖记录
                        del self.task_dependencies[waiting_task_id]


# 便捷函数
def create_distributed_scheduler(
    nodes: List[str],
    strategy: str = "weighted_score",
    checkpoint_dir: str = "./checkpoints"
) -> DistributedScheduler:
    """
    创建分布式调度器
    
    Args:
        nodes: 节点列表
        strategy: 负载均衡策略
        checkpoint_dir: 检查点目录
    
    Returns:
        调度器实例
    """
    load_balancer = create_load_balancer(strategy=strategy)
    fault_tolerance = create_fault_tolerance(checkpoint_dir=checkpoint_dir)
    
    return DistributedScheduler(
        nodes=nodes,
        load_balancer=load_balancer,
        fault_tolerance=fault_tolerance
    )


if __name__ == "__main__":
    # 测试分布式调度器
    import asyncio
    
    async def test_scheduler():
        # 创建调度器
        nodes = ["http://localhost:8001", "http://localhost:8002"]
        scheduler = create_distributed_scheduler(nodes)
        
        # 启动
        await scheduler.start()
        
        # 模拟节点状态
        scheduler.node_status = {
            "http://localhost:8001": {
                "status": "healthy",
                "cpu_usage": 30,
                "memory_usage": 40,
                "active_tasks": 1,
                "network_latency": 10,
                "node_url": "http://localhost:8001"
            },
            "http://localhost:8002": {
                "status": "healthy",
                "cpu_usage": 50,
                "memory_usage": 60,
                "active_tasks": 3,
                "network_latency": 20,
                "node_url": "http://localhost:8002"
            }
        }
        
        # 测试任务调度
        task = {
            "description": "Test task",
            "data": {"key": "value"}
        }
        
        # 注意：这里不会真正连接节点
        print("Distributed scheduler test (requires running node servers)")
        
        # 获取集群状态
        status = scheduler.get_cluster_status()
        print(f"Cluster status: {status}")
        
        # 停止
        await scheduler.stop()
    
    asyncio.run(test_scheduler())
