"""
覆盖率优化器模块 - 分析和优化测试覆盖率
自动识别未覆盖代码并生成测试建议
"""

import os
import re
import json
import asyncio
import subprocess
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoverageOptimizer:
    """覆盖率优化器 - 分析和优化测试覆盖率"""
    
    def __init__(self, project_path: str = "."):
        """
        初始化覆盖率优化器
        
        Args:
            project_path: 项目路径
        """
        self.project_path = os.path.abspath(project_path)
        self.coverage_data = {}
        self.analysis_cache = {}
        self.history = []
    
    async def run_coverage(
        self,
        source_dir: str = ".",
        test_dir: str = "./tests",
        extra_args: Optional[List[str]] = None
    ) -> Dict:
        """
        运行覆盖率测试
        
        Args:
            source_dir: 源代码目录
            test_dir: 测试目录
            extra_args: 额外的pytest参数
        
        Returns:
            覆盖率测试结果
        """
        logger.info(f"运行覆盖率测试: source={source_dir}, test={test_dir}")
        
        # 1. 构建命令
        cmd = [
            "pytest",
            test_dir,
            f"--cov={source_dir}",
            "--cov-report=json:coverage.json",
            "--cov-report=term-missing",
            "-v"
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
            
            output = stdout.decode()
            error_output = stderr.decode()
            
            logger.info(f"覆盖率测试完成: returncode={process.returncode}")
            
            # 3. 解析覆盖率报告
            coverage_file = os.path.join(self.project_path, "coverage.json")
            
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    self.coverage_data = json.load(f)
                
                # 保存历史
                self.history.append({
                    "timestamp": datetime.now().isoformat(),
                    "coverage": self.coverage_data.get("totals", {}),
                    "success": process.returncode == 0
                })
            else:
                logger.warning("未找到覆盖率报告文件")
            
            return {
                "success": process.returncode == 0,
                "output": output,
                "error": error_output,
                "coverage_data": self.coverage_data,
                "returncode": process.returncode
            }
            
        except Exception as e:
            logger.error(f"运行覆盖率测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "coverage_data": {}
            }
    
    def analyze_coverage(self) -> Dict:
        """分析覆盖率数据"""
        if not self.coverage_data:
            logger.warning("没有覆盖率数据")
            return {"error": "没有覆盖率数据"}
        
        logger.info("开始分析覆盖率")
        
        files = self.coverage_data.get("files", {})
        
        analysis = {
            "total_files": len(files),
            "fully_covered": 0,
            "partially_covered": 0,
            "not_covered": 0,
            "uncovered_lines": {},
            "files_analysis": {},
            "summary": {}
        }
        
        # 分析每个文件
        for file_path, data in files.items():
            summary = data.get("summary", {})
            covered_percent = summary.get("percent_covered", 0)
            
            file_analysis = {
                "path": file_path,
                "coverage_percent": covered_percent,
                "total_lines": summary.get("num_statements", 0),
                "covered_lines": summary.get("covered_lines", 0),
                "missing_lines": summary.get("missing_lines", 0),
                "status": self._get_coverage_status(covered_percent)
            }
            
            analysis["files_analysis"][file_path] = file_analysis
            
            # 统计
            if covered_percent == 100:
                analysis["fully_covered"] += 1
            elif covered_percent > 0:
                analysis["partially_covered"] += 1
            else:
                analysis["not_covered"] += 1
            
            # 记录未覆盖的行
            if covered_percent < 100:
                missing_lines = data.get("missing_lines", [])
                if missing_lines:
                    analysis["uncovered_lines"][file_path] = missing_lines
        
        # 计算总体覆盖率
        totals = self.coverage_data.get("totals", {})
        analysis["summary"] = {
            "total_lines": totals.get("num_statements", 0),
            "covered_lines": totals.get("covered_lines", 0),
            "overall_coverage": totals.get("percent_covered", 0),
            "missing_lines": totals.get("missing_lines", 0)
        }
        
        logger.info(
            f"覆盖率分析完成: "
            f"总体={analysis['summary']['overall_coverage']:.2f}%, "
            f"完全覆盖={analysis['fully_covered']}, "
            f"部分覆盖={analysis['partially_covered']}, "
            f"未覆盖={analysis['not_covered']}"
        )
        
        return analysis
    
    def _get_coverage_status(self, coverage_percent: float) -> str:
        """获取覆盖率状态"""
        if coverage_percent >= 90:
            return "excellent"
        elif coverage_percent >= 70:
            return "good"
        elif coverage_percent >= 50:
            return "fair"
        else:
            return "poor"
    
    async def suggest_tests(
        self,
        uncovered_lines: Optional[Dict] = None,
        max_suggestions: int = 10
    ) -> List[Dict]:
        """
        为未覆盖代码生成测试建议
        
        Args:
            uncovered_lines: 未覆盖的行（如果为None，使用最新的分析结果）
            max_suggestions: 最大建议数
        
        Returns:
            测试建议列表
        """
        if uncovered_lines is None:
            analysis = self.analyze_coverage()
            uncovered_lines = analysis.get("uncovered_lines", {})
        
        if not uncovered_lines:
            logger.info("没有未覆盖的代码")
            return []
        
        logger.info(f"生成测试建议: {len(uncovered_lines)}个文件")
        
        suggestions = []
        
        for file_path, lines in list(uncovered_lines.items())[:max_suggestions]:
            # 读取文件内容
            full_path = os.path.join(self.project_path, file_path)
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取未覆盖的代码
                code_lines = content.split('\n')
                uncovered_code = []
                
                for line_num in lines:
                    if 0 < line_num <= len(code_lines):
                        uncovered_code.append({
                            "line_number": line_num,
                            "code": code_lines[line_num - 1]
                        })
                
                # 推断测试类型
                test_type = self._infer_test_type(file_path, uncovered_code)
                
                suggestion = {
                    "file": file_path,
                    "lines": lines,
                    "uncovered_code": uncovered_code,
                    "suggested_test_type": test_type,
                    "priority": self._calculate_priority(file_path, len(lines))
                }
                
                suggestions.append(suggestion)
                
            except Exception as e:
                logger.error(f"处理文件 {file_path} 失败: {e}")
                continue
        
        # 按优先级排序
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        
        return suggestions
    
    def _infer_test_type(self, file_path: str, uncovered_code: List[Dict]) -> str:
        """推断需要的测试类型"""
        # 根据文件路径推断
        if "api" in file_path.lower() or "route" in file_path.lower():
            return "integration_test"
        elif "ui" in file_path.lower() or "component" in file_path.lower():
            return "e2e_test"
        elif "test" in file_path.lower():
            return "unit_test"
        
        # 根据代码内容推断
        code_text = ' '.join([item["code"] for item in uncovered_code])
        
        if "async def" in code_text or "await " in code_text:
            return "integration_test"
        elif "class " in code_text:
            return "unit_test"
        else:
            return "unit_test"
    
    def _calculate_priority(self, file_path: str, uncovered_count: int) -> float:
        """计算测试优先级"""
        priority = uncovered_count * 10  # 基础分：每行10分
        
        # 根据文件类型调整
        if "core" in file_path or "main" in file_path:
            priority *= 1.5
        elif "util" in file_path or "helper" in file_path:
            priority *= 0.8
        
        # 根据文件重要性调整
        if "__init__.py" in file_path:
            priority *= 0.5
        
        return priority
    
    async def optimize_coverage(
        self,
        target_coverage: float = 90.0,
        max_iterations: int = 5,
        test_generator=None
    ) -> Dict:
        """
        优化测试覆盖率
        
        Args:
            target_coverage: 目标覆盖率
            max_iterations: 最大迭代次数
            test_generator: 测试生成器实例
        
        Returns:
            优化结果
        """
        logger.info(f"开始优化覆盖率: 目标={target_coverage}%")
        
        results = {
            "iterations": [],
            "initial_coverage": 0,
            "final_coverage": 0,
            "improvement": 0,
            "tests_generated": 0
        }
        
        # 初始覆盖率
        initial = await self.run_coverage()
        if not initial.get("success"):
            return {
                "success": False,
                "error": "无法运行初始覆盖率测试"
            }
        
        analysis = self.analyze_coverage()
        results["initial_coverage"] = analysis["summary"]["overall_coverage"]
        
        current_coverage = results["initial_coverage"]
        iteration = 0
        
        while current_coverage < target_coverage and iteration < max_iterations:
            iteration += 1
            logger.info(f"迭代 {iteration}/{max_iterations}: 当前覆盖率={current_coverage:.2f}%")
            
            # 1. 获取未覆盖代码
            suggestions = await self.suggest_tests(max_suggestions=3)
            
            if not suggestions:
                logger.info("没有更多未覆盖的代码")
                break
            
            # 2. 生成测试（如果提供了生成器）
            if test_generator:
                for suggestion in suggestions:
                    file_path = os.path.join(self.project_path, suggestion["file"])
                    
                    try:
                        result = await test_generator.generate_from_file(
                            file_path,
                            suggestion["suggested_test_type"]
                        )
                        
                        if result.get("success"):
                            results["tests_generated"] += 1
                            logger.info(f"为 {suggestion['file']} 生成测试")
                    except Exception as e:
                        logger.error(f"生成测试失败: {e}")
            
            # 3. 重新运行覆盖率
            await self.run_coverage()
            analysis = self.analyze_coverage()
            current_coverage = analysis["summary"]["overall_coverage"]
            
            # 记录迭代
            results["iterations"].append({
                "iteration": iteration,
                "coverage": current_coverage,
                "tests_generated": results["tests_generated"]
            })
            
            # 如果没有改善，停止
            if iteration > 1 and current_coverage <= results["iterations"][-2]["coverage"]:
                logger.info("覆盖率没有改善，停止优化")
                break
        
        results["final_coverage"] = current_coverage
        results["improvement"] = results["final_coverage"] - results["initial_coverage"]
        results["success"] = current_coverage >= target_coverage
        
        logger.info(
            f"覆盖率优化完成: "
            f"初始={results['initial_coverage']:.2f}%, "
            f"最终={results['final_coverage']:.2f}%, "
            f"提升={results['improvement']:.2f}%"
        )
        
        return results
    
    def get_coverage_report(self) -> str:
        """生成覆盖率报告"""
        analysis = self.analyze_coverage()
        
        report_lines = [
            "# 测试覆盖率报告",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 总体覆盖率\n",
            f"- 总体覆盖率: **{analysis['summary']['overall_coverage']:.2f}%**",
            f"- 总代码行数: {analysis['summary']['total_lines']}",
            f"- 已覆盖行数: {analysis['summary']['covered_lines']}",
            f"- 未覆盖行数: {analysis['summary']['missing_lines']}",
            "\n## 文件统计\n",
            f"- 完全覆盖: {analysis['fully_covered']} 个文件",
            f"- 部分覆盖: {analysis['partially_covered']} 个文件",
            f"- 未覆盖: {analysis['not_covered']} 个文件",
            "\n## 需要改进的文件\n"
        ]
        
        # 按覆盖率排序
        files_sorted = sorted(
            analysis["files_analysis"].items(),
            key=lambda x: x[1]["coverage_percent"]
        )
        
        for file_path, file_data in files_sorted[:10]:  # 显示最差的10个
            if file_data["coverage_percent"] < 90:
                report_lines.append(
                    f"- `{file_path}`: {file_data['coverage_percent']:.1f}% "
                    f"({file_data['covered_lines']}/{file_data['total_lines']} 行)"
                )
        
        return '\n'.join(report_lines)
    
    def get_history(self) -> List[Dict]:
        """获取覆盖率历史"""
        return self.history
    
    def compare_with_previous(self) -> Optional[Dict]:
        """与上一次覆盖率对比"""
        if len(self.history) < 2:
            return None
        
        current = self.history[-1]
        previous = self.history[-2]
        
        current_coverage = current["coverage"].get("percent_covered", 0)
        previous_coverage = previous["coverage"].get("percent_covered", 0)
        
        return {
            "current": current_coverage,
            "previous": previous_coverage,
            "change": current_coverage - previous_coverage,
            "improved": current_coverage > previous_coverage
        }
    
    async def identify_dead_code(self) -> List[Dict]:
        """识别死代码（从未被执行的代码）"""
        logger.info("识别死代码")
        
        if not self.coverage_data:
            await self.run_coverage()
        
        dead_code = []
        files = self.coverage_data.get("files", {})
        
        for file_path, data in files.items():
            # 如果文件完全没有被覆盖
            if data.get("summary", {}).get("percent_covered", 0) == 0:
                full_path = os.path.join(self.project_path, file_path)
                
                # 检查是否是测试文件
                if not file_path.startswith("test_") and "/tests/" not in file_path:
                    dead_code.append({
                        "file": file_path,
                        "type": "entire_file",
                        "reason": "文件完全没有被测试覆盖"
                    })
        
        return dead_code
    
    async def find_duplicate_tests(self, test_dir: str = "./tests") -> List[Dict]:
        """查找重复的测试"""
        logger.info("查找重复测试")
        
        duplicates = []
        test_signatures = defaultdict(list)
        
        # 扫描测试文件
        for root, dirs, files in os.walk(os.path.join(self.project_path, test_dir)):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        # 提取测试函数
                        test_functions = re.findall(r'def (test_\w+)\(', content)
                        
                        for func in test_functions:
                            signature = f"{file}::{func}"
                            test_signatures[func].append({
                                "file": file_path,
                                "function": func
                            })
                    except Exception as e:
                        logger.error(f"读取文件 {file_path} 失败: {e}")
        
        # 找出重复的测试
        for func_name, locations in test_signatures.items():
            if len(locations) > 1:
                duplicates.append({
                    "function": func_name,
                    "locations": locations,
                    "count": len(locations)
                })
        
        return duplicates
    
    def export_coverage_data(self, output_file: str = "coverage_report.json") -> str:
        """导出覆盖率数据"""
        output_path = os.path.join(self.project_path, output_file)
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "coverage_data": self.coverage_data,
            "analysis": self.analyze_coverage(),
            "history": self.history
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"覆盖率数据已导出: {output_path}")
        
        return output_path


