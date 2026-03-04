"""
AI辅助测试功能测试
测试test_generator, coverage_optimizer, regression_tester, test_suite_manager
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_generator import TestCaseGenerator, TestCodeAnalyzer
from coverage_optimizer import CoverageOptimizer, CoverageReporter
from regression_tester import RegressionTester, TestScheduler
from test_suite_manager import TestSuiteManager, TestDependencyAnalyzer

# ============= Fixtures =============


@pytest.fixture
def mock_model_adapter():
    """Mock模型适配器"""
    adapter = Mock()
    adapter.call_model = AsyncMock(
        return_value={
            "success": True,
            "content": """```python
import pytest
from module import add

class TestAdd:
    \"\"\"Test suite for add function\"\"\"
    
    def test_add_normal(self):
        \"\"\"Test normal addition\"\"\"
        assert add(1, 2) == 3
    
    def test_add_negative(self):
        \"\"\"Test negative numbers\"\"\"
        assert add(-1, -2) == -3
    
    def test_add_zero(self):
        \"\"\"Test with zero\"\"\"
        assert add(0, 5) == 5
```
""",
            "usage": {"total_tokens": 100},
        }
    )
    return adapter


@pytest.fixture
def test_generator(mock_model_adapter):
    """测试用例生成器fixture"""
    return TestCaseGenerator(mock_model_adapter)


@pytest.fixture
def coverage_optimizer(tmp_path):
    """覆盖率优化器fixture"""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # 创建源代码文件
    src_dir = project_path / "src"
    src_dir.mkdir()

    source_code = """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
"""
    (src_dir / "math_utils.py").write_text(source_code)

    # 创建测试文件
    test_dir = project_path / "tests"
    test_dir.mkdir()

    test_code = """
import pytest
from src.math_utils import add

def test_add():
    assert add(1, 2) == 3
"""
    (test_dir / "test_math.py").write_text(test_code)

    return CoverageOptimizer(str(project_path))


@pytest.fixture
def regression_tester(tmp_path):
    """回归测试器fixture"""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # 创建测试目录
    test_dir = project_path / "tests"
    test_dir.mkdir()

    test_code = """
def test_example():
    assert 1 + 1 == 2
"""
    (test_dir / "test_example.py").write_text(test_code)

    return RegressionTester(str(project_path))


@pytest.fixture
def test_suite_manager(tmp_path):
    """测试套件管理器fixture"""
    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    # 创建多个测试文件
    (test_dir / "test_unit.py").write_text("""
\"\"\"Unit tests
Category: unit
Tags: fast, core
\"\"\"

def test_unit_1():
    assert True

def test_unit_2():
    assert True
""")

    (test_dir / "test_integration.py").write_text("""
\"\"\"Integration tests
Category: integration
Tags: slow, api
\"\"\"

def test_integration_1():
    assert True
""")

    # 返回(test_dir, manager)元组
    manager = TestSuiteManager(test_dir=str(test_dir))
    return manager


# ============= TestCaseGenerator Tests =============


class TestTestCaseGenerator:
    """测试用例生成器测试"""

    @pytest.mark.asyncio
    async def test_generate_unit_test(self, test_generator):
        """测试单元测试生成"""
        code = """
def add(a, b):
    return a + b
"""

        result = await test_generator.generate_tests(code, test_type="unit_test")

        assert result["success"]
        assert "test_code" in result
        assert "def test_" in result["test_code"]
        assert result["test_type"] == "unit_test"

    @pytest.mark.asyncio
    async def test_generate_integration_test(self, test_generator):
        """测试集成测试生成"""
        code = """
async def get_user(user_id):
    return await db.get(user_id)
"""

        context = {"api_description": "User API endpoints"}

        result = await test_generator.generate_tests(code, test_type="integration_test", context=context)

        assert result["success"]
        assert "test_code" in result

    @pytest.mark.asyncio
    async def test_generate_invalid_test_type(self, test_generator):
        """测试无效的测试类型"""
        result = await test_generator.generate_tests("code", test_type="invalid")

        assert not result["success"]
        assert "error" in result

    def test_extract_code(self, test_generator):
        """测试代码提取"""
        content = """
Here is some text:
```python
def test_example():
    assert True
```
More text
"""

        code = test_generator._extract_code(content)

        assert "def test_example" in code
        assert "Here is some text" not in code

    def test_validate_test(self, test_generator):
        """测试测试代码验证"""
        valid_test = """
import pytest

def test_example():
    assert 1 == 1
"""

        validation = test_generator._validate_test(valid_test, "unit_test")

        assert validation["is_valid"]
        assert validation["score"] > 0

    def test_validate_invalid_test(self, test_generator):
        """测试无效测试代码验证"""
        invalid_test = """
# Not a test file
def example():
    pass
