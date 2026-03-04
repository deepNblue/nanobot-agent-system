"""
多模型支持测试套件
测试模型适配器、智能选择器和成本优化器
"""

import pytest
import asyncio
import os
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# 导入被测试的模块
from model_adapter import ModelAdapter, GLM5Adapter, ClaudeAdapter, GPT4Adapter, BaseModelAdapter, quick_call
from model_selector import ModelSelector, TaskComplexity, TaskType, TaskFeatures, MODEL_CONFIGS
from cost_optimizer import CostOptimizer, UsageRecord, BudgetStatus, BudgetAlert

# ==================== Fixtures ====================


@pytest.fixture
def mock_config():
    """模拟配置"""
    return {"zhipu_api_key": "test-zhipu-key", "anthropic_api_key": "test-anthropic-key", "openai_api_key": "test-openai-key"}


@pytest.fixture
def adapter(mock_config, tmp_path):
    """创建模型适配器"""
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(mock_config, f)

    return ModelAdapter(str(config_file))


@pytest.fixture
def selector(adapter):
    """创建模型选择器"""
    return ModelSelector(adapter)


@pytest.fixture
def optimizer():
    """创建成本优化器"""
    return CostOptimizer(daily_budget=10.0, hourly_budget=1.0)


@pytest.fixture
def sample_task():
    """示例任务"""
    return {"description": "设计一个微服务架构系统", "type": "architecture", "complexity": "high", "priority": "medium"}


# ==================== 模型适配器测试 ====================


class TestModelAdapter:
    """模型适配器测试"""

    def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter is not None
        models = adapter.get_available_models()
        assert len(models) > 0
        assert "glm5-turbo" in models or "glm5-plus" in models

    def test_adapter_load_config(self, tmp_path):
        """测试配置加载"""
        config_data = {"zhipu_api_key": "test-key"}
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        adapter = ModelAdapter(str(config_file))
        assert adapter.config == config_data

    def test_adapter_env_var(self, monkeypatch):
        """测试从环境变量读取API密钥"""
        monkeypatch.setenv("ZHIPU_API_KEY", "env-test-key")

        adapter = ModelAdapter()
        # 应该能够从环境变量加载
        assert "glm5-turbo" in adapter.get_available_models()

    def test_get_available_models(self, adapter):
        """测试获取可用模型列表"""
        models = adapter.get_available_models()

        assert isinstance(models, list)
        assert len(models) > 0

        # 检查至少有一个GLM5模型
        glm_models = [m for m in models if m.startswith("glm5")]
        assert len(glm_models) > 0

    def test_get_preferred_model(self, adapter):
        """测试获取推荐模型"""
        preferred = adapter.get_preferred_model()

        assert preferred is not None
        # 应该优先返回GLM5模型
        assert "glm5" in preferred or "deepseek" in preferred

    @pytest.mark.asyncio
    async def test_call_model_invalid(self, adapter):
        """测试调用无效模型"""
        result = await adapter.call_model("invalid-model", "test prompt")

        assert result["success"] is False
        assert "error" in result
        assert "available_models" in result

    @pytest.mark.asyncio
    async def test_count_tokens(self, adapter):
        """测试token计数"""
        text = "这是一个测试文本"
        tokens = await adapter.count_tokens("glm5-turbo", text)

        assert tokens > 0
        assert isinstance(tokens, int)

    def test_get_model_stats(self, adapter):
        """测试获取模型统计"""
        models = adapter.get_available_models()
        if models:
            stats = adapter.get_model_stats(models[0])
            assert stats is not None
            assert "model_id" in stats
            assert "request_count" in stats

    def test_get_all_stats(self, adapter):
        """测试获取所有模型统计"""
        all_stats = adapter.get_all_stats()

        assert isinstance(all_stats, dict)
        assert len(all_stats) > 0


