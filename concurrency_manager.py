"""
并发管理器 - 限制并发数和批量处理

功能：
1. 并发数限制（避免资源耗尽）
2. 批量处理（提高效率）
3. 任务队列管理
4. 优先级调度
"""

import asyncio
from typing import List, Dict, Any, Callable, Optional
from collections import defaultdict
from datetime import datetime
import heapq


class ConcurrencyManager:
    """并发管理器"""

    def __init__(self, max_concurrent: int = 5):
        """
        初始化并发管理器

        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks = {}
        self.task_queue = []
        self.stats = {"total_executed": 0, "total_failed": 0, "current_active": 0}

    async def run_with_limit(self, task_func: Callable, *args, task_id: str = None, priority: int = 0, **kwargs) -> Any:
        """
        限制并发数执行任务

        Args:
            task_func: 任务函数
            *args: 位置参数
            task_id: 任务ID
            priority: 优先级（数字越小优先级越高）
            **kwargs: 关键字参数

        Returns:
            任务结果
        """
        async with self.semaphore:
            task_id = task_id or f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 记录活动任务
            self.active_tasks[task_id] = {"function": task_func.__name__, "started_at": datetime.now().isoformat()}
            self.stats["current_active"] = len(self.active_tasks)

            try:
                result = await task_func(*args, **kwargs)
                self.stats["total_executed"] += 1
                return result
            except Exception as e:
                self.stats["total_failed"] += 1
                raise e
            finally:
                del self.active_tasks[task_id]
                self.stats["current_active"] = len(self.active_tasks)

    async def batch_process(self, tasks: List[Callable], batch_size: int = 10, fail_fast: bool = False) -> List[Any]:
        """
        批量处理任务

        Args:
            tasks: 任务列表
            batch_size: 每批数量
            fail_fast: 是否快速失败（遇到错误立即停止）

        Returns:
            结果列表
        """
        results = []
        errors = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]

            # 并发执行一批任务
            batch_results = await asyncio.gather(
                *[self.run_with_limit(task) for task in batch], return_exceptions=not fail_fast
            )

            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    if fail_fast:
                        raise result
                    errors.append(result)
                    results.append(None)
                else:
                    results.append(result)

        if errors:
            print(f"Batch processing completed with {len(errors)} errors")

        return results

    async def priority_execute(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """
        按优先级执行任务

        Args:
            tasks: 任务列表，格式：[
                {
                    "func": callable,
                    "priority": int,
                    "args": tuple,
                    "kwargs": dict
                }
            ]

        Returns:
            结果列表（按原顺序）
        """
        # 创建优先级队列
        heap = []
        for idx, task in enumerate(tasks):
            priority = task.get("priority", 0)
            func = task["func"]
            args = task.get("args", ())
            kwargs = task.get("kwargs", {})

            heapq.heappush(heap, (priority, idx, func, args, kwargs))

        # 按优先级执行
        results = [None] * len(tasks)

        while heap:
            priority, idx, func, args, kwargs = heapq.heappop(heap)

            try:
                result = await self.run_with_limit(func, *args, **kwargs)
                results[idx] = result
            except Exception as e:
                results[idx] = e

        return results

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - self.stats["current_active"],
            "queue_size": len(self.task_queue),
        }

    def get_active_tasks(self) -> Dict:
        """获取活动任务"""
        return self.active_tasks.copy()


class TaskQueue:
    """任务队列（带优先级）"""

    def __init__(self):
        self.queue = []
        self.task_count = 0

    def add_task(self, func: Callable, *args, priority: int = 0, **kwargs) -> str:
        """
        添加任务到队列

        Args:
            func: 任务函数
            *args: 位置参数
            priority: 优先级
            **kwargs: 关键字参数

        Returns:
            任务ID
        """
        task_id = f"task_{self.task_count}"
        self.task_count += 1

        heapq.heappush(self.queue, (priority, task_id, func, args, kwargs))

        return task_id

    def get_next_task(self) -> Optional[Dict]:
        """获取下一个任务"""
        if not self.queue:
            return None

        priority, task_id, func, args, kwargs = heapq.heappop(self.queue)

        return {"id": task_id, "priority": priority, "func": func, "args": args, "kwargs": kwargs}

    def size(self) -> int:
        """获取队列大小"""
        return len(self.queue)

    def clear(self):
        """清空队列"""
        self.queue = []
        self.task_count = 0


class RateLimiter:
    """速率限制器"""

    def __init__(self, rate: int = 10, period: float = 1.0):
        """
        初始化速率限制器

        Args:
            rate: 时间窗口内允许的请求数
            period: 时间窗口（秒）
        """
        self.rate = rate
        self.period = period
        self.tokens = rate
        self.last_update = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """获取令牌（如果可用）"""
        async with self.lock:
            now = asyncio.get_event_loop().time()

            # 补充令牌
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate / self.period)
            self.last_update = now

            # 检查是否有令牌
            if self.tokens < 1:
                # 等待令牌补充
                wait_time = (1 - self.tokens) * self.period / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# 全局并发管理器
_concurrency_manager = None
_task_queue = None


def get_concurrency_manager(max_concurrent: int = 5) -> ConcurrencyManager:
    """获取全局并发管理器"""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager(max_concurrent)
    return _concurrency_manager


def get_task_queue() -> TaskQueue:
    """获取全局任务队列"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


# 使用示例
if __name__ == "__main__":
    import asyncio

    async def test_task(n: int):
        await asyncio.sleep(1)
        return n * 2

    async def main():
        manager = get_concurrency_manager(max_concurrent=3)

        # 测试并发限制
        tasks = [test_task(i) for i in range(10)]
        results = await manager.batch_process(tasks, batch_size=5)

        print(f"Results: {results}")
        print(f"Stats: {manager.get_stats()}")

    asyncio.run(main())