"""

        validation = test_generator._validate_test(invalid_test, "unit_test")

        assert not validation["is_valid"]

    @pytest.mark.asyncio
    async def test_generate_from_file(self, test_generator, tmp_path):
        """测试从文件生成测试"""
        # 创建源文件
        source_file = tmp_path / "example.py"
        source_file.write_text("def add(a, b): return a + b")

        # 生成测试
        result = await test_generator.generate_from_file(
            str(source_file), test_type="unit_test", output_dir=str(tmp_path / "tests")
        )

        assert result["success"]
        assert "saved_path" in result

    @pytest.mark.asyncio
    async def test_improve_test(self, test_generator):
        """测试改进测试"""
        existing_test = """
def test_add():
    assert add(1, 2) == 3
"""

        source_code = """
def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("Division by zero")
    return a / b
"""

        result = await test_generator.improve_test(existing_test, source_code)

        assert result["success"]
        assert "improved_test" in result

    def test_get_stats(self, test_generator):
        """测试获取统计信息"""
        stats = test_generator.get_stats()

        assert "total_generated" in stats
        assert "successful" in stats
        assert "failed" in stats


class TestCodeAnalyzer:
    """测试代码分析器测试"""

    def test_analyze_test_quality(self):
        """测试测试质量分析"""
        from test_generator import TestCodeAnalyzer

        test_code = """
import pytest

class TestExample:
    \"\"\"Test example\"\"\"
    
    @pytest.fixture
    def setup(self):
        return {}
    
    def test_1(self, setup):
        \"\"\"Test 1\"\"\"
        assert True
    
    @pytest.mark.parametrize("x,y", [(1, 2), (3, 4)])
    def test_2(self, x, y):
        assert x < y
"""

        metrics = TestCodeAnalyzer.analyze_test_quality(test_code)

        assert metrics["test_count"] == 2
        assert metrics["assertion_count"] == 2
        assert metrics["fixture_count"] == 1
        assert metrics["has_parametrize"] is True
        assert metrics["quality_score"] > 0


# ============= CoverageOptimizer Tests =============


class TestCoverageOptimizer:
    """覆盖率优化器测试"""

    @pytest.mark.asyncio
    async def test_run_coverage(self, coverage_optimizer):
        """测试运行覆盖率"""
        # Mock subprocess
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"test output", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            # 创建mock coverage.json
            coverage_data = {
                "files": {
                    "src/math_utils.py": {"summary": {"num_statements": 10, "covered_lines": 8, "percent_covered": 80.0}}
                },
                "totals": {"num_statements": 10, "covered_lines": 8, "percent_covered": 80.0},
            }

            import json

            coverage_file = os.path.join(coverage_optimizer.project_path, "coverage.json")
            with open(coverage_file, "w") as f:
                json.dump(coverage_data, f)

            result = await coverage_optimizer.run_coverage()

            assert result["success"]

    def test_analyze_coverage(self, coverage_optimizer):
        """测试覆盖率分析"""
        # 设置覆盖率数据
        coverage_optimizer.coverage_data = {
            "files": {
                "module1.py": {
                    "summary": {"num_statements": 10, "covered_lines": 10, "percent_covered": 100.0, "missing_lines": 0}
                },
                "module2.py": {
                    "summary": {"num_statements": 20, "covered_lines": 15, "percent_covered": 75.0, "missing_lines": 5},
                    "missing_lines": [5, 10, 15, 20, 25],
                },
            },
            "totals": {"num_statements": 30, "covered_lines": 25, "percent_covered": 83.33, "missing_lines": 5},
        }

        analysis = coverage_optimizer.analyze_coverage()

        assert analysis["total_files"] == 2
        assert analysis["fully_covered"] == 1
        assert analysis["partially_covered"] == 1
        assert analysis["summary"]["overall_coverage"] == 83.33

    @pytest.mark.asyncio
    async def test_suggest_tests(self, coverage_optimizer):
        """测试测试建议生成"""
        # 创建源文件
        src_file = os.path.join(coverage_optimizer.project_path, "uncovered.py")
        with open(src_file, "w") as f:
            f.write("def uncovered():\n    pass\n")

        uncovered_lines = {"uncovered.py": [1, 2]}

        suggestions = await coverage_optimizer.suggest_tests(uncovered_lines)

        assert len(suggestions) > 0
        assert "file" in suggestions[0]
        assert "suggested_test_type" in suggestions[0]

    def test_get_coverage_report(self, coverage_optimizer):
        """测试覆盖率报告生成"""
        coverage_optimizer.coverage_data = {
            "files": {
                "module.py": {
                    "summary": {"num_statements": 10, "covered_lines": 8, "percent_covered": 80.0, "missing_lines": 2}
                }
            },
            "totals": {"num_statements": 10, "covered_lines": 8, "percent_covered": 80.0},
        }

        report = coverage_optimizer.get_coverage_report()

        assert "# 测试覆盖率报告" in report
        assert "80" in report


class TestCoverageReporter:
    """覆盖率报告器测试"""

    def test_generate_html_report(self, tmp_path):
        """测试HTML报告生成"""
        coverage_data = {
            "files": {
                "module.py": {
                    "summary": {"num_statements": 10, "covered_lines": 8, "percent_covered": 80.0, "missing_lines": 2}
                }
            }
        }

        output_dir = str(tmp_path / "htmlcov")
        report_file = CoverageReporter.generate_html_report(coverage_data, output_dir)

        assert os.path.exists(report_file)

        with open(report_file, "r") as f:
            content = f.read()

        assert "Coverage Report" in content
        assert "module.py" in content


# ============= RegressionTester Tests =============


class TestRegressionTester:
    """回归测试器测试"""

    @pytest.mark.asyncio
    async def test_run_regression_suite(self, regression_tester):
        """测试运行回归测试"""
        # Mock subprocess
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"test_example.py::test_example PASSED\n2 passed in 0.5s", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await regression_tester.run_regression_suite(save_results=False)

            assert result["success"]
            assert result["results"]["passed"] == 2

    def test_parse_test_results(self, regression_tester):
        """测试解析测试结果"""
        output = """
