"""
测试套件管理器模块 - 管理和组织测试套件
支持测试发现、分类、并行执行
"""

import os
import re
import json
import asyncio
import subprocess
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import ast

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TestSuiteManager:
    """测试套件管理器 - 管理和组织测试套件"""

    def __init__(self, test_dir: str = "./tests"):
        """
        初始化测试套件管理器

        Args:
            test_dir: 测试目录
        """
        self.test_dir = os.path.abspath(test_dir)
        self.suites = {}
        self.categories = defaultdict(list)
        self.tags = defaultdict(list)

        # 加载测试套件
        self.load_suites()

    def load_suites(self) -> Dict:
        """加载测试套件"""
        logger.info(f"加载测试套件: {self.test_dir}")

        if not os.path.exists(self.test_dir):
            logger.warning(f"测试目录不存在: {self.test_dir}")
            return {}

        # 扫描测试目录
        for root, dirs, files in os.walk(self.test_dir):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    relative_path = os.path.relpath(filepath, self.test_dir)

                    try:
                        # 读取文件
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()

                        # 提取测试函数
                        test_functions = self._extract_test_functions(content)

                        # 提取元数据
                        metadata = self._extract_metadata(content)

                        # 创建套件信息
                        suite_info = {
                            "file": filepath,
                            "relative_path": relative_path,
                            "tests": test_functions,
                            "count": len(test_functions),
                            "metadata": metadata,
                            "last_modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                        }

                        self.suites[filepath] = suite_info

                        # 按分类组织
                        category = metadata.get("category", "general")
                        self.categories[category].append(filepath)

                        # 按标签组织
                        for tag in metadata.get("tags", []):
                            self.tags[tag].append(filepath)

                    except Exception as e:
                        logger.error(f"加载测试文件失败 {filepath}: {e}")

        logger.info(f"加载完成: {len(self.suites)}个文件, " f"{sum(s['count'] for s in self.suites.values())}个测试")

        return self.suites

    def _extract_test_functions(self, content: str) -> List[Dict]:
        """提取测试函数"""
        tests = []

        # 使用正则提取
        pattern = r'def (test_\w+)\((.*?)\):\s*"""(.*?)"""'
        matches = re.findall(pattern, content, re.DOTALL)

        for func_name, params, docstring in matches:
            tests.append(
                {
                    "name": func_name,
                    "params": params.strip(),
                    "docstring": docstring.strip(),
                    "markers": self._extract_markers(content, func_name),
                }
            )

        # 如果正则没找到，尝试AST
        if not tests:
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        docstring = ast.get_docstring(node) or ""
                        tests.append(
                            {
                                "name": node.name,
                                "params": ", ".join([arg.arg for arg in node.args.args]),
                                "docstring": docstring,
                                "markers": [],
                            }
                        )
            except Exception as e:
                logger.error(f"AST解析失败: {e}")

        return tests

    def _extract_markers(self, content: str, func_name: str) -> List[str]:
        """提取pytest markers"""
        markers = []

        # 查找函数定义之前的decorators
        pattern = rf"(@pytest\.mark\.\w+.*?)(?=\ndef {func_name})"
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            # 提取marker名称
            marker_match = re.search(r"@pytest\.mark\.(\w+)", match)
            if marker_match:
                markers.append(marker_match.group(1))

        return markers

    def _extract_metadata(self, content: str) -> Dict:
        """提取测试元数据"""
        metadata = {"category": "general", "tags": [], "priority": "normal", "timeout": None}

        # 提取模块级文档字符串
        docstring_match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1)

            # 提取category
            category_match = re.search(r"Category:\s*(\w+)", docstring)
            if category_match:
                metadata["category"] = category_match.group(1).lower()

            # 提取tags
            tags_match = re.search(r"Tags:\s*(.+)", docstring)
            if tags_match:
                tags_str = tags_match.group(1)
                metadata["tags"] = [tag.strip() for tag in tags_str.split(",")]

            # 提取priority
            priority_match = re.search(r"Priority:\s*(\w+)", docstring)
            if priority_match:
                metadata["priority"] = priority_match.group(1).lower()

        return metadata

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total_tests = sum(suite["count"] for suite in self.suites.values())

        # 按分类统计
        category_stats = {
            category: {"file_count": len(files), "test_count": sum(self.suites[f]["count"] for f in files if f in self.suites)}
            for category, files in self.categories.items()
        }

        # 按标签统计
        tag_stats = {
            tag: {"file_count": len(files), "test_count": sum(self.suites[f]["count"] for f in files if f in self.suites)}
            for tag, files in self.tags.items()
        }

        return {
            "total_files": len(self.suites),
            "total_tests": total_tests,
            "categories": dict(category_stats),
            "tags": dict(tag_stats),
            "suites": {
                filepath: {
                    "count": suite["count"],
                    "category": suite["metadata"]["category"],
                    "relative_path": suite["relative_path"],
                }
                for filepath, suite in self.suites.items()
            },
        }

    async def run_suite(self, suite_name: str, verbose: bool = True) -> Dict:
        """
        运行指定测试套件

        Args:
            suite_name: 套件名称（文件路径或相对路径）
            verbose: 是否详细输出

        Returns:
            测试结果
        """
        logger.info(f"运行测试套件: {suite_name}")

        # 查找套件
        suite_path = None
        if suite_name in self.suites:
            suite_path = suite_name
        else:
            # 尝试查找匹配的文件
            for filepath in self.suites:
                if suite_name in filepath:
                    suite_path = filepath
                    break

        if not suite_path:
            return {"success": False, "error": f"未找到测试套件: {suite_name}"}

        # 构建命令
        cmd = ["pytest", suite_path]
        if verbose:
            cmd.append("-v")

        # 运行测试
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            output = stdout.decode()
            error_output = stderr.decode()

            # 解析结果
            results = self._parse_test_output(output)

            logger.info(f"测试完成: passed={results['passed']}, " f"failed={results['failed']}")

            return {
                "success": process.returncode == 0,
                "suite": suite_name,
                "results": results,
                "output": output,
                "error": error_output,
            }

        except Exception as e:
            logger.error(f"运行测试失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _parse_test_output(self, output: str) -> Dict:
        """解析测试输出"""
        results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "failures": []}

        # 解析统计
        passed_match = re.search(r"(\d+) passed", output)
        if passed_match:
            results["passed"] = int(passed_match.group(1))

        failed_match = re.search(r"(\d+) failed", output)
        if failed_match:
            results["failed"] = int(failed_match.group(1))

        skipped_match = re.search(r"(\d+) skipped", output)
        if skipped_match:
            results["skipped"] = int(skipped_match.group(1))

        results["total"] = results["passed"] + results["failed"] + results["skipped"]

        # 提取失败信息
        failed_tests = re.findall(r"FAILED (.*?)::", output)
        results["failures"] = failed_tests

        return results

    async def run_category(self, category: str, parallel: bool = False) -> Dict:
        """
        运行指定分类的所有测试

        Args:
            category: 分类名称
            parallel: 是否并行执行

        Returns:
            测试结果
        """
        logger.info(f"运行分类测试: {category}")

        if category not in self.categories:
            return {"success": False, "error": f"未找到分类: {category}"}

        files = self.categories[category]

        if parallel:
            # 并行执行
            tasks = [self.run_suite(f) for f in files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 合并结果
            merged = {
                "success": all(r.get("success", False) for r in results if not isinstance(r, Exception)),
                "results": {
                    "total": sum(r["results"]["total"] for r in results if not isinstance(r, Exception) and "results" in r),
                    "passed": sum(r["results"]["passed"] for r in results if not isinstance(r, Exception) and "results" in r),
                    "failed": sum(r["results"]["failed"] for r in results if not isinstance(r, Exception) and "results" in r),
                    "skipped": sum(
                        r["results"]["skipped"] for r in results if not isinstance(r, Exception) and "results" in r
                    ),
                },
                "details": results,
            }
        else:
            # 串行执行
            all_results = []
            for filepath in files:
                result = await self.run_suite(filepath)
                all_results.append(result)

            merged = {
                "success": all(r.get("success", False) for r in all_results),
                "results": {
                    "total": sum(r["results"]["total"] for r in all_results if r.get("results")),
                    "passed": sum(r["results"]["passed"] for r in all_results if r.get("results")),
                    "failed": sum(r["results"]["failed"] for r in all_results if r.get("results")),
                    "skipped": sum(r["results"]["skipped"] for r in all_results if r.get("results")),
                },
                "details": all_results,
            }

        return merged

    async def run_by_tags(self, tags: List[str], mode: str = "any") -> Dict:
        """
        按标签运行测试

        Args:
            tags: 标签列表
            mode: 匹配模式（any=任意标签, all=所有标签）

        Returns:
            测试结果
        """
        logger.info(f"按标签运行测试: tags={tags}, mode={mode}")

        # 查找匹配的文件
        matched_files = set()

        if mode == "any":
            # 任意标签匹配
            for tag in tags:
                if tag in self.tags:
                    matched_files.update(self.tags[tag])
        else:
            # 所有标签匹配
            if all(tag in self.tags for tag in tags):
                matched_files = set(self.tags[tags[0]])
                for tag in tags[1:]:
                    matched_files &= set(self.tags[tag])

        if not matched_files:
            return {"success": False, "error": f"未找到匹配的测试: tags={tags}"}

        # 运行测试
        tasks = [self.run_suite(f) for f in matched_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        merged = {
            "success": all(r.get("success", False) for r in results if not isinstance(r, Exception)),
            "matched_files": list(matched_files),
            "results": {
                "total": sum(r["results"]["total"] for r in results if not isinstance(r, Exception) and "results" in r),
                "passed": sum(r["results"]["passed"] for r in results if not isinstance(r, Exception) and "results" in r),
                "failed": sum(r["results"]["failed"] for r in results if not isinstance(r, Exception) and "results" in r),
                "skipped": sum(r["results"]["skipped"] for r in results if not isinstance(r, Exception) and "results" in r),
            },
            "details": results,
        }

        return merged

    def find_tests(self, query: str, search_in: str = "all") -> List[Dict]:
        """
        搜索测试

        Args:
            query: 搜索查询
            search_in: 搜索范围（all, name, docstring, code）

        Returns:
            匹配的测试列表
        """
        logger.info(f"搜索测试: query={query}")

        results = []
        query_lower = query.lower()

        for filepath, suite in self.suites.items():
            for test in suite["tests"]:
                match = False

                if search_in in ["all", "name"]:
                    if query_lower in test["name"].lower():
                        match = True

                if not match and search_in in ["all", "docstring"]:
                    if query_lower in test["docstring"].lower():
                        match = True

                if match:
                    results.append(
                        {
                            "file": filepath,
                            "relative_path": suite["relative_path"],
                            "test": test["name"],
                            "docstring": test["docstring"],
                            "markers": test["markers"],
                        }
                    )

        return results

    def organize_tests(self) -> Dict:
        """组织测试（自动分类）"""
        logger.info("组织测试")

        organization = {
            "by_priority": defaultdict(list),
            "by_type": defaultdict(list),
            "by_speed": defaultdict(list),
            "recommendations": [],
        }

        for filepath, suite in self.suites.items():
            # 按优先级
            priority = suite["metadata"]["priority"]
            organization["by_priority"][priority].append(filepath)

            # 按类型（根据markers）
            has_slow = any("slow" in test["markers"] for test in suite["tests"])
            has_async = any("asyncio" in test["markers"] for test in suite["tests"])

            if has_slow:
                organization["by_type"]["slow"].append(filepath)
            if has_async:
                organization["by_type"]["async"].append(filepath)

            # 分类建议
            if suite["count"] > 20:
                organization["recommendations"].append(
                    {"file": filepath, "recommendation": "测试过多，建议拆分", "priority": "medium"}
                )

            if not suite["metadata"]["tags"]:
                organization["recommendations"].append(
                    {"file": filepath, "recommendation": "缺少标签，建议添加", "priority": "low"}
                )

        return organization

    def export_suite_config(self, output_file: str = "test_suites.json") -> str:
        """导出测试套件配置"""
        config = {
            "test_dir": self.test_dir,
            "generated_at": datetime.now().isoformat(),
            "statistics": self.get_statistics(),
            "suites": self.suites,
            "categories": dict(self.categories),
            "tags": dict(self.tags),
        }

        output_path = os.path.join(self.test_dir, output_file)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"配置已导出: {output_path}")

        return output_path

    def import_suite_config(self, config_file: str):
        """导入测试套件配置"""
        with open(config_file, "r") as f:
            config = json.load(f)

        # 恢复配置
        if "suites" in config:
            self.suites = config["suites"]

        if "categories" in config:
            self.categories = defaultdict(list, config["categories"])

        if "tags" in config:
            self.tags = defaultdict(list, config["tags"])

        logger.info(f"配置已导入: {config_file}")

    async def create_test_plan(self, requirements: List[str], coverage_target: float = 80.0) -> Dict:
        """
        创建测试计划

        Args:
            requirements: 需求列表
            coverage_target: 覆盖率目标

        Returns:
            测试计划
        """
        logger.info(f"创建测试计划: {len(requirements)}个需求")

        plan = {
            "requirements": requirements,
            "test_suites": [],
            "estimated_time": 0,
            "coverage_target": coverage_target,
            "created_at": datetime.now().isoformat(),
        }

        # 为每个需求查找相关测试
        for req in requirements:
            related_tests = self.find_tests(req, search_in="all")

            if related_tests:
                plan["test_suites"].append({"requirement": req, "tests": related_tests, "count": len(related_tests)})

                # 估算时间（假设每个测试1秒）
                plan["estimated_time"] += len(related_tests)

        # 添加建议
        plan["recommendations"] = []

        if plan["estimated_time"] > 300:  # 5分钟
            plan["recommendations"].append("测试时间较长，建议并行执行")

        if len(plan["test_suites"]) < len(requirements):
            plan["recommendations"].append("部分需求缺少测试覆盖，建议补充测试")

        return plan


class TestDependencyAnalyzer:
    """测试依赖分析器"""

    def __init__(self, test_dir: str = "./tests"):
        self.test_dir = test_dir
        self.dependencies = {}

    def analyze_dependencies(self) -> Dict:
        """分析测试依赖关系"""
        logger.info("分析测试依赖")

        dependencies = {"fixtures": {}, "imports": {}, "shared_resources": []}

        # 扫描测试文件
        for root, dirs, files in os.walk(self.test_dir):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    filepath = os.path.join(root, file)

                    try:
                        with open(filepath, "r") as f:
                            content = f.read()

                        # 提取fixtures
                        fixtures = re.findall(r"@pytest\.fixture\ndef (\w+)", content)
                        if fixtures:
                            dependencies["fixtures"][filepath] = fixtures

                        # 提取imports
                        imports = re.findall(r"from (.*?) import|import (.*)", content)
                        if imports:
                            dependencies["imports"][filepath] = imports

                    except Exception as e:
                        logger.error(f"分析文件 {filepath} 失败: {e}")

        # 查找共享资源
        all_fixtures = set()
        for fixtures in dependencies["fixtures"].values():
            for fixture in fixtures:
                if fixture in all_fixtures:
                    dependencies["shared_resources"].append(fixture)
                all_fixtures.add(fixture)

        self.dependencies = dependencies
        return dependencies

    def get_execution_order(self) -> List[str]:
        """获取推荐的执行顺序"""
        if not self.dependencies:
            self.analyze_dependencies()

        # 简化实现：按文件名排序
        # 实际应该使用拓扑排序
        test_files = []

        for root, dirs, files in os.walk(self.test_dir):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(root, file))

        # 排序：基础测试优先
        test_files.sort(key=lambda x: ("unit" not in x.lower(), "integration" not in x.lower(), "e2e" not in x.lower(), x))

        return test_files


# 便捷函数
def get_test_stats(test_dir: str = "./tests") -> Dict:
    """快速获取测试统计"""
    manager = TestSuiteManager(test_dir)
    return manager.get_statistics()


if __name__ == "__main__":
    # 测试代码
    async def test():
        manager = TestSuiteManager("./tests")

        # 获取统计
        stats = manager.get_statistics()
        print(f"测试统计: {json.dumps(stats, indent=2)}")

        # 搜索测试
        results = manager.find_tests("model", search_in="all")
        print(f"\n搜索结果: {len(results)}个")

        # 组织测试
        org = manager.organize_tests()
        print(f"\n组织建议: {len(org['recommendations'])}条")

        # 导出配置
        config_file = manager.export_suite_config()
        print(f"\n配置已导出: {config_file}")

    asyncio.run(test())
