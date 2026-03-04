"""
Code Review 和 CI/CD 集成测试

测试用例：
1. 测试Code Review评分逻辑
2. 测试CI状态检查
3. 测试CI失败分析
4. 测试CI重试
5. 测试完整工作流
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

# 导入模块
try:
    from code_reviewer import get_code_reviewer, CodeReviewer
    from cicd_integration import get_cicd_integration, CICDIntegration
    from nanobot_scheduler_enhanced import get_orchestrator_enhanced
except ImportError:
    print("请确保在正确的目录下运行此脚本")
    exit(1)


class TestCodeReview:
    """Code Review测试类"""

    def __init__(self):
        self.reviewer = get_code_reviewer()
        self.test_results = []

    async def test_security_check(self):
        """测试1: 安全检查"""
        print("\n=== 测试1: 安全检查 ===")

        # 包含安全问题的代码
        code_with_issues = """
password = "secret123"
api_key = "sk-1234567890"

def unsafe_query(user_input):
    cursor.execute("SELECT * FROM users WHERE id = " + user_input)
    eval(user_input)
    subprocess.run(user_input, shell=True)
"""

        # 检查安全问题
        security_issues = self.reviewer._check_security(code_with_issues)

        print(f"发现 {len(security_issues)} 个安全问题:")
        for issue in security_issues:
            print(f"  - [{issue['severity']}] {issue['message']}")

        # 验证
        assert len(security_issues) > 0, "应该检测到安全问题"
        assert any(i["severity"] == "high" for i in security_issues), "应该有高危问题"

        self.test_results.append({"test": "security_check", "status": "passed", "issues_found": len(security_issues)})

        print("✅ 安全检查测试通过")

    async def test_performance_check(self):
        """测试2: 性能检查"""
        print("\n=== 测试2: 性能检查 ===")

        # 包含性能问题的代码
        code_with_issues = """
def process_items(items):
    result = ""
    for i in range(len(items)):
        result += str(items[i])
    return result

from module import *
"""

        # 检查性能问题
        performance_issues = self.reviewer._check_performance(code_with_issues)

        print(f"发现 {len(performance_issues)} 个性能问题:")
        for issue in performance_issues:
            print(f"  - [{issue['severity']}] {issue['message']}")

        # 验证
        assert len(performance_issues) > 0, "应该检测到性能问题"

        self.test_results.append({"test": "performance_check", "status": "passed", "issues_found": len(performance_issues)})

        print("✅ 性能检查测试通过")

    async def test_code_quality_check(self):
        """测试3: 代码质量检查"""
        print("\n=== 测试3: 代码质量检查 ===")

        # 包含质量问题的代码
        code_with_issues = """
def process_data():
    # TODO: 需要优化这个函数
    # FIXME: 这里有bug
    very_long_line = "这是一个超过100字符的长行，应该被检测出来........................................................................"
    pass
