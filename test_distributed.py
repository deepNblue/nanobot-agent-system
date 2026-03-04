"""
分布式系统测试 - 测试分布式调度、负载均衡和故障容错

测试覆盖：
- 负载均衡算法
- 任务调度
- 检查点保存和恢复
- 故障恢复
- 熔断器
- 节点选择
"""

import pytest
import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from distributed_scheduler import DistributedScheduler, PriorityTaskScheduler, TaskPriority, create_distributed_scheduler
from load_balancer import LoadBalancer, AdvancedLoadBalancer, create_load_balancer
from fault_tolerance import FaultTolerance, TaskRecovery, CircuitState, create_fault_tolerance

# ============== Fixtures ==============


@pytest.fixture
def load_balancer():
    """创建负载均衡器"""
    return LoadBalancer()


@pytest.fixture
def advanced_load_balancer():
    """创建高级负载均衡器"""
    return AdvancedLoadBalancer()


@pytest.fixture
def fault_tolerance():
    """创建故障容错实例"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield FaultTolerance(checkpoint_dir=tmpdir)


@pytest.fixture
def scheduler():
    """创建分布式调度器"""
    nodes = ["http://localhost:8001", "http://localhost:8002", "http://localhost:8003"]

    with tempfile.TemporaryDirectory() as tmpdir:
        lb = create_load_balancer()
        ft = create_fault_tolerance(checkpoint_dir=tmpdir)

        scheduler = DistributedScheduler(nodes=nodes, load_balancer=lb, fault_tolerance=ft)

        yield scheduler


@pytest.fixture
def sample_nodes():
    """示例节点状态"""
    return {
        "http://node1:8000": {
            "status": "healthy",
            "cpu_usage": 30,
            "memory_usage": 40,
            "active_tasks": 2,
            "network_latency": 10,
            "has_gpu": False,
            "available_env": ["python3.11", "nodejs"],
            "node_url": "http://node1:8000",
        },
        "http://node2:8000": {
            "status": "healthy",
            "cpu_usage": 60,
            "memory_usage": 70,
            "active_tasks": 5,
            "network_latency": 20,
            "has_gpu": True,
            "gpu_memory": 8,
            "available_env": ["python3.11", "cuda"],
            "node_url": "http://node2:8000",
        },
        "http://node3:8000": {
            "status": "healthy",
            "cpu_usage": 20,
            "memory_usage": 30,
            "active_tasks": 1,
            "network_latency": 5,
            "has_gpu": False,
            "available_env": ["python3.11", "nodejs", "go"],
            "node_url": "http://node3:8000",
        },
    }


# ============== Load Balancer Tests ==============


class TestLoadBalancer:
    """负载均衡器测试"""

    def test_calculate_score(self, load_balancer, sample_nodes):
        """测试得分计算"""
        for node_url, status in sample_nodes.items():
            score = load_balancer.calculate_score(status, {})

            # 检查得分范围（可以超过100，因为有奖励分数）
            assert score >= 0, f"Score negative for {node_url}: {score}"

            print(f"{node_url}: score={score:.2f}")

    def test_select_node(self, load_balancer, sample_nodes):
        """测试节点选择"""
        task = {"id": "test_task", "description": "Test task"}

        selected = load_balancer.select_node(task, sample_nodes)

        assert selected is not None
        assert selected in sample_nodes

        print(f"Selected node: {selected}")

    def test_select_node_with_gpu_requirement(self, load_balancer, sample_nodes):
        """测试GPU任务节点选择"""
        task = {"id": "gpu_task", "description": "GPU task", "requires_gpu": True}

        selected = load_balancer.select_node(task, sample_nodes)

        # 应该选择有GPU的节点
        assert selected is not None
        assert sample_nodes[selected]["has_gpu"]

        print(f"Selected GPU node: {selected}")

    def test_select_node_with_env_requirement(self, load_balancer, sample_nodes):
        """测试环境依赖节点选择"""
        task = {"id": "env_task", "description": "Task with env requirement", "required_env": ["go"]}

        selected = load_balancer.select_node(task, sample_nodes)

        # 应该选择有Go环境的节点
        assert selected is not None
        assert "go" in sample_nodes[selected]["available_env"]

        print(f"Selected node with Go: {selected}")

    def test_no_healthy_nodes(self, load_balancer):
        """测试无健康节点情况"""
        nodes = {"http://node1:8000": {"status": "unhealthy"}, "http://node2:8000": {"status": "unhealthy"}}

        task = {"id": "test_task"}

        selected = load_balancer.select_node(task, nodes)

        assert selected is None

    def test_get_node_ranking(self, load_balancer, sample_nodes):
        """测试节点排名"""
        task = {"id": "test_task"}

        ranking = load_balancer.get_node_ranking(sample_nodes, task)

        assert len(ranking) == len(sample_nodes)

        # 检查排序（得分应该递减）
        for i in range(len(ranking) - 1):
            assert ranking[i]["score"] >= ranking[i + 1]["score"]

        print("\nNode ranking:")
        for r in ranking:
            print(f"  {r['node']}: score={r['score']:.2f}")

    def test_round_robin_strategy(self):
        """测试轮询策略"""
        lb = LoadBalancer(strategy="round_robin")

        nodes = {
            "http://node1:8000": {"status": "healthy", "cpu_usage": 30, "memory_usage": 40, "active_tasks": 0},
            "http://node2:8000": {"status": "healthy", "cpu_usage": 30, "memory_usage": 40, "active_tasks": 0},
            "http://node3:8000": {"status": "healthy", "cpu_usage": 30, "memory_usage": 40, "active_tasks": 0},
        }

        # 连续选择3次
        selections = []
        for _ in range(3):
            selected = lb.select_node({}, nodes)
            selections.append(selected)

        # 应该依次选择不同节点
        assert len(set(selections)) == 3

        print(f"Round robin selections: {selections}")

    def test_least_connections_strategy(self):
        """测试最少连接策略"""
        lb = LoadBalancer(strategy="least_connections")

        nodes = {
            "http://node1:8000": {"status": "healthy", "active_tasks": 5},
            "http://node2:8000": {"status": "healthy", "active_tasks": 2},
            "http://node3:8000": {"status": "healthy", "active_tasks": 8},
        }

        selected = lb.select_node({}, nodes)

        # 应该选择任务数最少的节点
        assert selected == "http://node2:8000"

        print(f"Least connections selected: {selected}")


class TestAdvancedLoadBalancer:
    """高级负载均衡器测试"""

    def test_predict_node_load(self, advanced_load_balancer):
        """测试负载预测"""
        node_url = "http://node1:8000"

        # 添加历史数据
        for i in range(10):
            advanced_load_balancer.update_performance_history(
                node_url, {"cpu_usage": 30 + i * 2, "memory_usage": 40 + i, "active_tasks": i % 3}
            )

        # 预测负载
        prediction = advanced_load_balancer.predict_node_load(node_url)

        assert "predicted_cpu" in prediction
        assert "predicted_memory" in prediction
        assert "confidence" in prediction

        print(f"Prediction: {prediction}")

    def test_select_with_prediction(self, advanced_load_balancer, sample_nodes):
        """测试基于预测的选择"""
        # 添加历史数据
        for node_url in sample_nodes.keys():
            for i in range(10):
                advanced_load_balancer.update_performance_history(node_url, sample_nodes[node_url])

        task = {"id": "test_task"}

        selected = advanced_load_balancer.select_node_with_prediction(task, sample_nodes)

        assert selected is not None

        print(f"Selected with prediction: {selected}")


# ============== Fault Tolerance Tests ==============


class TestFaultTolerance:
    """故障容错测试"""

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self, fault_tolerance):
        """测试检查点保存和加载"""
        task_id = "test_task_1"
        state = {"progress": 50, "completed_steps": ["step1", "step2"], "data": {"key": "value"}}

        # 保存
        success = await fault_tolerance.save_checkpoint(task_id, state)
        assert success

        # 加载
        loaded = await fault_tolerance.load_checkpoint(task_id)

        assert loaded is not None
        assert loaded["task_id"] == task_id
        assert loaded["state"]["progress"] == 50
        assert loaded["state"]["completed_steps"] == ["step1", "step2"]

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, fault_tolerance):
        """测试删除检查点"""
        task_id = "test_task_2"
        state = {"progress": 30}

        # 保存
        await fault_tolerance.save_checkpoint(task_id, state)

        # 删除
        success = await fault_tolerance.delete_checkpoint(task_id)
        assert success

        # 尝试加载
        loaded = await fault_tolerance.load_checkpoint(task_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_retry_success(self, fault_tolerance):
        """测试重试成功"""
        call_count = 0

        async def flaky_task():
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                raise Exception("Temporary failure")

            return "Success!"

        result = await fault_tolerance.retry_task(flaky_task, "test_retry")

        assert result["success"]
        assert result["result"] == "Success!"
        assert result["retries"] == 2

    @pytest.mark.asyncio
    async def test_retry_max_retries(self, fault_tolerance):
        """测试达到最大重试次数"""
        fault_tolerance.max_retries = 3

        async def always_fail():
            raise Exception("Always fails")

        result = await fault_tolerance.retry_task(always_fail, "test_max_retries")

        assert not result["success"]
        assert result["retries"] == 3

    def test_circuit_breaker(self, fault_tolerance):
        """测试熔断器"""
        node_url = "http://node1:8000"

        # 初始状态应该可以访问
        assert fault_tolerance.check_circuit(node_url)

        # 记录失败
        for i in range(5):
            fault_tolerance._record_failure(node_url)

        # 熔断器应该打开
        cb = fault_tolerance.circuit_breakers[node_url]
        assert cb["state"] == CircuitState.OPEN

        # 不应该可以访问
        assert not fault_tolerance.check_circuit(node_url)

        # 重置熔断器
        fault_tolerance.reset_circuit(node_url)

        # 应该可以访问
        assert fault_tolerance.check_circuit(node_url)

    def test_list_checkpoints(self, fault_tolerance):
        """测试列出检查点"""
        import asyncio

        # 创建多个检查点
        async def create_checkpoints():
            for i in range(5):
                await fault_tolerance.save_checkpoint(f"task_{i}", {"progress": i * 20})

        asyncio.run(create_checkpoints())

        # 列出检查点
        checkpoints = fault_tolerance.list_checkpoints()

        assert len(checkpoints) == 5

    def test_cleanup_old_checkpoints(self, fault_tolerance):
        """测试清理旧检查点"""
        import asyncio
        import time

        async def create_checkpoints():
            # 创建检查点
            await fault_tolerance.save_checkpoint("new_task", {"progress": 100})

            # 创建旧检查点（修改文件时间）
            await fault_tolerance.save_checkpoint("old_task", {"progress": 50})

            # 修改文件时间为8天前
            old_file = fault_tolerance.checkpoint_dir / "old_task.json"
            old_time = time.time() - (8 * 24 * 3600)
            os.utime(old_file, (old_time, old_time))

        asyncio.run(create_checkpoints())

        # 清理7天前的检查点
        deleted = fault_tolerance.cleanup_old_checkpoints(max_age_days=7)

        assert deleted == 1

        # 检查剩余检查点
        checkpoints = fault_tolerance.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0]["task_id"] == "new_task"


class TestTaskRecovery:
    """任务恢复测试"""

    @pytest.mark.asyncio
    async def test_recover_task(self, fault_tolerance):
        """测试任务恢复"""
        recovery = TaskRecovery(fault_tolerance)

        task_id = "test_recover"
        state = {"progress": 75, "data": "test"}

        # 保存检查点
        await fault_tolerance.save_checkpoint(task_id, state)

        # 恢复任务
        result = await recovery.recover_task(task_id)

        assert result["success"]
        assert result["state"]["progress"] == 75

    @pytest.mark.asyncio
    async def test_batch_recover(self, fault_tolerance):
        """测试批量恢复"""
        recovery = TaskRecovery(fault_tolerance)

        # 创建多个检查点
        task_ids = []
        for i in range(5):
            task_id = f"batch_task_{i}"
            task_ids.append(task_id)
            await fault_tolerance.save_checkpoint(task_id, {"progress": i * 20})

        # 批量恢复
        result = await recovery.batch_recover(task_ids)

        assert result["total"] == 5
        assert result["success"] == 5
        assert result["failed"] == 0


# ============== Distributed Scheduler Tests ==============


class TestDistributedScheduler:
    """分布式调度器测试"""

    def test_initialization(self, scheduler):
        """测试初始化"""
        assert len(scheduler.nodes) == 3
        assert scheduler.load_balancer is not None
        assert scheduler.fault_tolerance is not None

    @pytest.mark.asyncio
    async def test_update_node_status(self, scheduler):
        """测试更新节点状态"""
        # 模拟节点状态
        scheduler.node_status = {
            "http://localhost:8001": {"status": "healthy", "cpu_usage": 30, "memory_usage": 40, "active_tasks": 1},
            "http://localhost:8002": {"status": "healthy", "cpu_usage": 50, "memory_usage": 60, "active_tasks": 3},
        }

        # 注意：这里不会真正连接节点
        # 实际测试需要启动节点服务器

        print("Node status update test (requires running node servers)")

    def test_get_cluster_status(self, scheduler):
        """测试获取集群状态"""
        # 设置模拟状态
        scheduler.node_status = {
            "http://localhost:8001": {"status": "healthy"},
            "http://localhost:8002": {"status": "healthy"},
            "http://localhost:8003": {"status": "unhealthy"},
        }

        scheduler.task_assignments = {
            "task1": {"status": "running", "node": "http://localhost:8001"},
            "task2": {"status": "completed", "node": "http://localhost:8002"},
        }

        status = scheduler.get_cluster_status()

        assert status["nodes"]["total"] == 3
        assert status["nodes"]["healthy"] == 2
        assert status["tasks"]["active"] == 1
        assert status["tasks"]["completed"] == 1

    def test_get_task_status(self, scheduler):
        """测试获取任务状态"""
        # 添加任务
        scheduler.task_assignments["task1"] = {"node": "http://localhost:8001", "status": "running"}

        # 获取状态
        status = scheduler.get_task_status("task1")

        assert status is not None
        assert status["status"] == "running"

        # 不存在的任务
        status = scheduler.get_task_status("nonexistent")
        assert status is None


class TestPriorityTaskScheduler:
    """优先级任务调度器测试"""

    @pytest.fixture
    def priority_scheduler(self):
        """创建优先级调度器"""
        nodes = ["http://localhost:8001", "http://localhost:8002"]

        with tempfile.TemporaryDirectory() as tmpdir:
            lb = create_load_balancer()
            ft = create_fault_tolerance(checkpoint_dir=tmpdir)

            scheduler = PriorityTaskScheduler(nodes=nodes, load_balancer=lb, fault_tolerance=ft)

            yield scheduler

    def test_initialization(self, priority_scheduler):
        """测试初始化"""
        assert len(priority_scheduler.nodes) == 2
        assert priority_scheduler.task_dependencies == {}
        assert priority_scheduler.completed_tasks == set()

    @pytest.mark.asyncio
    async def test_check_dependencies(self, priority_scheduler):
        """测试依赖检查"""
        task_id = "task_with_deps"

        # 无依赖
        assert await priority_scheduler.check_dependencies(task_id)

        # 添加依赖
        priority_scheduler.task_dependencies[task_id] = ["dep1", "dep2"]

        # 依赖未满足
        assert not await priority_scheduler.check_dependencies(task_id)

        # 完成一个依赖
        priority_scheduler.completed_tasks.add("dep1")
        assert not await priority_scheduler.check_dependencies(task_id)

        # 完成所有依赖
        priority_scheduler.completed_tasks.add("dep2")
        assert await priority_scheduler.check_dependencies(task_id)


# ============== Integration Tests ==============


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, scheduler, sample_nodes):
        """测试完整工作流"""
        # 设置节点状态
        scheduler.node_status = sample_nodes

        # 创建任务
        task = {"description": "Integration test task", "data": {"key": "value"}}

        # 调度任务（不会真正执行，因为没有运行节点服务器）
        # 这里只测试调度逻辑

        # 选择最佳节点
        best_node = scheduler.load_balancer.select_node(task, sample_nodes)

        assert best_node is not None

        print(f"Integration test - Selected node: {best_node}")

    @pytest.mark.asyncio
    async def test_fault_tolerance_integration(self, scheduler):
        """测试故障容错集成"""
        # 创建检查点
        task_id = "integration_task"
        state = {"progress": 50}

        await scheduler.fault_tolerance.save_checkpoint(task_id, state)

        # 加载检查点
        loaded = await scheduler.fault_tolerance.load_checkpoint(task_id)

        assert loaded is not None
        assert loaded["state"]["progress"] == 50

    def test_load_balancer_integration(self, scheduler, sample_nodes):
        """测试负载均衡集成"""
        # 获取排名
        ranking = scheduler.load_balancer.get_node_ranking(sample_nodes)

        assert len(ranking) == 3

        # 检查一致性
        best_node = scheduler.load_balancer.select_node({}, sample_nodes)

        assert best_node == ranking[0]["node"]


# ============== Performance Tests ==============


class TestPerformance:
    """性能测试"""

    def test_score_calculation_performance(self, load_balancer, sample_nodes):
        """测试得分计算性能"""
        import time

        iterations = 1000

        start = time.time()

        for _ in range(iterations):
            for status in sample_nodes.values():
                load_balancer.calculate_score(status, {})

        elapsed = time.time() - start

        avg_time = elapsed / (iterations * len(sample_nodes))

        print(f"\nScore calculation - Avg time: {avg_time * 1000:.3f}ms")

        # 应该很快（< 1ms）
        assert avg_time < 0.001

    def test_node_selection_performance(self, load_balancer, sample_nodes):
        """测试节点选择性能"""
        import time

        iterations = 1000

        start = time.time()

        for _ in range(iterations):
            load_balancer.select_node({}, sample_nodes)

        elapsed = time.time() - start

        avg_time = elapsed / iterations

        print(f"Node selection - Avg time: {avg_time * 1000:.3f}ms")

        # 应该很快（< 1ms）
        assert avg_time < 0.001

    @pytest.mark.asyncio
    async def test_checkpoint_performance(self, fault_tolerance):
        """测试检查点性能"""
        import time

        iterations = 100

        # 测试保存性能
        start = time.time()

        for i in range(iterations):
            await fault_tolerance.save_checkpoint(f"perf_task_{i}", {"progress": i, "data": "x" * 1000})

        save_time = time.time() - start

        # 测试加载性能
        start = time.time()

        for i in range(iterations):
            await fault_tolerance.load_checkpoint(f"perf_task_{i}")

        load_time = time.time() - start

        print(f"\nCheckpoint save - Avg time: {save_time / iterations * 1000:.3f}ms")
        print(f"Checkpoint load - Avg time: {load_time / iterations * 1000:.3f}ms")

        # 应该合理快（< 10ms）
        assert save_time / iterations < 0.01
        assert load_time / iterations < 0.01


# ============== Run Tests ==============


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])
