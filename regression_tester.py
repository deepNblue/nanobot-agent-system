"""
回归测试器模块 - 自动化回归测试和变更检测
支持基线对比、变更检测、测试历史管理
"""

import os
import re
import json
import asyncio
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RegressionTester:
    """回归测试器 - 自动化回归测试和变更检测"""
    
    def __init__(self, project_path: str = "."):
        """
        初始化回归测试器
        
        Args:
            project_path: 项目路径
        """
        self.project_path = os.path.abspath(project_path)
        self.baseline_dir = os.path.join(self.project_path, ".baselines")
        self.results_dir = os.path.join(self.project_path, ".test_results")
        self.test_history = []
        self.baselines = {}
        
        # 创建目录
        os.makedirs(self.baseline_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 加载历史
        self._load_history()
    
    async def run_regression_suite(
        self,
        test_path: str = "./tests",
        extra_args: Optional[List[str]] = None,
        save_results: bool = True
    ) -> Dict:
        """
        运行回归测试套件
        
        Args:
            test_path: 测试路径
            extra_args: 额外的pytest参数
            save_results: 是否保存结果
        
        Returns:
            测试结果
        """
        logger.info(f"运行回归测试: path={test_path}")
        
        start_time = datetime.now()
        
        # 1. 构建命令
        cmd = [
            "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=.test_results/report.json"
        ]
        
        if extra_args:
            cmd.extend(extra_args)
        
        # 2. 运行测试
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            output = stdout.decode()
            error_output = stderr.decode()
            
            # 3. 解析结果
            results = self._parse_test_results(output)
            
            # 4. 保存结果
            test_result = {
                "timestamp": start_time.isoformat(),
                "duration": duration,
                "results": results,
                "returncode": process.returncode,
                "output": output,
                "error": error_output
            }
            
            if save_results:
                self.test_history.append(test_result)
                self._save_history()
            
            logger.info(
                f"回归测试完成: "
                f"passed={results['passed']}, "
                f"failed={results['failed']}, "
                f"duration={duration:.2f}s"
            )
            
            return {
                "success": process.returncode == 0,
                "duration": duration,
                "results": results,
                "output": output,
                "error": error_output
            }
            
        except Exception as e:
            logger.error(f"运行回归测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "duration": 0,
                "results": {}
            }
    
    def _parse_test_results(self, output: str) -> Dict:
        """解析测试结果"""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "failures": [],
            "passes": []
        }
        
        # 解析passed
        passed_match = re.search(r'(\d+) passed', output)
        if passed_match:
            results["passed"] = int(passed_match.group(1))
        
        # 解析failed
        failed_match = re.search(r'(\d+) failed', output)
        if failed_match:
            results["failed"] = int(failed_match.group(1))
        
        # 解析skipped
        skipped_match = re.search(r'(\d+) skipped', output)
        if skipped_match:
            results["skipped"] = int(skipped_match.group(1))
        
        # 解析errors
        error_match = re.search(r'(\d+) error', output)
        if error_match:
            results["errors"] = int(error_match.group(1))
        
        # 计算总数
        results["total"] = (
            results["passed"] + 
            results["failed"] + 
            results["skipped"] + 
            results["errors"]
        )
        
        # 提取失败的测试
        failed_tests = re.findall(r'FAILED (.*?) ', output)
        for test in failed_tests:
            results["failures"].append(test)
        
        # 提取通过的测试
        passed_tests = re.findall(r'PASSED (.*?) ', output)
        for test in passed_tests:
            results["passes"].append(test)
        
        return results
    
    async def capture_baseline(self, test_suite: str = "all") -> Dict:
        """
        捕获测试基线
        
        Args:
            test_suite: 测试套件名称
        
        Returns:
            基线信息
        """
        logger.info(f"捕获基线: suite={test_suite}")
        
        # 运行测试
        test_path = "./tests" if test_suite == "all" else f"./tests/{test_suite}"
        result = await self.run_regression_suite(test_path, save_results=False)
        
        if not result.get("success"):
            return {
                "success": False,
                "error": "测试运行失败"
            }
        
        # 保存基线
        baseline = {
            "suite": test_suite,
            "timestamp": datetime.now().isoformat(),
            "results": result["results"],
            "duration": result["duration"]
        }
        
        baseline_file = os.path.join(self.baseline_dir, f"{test_suite}_baseline.json")
        with open(baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        self.baselines[test_suite] = baseline
        
        logger.info(f"基线已保存: {baseline_file}")
        
        return {
            "success": True,
            "baseline": baseline,
            "file": baseline_file
        }
    
    def load_baseline(self, test_suite: str = "all") -> Optional[Dict]:
        """加载基线"""
        baseline_file = os.path.join(self.baseline_dir, f"{test_suite}_baseline.json")
        
        if os.path.exists(baseline_file):
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
            self.baselines[test_suite] = baseline
            return baseline
        
        return None
    
    async def compare_with_baseline(
        self,
        test_suite: str = "all"
    ) -> Dict:
        """
        与基线对比
        
        Args:
            test_suite: 测试套件名称
        
        Returns:
            对比结果
        """
        logger.info(f"与基线对比: suite={test_suite}")
        
        # 1. 加载基线
        baseline = self.load_baseline(test_suite)
        
        if not baseline:
            return {
                "success": False,
                "error": "未找到基线",
                "is_baseline": True
            }
        
        # 2. 运行当前测试
        test_path = "./tests" if test_suite == "all" else f"./tests/{test_suite}"
        current_result = await self.run_regression_suite(test_path, save_results=False)
        
        if not current_result.get("success"):
            return {
                "success": False,
                "error": "当前测试运行失败"
            }
        
        # 3. 对比
        comparison = {
            "baseline": baseline,
            "current": {
                "timestamp": datetime.now().isoformat(),
                "results": current_result["results"],
                "duration": current_result["duration"]
            },
            "changes": {
                "passed_diff": current_result["results"]["passed"] - baseline["results"]["passed"],
                "failed_diff": current_result["results"]["failed"] - baseline["results"]["failed"],
                "skipped_diff": current_result["results"]["skipped"] - baseline["results"]["skipped"],
                "duration_diff": current_result["duration"] - baseline["duration"]
            },
            "new_failures": [],
            "fixed_tests": [],
            "still_failing": []
        }
        
        # 4. 详细对比
        baseline_failures = set(baseline["results"]["failures"])
        current_failures = set(current_result["results"]["failures"])
        
        comparison["new_failures"] = list(current_failures - baseline_failures)
        comparison["fixed_tests"] = list(baseline_failures - current_failures)
        comparison["still_failing"] = list(current_failures & baseline_failures)
        
        # 5. 判断是否有回归
        comparison["has_regression"] = (
            comparison["changes"]["failed_diff"] > 0 or
            comparison["changes"]["passed_diff"] < 0 or
            len(comparison["new_failures"]) > 0
        )
        
        # 6. 判断是否有改进
        comparison["has_improvement"] = (
            comparison["changes"]["failed_diff"] < 0 or
            comparison["changes"]["passed_diff"] > 0 or
            len(comparison["fixed_tests"]) > 0
        )
        
        logger.info(
            f"对比完成: "
            f"新失败={len(comparison['new_failures'])}, "
            f"已修复={len(comparison['fixed_tests'])}, "
            f"回归={comparison['has_regression']}"
        )
        
        return {
            "success": True,
            **comparison
        }
    
    async def detect_flaky_tests(
        self,
        test_path: str = "./tests",
        runs: int = 5,
        threshold: float = 0.8
    ) -> List[Dict]:
        """
        检测不稳定的测试（Flaky Tests）
        
        Args:
            test_path: 测试路径
            runs: 运行次数
            threshold: 稳定性阈值（通过率低于此值视为不稳定）
        
        Returns:
            不稳定测试列表
        """
        logger.info(f"检测不稳定测试: runs={runs}")
        
        # 记录每个测试的结果
        test_results = defaultdict(lambda: {"passed": 0, "failed": 0, "total": 0})
        
        # 多次运行测试
        for i in range(runs):
            logger.info(f"运行 {i+1}/{runs}")
            
            result = await self.run_regression_suite(test_path, save_results=False)
            
            if result.get("success"):
                # 记录通过的测试
                for test in result["results"]["passes"]:
                    test_results[test]["passed"] += 1
                    test_results[test]["total"] += 1
                
                # 记录失败的测试
                for test in result["results"]["failures"]:
                    test_results[test]["failed"] += 1
                    test_results[test]["total"] += 1
            
            # 短暂延迟
            if i < runs - 1:
                await asyncio.sleep(1)
        
        # 分析结果
        flaky_tests = []
        
        for test, stats in test_results.items():
            pass_rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            
            # 如果通过率低于阈值，认为是flaky
            if 0 < pass_rate < threshold:
                flaky_tests.append({
                    "test": test,
                    "pass_rate": pass_rate,
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "total": stats["total"],
                    "flakiness": 1 - pass_rate
                })
        
        # 按不稳定性排序
        flaky_tests.sort(key=lambda x: x["flakiness"], reverse=True)
        
        logger.info(f"检测到 {len(flaky_tests)} 个不稳定测试")
        
        return flaky_tests
    
    async def run_impact_analysis(
        self,
        changed_files: List[str]
    ) -> Dict:
        """
        影响分析 - 确定哪些测试受代码变更影响
        
        Args:
            changed_files: 变更的文件列表
        
        Returns:
            影响分析结果
        """
        logger.info(f"影响分析: {len(changed_files)}个文件变更")
        
        impacted_tests = []
        
        # 简化实现：查找测试文件中的导入
        for test_file in self._find_test_files():
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
                
                # 检查是否导入了变更的文件
                for changed_file in changed_files:
                    module_name = self._file_to_module(changed_file)
                    
                    if module_name and module_name in content:
                        impacted_tests.append({
                            "test_file": test_file,
                            "impacted_by": changed_file,
                            "reason": f"导入了 {module_name}"
                        })
                        break
            except Exception as e:
                logger.error(f"分析文件 {test_file} 失败: {e}")
        
        return {
            "changed_files": changed_files,
            "impacted_tests": impacted_tests,
            "total_impacted": len(impacted_tests)
        }
    
    def _find_test_files(self) -> List[str]:
        """查找所有测试文件"""
        test_files = []
        tests_dir = os.path.join(self.project_path, "tests")
        
        if os.path.exists(tests_dir):
            for root, dirs, files in os.walk(tests_dir):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        test_files.append(os.path.join(root, file))
        
        return test_files
    
    def _file_to_module(self, file_path: str) -> Optional[str]:
        """将文件路径转换为模块名"""
        # 简化实现
        if file_path.endswith(".py"):
            return file_path[:-3].replace("/", ".")
        return None
    
    def _save_history(self):
        """保存测试历史"""
        history_file = os.path.join(self.results_dir, "test_history.json")
        
        # 只保留最近100条记录
        history_to_save = self.test_history[-100:]
        
        with open(history_file, 'w') as f:
            json.dump(history_to_save, f, indent=2)
    
    def _load_history(self):
        """加载测试历史"""
        history_file = os.path.join(self.results_dir, "test_history.json")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    self.test_history = json.load(f)
                logger.info(f"加载了 {len(self.test_history)} 条历史记录")
            except Exception as e:
                logger.error(f"加载历史失败: {e}")
    
    def get_trend_analysis(self, days: int = 7) -> Dict:
        """
        趋势分析 - 分析测试结果趋势
        
        Args:
            days: 分析最近几天的数据
        
        Returns:
            趋势分析结果
        """
        logger.info(f"趋势分析: 最近{days}天")
        
        if not self.test_history:
            return {"error": "没有历史数据"}
        
        # 过滤最近的数据
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        
        recent_runs = [
            run for run in self.test_history
            if datetime.fromisoformat(run["timestamp"]).timestamp() > cutoff
        ]
        
        if not recent_runs:
            return {"error": "没有最近的数据"}
        
        # 计算趋势
        analysis = {
            "total_runs": len(recent_runs),
            "avg_pass_rate": 0,
            "avg_duration": 0,
            "pass_rate_trend": [],
            "duration_trend": [],
            "failure_frequency": defaultdict(int)
        }
        
        total_pass_rate = 0
        total_duration = 0
        
        for run in recent_runs:
            results = run["results"]
            total = results.get("total", 1)
            passed = results.get("passed", 0)
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            duration = run.get("duration", 0)
            
            total_pass_rate += pass_rate
            total_duration += duration
            
            analysis["pass_rate_trend"].append(pass_rate)
            analysis["duration_trend"].append(duration)
            
            # 统计失败频率
            for failure in results.get("failures", []):
                analysis["failure_frequency"][failure] += 1
        
        analysis["avg_pass_rate"] = total_pass_rate / len(recent_runs)
        analysis["avg_duration"] = total_duration / len(recent_runs)
        
        # 最常失败的测试
        analysis["most_failing"] = sorted(
            [
                {"test": test, "count": count}
                for test, count in analysis["failure_frequency"].items()
            ],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        return analysis
    
    def generate_report(self, format: str = "markdown") -> str:
        """
        生成回归测试报告
        
        Args:
            format: 报告格式（markdown, html, json）
        
        Returns:
            报告内容
        """
        logger.info(f"生成报告: format={format}")
        
        if format == "json":
            return json.dumps({
                "history": self.test_history[-10:],
                "baselines": self.baselines
            }, indent=2)
        
        elif format == "markdown":
            lines = [
                "# 回归测试报告",
                f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"\n## 测试统计\n",
                f"- 历史运行次数: {len(self.test_history)}",
                f"- 基线数量: {len(self.baselines)}",
                "\n## 最近运行结果\n"
            ]
            
            # 最近5次运行
            for run in self.test_history[-5:]:
                results = run["results"]
                lines.append(
                    f"- {run['timestamp']}: "
                    f"✅ {results['passed']} / "
                    f"❌ {results['failed']} / "
                    f"⏭️ {results['skipped']} "
                    f"({run['duration']:.2f}s)"
                )
            
            # 趋势分析
            trend = self.get_trend_analysis(days=7)
            if "error" not in trend:
                lines.extend([
                    "\n## 趋势分析（最近7天）\n",
                    f"- 运行次数: {trend['total_runs']}",
                    f"- 平均通过率: {trend['avg_pass_rate']:.2f}%",
                    f"- 平均耗时: {trend['avg_duration']:.2f}s"
                ])
                
                if trend["most_failing"]:
                    lines.append("\n### 最常失败的测试\n")
                    for item in trend["most_failing"][:5]:
                        lines.append(f"- {item['test']}: {item['count']}次")
            
            return '\n'.join(lines)
        
        else:
            return "不支持的格式"


class TestScheduler:
    """测试调度器 - 定期运行回归测试"""
    
    def __init__(self, tester: RegressionTester):
        self.tester = tester
        self.scheduled_tests = []
        self.running = False
    
    def schedule_test(
        self,
        test_path: str,
        interval_minutes: int = 60,
        name: str = None
    ):
        """
        调度定期测试
        
        Args:
            test_path: 测试路径
            interval_minutes: 间隔分钟数
            name: 任务名称
        """
        task = {
            "name": name or f"test_{len(self.scheduled_tests)}",
            "test_path": test_path,
            "interval_minutes": interval_minutes,
            "last_run": None,
            "next_run": datetime.now().isoformat()
        }
        
        self.scheduled_tests.append(task)
        logger.info(f"已调度测试: {task['name']}, 间隔={interval_minutes}分钟")
    
    async def start(self):
        """启动调度器"""
        logger.info("启动测试调度器")
        self.running = True
        
        while self.running:
            now = datetime.now()
            
            for task in self.scheduled_tests:
                next_run = datetime.fromisoformat(task["next_run"])
                
                if now >= next_run:
                    logger.info(f"运行调度测试: {task['name']}")
                    
                    # 运行测试
                    result = await self.tester.run_regression_suite(task["test_path"])
                    
                    # 更新下次运行时间
                    task["last_run"] = now.isoformat()
                    task["next_run"] = (
                        now + timedelta(minutes=task["interval_minutes"])
                    ).isoformat()
                    
                    logger.info(f"测试完成: {task['name']}, success={result['success']}")
            
            # 等待1分钟
            await asyncio.sleep(60)
    
    def stop(self):
        """停止调度器"""
        logger.info("停止测试调度器")
        self.running = False


# 便捷函数
async def run_regression_quick(project_path: str = ".") -> Dict:
    """快速运行回归测试"""
    tester = RegressionTester(project_path)
    return await tester.run_regression_suite()


if __name__ == "__main__":
    # 测试代码
    async def test():
        tester = RegressionTester(".")
        
        # 运行回归测试
        result = await tester.run_regression_suite()
        print(f"测试结果: {result['success']}")
        print(f"通过: {result['results']['passed']}")
        print(f"失败: {result['results']['failed']}")
        
        # 捕获基线
        baseline = await tester.capture_baseline()
        print(f"\n基线已捕获: {baseline['success']}")
        
        # 生成报告
        report = tester.generate_report("markdown")
        print(f"\n{report}")
    
    asyncio.run(test())
