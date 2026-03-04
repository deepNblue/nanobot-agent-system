"""
PR管理器测试
测试PR自动创建、监控、合并等功能
"""

import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from pr_manager import PRManager, get_pr_manager


class TestPRManager:
    """PR管理器测试"""

    @pytest.fixture
    def pr_manager(self):
        """创建PR管理器实例"""
        config = {
            "auto_merge": False,
            "merge_method": "squash",
            "require_review": True,
            "require_ci": True,
            "min_review_score": 80,
        }

        return PRManager(config)

    @pytest.fixture
    def sample_task(self):
        """示例任务数据"""
        return {
            "id": "task_test_001",
            "description": "实现用户头像上传功能",
            "type": "feature",
            "agent": "GLM5-Turbo",
            "complexity": "Medium",
            "priority": "High",
            "status": "completed",
            "branch": "feature/task_test_001",
            "baseBranch": "main",
            "review_score": 85,
            "ci_passed": True,
            "security_passed": True,
            "performance_passed": True,
            "stats": {"unit_tests": "15/15 通过", "integration_tests": "5/5 通过", "coverage": 92},
        }

    # ==================== PR标题和描述生成测试 ====================

    def test_generate_pr_title_feature(self, pr_manager):
        """测试PR标题生成 - Feature类型"""
        task = {"type": "feature", "description": "实现用户头像上传功能"}

        title = pr_manager.generate_pr_title(task)

        assert "[Agent] Feature:" in title
        assert "实现用户头像上传功能" in title

    def test_generate_pr_title_bugfix(self, pr_manager):
        """测试PR标题生成 - Bugfix类型"""
        task = {"type": "bugfix", "description": "修复登录超时问题"}

        title = pr_manager.generate_pr_title(task)

        assert "[Agent] Bugfix:" in title
        assert "修复登录超时问题" in title

    def test_generate_pr_title_refactor(self, pr_manager):
        """测试PR标题生成 - Refactor类型"""
        task = {"type": "refactor", "description": "优化数据库查询性能"}

        title = pr_manager.generate_pr_title(task)

        assert "[Agent] Refactor:" in title
        assert "优化数据库查询性能" in title

    def test_generate_pr_title_long_description(self, pr_manager):
        """测试PR标题生成 - 长描述截断"""
        task = {
            "type": "feature",
            "description": "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的描述",
        }

        title = pr_manager.generate_pr_title(task)

        assert len(title) <= 100  # 标题不应太长
        assert "..." in title  # 应该被截断

    def test_generate_pr_body(self, pr_manager, sample_task):
        """测试PR描述生成"""
        body = pr_manager.generate_pr_body(sample_task)

        # 检查必要信息
        assert "task_test_001" in body
        assert "GLM5-Turbo" in body
        assert "实现用户头像上传功能" in body
        assert "Medium" in body
        assert "High" in body
        assert "15/15 通过" in body
        assert "92%" in body
        assert "85/100" in body
        assert "✅ 通过" in body
        assert "Nanobot AI Agent" in body

    def test_generate_pr_body_with_stats(self, pr_manager):
        """测试PR描述生成 - 包含统计信息"""
        task = {
            "id": "task_stats",
            "description": "测试任务",
            "stats": {"unit_tests": "20/20 通过", "integration_tests": "10/10 通过", "coverage": 95},
        }

        body = pr_manager.generate_pr_body(task)

        assert "20/20 通过" in body
        assert "10/10 通过" in body
        assert "95%" in body

    # ==================== 标签生成测试 ====================

    def test_get_task_tags_feature(self, pr_manager):
        """测试标签生成 - Feature类型"""
        task = {"type": "feature", "priority": "high", "complexity": "medium", "agent": "GLM5-Turbo"}

        tags = pr_manager._get_task_tags(task)

        assert "agent-generated" in tags
        assert "feature" in tags
        assert "priority-high" in tags
        assert "complexity-medium" in tags
        assert "agent-glm5-turbo" in tags

    def test_get_task_tags_bugfix(self, pr_manager):
        """测试标签生成 - Bugfix类型"""
        task = {"type": "bugfix", "priority": "critical", "complexity": "high", "agent": "Claude"}

        tags = pr_manager._get_task_tags(task)

        assert "bugfix" in tags
        assert "priority-high" in tags
        assert "complexity-high" in tags

    # ==================== PR编号提取测试 ====================

    def test_extract_pr_number_from_url(self, pr_manager):
        """测试从URL提取PR编号"""
        output = "https://github.com/deepNblue/nanobot-agent-system/pull/123"

        pr_number = pr_manager.extract_pr_number(output)

        assert pr_number == 123

    def test_extract_pr_number_from_number(self, pr_manager):
        """测试从数字提取PR编号"""
        output = "123"

        pr_number = pr_manager.extract_pr_number(output)

        assert pr_number == 123

    def test_extract_pr_number_invalid(self, pr_manager):
        """测试无效PR编号提取"""
        output = "invalid output"

        with pytest.raises(ValueError):
            pr_manager.extract_pr_number(output)

    # ==================== 合并阻止原因测试 ====================

    def test_get_merge_block_reason_review_not_approved(self, pr_manager):
        """测试合并阻止原因 - Review未通过"""
        status = {
            "review": {"approved": False, "decision": "CHANGES_REQUESTED"},
            "ci": {"success": True},
            "mergeable": True,
            "merge_state": "CLEAN",
        }

        reason = pr_manager.get_merge_block_reason(status)

        assert "Code Review" in reason

    def test_get_merge_block_reason_ci_failed(self, pr_manager):
        """测试合并阻止原因 - CI失败"""
        status = {"review": {"approved": True}, "ci": {"success": False}, "mergeable": True, "merge_state": "CLEAN"}

        reason = pr_manager.get_merge_block_reason(status)

        assert "CI" in reason

    def test_get_merge_block_reason_conflicts(self, pr_manager):
        """测试合并阻止原因 - 合并冲突"""
        status = {"review": {"approved": True}, "ci": {"success": True}, "mergeable": False, "merge_state": "DIRTY"}

        reason = pr_manager.get_merge_block_reason(status)

        assert "冲突" in reason

    def test_get_merge_block_reason_multiple(self, pr_manager):
        """测试合并阻止原因 - 多个原因"""
        status = {
            "review": {"approved": False, "decision": "PENDING"},
            "ci": {"success": False},
            "mergeable": False,
            "merge_state": "BLOCKED",
        }

        reason = pr_manager.get_merge_block_reason(status)

        assert "Code Review" in reason
        assert "CI" in reason
        assert "冲突" in reason

    # ==================== 任务统计测试 ====================

    def test_get_task_stats_default(self, pr_manager):
        """测试任务统计 - 默认值"""
        task = {}

        stats = pr_manager._get_task_stats(task)

        assert "unit_tests" in stats
        assert "integration_tests" in stats
        assert "coverage" in stats

    def test_get_task_stats_custom(self, pr_manager):
        """测试任务统计 - 自定义值"""
        task = {"stats": {"unit_tests": "30/30 通过", "coverage": 98}}

        stats = pr_manager._get_task_stats(task)

        assert stats["unit_tests"] == "30/30 通过"
        assert stats["coverage"] == 98

    # ==================== PR报告生成测试 ====================

    def test_generate_pr_report(self, pr_manager):
        """测试PR报告生成"""
        pr_number = 123

        # 模拟缓存状态
        pr_manager._pr_cache[pr_number] = {
            "pr_number": pr_number,
            "title": "Test PR",
            "state": "OPEN",
            "branch": "feature/test",
            "base_branch": "main",
            "url": "https://github.com/test/test/pull/123",
            "review": {"decision": "APPROVED", "approved": True},
            "ci": {"success": True, "total": 5, "completed": 5},
            "mergeable": True,
            "merge_state": "CLEAN",
            "ready_to_merge": True,
        }

        report = pr_manager.generate_pr_report(pr_number)

        assert "# PR #123" in report
        assert "Test PR" in report
        assert "OPEN" in report
        assert "feature/test" in report
        assert "✅" in report

    # ==================== 异步测试 ====================

    @pytest.mark.asyncio
    async def test_load_task(self, pr_manager, sample_task, tmp_path):
        """测试加载任务"""
        # 创建临时任务文件
        task_file = pr_manager.tasks_dir / f"{sample_task['id']}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(sample_task, f)

        # 加载任务
        task = await pr_manager.load_task(sample_task["id"])

        assert task is not None
        assert task["id"] == sample_task["id"]
        assert task["description"] == sample_task["description"]

    @pytest.mark.asyncio
    async def test_load_task_not_found(self, pr_manager):
        """测试加载不存在的任务"""
        task = await pr_manager.load_task("non_existent_task")

        assert task is None

    @pytest.mark.asyncio
    async def test_save_task(self, pr_manager, sample_task):
        """测试保存任务"""
        await pr_manager.save_task(sample_task)

        # 验证文件已创建
        task_file = pr_manager.tasks_dir / f"{sample_task['id']}.json"
        assert task_file.exists()

        # 验证内容
        with open(task_file, "r", encoding="utf-8") as f:
            saved_task = json.load(f)

        assert saved_task["id"] == sample_task["id"]

    @pytest.mark.asyncio
    async def test_run_command_success(self, pr_manager):
        """测试命令执行 - 成功"""
        result = await pr_manager.run_command("echo 'test'")

        assert result["success"] is True
        assert "test" in result["output"]

    @pytest.mark.asyncio
    async def test_run_command_failure(self, pr_manager):
        """测试命令执行 - 失败"""
        result = await pr_manager.run_command("nonexistent_command_12345")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_find_task_by_pr(self, pr_manager, sample_task):
        """测试根据PR查找任务"""
        # 添加PR信息
        sample_task["pr"] = {"number": 123, "url": "https://github.com/test/test/pull/123"}

        # 保存任务
        await pr_manager.save_task(sample_task)

        # 查找任务
        task = await pr_manager.find_task_by_pr(123)

        assert task is not None
        assert task["id"] == sample_task["id"]

    @pytest.mark.asyncio
    async def test_find_task_by_pr_not_found(self, pr_manager):
        """测试根据PR查找不存在的任务"""
        task = await pr_manager.find_task_by_pr(999)

        assert task is None

    # ==================== 集成测试（需要mock） ====================

    @pytest.mark.asyncio
    async def test_auto_create_pr_task_not_completed(self, pr_manager, sample_task):
        """测试自动创建PR - 任务未完成"""
        sample_task["status"] = "running"
        await pr_manager.save_task(sample_task)

        result = await pr_manager.auto_create_pr(sample_task["id"])

        assert result["success"] is False
        assert "未完成" in result["error"]

    @pytest.mark.asyncio
    async def test_auto_create_pr_review_not_passed(self, pr_manager, sample_task):
        """测试自动创建PR - Code Review未通过"""
        sample_task["review_score"] = 70  # 低于阈值
        await pr_manager.save_task(sample_task)

        result = await pr_manager.auto_create_pr(sample_task["id"])

        assert result["success"] is False
        assert "Code Review" in result["error"]

    @pytest.mark.asyncio
    async def test_auto_create_pr_ci_not_passed(self, pr_manager, sample_task):
        """测试自动创建PR - CI未通过"""
        sample_task["ci_passed"] = False
        await pr_manager.save_task(sample_task)

        result = await pr_manager.auto_create_pr(sample_task["id"])

        assert result["success"] is False
        assert "CI" in result["error"]

    @pytest.mark.asyncio
    async def test_auto_create_pr_no_branch(self, pr_manager, sample_task):
        """测试自动创建PR - 没有分支"""
        del sample_task["branch"]
        await pr_manager.save_task(sample_task)

        result = await pr_manager.auto_create_pr(sample_task["id"])

        assert result["success"] is False
        assert "分支" in result["error"]

    # ==================== 边界条件测试 ====================

    def test_generate_pr_title_empty_description(self, pr_manager):
        """测试PR标题生成 - 空描述"""
        task = {"type": "feature", "description": ""}

        title = pr_manager.generate_pr_title(task)

        assert "[Agent] Feature:" in title

    def test_generate_pr_title_special_characters(self, pr_manager):
        """测试PR标题生成 - 特殊字符"""
        task = {"type": "feature", "description": "实现功能 <script>alert('xss')</script>"}

        title = pr_manager.generate_pr_title(task)

        # 确保标题被正确处理（可能需要转义）
        assert "[Agent] Feature:" in title

    def test_get_merge_block_reason_all_passed(self, pr_manager):
        """测试合并阻止原因 - 全部通过"""
        status = {"review": {"approved": True}, "ci": {"success": True}, "mergeable": True, "merge_state": "CLEAN"}

        reason = pr_manager.get_merge_block_reason(status)

        # 全部通过时应该返回"未知原因"或空
        assert reason in ["未知原因", ""]

    # ==================== 配置测试 ====================

    def test_pr_manager_config_default(self):
        """测试PR管理器默认配置"""
        manager = PRManager()

        assert manager.auto_merge_enabled is False
        assert manager.merge_method == "squash"
        assert manager.require_review is True
        assert manager.require_ci is True
        assert manager.min_review_score == 80

    def test_pr_manager_config_custom(self):
        """测试PR管理器自定义配置"""
        config = {
            "auto_merge": True,
            "merge_method": "merge",
            "require_review": False,
            "require_ci": False,
            "min_review_score": 70,
        }

        manager = PRManager(config)

        assert manager.auto_merge_enabled is True
        assert manager.merge_method == "merge"
        assert manager.require_review is False
        assert manager.require_ci is False
        assert manager.min_review_score == 70

    # ==================== 单例测试 ====================

    def test_get_pr_manager_singleton(self):
        """测试PR管理器单例"""
        manager1 = get_pr_manager()
        manager2 = get_pr_manager()

        assert manager1 is manager2


