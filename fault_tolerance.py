"""
故障容错模块 - 提供检查点、恢复和故障处理

功能：
- 任务检查点保存和恢复
- 节点故障检测和处理
- 自动重试机制
- 任务迁移
- 熔断器模式
"""

import os
import json
import asyncio
import logging
from typing import Dict, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CHECKPOINTED = "checkpointed"


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


class FaultTolerance:
    """故障容错管理"""

    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        """
        初始化故障容错

        Args:
            checkpoint_dir: 检查点存储目录
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 5  # 秒
        self.retry_backoff = 2.0  # 指数退避因子

        # 熔断器配置
        self.circuit_breakers = {}
        self.failure_threshold = 5  # 失败次数阈值
        self.recovery_timeout = 60  # 恢复超时（秒）

        # 任务状态跟踪
        self.task_states = {}
        self.task_history = {}

    async def save_checkpoint(self, task_id: str, state: Dict) -> bool:
        """
        保存检查点（原子操作）

        Args:
            task_id: 任务ID
            state: 任务状态

        Returns:
            是否成功
        """
        try:
            checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
            temp_file = self.checkpoint_dir / f"{task_id}.json.tmp"

            checkpoint_data = {"task_id": task_id, "state": state, "timestamp": datetime.now().isoformat(), "version": "1.0"}

            # 写入临时文件
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

            # 原子操作：重命名
            os.rename(temp_file, checkpoint_file)

            # 更新任务状态
            self.task_states[task_id] = TaskStatus.CHECKPOINTED

            logger.info(f"Checkpoint saved for task {task_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint for task {task_id}: {e}")
            return False

    async def load_checkpoint(self, task_id: str) -> Optional[Dict]:
        """
        加载检查点

        Args:
            task_id: 任务ID

        Returns:
            检查点数据，如果不存在则返回None
        """
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"

        if not checkpoint_file.exists():
            logger.debug(f"No checkpoint found for task {task_id}")
            return None

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"Checkpoint loaded for task {task_id}")

            return data

        except Exception as e:
            logger.error(f"Failed to load checkpoint for task {task_id}: {e}")
            return None

    async def delete_checkpoint(self, task_id: str) -> bool:
        """删除检查点"""
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"

        if checkpoint_file.exists():
            try:
                os.remove(checkpoint_file)
                logger.info(f"Checkpoint deleted for task {task_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete checkpoint for task {task_id}: {e}")
                return False

        return True

    async def handle_node_failure(self, scheduler, failed_node: str) -> Dict:
        """
        处理节点故障

        Args:
            scheduler: 调度器实例
            failed_node: 故障节点URL

        Returns:
            处理结果
        """
        logger.warning(f"Handling node failure: {failed_node}")

        # 1. 找到该节点上的所有任务
        failed_tasks = [
            {"id": task_id, **data} for task_id, data in scheduler.task_assignments.items() if data.get("node") == failed_node
        ]

        logger.info(f"Found {len(failed_tasks)} tasks on failed node")

        # 2. 更新熔断器
        self._record_failure(failed_node)

        # 3. 重新调度任务
        results = {"total": len(failed_tasks), "rescheduled": 0, "failed": 0, "restored_from_checkpoint": 0}

        for task_data in failed_tasks:
            task_id = task_data["id"]
            task = task_data["task"]

            try:
                # 尝试加载检查点
                checkpoint = await self.load_checkpoint(task_id)

                if checkpoint:
                    # 从检查点恢复
                    task["restore_from"] = checkpoint
                    task["checkpoint_state"] = checkpoint["state"]
                    results["restored_from_checkpoint"] += 1
                    logger.info(f"Restoring task {task_id} from checkpoint")
                else:
                    # 从头开始
                    logger.info(f"Restarting task {task_id} from scratch")

                # 重新调度
                new_task_id = await scheduler.schedule_task(task)

                # 移除旧的分配记录
                if task_id in scheduler.task_assignments:
                    del scheduler.task_assignments[task_id]

                results["rescheduled"] += 1

            except Exception as e:
                logger.error(f"Failed to reschedule task {task_id}: {e}")
                results["failed"] += 1

                # 记录失败历史
                self._record_task_failure(task_id, str(e))

        return results

    async def retry_task(self, task_func: Callable, task_id: str, *args, **kwargs) -> Dict:
        """
        带重试的任务执行

        Args:
            task_func: 任务函数
            task_id: 任务ID
            *args, **kwargs: 任务参数

        Returns:
            执行结果
        """
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                # 更新任务状态
                self.task_states[task_id] = TaskStatus.RUNNING

                # 执行任务
                result = await task_func(*args, **kwargs)

                # 成功
                self.task_states[task_id] = TaskStatus.COMPLETED

                return {"success": True, "result": result, "retries": retries}

            except Exception as e:
                last_error = e
                retries += 1

                logger.warning(f"Task {task_id} failed (attempt {retries}/{self.max_retries}): {e}")

                # 保存检查点（如果可能）
                if retries < self.max_retries:
                    await self._save_error_checkpoint(task_id, str(e))

                # 指数退避
                delay = self.retry_delay * (self.retry_backoff ** (retries - 1))
                await asyncio.sleep(delay)

        # 所有重试都失败
        self.task_states[task_id] = TaskStatus.FAILED
        self._record_task_failure(task_id, str(last_error))

        return {"success": False, "error": str(last_error), "retries": retries}

    async def _save_error_checkpoint(self, task_id: str, error: str):
        """保存错误检查点"""
        checkpoint_data = {"error": error, "timestamp": datetime.now().isoformat(), "status": "error"}

        await self.save_checkpoint(task_id, checkpoint_data)

    def _record_failure(self, node_url: str):
        """记录节点失败"""
        if node_url not in self.circuit_breakers:
            self.circuit_breakers[node_url] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "opened_at": None,
            }

        cb = self.circuit_breakers[node_url]
        cb["failure_count"] += 1
        cb["last_failure"] = datetime.now()

        # 检查是否需要熔断
        if cb["failure_count"] >= self.failure_threshold:
            cb["state"] = CircuitState.OPEN
            cb["opened_at"] = datetime.now()
            logger.warning(f"Circuit breaker OPEN for node {node_url}")

    def _record_task_failure(self, task_id: str, error: str):
        """记录任务失败"""
        if task_id not in self.task_history:
            self.task_history[task_id] = []

        self.task_history[task_id].append({"timestamp": datetime.now().isoformat(), "error": error, "status": "failed"})

    def check_circuit(self, node_url: str) -> bool:
        """
        检查熔断器状态

        Args:
            node_url: 节点URL

        Returns:
            是否可以访问节点
        """
        if node_url not in self.circuit_breakers:
            return True

        cb = self.circuit_breakers[node_url]

        if cb["state"] == CircuitState.CLOSED:
            return True

        elif cb["state"] == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if cb["opened_at"]:
                elapsed = (datetime.now() - cb["opened_at"]).total_seconds()

                if elapsed >= self.recovery_timeout:
                    cb["state"] = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker HALF_OPEN for node {node_url}")
                    return True

            return False

        elif cb["state"] == CircuitState.HALF_OPEN:
            return True

        return True

    def reset_circuit(self, node_url: str):
        """重置熔断器"""
        if node_url in self.circuit_breakers:
            self.circuit_breakers[node_url] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "opened_at": None,
            }
            logger.info(f"Circuit breaker RESET for node {node_url}")

    async def migrate_task(self, scheduler, task_id: str, from_node: str, to_node: str) -> bool:
        """
        迁移任务

        Args:
            scheduler: 调度器实例
            task_id: 任务ID
            from_node: 源节点
            to_node: 目标节点

        Returns:
            是否成功
        """
        logger.info(f"Migrating task {task_id} from {from_node} to {to_node}")

        try:
            # 1. 从源节点获取任务状态
            # （这里需要调用源节点的API）

            # 2. 保存检查点
            checkpoint = await self.load_checkpoint(task_id)

            # 3. 取消源节点的任务
            # （这里需要调用源节点的API）

            # 4. 在目标节点启动任务
            task_data = scheduler.task_assignments.get(task_id)

            if task_data:
                task = task_data.get("task", {})

                if checkpoint:
                    task["restore_from"] = checkpoint

                # 分配到新节点
                success = await scheduler.assign_task_to_node(to_node, task_id, task)

                if success:
                    # 更新分配记录
                    scheduler.task_assignments[task_id]["node"] = to_node
                    scheduler.task_assignments[task_id]["migrated_at"] = datetime.now().isoformat()

                    logger.info(f"Task {task_id} migrated successfully")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to migrate task {task_id}: {e}")
            return False

    def get_checkpoint_info(self, task_id: str) -> Optional[Dict]:
        """获取检查点信息"""
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            stat = checkpoint_file.stat()

            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return {
                "task_id": task_id,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "timestamp": data.get("timestamp"),
                "version": data.get("version"),
            }

        except Exception as e:
            logger.error(f"Failed to get checkpoint info: {e}")
            return None

    def list_checkpoints(self) -> List[Dict]:
        """列出所有检查点"""
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            task_id = checkpoint_file.stem
            info = self.get_checkpoint_info(task_id)

            if info:
                checkpoints.append(info)

        # 按修改时间排序
        checkpoints.sort(key=lambda x: x["modified"], reverse=True)

        return checkpoints

    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """
        清理旧检查点

        Args:
            max_age_days: 最大保留天数

        Returns:
            删除的检查点数量
        """
        deleted_count = 0
        cutoff = datetime.now() - timedelta(days=max_age_days)

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                stat = checkpoint_file.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)

                if modified < cutoff:
                    os.remove(checkpoint_file)
                    deleted_count += 1
                    logger.info(f"Deleted old checkpoint: {checkpoint_file.name}")

            except Exception as e:
                logger.error(f"Failed to delete checkpoint {checkpoint_file}: {e}")

        return deleted_count

    def get_statistics(self) -> Dict:
        """获取故障容错统计信息"""
        # 检查点统计
        checkpoints = self.list_checkpoints()
        total_checkpoint_size = sum(cp["size"] for cp in checkpoints)

        # 熔断器统计
        circuit_stats = {
            "total": len(self.circuit_breakers),
            "open": sum(1 for cb in self.circuit_breakers.values() if cb["state"] == CircuitState.OPEN),
            "half_open": sum(1 for cb in self.circuit_breakers.values() if cb["state"] == CircuitState.HALF_OPEN),
            "closed": sum(1 for cb in self.circuit_breakers.values() if cb["state"] == CircuitState.CLOSED),
        }

        # 任务状态统计
        task_stats = {}
        for status in TaskStatus:
            task_stats[status.value] = sum(1 for s in self.task_states.values() if s == status)

        return {
            "checkpoints": {
                "total": len(checkpoints),
                "total_size": total_checkpoint_size,
                "oldest": checkpoints[-1]["modified"] if checkpoints else None,
                "newest": checkpoints[0]["modified"] if checkpoints else None,
            },
            "circuit_breakers": circuit_stats,
            "task_states": task_stats,
            "task_history_count": len(self.task_history),
        }


class TaskRecovery:
    """任务恢复管理"""

    def __init__(self, fault_tolerance: FaultTolerance):
        self.ft = fault_tolerance

    async def recover_task(self, task_id: str) -> Dict:
        """
        恢复任务

        Args:
            task_id: 任务ID

        Returns:
            恢复结果
        """
        # 加载检查点
        checkpoint = await self.ft.load_checkpoint(task_id)

        if not checkpoint:
            return {"success": False, "error": "No checkpoint found"}

        # 检查检查点完整性
        if not self._validate_checkpoint(checkpoint):
            return {"success": False, "error": "Checkpoint validation failed"}

        # 恢复任务状态
        state = checkpoint.get("state", {})

        return {"success": True, "task_id": task_id, "state": state, "checkpoint_timestamp": checkpoint.get("timestamp")}

    def _validate_checkpoint(self, checkpoint: Dict) -> bool:
        """验证检查点完整性"""
        required_fields = ["task_id", "state", "timestamp"]

        for field in required_fields:
            if field not in checkpoint:
                return False

        return True

    async def batch_recover(self, task_ids: List[str]) -> Dict:
        """批量恢复任务"""
        results = {"total": len(task_ids), "success": 0, "failed": 0, "details": []}

        for task_id in task_ids:
            result = await self.recover_task(task_id)

            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1

            results["details"].append({"task_id": task_id, "success": result["success"], "error": result.get("error")})

        return results


# 便捷函数
def create_fault_tolerance(checkpoint_dir: str = "./checkpoints") -> FaultTolerance:
    """创建故障容错实例"""
    return FaultTolerance(checkpoint_dir=checkpoint_dir)


if __name__ == "__main__":
    # 测试故障容错
    import asyncio

    async def test_fault_tolerance():
        ft = FaultTolerance()

        # 测试检查点
        task_id = "test_task_1"
        state = {"progress": 50, "completed_steps": ["step1", "step2"], "data": {"key": "value"}}

        # 保存
        success = await ft.save_checkpoint(task_id, state)
        print(f"Checkpoint saved: {success}")

        # 加载
        loaded = await ft.load_checkpoint(task_id)
        print(f"Checkpoint loaded: {loaded}")

        # 获取统计
        stats = ft.get_statistics()
        print(f"Statistics: {stats}")

        # 测试熔断器
        node_url = "http://node1:8000"

        # 记录失败
        for i in range(6):
            ft._record_failure(node_url)
            can_access = ft.check_circuit(node_url)
            print(f"After failure {i+1}, can access: {can_access}")

        # 重置
        ft.reset_circuit(node_url)
        can_access = ft.check_circuit(node_url)
        print(f"After reset, can access: {can_access}")

        # 测试重试
        async def flaky_task():
            import random

            if random.random() < 0.7:
                raise Exception("Random failure")
            return "Success!"

        result = await ft.retry_task(flaky_task, "test_retry_task")
        print(f"Retry result: {result}")

    asyncio.run(test_fault_tolerance())