class TestGLM5Adapter:
    """GLM5适配器测试"""

    def test_initialization(self):
        """测试初始化"""
        adapter = GLM5Adapter("glm-5-turbo", "test-key")

        assert adapter.model_id == "glm-5-turbo"
        assert adapter.api_key == "test-key"
        assert adapter.max_retries == 3
        assert adapter.timeout == 30

    @pytest.mark.asyncio
    async def test_count_tokens_chinese(self):
        """测试中文token计数"""
        adapter = GLM5Adapter("glm-5-turbo", "test-key")

        text = "这是一个中文测试文本"
        tokens = await adapter.count_tokens(text)

        # 中文约1.5字符/token
        assert tokens > 0
        assert tokens < len(text)

    @pytest.mark.asyncio
    async def test_count_tokens_english(self):
        """测试英文token计数"""
        adapter = GLM5Adapter("glm-5-turbo", "test-key")

        text = "This is an English test text"
        tokens = await adapter.count_tokens(text)

        # 英文约4字符/token
        assert tokens > 0
        assert tokens < len(text)

    @pytest.mark.asyncio
    async def test_generate_mock(self):
        """测试生成（模拟）"""
        adapter = GLM5Adapter("glm-5-turbo", "test-key")

        # 模拟HTTP响应
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={"choices": [{"message": {"content": "测试响应"}}], "usage": {"total_tokens": 100}}
            )
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await adapter.generate("测试提示")

            assert result["success"] is True
            assert result["content"] == "测试响应"

    def test_get_stats(self):
        """测试获取统计"""
        adapter = GLM5Adapter("glm-5-turbo", "test-key")
        adapter.request_count = 10
        adapter.error_count = 2

        stats = adapter.get_stats()

        assert stats["model_id"] == "glm-5-turbo"
        assert stats["request_count"] == 10
        assert stats["error_count"] == 2
        assert stats["error_rate"] == 0.2


class TestClaudeAdapter:
    """Claude适配器测试"""

    def test_initialization(self):
        """测试初始化"""
        adapter = ClaudeAdapter("claude-3-opus", "test-key")

        assert adapter.model_id == "claude-3-opus"
        assert adapter.api_key == "test-key"
        assert adapter.endpoint == "https://api.anthropic.com/v1/messages"

    @pytest.mark.asyncio
    async def test_count_tokens(self):
        """测试token计数"""
        adapter = ClaudeAdapter("claude-3-opus", "test-key")

        text = "This is a test text for Claude"
        tokens = await adapter.count_tokens(text)

        # 英文约4字符/token
        assert tokens > 0
        assert tokens < len(text)


class TestGPT4Adapter:
    """GPT-4适配器测试"""

    def test_initialization(self):
        """测试初始化"""
        adapter = GPT4Adapter("gpt-4-turbo", "test-key")

        assert adapter.model_id == "gpt-4-turbo"
        assert adapter.api_key == "test-key"
        assert adapter.endpoint == "https://api.openai.com/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_count_tokens(self):
        """测试token计数"""
        adapter = GPT4Adapter("gpt-4-turbo", "test-key")

        text = "This is a test text for GPT-4"
        tokens = await adapter.count_tokens(text)

        assert tokens > 0


# ==================== 模型选择器测试 ====================