class TestPRManagerIntegration:
    """PR管理器集成测试（需要GitHub CLI）"""

    @pytest.fixture
    def pr_manager(self):
        """创建PR管理器实例"""
        return PRManager()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not Path.home().joinpath(".config/gh/hosts.yml").exists(), reason="需要GitHub CLI认证")
    async def test_list_prs(self, pr_manager):
        """测试列出PR（集成测试）"""
        result = await pr_manager.list_prs(state="open", limit=5)

        assert result["success"] is True
        assert "prs" in result

    @pytest.mark.asyncio
    @pytest.mark.skipif(not Path.home().joinpath(".config/gh/hosts.yml").exists(), reason="需要GitHub CLI认证")
    async def test_monitor_pr_status(self, pr_manager):
        """测试监控PR状态（集成测试）"""
        # 使用一个存在的PR编号
        pr_number = 1

        result = await pr_manager.monitor_pr_status(pr_number)

        # 检查返回的结构
        assert "pr_number" in result
        assert result["pr_number"] == pr_number


# ==================== 性能测试 ====================


class TestPRManagerPerformance:
    """PR管理器性能测试"""

    @pytest.fixture
    def pr_manager(self):
        """创建PR管理器实例"""
        return PRManager()

    def test_generate_pr_title_performance(self, pr_manager):
        """测试PR标题生成性能"""
        task = {"type": "feature", "description": "测试性能"}

        # 执行1000次
        import time

        start = time.time()

        for _ in range(1000):
            pr_manager.generate_pr_title(task)

        elapsed = time.time() - start

        # 应该在1秒内完成
        assert elapsed < 1.0

    def test_generate_pr_body_performance(self, pr_manager):
        """测试PR描述生成性能"""
        task = {
            "id": "test",
            "description": "测试性能",
            "agent": "GLM5-Turbo",
            "stats": {"unit_tests": "10/10 通过", "coverage": 90},
        }

        # 执行1000次
        import time

        start = time.time()

        for _ in range(1000):
            pr_manager.generate_pr_body(task)

        elapsed = time.time() - start

        # 应该在1秒内完成
        assert elapsed < 1.0


# ==================== 运行测试 ====================

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