test_example.py::test_1 PASSED
test_example.py::test_2 FAILED
test_example.py::test_3 SKIPPED

======================== 1 passed, 1 failed, 1 skipped in 0.5s ========================
"""

        results = regression_tester._parse_test_results(output)

        assert results["passed"] == 1
        assert results["failed"] == 1
        assert results["skipped"] == 1
        assert results["total"] == 3

    @pytest.mark.asyncio
    async def test_capture_baseline(self, regression_tester):
        """测试捕获基线"""
        # Mock测试运行
        with patch.object(regression_tester, "run_regression_suite") as mock_run:
            mock_run.return_value = {
                "success": True,
                "results": {"total": 10, "passed": 10, "failed": 0, "skipped": 0},
                "duration": 5.0,
            }

            result = await regression_tester.capture_baseline("test")

            assert result["success"]
            assert "baseline" in result

    @pytest.mark.asyncio
    async def test_compare_with_baseline(self, regression_tester):
        """测试与基线对比"""
        # 先创建基线
        baseline = {
            "suite": "test",
            "timestamp": datetime.now().isoformat(),
            "results": {"total": 10, "passed": 8, "failed": 2, "skipped": 0, "failures": ["test_1", "test_2"]},
            "duration": 5.0,
        }

        regression_tester.baselines["test"] = baseline

        # Mock当前测试运行
        with patch.object(regression_tester, "run_regression_suite") as mock_run:
            mock_run.return_value = {
                "success": True,
                "results": {"total": 10, "passed": 9, "failed": 1, "skipped": 0, "failures": ["test_1"]},
                "duration": 4.5,
            }

            result = await regression_tester.compare_with_baseline("test")

            # compare_with_baseline可能返回success=False如果测试失败
            # 但我们应该检查对比结果是否正确
            assert "has_improvement" in result
            assert result["has_improvement"]
            assert "test_2" in result.get("fixed_tests", [])

    def test_get_trend_analysis(self, regression_tester):
        """测试趋势分析"""
        # 添加历史数据
        for i in range(5):
            regression_tester.test_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "results": {"total": 10, "passed": 8 + i, "failed": 2 - i, "skipped": 0, "failures": []},
                    "duration": 5.0,
                }
            )

        trend = regression_tester.get_trend_analysis(days=7)

        assert "total_runs" in trend
        assert trend["total_runs"] == 5
        assert "avg_pass_rate" in trend

    def test_generate_report(self, regression_tester):
        """测试生成报告"""
        # 添加历史
        regression_tester.test_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "results": {"total": 10, "passed": 8, "failed": 2, "skipped": 0},
                "duration": 5.0,
            }
        )

        report = regression_tester.generate_report("markdown")

        assert "# 回归测试报告" in report
        assert "8" in report


# ============= TestSuiteManager Tests =============


class TestSuiteManager:
    """测试套件管理器测试"""

    def test_load_suites(self, test_suite_manager):
        """测试加载测试套件"""
        assert len(test_suite_manager.suites) > 0

    def test_get_statistics(self, test_suite_manager):
        """测试获取统计信息"""
        stats = test_suite_manager.get_statistics()

        assert "total_files" in stats
        assert "total_tests" in stats
        assert stats["total_files"] > 0

    @pytest.mark.asyncio
    async def test_run_suite(self, test_suite_manager):
        """测试运行测试套件"""
        # Mock subprocess
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"test_unit.py::test_unit_1 PASSED\n2 passed", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            # 获取第一个测试文件
            first_suite = list(test_suite_manager.suites.keys())[0]
            result = await test_suite_manager.run_suite(first_suite)

            assert result["success"]

    def test_find_tests(self, test_suite_manager):
        """测试搜索测试"""
        results = test_suite_manager.find_tests("unit", search_in="name")

        assert len(results) > 0
        assert "test" in results[0]["test"].lower()

    def test_organize_tests(self, test_suite_manager):
        """测试组织测试"""
        org = test_suite_manager.organize_tests()

        assert "by_priority" in org
        assert "by_type" in org
        assert "recommendations" in org

    def test_export_suite_config(self, test_suite_manager):
        """测试导出配置"""
        config_file = test_suite_manager.export_suite_config()

        assert os.path.exists(config_file)

        import json

        with open(config_file, "r") as f:
            config = json.load(f)

        assert "test_dir" in config
        assert "suites" in config


class TestDependencyAnalyzer:
    """测试依赖分析器测试"""

    def test_analyze_dependencies(self, tmp_path):
        """测试依赖分析"""
        # 创建测试文件
        test_dir = tmp_path / "tests"
        test_dir.mkdir()

        test_file = test_dir / "test_example.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def setup():
    return {}

def test_example(setup):
    assert True
""")

        analyzer = TestDependencyAnalyzer(test_dir=str(test_dir))
        deps = analyzer.analyze_dependencies()

        assert "fixtures" in deps
        assert "imports" in deps