"""

        # 检查代码质量
        quality_issues = self.reviewer._check_code_quality(code_with_issues)

        print(f"发现 {len(quality_issues)} 个质量问题:")
        for issue in quality_issues:
            print(f"  - [{issue['severity']}] {issue['message']}")

        # 验证
        assert len(quality_issues) > 0, "应该检测到质量问题"

        self.test_results.append({"test": "code_quality_check", "status": "passed", "issues_found": len(quality_issues)})

        print("✅ 代码质量检查测试通过")

    async def test_score_calculation(self):
        """测试4: 评分计算"""
        print("\n=== 测试4: 评分计算 ===")

        # 测试不同场景的评分
        test_cases = [
            {"name": "优秀代码", "llm_score": 95, "static_score": 98, "test_score": 92, "expected_range": (90, 100)},
            {"name": "良好代码", "llm_score": 85, "static_score": 88, "test_score": 82, "expected_range": (80, 89)},
            {"name": "一般代码", "llm_score": 75, "static_score": 72, "test_score": 78, "expected_range": (70, 79)},
            {"name": "较差代码", "llm_score": 60, "static_score": 65, "test_score": 70, "expected_range": (0, 69)},
        ]

        for case in test_cases:
            score = self.reviewer.calculate_score(
                {"score": case["llm_score"]}, {"score": case["static_score"]}, {"score": case["test_score"]}
            )

            min_score, max_score = case["expected_range"]
            in_range = min_score <= score <= max_score

            print(f"{case['name']}: {score}/100 {'✅' if in_range else '❌'}")

            assert in_range, f"评分 {score} 应该在 {min_score}-{max_score} 范围内"

        self.test_results.append({"test": "score_calculation", "status": "passed", "cases_tested": len(test_cases)})

        print("✅ 评分计算测试通过")

    async def test_comment_generation(self):
        """测试5: 评论生成"""
        print("\n=== 测试5: 评论生成 ===")

        # 模拟审查结果
        llm_review = {
            "score": 75,
            "details": {
                "security": [{"severity": "high", "message": "硬编码密码", "line": 10}],
                "performance": [{"severity": "medium", "message": "循环中字符串拼接", "line": 20}],
            },
            "suggestions": ["建议使用更安全的密码存储方式"],
        }

        static_review = {"score": 80, "details": [{"tool": "flake8", "error_count": 3, "errors": ["E501 line too long"]}]}

        test_review = {"score": 70, "new_coverage": 65}

        # 生成评论
        comments = self.reviewer.generate_comments(llm_review, static_review, test_review)

        print(f"生成了 {len(comments)} 条评论:")
        for comment in comments:
            print(f"  - [{comment['type']}] {comment['message']}")

        # 验证
        assert len(comments) > 0, "应该生成评论"
        assert any(c["type"] == "security" for c in comments), "应该包含安全评论"

        self.test_results.append({"test": "comment_generation", "status": "passed", "comments_generated": len(comments)})

        print("✅ 评论生成测试通过")


class TestCICDIntegration:
    """CI/CD集成测试类"""

    def __init__(self):
        self.cicd = get_cicd_integration()
        self.test_results = []

    async def test_ci_status_check(self):
        """测试6: CI状态检查"""
        print("\n=== 测试6: CI状态检查 ===")

        # 测试不存在的分支（应该返回no_runs）
        status = await self.cicd.check_ci_status("non-existent-branch-12345")

        print(f"CI状态: {status.get('status', 'unknown')}")

        # 验证基本结构
        assert "success" in status, "应该返回success字段"
        assert "branch" in status, "应该返回branch字段"

        self.test_results.append({"test": "ci_status_check", "status": "passed", "result": status.get("status")})

        print("✅ CI状态检查测试通过")

    async def test_failure_analysis(self):
        """测试7: 失败分析（规则基础）"""
        print("\n=== 测试7: CI失败分析 ===")

        # 测试规则基础分析
        error_messages = [
            "ModuleNotFoundError: No module named 'requests'",
            "ImportError: cannot import name 'foo'",
            "AssertionError: Expected 1 but got 2",
            "ERROR: connection timeout",
        ]

        # 使用规则基础分析
        analysis = self.cicd._rule_based_analysis(error_messages)

        print(f"失败类型: {analysis.get('error_type')}")
        print(f"失败原因: {analysis.get('reason')}")
        print(f"建议修复: {analysis.get('fix')}")
        print(f"置信度: {analysis.get('confidence')}")

        # 验证
        assert "error_type" in analysis, "应该返回error_type"
        assert "reason" in analysis, "应该返回reason"
        assert "fix" in analysis, "应该返回fix建议"

        self.test_results.append({"test": "failure_analysis", "status": "passed", "error_type": analysis.get("error_type")})

        print("✅ 失败分析测试通过")

    async def test_retry_logic(self):
        """测试8: 重试逻辑"""
        print("\n=== 测试8: CI重试逻辑 ===")

        # 测试是否应该重试的判断
        test_cases = [
            {"analysis": {"error_type": "network", "confidence": 0.8}, "should_retry": True, "reason": "网络问题应该重试"},
            {
                "analysis": {"error_type": "dependency", "confidence": 0.7},
                "should_retry": True,
                "reason": "依赖问题可能重试成功",
            },
            {"analysis": {"error_type": "build", "confidence": 0.9}, "should_retry": False, "reason": "构建问题不应重试"},
            {"analysis": {"error_type": "test", "confidence": 0.6}, "should_retry": False, "reason": "测试失败不应重试"},
            {"analysis": {"error_type": "network", "confidence": 0.3}, "should_retry": False, "reason": "置信度太低不应重试"},
        ]

        # 创建临时编排器实例
        from nanobot_scheduler_enhanced import NanobotOrchestratorEnhanced

        orchestrator = NanobotOrchestratorEnhanced()

        for case in test_cases:
            should_retry = orchestrator._should_retry_ci(case["analysis"])

            print(f"{case['reason']}: {'✅' if should_retry == case['should_retry'] else '❌'}")

            assert should_retry == case["should_retry"], f"重试判断错误: {case['reason']}"

        self.test_results.append({"test": "retry_logic", "status": "passed", "cases_tested": len(test_cases)})

        print("✅ 重试逻辑测试通过")

    async def test_notification(self):
        """测试9: 通知功能"""
        print("\n=== 测试9: 通知功能 ===")

        # 发送测试通知
        result = await self.cicd.notify_ci_status(
            branch="test-branch", status="success", details={"run_id": "12345", "workflow": "Agent CI"}
        )

        print(f"通知结果: {result.get('success')}")

        # 验证
        assert result.get("success"), "通知应该成功"

        self.test_results.append({"test": "notification", "status": "passed"})

        print("✅ 通知功能测试通过")


class TestIntegration:
    """集成测试类"""

    def __init__(self):
        self.orchestrator = get_orchestrator_enhanced()
        self.test_results = []

    async def test_full_workflow_simulation(self):
        """测试10: 完整工作流模拟"""
        print("\n=== 测试10: 完整工作流模拟 ===")

        # 模拟任务数据
        task_id = "test_task_001"
        task_info = {
            "id": task_id,
            "description": "测试任务",
            "agent": "codex",
            "branch": "test-branch-001",
            "status": "needs_review",
            "createdAt": datetime.now().isoformat(),
            "code_review": None,
            "ci_status": None,
        }

        # 保存任务
        self.orchestrator._save_task(task_info)

        print(f"创建测试任务: {task_id}")

        # 1. 模拟代码审查
        print("\n步骤1: 模拟代码审查...")

        # 创建模拟审查结果
        review_result = {
            "success": True,
            "score": 85,
            "approved": True,
            "layers": {"llm_review": {"score": 88}, "static_review": {"score": 82}, "test_review": {"score": 85}},
            "summary": "代码质量良好，建议通过",
        }

        task_info["code_review"] = {
            "score": review_result["score"],
            "approved": review_result["approved"],
            "timestamp": datetime.now().isoformat(),
        }
        self.orchestrator._save_task(task_info)

        print(f"代码审查评分: {review_result['score']}/100")
        print(f"审查结果: {'✅ 通过' if review_result['approved'] else '❌ 未通过'}")

        # 2. 模拟CI检查
        print("\n步骤2: 模拟CI检查...")

        ci_status = {"success": True, "status": "completed", "conclusion": "success", "run_id": 12345, "is_success": True}

        task_info["ci_status"] = {
            "status": ci_status["status"],
            "conclusion": ci_status["conclusion"],
            "run_id": ci_status["run_id"],
            "checked_at": datetime.now().isoformat(),
        }
        self.orchestrator._save_task(task_info)

        print(f"CI状态: {ci_status['conclusion']}")
        print(f"CI结果: {'✅ 成功' if ci_status['is_success'] else '❌ 失败'}")

        # 3. 验证任务状态
        print("\n步骤3: 验证任务状态...")

        loaded_task = self.orchestrator.task_monitor._load_task(task_id)

        assert loaded_task is not None, "任务应该存在"
        assert loaded_task.get("code_review") is not None, "应该有代码审查记录"
        assert loaded_task.get("ci_status") is not None, "应该有CI状态记录"

        print("✅ 任务状态验证通过")

        self.test_results.append({"test": "full_workflow_simulation", "status": "passed", "task_id": task_id})

        print("✅ 完整工作流模拟测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始运行 Code Review 和 CI/CD 集成测试")
    print("=" * 60)

    all_results = []

    # Code Review测试
    print("\n### Code Review 测试 ###")
    cr_test = TestCodeReview()

    await cr_test.test_security_check()
    await cr_test.test_performance_check()
    await cr_test.test_code_quality_check()
    await cr_test.test_score_calculation()
    await cr_test.test_comment_generation()

    all_results.extend(cr_test.test_results)

    # CI/CD集成测试
    print("\n### CI/CD 集成测试 ###")
    cicd_test = TestCICDIntegration()

    await cicd_test.test_ci_status_check()
    await cicd_test.test_failure_analysis()
    await cicd_test.test_retry_logic()
    await cicd_test.test_notification()

    all_results.extend(cicd_test.test_results)

    # 集成测试
    print("\n### 集成测试 ###")
    integration_test = TestIntegration()

    await integration_test.test_full_workflow_simulation()

    all_results.extend(integration_test.test_results)

    # 生成测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)

    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r["status"] == "passed"])

    print(f"\n总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")

    print("\n详细结果:")
    for result in all_results:
        status_emoji = "✅" if result["status"] == "passed" else "❌"
        print(f"  {status_emoji} {result['test']}: {result['status']}")

    # 保存测试报告
    report_path = Path.home() / ".nanobot" / "workspace" / "test_report.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "pass_rate": passed_tests / total_tests * 100,
                "results": all_results,
            },
            f,
            indent=2,
        )

    print(f"\n测试报告已保存到: {report_path}")

    # 返回是否所有测试通过
    return passed_tests == total_tests


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(run_all_tests())

    if success:
        print("\n🎉 所有测试通过！")
        exit(0)
    else:
        print("\n❌ 部分测试失败")
        exit(1)
