"""
性能监控器 - 监控系统性能

功能：
1. 执行时间跟踪
2. API调用统计
3. 错误追踪
4. 性能报告生成
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from collections import defaultdict
import statistics


@dataclass
class MetricEntry:
    """指标条目"""

    operation: str
    value: float
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, max_entries: int = 10000):
        """
        初始化性能监控器

        Args:
            max_entries: 最大条目数
        """
        self.max_entries = max_entries

        # 指标存储
        self.metrics = {"execution_times": [], "api_calls": [], "errors": [], "cache_stats": []}

        # 聚合统计
        self.aggregated = defaultdict(lambda: {"count": 0, "total": 0.0, "min": float("inf"), "max": 0.0, "values": []})

        # 错误追踪
        self.error_counts = defaultdict(int)
        self.recent_errors = []

        # API调用追踪
        self.api_stats = defaultdict(lambda: {"calls": 0, "errors": 0, "total_time": 0.0})

    @contextmanager
    def track_time(self, operation: str, metadata: Dict = None):
        """
        跟踪执行时间（同步）

        Args:
            operation: 操作名称
            metadata: 元数据

        Usage:
            with monitor.track_time("database_query", {"table": "users"}):
                # 执行操作
                pass
        """
        start = time.time()
        yield

        elapsed = time.time() - start

        self._record_execution_time(operation, elapsed, metadata)

    @asynccontextmanager
    async def track_time_async(self, operation: str, metadata: Dict = None):
        """
        跟踪执行时间（异步）

        Args:
            operation: 操作名称
            metadata: 元数据

        Usage:
            async with monitor.track_time_async("api_call", {"endpoint": "/users"}):
                # 执行操作
                pass
        """
        start = time.time()
        yield

        elapsed = time.time() - start

        self._record_execution_time(operation, elapsed, metadata)

    def _record_execution_time(self, operation: str, elapsed: float, metadata: Dict = None):
        """记录执行时间"""
        entry = MetricEntry(operation=operation, value=elapsed, timestamp=datetime.now(), metadata=metadata or {})

        self.metrics["execution_times"].append(entry)

        # 更新聚合统计
        stats = self.aggregated[operation]
        stats["count"] += 1
        stats["total"] += elapsed
        stats["min"] = min(stats["min"], elapsed)
        stats["max"] = max(stats["max"], elapsed)
        stats["values"].append(elapsed)

        # 限制条目数
        if len(self.metrics["execution_times"]) > self.max_entries:
            self.metrics["execution_times"].pop(0)

    def record_api_call(self, api_name: str, success: bool, duration: float, metadata: Dict = None):
        """
        记录API调用

        Args:
            api_name: API名称
            success: 是否成功
            duration: 耗时
            metadata: 元数据
        """
        entry = MetricEntry(
            operation=api_name, value=duration, timestamp=datetime.now(), metadata={"success": success, **(metadata or {})}
        )

        self.metrics["api_calls"].append(entry)

        # 更新API统计
        stats = self.api_stats[api_name]
        stats["calls"] += 1
        if not success:
            stats["errors"] += 1
        stats["total_time"] += duration

    def record_error(self, error_type: str, error_message: str, metadata: Dict = None):
        """
        记录错误

        Args:
            error_type: 错误类型
            error_message: 错误消息
            metadata: 元数据
        """
        entry = MetricEntry(
            operation=error_type, value=1, timestamp=datetime.now(), metadata={"message": error_message, **(metadata or {})}
        )

        self.metrics["errors"].append(entry)

        # 更新错误统计
        self.error_counts[error_type] += 1

        # 保存最近错误
        self.recent_errors.append(
            {"type": error_type, "message": error_message, "timestamp": datetime.now().isoformat(), "metadata": metadata or {}}
        )

        # 限制最近错误数量
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)

    def record_cache_stats(self, hits: int, misses: int, evictions: int):
        """记录缓存统计"""
        entry = MetricEntry(
            operation="cache",
            value=hits / (hits + misses) if (hits + misses) > 0 else 0,
            timestamp=datetime.now(),
            metadata={"hits": hits, "misses": misses, "evictions": evictions},
        )

        self.metrics["cache_stats"].append(entry)

    def get_operation_stats(self, operation: str) -> Dict:
        """
        获取操作统计

        Args:
            operation: 操作名称

        Returns:
            统计信息
        """
        stats = self.aggregated.get(operation)

        if not stats or stats["count"] == 0:
            return {}

        values = stats["values"]

        return {
            "operation": operation,
            "count": stats["count"],
            "total_time": stats["total"],
            "avg_time": stats["total"] / stats["count"],
            "min_time": stats["min"],
            "max_time": stats["max"],
            "median_time": statistics.median(values) if values else 0,
            "p95_time": self._percentile(values, 95) if values else 0,
            "p99_time": self._percentile(values, 99) if values else 0,
        }

    def get_api_stats(self, api_name: str = None) -> Dict:
        """
        获取API统计

        Args:
            api_name: API名称（None表示所有API）

        Returns:
            统计信息
        """
        if api_name:
            stats = self.api_stats.get(api_name, {})

            if not stats or stats["calls"] == 0:
                return {}

            return {
                "api": api_name,
                "total_calls": stats["calls"],
                "total_errors": stats["errors"],
                "error_rate": (stats["errors"] / stats["calls"] * 100) if stats["calls"] > 0 else 0,
                "avg_time": stats["total_time"] / stats["calls"] if stats["calls"] > 0 else 0,
            }
        else:
            # 返回所有API统计
            result = {}
            for api, stats in self.api_stats.items():
                result[api] = self.get_api_stats(api)
            return result

    def get_error_stats(self) -> Dict:
        """获取错误统计"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "by_type": dict(self.error_counts),
            "recent": self.recent_errors[-10:],  # 最近10个错误
        }

    def get_performance_report(self, period_hours: int = 24) -> Dict:
        """
        生成性能报告

        Args:
            period_hours: 报告周期（小时）

        Returns:
            性能报告
        """
        cutoff = datetime.now() - timedelta(hours=period_hours)

        # 筛选周期内的指标
        recent_metrics = {
            "execution_times": [m for m in self.metrics["execution_times"] if m.timestamp >= cutoff],
            "api_calls": [m for m in self.metrics["api_calls"] if m.timestamp >= cutoff],
            "errors": [m for m in self.metrics["errors"] if m.timestamp >= cutoff],
        }

        # 计算统计
        operations = defaultdict(list)
        for metric in recent_metrics["execution_times"]:
            operations[metric.operation].append(metric.value)

        operation_stats = {}
        for op, values in operations.items():
            if values:
                operation_stats[op] = {
                    "count": len(values),
                    "avg_time": statistics.mean(values),
                    "max_time": max(values),
                    "min_time": min(values),
                }

        # API统计
        api_stats = {}
        apis = defaultdict(lambda: {"calls": 0, "errors": 0, "times": []})
        for metric in recent_metrics["api_calls"]:
            apis[metric.operation]["calls"] += 1
            if not metric.metadata.get("success", True):
                apis[metric.operation]["errors"] += 1
            apis[metric.operation]["times"].append(metric.value)

        for api, stats in apis.items():
            api_stats[api] = {
                "total_calls": stats["calls"],
                "error_rate": (stats["errors"] / stats["calls"] * 100) if stats["calls"] > 0 else 0,
                "avg_time": statistics.mean(stats["times"]) if stats["times"] else 0,
            }

        # 错误统计
        error_stats = defaultdict(int)
        for metric in recent_metrics["errors"]:
            error_stats[metric.operation] += 1

        return {
            "period": f"Last {period_hours} hours",
            "generated_at": datetime.now().isoformat(),
            "operations": operation_stats,
            "apis": api_stats,
            "errors": {"total": len(recent_metrics["errors"]), "by_type": dict(error_stats)},
            "summary": {
                "total_operations": len(recent_metrics["execution_times"]),
                "total_api_calls": len(recent_metrics["api_calls"]),
                "total_errors": len(recent_metrics["errors"]),
            },
        }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)

        return sorted_values[min(index, len(sorted_values) - 1)]

    def clear_old_metrics(self, days: int = 7):
        """清理旧指标"""
        cutoff = datetime.now() - timedelta(days=days)

        for metric_type in self.metrics:
            self.metrics[metric_type] = [m for m in self.metrics[metric_type] if m.timestamp >= cutoff]

    def export_metrics(self, filepath: str):
        """导出指标到文件"""
        data = {
            "metrics": {
                k: [
                    {"operation": m.operation, "value": m.value, "timestamp": m.timestamp.isoformat(), "metadata": m.metadata}
                    for m in v
                ]
                for k, v in self.metrics.items()
            },
            "aggregated": dict(self.aggregated),
            "api_stats": dict(self.api_stats),
            "error_counts": dict(self.error_counts),
            "recent_errors": self.recent_errors,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


# 全局性能监控器
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# 使用示例
if __name__ == "__main__":
    import asyncio

    monitor = get_performance_monitor()

    # 同步跟踪
    with monitor.track_time("database_query"):
        time.sleep(0.1)

    # 异步跟踪
    async def async_operation():
        async with monitor.track_time_async("api_call"):
            await asyncio.sleep(0.1)

    asyncio.run(async_operation())

    # 记录API调用
    monitor.record_api_call("openai_api", success=True, duration=0.5)

    # 记录错误
    monitor.record_error("ConnectionError", "Failed to connect to API")

    # 获取统计
    stats = monitor.get_operation_stats("database_query")
    print(f"Database query stats: {stats}")

    # 生成报告
    report = monitor.get_performance_report(period_hours=1)
    print(f"Performance report: {report}")