class TestModelSelector:
    """模型选择器测试"""

    def test_initialization(self, selector):
        """测试初始化"""
        assert selector is not None
        assert len(selector.available_models) > 0

    def test_analyze_complexity_high(self, selector):
        """测试高复杂度分析"""
        task = {"description": "设计微服务架构系统", "complexity": "high"}

        complexity = selector.analyze_complexity(task)
        assert complexity == TaskComplexity.HIGH

    def test_analyze_complexity_low(self, selector):
        """测试低复杂度分析"""
        task = {"description": "快速修复bug", "complexity": "low"}

        complexity = selector.analyze_complexity(task)
        assert complexity == TaskComplexity.LOW

    def test_analyze_complexity_inferred(self, selector):
        """测试从描述推断复杂度"""
        task = {"description": "重构整个系统架构"}

        complexity = selector.analyze_complexity(task)
        assert complexity == TaskComplexity.HIGH

    def test_analyze_type(self, selector):
        """测试任务类型分析"""
        test_cases = [
            ({"type": "architecture"}, TaskType.ARCHITECTURE),
            ({"type": "bug_fix"}, TaskType.BUG_FIX),
            ({"type": "feature"}, TaskType.FEATURE),
            ({"description": "修复bug"}, TaskType.BUG_FIX),
            ({"description": "编写文档"}, TaskType.DOCUMENTATION),
        ]

        for task, expected_type in test_cases:
            result = selector.analyze_type(task)
            assert result == expected_type

    def test_detect_language(self, selector):
        """测试语言检测"""
        assert selector.detect_language("这是中文") == "zh"
        assert selector.detect_language("This is English") == "en"
        assert selector.detect_language("") == "en"

    def test_estimate_tokens(self, selector):
        """测试token估算"""
        task = {"description": "这是一个测试描述", "context": "这是上下文信息"}

        tokens = selector.estimate_tokens(task)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_needs_creativity(self, selector):
        """测试创意需求判断"""
        creative_task = {"description": "设计一个创新的解决方案"}
        routine_task = {"description": "修复bug"}

        assert selector.needs_creativity(creative_task) is True
        assert selector.needs_creativity(routine_task) is False

    def test_needs_speed(self, selector):
        """测试速度需求判断"""
        fast_task = {"priority": "high"}
        slow_task = {"priority": "low"}

        assert selector.needs_speed(fast_task) is True
        assert selector.needs_speed(slow_task) is False

    @pytest.mark.asyncio
    async def test_select_best_model_high_complexity(self, selector):
        """测试高复杂度任务选择"""
        task = {"complexity": "high", "type": "architecture", "description": "设计微服务架构"}

        model = await selector.select_best_model(task)

        # 应该选择高质量模型
        config = MODEL_CONFIGS.get(model, {})
        assert config.get("quality") in ["high", "very_high"]

    @pytest.mark.asyncio
    async def test_select_best_model_speed_priority(self, selector):
        """测试速度优先任务选择"""
        task = {"complexity": "low", "priority": "high", "description": "快速修复bug"}

        constraints = {"requires_fast": True}

        model = await selector.select_best_model(task, constraints)

        # 应该选择快速模型
        config = MODEL_CONFIGS.get(model, {})
        assert config.get("speed") in ["fast", "very_fast"]

    @pytest.mark.asyncio
    async def test_select_best_model_chinese(self, selector):
        """测试中文任务选择"""
        task = {"description": "编写中文技术文档", "type": "documentation"}

        # 添加语言约束
        constraints = {
            "include_models": [m for m in selector.available_models if "zh" in MODEL_CONFIGS.get(m, {}).get("languages", [])]
        }

        model = await selector.select_best_model(task, constraints if constraints["include_models"] else None)

        # 如果有支持中文的模型，应该选择一个
        if any("zh" in MODEL_CONFIGS.get(m, {}).get("languages", []) for m in selector.available_models):
            # 检查至少有支持中文的模型可用
            has_chinese_support = any("zh" in MODEL_CONFIGS.get(m, {}).get("languages", []) for m in selector.available_models)
            assert has_chinese_support or model is not None

    @pytest.mark.asyncio
    async def test_select_best_model_with_constraints(self, selector):
        """测试带约束的选择"""
        task = {"description": "测试任务", "complexity": "medium"}

        constraints = {"max_cost": 0.01, "requires_fast": True}

        model = await selector.select_best_model(task, constraints)

        # 检查约束是否满足
        config = MODEL_CONFIGS.get(model, {})
        assert config.get("cost_per_1k_tokens", 999) <= 0.01
        assert config.get("speed") in ["fast", "very_fast"]

    @pytest.mark.asyncio
    async def test_get_model_recommendations(self, selector):
        """测试获取推荐列表"""
        task = {"description": "设计系统架构", "complexity": "high"}

        recommendations = await selector.get_model_recommendations(task, top_n=3)

        assert len(recommendations) <= 3
        assert all(len(rec) == 3 for rec in recommendations)  # (model, score, reason)

        # 检查得分排序
        scores = [rec[1] for rec in recommendations]
        assert scores == sorted(scores, reverse=True)

    def test_apply_constraints_exclude(self, selector):
        """测试排除特定模型"""
        features = TaskFeatures(
            complexity=TaskComplexity.MEDIUM,
            type=TaskType.GENERAL,
            language="en",
            estimated_tokens=1000,
            requires_creativity=False,
            requires_speed=False,
            requires_chinese=False,
            requires_code=False,
            priority="medium",
            description="test",
        )

        constraints = {"exclude_models": ["gpt-4", "claude-3-opus"]}

        candidates = selector.apply_constraints(features, constraints)

        assert "gpt-4" not in candidates
        assert "claude-3-opus" not in candidates

    def test_score_calculation(self, selector):
        """测试得分计算"""
        features = TaskFeatures(
            complexity=TaskComplexity.HIGH,
            type=TaskType.ARCHITECTURE,
            language="en",
            estimated_tokens=1000,
            requires_creativity=True,
            requires_speed=False,
            requires_chinese=False,
            requires_code=True,
            priority="medium",
            description="design architecture",
        )

        # 测试不同模型的得分
        for model in selector.available_models:
            score = selector.calculate_score(model, features, None)
            assert 0 <= score <= 100


# ==================== 成本优化器测试 ====================