class CoverageReporter:
    """覆盖率报告生成器"""
    
    @staticmethod
    def generate_html_report(coverage_data: Dict, output_dir: str = "./htmlcov") -> str:
        """生成HTML覆盖率报告"""
        # 这里简化实现，实际可以使用coverage.py的HTML报告功能
        os.makedirs(output_dir, exist_ok=True)
        
        index_file = os.path.join(output_dir, "index.html")
        
        # 生成简单的HTML报告
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Coverage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .excellent {{ background-color: #d4edda; }}
        .good {{ background-color: #fff3cd; }}
        .poor {{ background-color: #f8d7da; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Coverage Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <table>
        <tr>
            <th>File</th>
            <th>Coverage</th>
            <th>Lines</th>
            <th>Missing</th>
        </tr>
"""
        
        # 添加文件信息
        for file_path, data in coverage_data.get("files", {}).items():
            summary = data.get("summary", {})
            coverage = summary.get("percent_covered", 0)
            status = "excellent" if coverage >= 80 else ("good" if coverage >= 50 else "poor")
            
            html_content += f"""
        <tr class="{status}">
            <td>{file_path}</td>
            <td>{coverage:.1f}%</td>
            <td>{summary.get('num_statements', 0)}</td>
            <td>{summary.get('missing_lines', 0)}</td>
        </tr>
"""
        
        html_content += """
    </table>
</body>
</html>
"""
        
        with open(index_file, 'w') as f:
            f.write(html_content)
        
        return index_file


# 便捷函数
async def analyze_coverage_quick(project_path: str = ".") -> Dict:
    """快速分析覆盖率"""
    optimizer = CoverageOptimizer(project_path)
    result = await optimizer.run_coverage()
    
    if result.get("success"):
        return optimizer.analyze_coverage()
    else:
        return result


if __name__ == "__main__":
    # 测试代码
    async def test():
        optimizer = CoverageOptimizer(".")
        
        # 运行覆盖率
        result = await optimizer.run_coverage()
        print(f"覆盖率测试结果: {result['success']}")
        
        # 分析覆盖率
        analysis = optimizer.analyze_coverage()
        print(f"\n总体覆盖率: {analysis['summary']['overall_coverage']:.2f}%")
        
        # 生成报告
        report = optimizer.get_coverage_report()
        print(f"\n{report}")
        
        # 获取建议
        suggestions = await optimizer.suggest_tests(max_suggestions=5)
        print(f"\n测试建议: {len(suggestions)}个")
    
    asyncio.run(test())