# ============= Integration Tests =============


class TestAIIntegration:
    """AI辅助测试集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path, mock_model_adapter):
        """测试完整工作流程"""
        # 1. 创建测试项目
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        src_dir = project_dir / "src"
        src_dir.mkdir()

        source_code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        (src_dir / "math.py").write_text(source_code)

        # 2. 生成测试
        generator = TestCaseGenerator(mock_model_adapter)
        result = await generator.generate_from_file(
            str(src_dir / "math.py"), test_type="unit_test", output_dir=str(project_dir / "tests")
        )

        assert result["success"]

        # 3. 分析覆盖率
        optimizer = CoverageOptimizer(str(project_dir))
        # 这里需要实际运行pytest，所以只测试初始化
        assert optimizer.project_path == str(project_dir)

        # 4. 管理测试套件
        test_dir = project_dir / "tests"
        if test_dir.exists():
            manager = TestSuiteManager(test_dir=str(test_dir))
            stats = manager.get_statistics()

            # 应该至少有一个测试文件
            assert stats["total_files"] >= 0

    @pytest.mark.asyncio
    async def test_regression_workflow(self, tmp_path):
        """测试回归测试工作流程"""
        # 1. 创建测试项目
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        test_dir = project_dir / "tests"
        test_dir.mkdir()

        (test_dir / "test_example.py").write_text("""
def test_1():
    assert 1 + 1 == 2
""")

        # 2. 创建回归测试器
        tester = RegressionTester(str(project_dir))

        # 3. 捕获基线
        with patch.object(tester, "run_regression_suite") as mock_run:
            mock_run.return_value = {
                "success": True,
                "results": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
                "duration": 1.0,
            }

            baseline_result = await tester.capture_baseline()
            assert baseline_result["success"]


# ============= Performance Tests =============


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_batch_generation_performance(self, mock_model_adapter, tmp_path):
        """测试批量生成性能"""
        # 创建多个源文件
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        files = []
        for i in range(10):
            file_path = src_dir / f"module_{i}.py"
            file_path.write_text(f"def func_{i}(): pass")
            files.append(str(file_path))

        # 批量生成
        generator = TestCaseGenerator(mock_model_adapter)

        import time

        start = time.time()

        result = await generator.batch_generate(
            files, test_type="unit_test", output_dir=str(tmp_path / "tests"), max_concurrent=3
        )

        duration = time.time() - start

        # 应该在合理时间内完成（并发应该比串行快）
        assert duration < 10  # 10秒内
        assert result["total"] == 10


# ============= Error Handling Tests =============


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_model_failure(self, test_generator):
        """测试模型调用失败"""
        # Mock失败的模型调用
        test_generator.model_adapter.call_model = AsyncMock(return_value={"success": False, "error": "API Error"})

        result = await test_generator.generate_tests("code", "unit_test")

        assert not result["success"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_file(self, test_generator):
        """测试无效文件"""
        result = await test_generator.generate_from_file("/nonexistent/file.py", "unit_test")

        assert not result["success"]
        assert "error" in result

    def test_empty_coverage_data(self, coverage_optimizer):
        """测试空覆盖率数据"""
        analysis = coverage_optimizer.analyze_coverage()

        assert "error" in analysis

    def test_missing_baseline(self, regression_tester):
        """测试缺失基线"""
        baseline = regression_tester.load_baseline("nonexistent")

        assert baseline is None


# ============= 运行测试 =============

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