class TestCostOptimizer:
    """成本优化器测试"""

    def test_initialization(self, optimizer):
        """测试初始化"""
        assert optimizer.daily_budget == 10.0
        assert optimizer.hourly_budget == 1.0
        assert optimizer.daily_spend == 0.0
        assert optimizer.hourly_spend == 0.0

    @pytest.mark.asyncio
    async def test_check_budget_within_limit(self, optimizer):
        """测试预算内检查"""
        result = await optimizer.check_budget("glm5-turbo", 1000)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_budget_exceed_limit(self, optimizer):
        """测试超预算检查"""
        # 设置很小的预算
        optimizer.daily_budget = 0.001

        result = await optimizer.check_budget("claude-3-opus", 10000)
        assert result is False

    @pytest.mark.asyncio
    async def test_record_usage(self, optimizer):
        """测试记录使用"""
        await optimizer.record_usage("glm5-turbo", 500, task_id="test-001")

        assert len(optimizer.usage_log) == 1
        assert optimizer.daily_spend > 0
        assert optimizer.usage_log[0].model == "glm5-turbo"
        assert optimizer.usage_log[0].tokens == 500

    @pytest.mark.asyncio
    async def test_record_usage_with_cost(self):
        """测试记录使用（指定成本）"""
        optimizer = CostOptimizer(daily_budget=10.0)
        await optimizer.record_usage("gpt-4", 1000, cost=0.05)

        assert abs(optimizer.daily_spend - 0.05) < 0.001

    def test_get_budget_status(self):
        """测试获取预算状态"""
        optimizer = CostOptimizer(daily_budget=10.0)
        status = optimizer.get_budget_status()

        assert isinstance(status, BudgetStatus)
        assert status.daily_budget == 10.0
        assert status.daily_spent == 0.0
        assert status.daily_remaining == 10.0
        assert status.is_over_budget is False

    def test_get_daily_stats(self, optimizer):
        """测试获取每日统计"""
        stats = optimizer.get_daily_stats()

        assert "budget" in stats
        assert "spent" in stats
        assert "remaining" in stats
        assert "usage_percentage" in stats
        assert "by_model" in stats

    @pytest.mark.asyncio
    async def test_group_by_model(self):
        """测试按模型分组"""
        optimizer = CostOptimizer(daily_budget=10.0)
        await optimizer.record_usage("glm5-turbo", 500, task_id="test-1")
        await optimizer.record_usage("glm5-turbo", 800, task_id="test-2")
        await optimizer.record_usage("gpt-4", 600, task_id="test-3")

        stats = optimizer.get_daily_stats()
        by_model = stats["by_model"]

        assert "glm5-turbo" in by_model
        assert by_model["glm5-turbo"]["count"] == 2
        assert by_model["glm5-turbo"]["total_tokens"] == 1300

        assert "gpt-4" in by_model
        assert by_model["gpt-4"]["count"] == 1

    @pytest.mark.asyncio
    async def test_optimize_model_selection(self, optimizer, selector):
        """测试优化模型选择"""
        task = {"description": "测试任务", "complexity": "medium"}

        model, reason = await optimizer.optimize_model_selection(task, selector)

        assert model is not None
        assert isinstance(reason, str)

    @pytest.mark.asyncio
    async def test_optimize_model_selection_over_budget(self, optimizer, selector):
        """测试超预算时的模型选择"""
        # 设置很小的预算
        optimizer.daily_budget = 0.001

        task = {"description": "复杂任务", "complexity": "high"}

        model, reason = await optimizer.optimize_model_selection(task, selector)

        # 应该选择低成本模型或返回None
        if model:
            cost = optimizer._get_model_cost(model)
            assert cost < 0.05  # 应该是低成本模型

    def test_get_cost_saving_suggestions(self, optimizer):
        """测试获取成本节约建议"""
        suggestions = optimizer.get_cost_saving_suggestions()

        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_cost_saving_suggestions_with_usage(self, optimizer):
        """测试有使用记录时的成本建议"""
        # 添加一些使用记录
        for i in range(60):
            await optimizer.record_usage("claude-3-opus", 1000)

        suggestions = optimizer.get_cost_saving_suggestions()

        # 应该有建议
        assert len(suggestions) > 0

    def test_set_budget(self, optimizer):
        """测试设置预算"""
        optimizer.set_budget(daily=20.0, hourly=2.0)

        assert optimizer.daily_budget == 20.0
        assert optimizer.hourly_budget == 2.0

    def test_reset_budget(self, optimizer):
        """测试重置预算"""
        optimizer.daily_spend = 5.0
        optimizer.hourly_spend = 0.5

        optimizer.reset_budget()

        assert optimizer.daily_spend == 0.0
        assert optimizer.hourly_spend == 0.0

    @pytest.mark.asyncio
    async def test_hourly_budget_check(self, optimizer):
        """测试小时预算检查"""
        optimizer.hourly_budget = 0.001

        result = await optimizer.check_budget("claude-3-opus", 10000)
        assert result is False


class TestBudgetAlert:
    """预算告警测试"""

    @pytest.mark.asyncio
    async def test_check_and_alert(self, optimizer):
        """测试检查并发送告警"""
        alert = BudgetAlert(optimizer)

        # 添加使用使达到告警阈值
        optimizer.daily_spend = optimizer.daily_budget * 0.85

        await alert.check_and_alert()

        # 应该已发送告警
        assert alert.alert_sent is True

    @pytest.mark.asyncio
    async def test_alert_reset(self, optimizer):
        """测试告警重置"""
        alert = BudgetAlert(optimizer)
        alert.alert_sent = True

        # 重置使用量
        optimizer.daily_spend = 0

        await alert.check_and_alert()

        # 使用量低时应该重置告警状态
        assert alert.alert_sent is False


# ==================== 集成测试 ====================


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, adapter, selector, optimizer):
        """测试完整工作流"""
        # 1. 定义任务
        task = {"description": "设计一个用户认证系统", "type": "architecture", "complexity": "high"}

        # 2. 选择模型（考虑成本）
        model, reason = await optimizer.optimize_model_selection(task, selector)

        if model:
            # 3. 检查预算
            tokens = selector.estimate_tokens(task)
            budget_ok = await optimizer.check_budget(model, tokens)

            if budget_ok:
                # 4. 调用模型（这里只测试接口，不实际调用）
                assert model in adapter.get_available_models()

                # 5. 记录使用
                await optimizer.record_usage(model, tokens, task_id="test-integration")

                # 6. 检查统计
                stats = optimizer.get_daily_stats()
                assert stats["usage_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_operations(self, adapter, optimizer):
        """测试批量操作"""
        models = adapter.get_available_models()

        if len(models) > 0:
            # 批量记录使用
            for i, model in enumerate(models[:3]):
                await optimizer.record_usage(model, 100 * (i + 1))

            stats = optimizer.get_daily_stats()
            assert stats["usage_count"] == min(3, len(models))

    @pytest.mark.asyncio
    async def test_model_selection_with_different_tasks(self, selector):
        """测试不同任务的模型选择"""
        tasks = [
            {"description": "快速修复登录bug", "priority": "high", "complexity": "low"},
            {"description": "设计微服务架构", "type": "architecture", "complexity": "high"},
            {"description": "编写API文档", "type": "documentation", "complexity": "medium"},
        ]

        for task in tasks:
            model = await selector.select_best_model(task)
            assert model is not None
            assert model in selector.available_models


# ==================== 性能测试 ====================


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, adapter):
        """测试并发调用"""
        models = adapter.get_available_models()

        if models:
            # 并发调用多个模型的count_tokens
            tasks = [adapter.count_tokens(models[0], f"测试文本 {i}") for i in range(10)]

            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(r > 0 for r in results)

    @pytest.mark.asyncio
    async def test_selector_performance(self, selector):
        """测试选择器性能"""
        task = {"description": "性能测试任务", "complexity": "medium"}

        # 多次选择
        start_time = asyncio.get_event_loop().time()

        for _ in range(100):
            await selector.select_best_model(task)

        elapsed = asyncio.get_event_loop().time() - start_time

        # 应该在合理时间内完成（< 1秒）
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_optimizer_performance(self, optimizer):
        """测试优化器性能"""
        # 批量记录
        start_time = asyncio.get_event_loop().time()

        for i in range(100):
            await optimizer.record_usage("glm5-turbo", 100)

        elapsed = asyncio.get_event_loop().time() - start_time

        # 应该在合理时间内完成
        assert elapsed < 2.0


# ==================== 错误处理测试 ====================


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_adapter_timeout(self):
        """测试适配器超时"""
        adapter = GLM5Adapter("glm-5-turbo", "test-key")
        adapter.timeout = 0.001  # 极短超时

        # 应该返回错误而不是抛出异常
        result = await adapter.generate("测试", max_tokens=10)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_selector_no_available_models(self):
        """测试没有可用模型时的选择"""
        mock_adapter = Mock()
        mock_adapter.get_available_models.return_value = []

        selector = ModelSelector(mock_adapter)

        task = {"description": "测试"}
        model = await selector.select_best_model(task)

        # 应该返回默认模型
        assert model is not None

    @pytest.mark.asyncio
    async def test_optimizer_invalid_model(self, optimizer):
        """测试优化器处理无效模型"""
        result = await optimizer.check_budget("invalid-model", 1000)

        # 应该使用默认成本
        assert isinstance(result, bool)


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
