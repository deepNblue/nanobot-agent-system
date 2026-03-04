"""
测试用例生成器模块 - 使用AI自动生成测试用例
支持单元测试、集成测试、端到端测试
"""

import os
import re
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import ast

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """测试用例生成器 - 使用AI自动生成测试用例"""
    
    def __init__(self, model_adapter):
        """
        初始化测试用例生成器
        
        Args:
            model_adapter: 模型适配器实例（ModelAdapter）
        """
        self.model_adapter = model_adapter
        self.test_templates = self._load_templates()
        self.generation_stats = {
            "total_generated": 0,
            "successful": 0,
            "failed": 0,
            "by_type": {}
        }
    
    def _load_templates(self) -> Dict[str, str]:
        """加载测试模板"""
        return {
            "unit_test": """Generate comprehensive unit tests for the following Python code:

```python
{code}
```

Requirements:
1. Test all public methods and functions
2. Include edge cases and boundary conditions
3. Test error handling and exceptions
4. Use parametrize for multiple test scenarios
5. Add descriptive docstrings for each test
6. Use pytest fixtures where appropriate
7. Mock external dependencies
8. Achieve >90% code coverage

Generate only the test code following pytest conventions.
Use the template:
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
# Add necessary imports

class TestClassName:
    \"\"\"Test suite for ClassName\"\"\"
    
    @pytest.fixture
    def setup(self):
        \"\"\"Test fixture\"\"\"
        # Setup code
        pass
    
    def test_function_normal(self, setup):
        \"\"\"Test normal case\"\"\"
        # Test code
        pass
    
    def test_function_edge_case(self, setup):
        \"\"\"Test edge case\"\"\"
        # Test code
        pass
    
    def test_function_error(self, setup):
        \"\"\"Test error handling\"\"\"
        # Test code
        pass
```
""",
            
            "integration_test": """Generate integration tests for the following API:

API Description: {api_description}

Code:
```python
{code}
```

Requirements:
1. Test API endpoints (GET, POST, PUT, DELETE)
2. Test happy path scenarios
3. Test error cases (400, 401, 403, 404, 500)
4. Test authentication and authorization
5. Test request/response validation
6. Test database interactions
7. Use pytest and aiohttp (for async APIs)
8. Mock external services but test real integrations
9. Clean up test data after tests

Generate only the test code following pytest conventions.
Use the template:
```python
import pytest
import aiohttp
from unittest.mock import Mock, patch
# Add necessary imports

class TestAPIIntegration:
    \"\"\"Integration tests for API endpoints\"\"\"
    
    @pytest.fixture
    async def client(self):
        \"\"\"Test client fixture\"\"\"
        # Setup test client
        pass
    
    @pytest.mark.asyncio
    async def test_endpoint_success(self, client):
        \"\"\"Test successful API call\"\"\"
        # Test code
        pass
    
    @pytest.mark.asyncio
    async def test_endpoint_error(self, client):
        \"\"\"Test API error handling\"\"\"
        # Test code
        pass
```
""",
            
            "e2e_test": """Generate end-to-end tests for the following feature:

Feature: {feature_description}

Code Reference:
```python
{code}
```

Requirements:
1. Test complete user workflow from start to finish
2. Test multiple user scenarios
3. Use Playwright or Selenium for browser automation
4. Test UI interactions and state changes
5. Add screenshots on test failure
6. Test responsive design (mobile/desktop)
7. Test accessibility features
8. Clean up test data after tests
9. Handle async operations and wait times

Generate only the test code following pytest conventions.
Use the template:
```python
import pytest
from playwright.sync_api import Page, expect
# Or from selenium import webdriver
# Add necessary imports

class TestFeatureE2E:
    \"\"\"End-to-end tests for Feature\"\"\"
    
    @pytest.fixture
    def browser(self, page: Page):
        \"\"\"Browser fixture\"\"\"
        # Setup browser
        pass
    
    def test_user_workflow_happy_path(self, browser):
        \"\"\"Test happy path user workflow\"\"\"
        # Test code
        pass
    
    def test_user_workflow_error_handling(self, browser):
        \"\"\"Test error handling in user workflow\"\"\"
        # Test code
        pass
```
""",
            
            "performance_test": """Generate performance tests for the following code:

```python
{code}
```

Requirements:
1. Test response time under normal load
2. Test throughput (requests per second)
3. Test concurrent access
4. Test resource usage (CPU, memory)
5. Identify performance bottlenecks
6. Use pytest-benchmark or locust
7. Set performance thresholds
8. Test with different data sizes

Generate only the test code.
Use the template:
```python
import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
# Add necessary imports

class TestPerformance:
    \"\"\"Performance tests\"\"\"
    
    def test_response_time(self, benchmark):
        \"\"\"Test response time\"\"\"
        # Test code
        pass
    
    def test_concurrent_access(self):
        \"\"\"Test concurrent access\"\"\"
        # Test code
        pass
    
    def test_throughput(self):
        \"\"\"Test throughput\"\"\"
        # Test code
        pass
```
"""
        }
    
    async def generate_tests(
        self,
        code: str,
        test_type: str = "unit_test",
        context: Optional[Dict] = None,
        model: str = "glm5-turbo",
        temperature: float = 0.3,
        max_tokens: int = 3000
    ) -> Dict:
        """
        生成测试用例
        
        Args:
            code: 要测试的代码
            test_type: 测试类型（unit_test, integration_test, e2e_test, performance_test）
            context: 额外上下文信息
            model: 使用的模型（默认glm5-turbo，快速且便宜）
            temperature: 生成温度（低温度保证一致性）
            max_tokens: 最大token数
        
        Returns:
            生成结果字典
        """
        logger.info(f"开始生成测试用例: type={test_type}")
        
        # 1. 验证测试类型
        if test_type not in self.test_templates:
            return {
                "success": False,
                "error": f"未知的测试类型: {test_type}",
                "available_types": list(self.test_templates.keys())
            }
        
        # 2. 准备上下文
        context = context or {}
        
        # 3. 构建prompt
        template = self.test_templates[test_type]
        prompt = template.format(
            code=code,
            api_description=context.get("api_description", ""),
            feature_description=context.get("feature_description", "")
        )
        
        # 4. 调用AI模型生成测试
        try:
            result = await self.model_adapter.call_model(
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if not result.get("success"):
                self._update_stats(test_type, success=False)
                return {
                    "success": False,
                    "error": result.get("error", "模型调用失败"),
                    "test_type": test_type
                }
            
            # 5. 提取测试代码
            raw_content = result["content"]
            test_code = self._extract_code(raw_content)
            
            # 6. 验证测试代码
            validation = self._validate_test(test_code, test_type)
            
            # 7. 分析测试覆盖范围
            coverage_analysis = self._analyze_test_coverage(test_code, code)
            
            # 8. 更新统计
            self._update_stats(test_type, success=True)
            
            logger.info(f"测试用例生成成功: type={test_type}, valid={validation['is_valid']}")
            
            return {
                "success": True,
                "test_code": test_code,
                "test_type": test_type,
                "raw_content": raw_content,
                "validation": validation,
                "coverage_analysis": coverage_analysis,
                "model": model,
                "usage": result.get("usage", {}),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成测试用例失败: {e}", exc_info=True)
            self._update_stats(test_type, success=False)
            return {
                "success": False,
                "error": str(e),
                "test_type": test_type
            }
    
    def _extract_code(self, content: str) -> str:
        """从内容中提取Python代码"""
        # 提取```python ... ```之间的内容
        pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if matches:
            # 合并所有代码块
            return '\n\n'.join(matches)
        
        # 如果没有找到代码块，尝试提取所有```...```之间的内容
        pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if matches:
            return '\n\n'.join(matches)
        
        # 如果还是没有，返回整个内容（可能整个就是代码）
        return content
    
    def _validate_test(self, test_code: str, test_type: str) -> Dict:
        """验证测试代码的质量"""
        validation = {
            "is_valid": True,
            "score": 0,
            "checks": {}
        }
        
        # 基本检查
        checks = {
            "has_import_pytest": "import pytest" in test_code,
            "has_test_function": "def test_" in test_code,
            "has_assertion": "assert " in test_code,
            "has_docstring": '"""' in test_code or "'''" in test_code,
            "has_class": "class Test" in test_code,
            "has_fixture": "@pytest.fixture" in test_code,
            "proper_indentation": self._check_indentation(test_code),
            "syntax_valid": self._check_syntax(test_code)
        }
        
        validation["checks"] = checks
        
        # 计算得分
        score = sum(checks.values())
        validation["score"] = score
        
        # 根据测试类型调整验证标准
        if test_type == "unit_test":
            required = ["has_import_pytest", "has_test_function", "has_assertion"]
        elif test_type == "integration_test":
            required = ["has_import_pytest", "has_test_function", "has_assertion", "has_class"]
        elif test_type == "e2e_test":
            required = ["has_import_pytest", "has_test_function", "has_assertion", "has_class"]
        else:
            required = ["has_import_pytest", "has_test_function", "has_assertion"]
        
        # 检查必需项
        validation["is_valid"] = all(checks.get(req, False) for req in required)
        
        return validation
    
    def _check_indentation(self, code: str) -> bool:
        """检查代码缩进"""
        lines = code.split('\n')
        for line in lines:
            if line and not line[0].isspace() and not line[0] in ['#', '\n']:
                # 第一行不需要缩进
                continue
            if line.startswith(' ') and not line.startswith('    '):
                # 缩进应该是4的倍数
                return False
        return True
    
    def _check_syntax(self, code: str) -> bool:
        """检查Python语法"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _analyze_test_coverage(self, test_code: str, source_code: str) -> Dict:
        """分析测试覆盖范围"""
        analysis = {
            "test_functions": [],
            "tested_functions": [],
            "source_functions": [],
            "coverage_estimate": 0
        }
        
        # 提取测试函数
        test_pattern = r'def (test_\w+)\('
        analysis["test_functions"] = re.findall(test_pattern, test_code)
        
        # 提取源代码函数
        try:
            source_tree = ast.parse(source_code)
            for node in ast.walk(source_tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["source_functions"].append(node.name)
        except:
            pass
        
        # 检查哪些函数被测试
        for func in analysis["source_functions"]:
            if func in test_code:
                analysis["tested_functions"].append(func)
        
        # 估算覆盖率
        if analysis["source_functions"]:
            analysis["coverage_estimate"] = (
                len(analysis["tested_functions"]) / len(analysis["source_functions"]) * 100
            )
        
        return analysis
    
    def _update_stats(self, test_type: str, success: bool):
        """更新生成统计"""
        self.generation_stats["total_generated"] += 1
        
        if success:
            self.generation_stats["successful"] += 1
        else:
            self.generation_stats["failed"] += 1
        
        if test_type not in self.generation_stats["by_type"]:
            self.generation_stats["by_type"][test_type] = {"total": 0, "successful": 0}
        
        self.generation_stats["by_type"][test_type]["total"] += 1
        if success:
            self.generation_stats["by_type"][test_type]["successful"] += 1
    
    async def generate_from_file(
        self,
        file_path: str,
        test_type: str = "unit_test",
        output_dir: str = "./tests",
        context: Optional[Dict] = None
    ) -> Dict:
        """
        从文件生成测试用例
        
        Args:
            file_path: 源代码文件路径
            test_type: 测试类型
            output_dir: 输出目录
            context: 额外上下文
        
        Returns:
            生成结果
        """
        logger.info(f"从文件生成测试: {file_path}")
        
        # 1. 读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"无法读取文件: {e}"
            }
        
        # 2. 生成测试
        result = await self.generate_tests(code, test_type, context)
        
        if not result.get("success"):
            return result
        
        # 3. 保存测试文件
        test_filename = self._generate_test_filename(file_path)
        saved_path = await self.save_test(
            result["test_code"],
            test_filename,
            output_dir
        )
        
        result["saved_path"] = saved_path
        
        return result
    
    def _generate_test_filename(self, source_file: str) -> str:
        """生成测试文件名"""
        # 提取文件名（不含扩展名）
        basename = os.path.basename(source_file)
        name_without_ext = os.path.splitext(basename)[0]
        
        # 生成测试文件名
        return f"test_{name_without_ext}.py"
    
    async def save_test(
        self,
        test_code: str,
        filename: str,
        output_dir: str = "./tests"
    ) -> str:
        """
        保存测试文件
        
        Args:
            test_code: 测试代码
            filename: 文件名
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        # 创建目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 文件路径
        filepath = os.path.join(output_dir, filename)
        
        # 添加文件头
        header = f'"""\n自动生成的测试文件\n生成时间: {datetime.now().isoformat()}\n文件: {filename}\n"""\n\n'
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + test_code)
        
        logger.info(f"测试文件已保存: {filepath}")
        
        return filepath
    
    async def batch_generate(
        self,
        files: List[str],
        test_type: str = "unit_test",
        output_dir: str = "./tests",
        max_concurrent: int = 3
    ) -> Dict:
        """
        批量生成测试用例
        
        Args:
            files: 文件列表
            test_type: 测试类型
            output_dir: 输出目录
            max_concurrent: 最大并发数
        
        Returns:
            批量生成结果
        """
        logger.info(f"批量生成测试: {len(files)}个文件")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(file_path: str):
            async with semaphore:
                return await self.generate_from_file(
                    file_path,
                    test_type,
                    output_dir
                )
        
        # 并发生成
        tasks = [generate_with_semaphore(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        summary = {
            "total": len(files),
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                summary["failed"] += 1
                summary["results"].append({
                    "file": files[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                if result.get("success"):
                    summary["successful"] += 1
                else:
                    summary["failed"] += 1
                summary["results"].append({
                    "file": files[i],
                    **result
                })
        
        logger.info(f"批量生成完成: 成功={summary['successful']}, 失败={summary['failed']}")
        
        return summary
    
    def get_stats(self) -> Dict:
        """获取生成统计信息"""
        return {
            **self.generation_stats,
            "success_rate": (
                self.generation_stats["successful"] / max(self.generation_stats["total_generated"], 1) * 100
            )
        }
    
    async def improve_test(
        self,
        existing_test: str,
        source_code: str,
        issues: Optional[List[str]] = None
    ) -> Dict:
        """
        改进现有测试
        
        Args:
            existing_test: 现有测试代码
            source_code: 源代码
            issues: 已知问题列表
        
        Returns:
            改进后的测试
        """
        prompt = f"""Improve the following test code:

Source Code:
```python
{source_code}
```

Current Test:
```python
{existing_test}
```

{f"Known Issues: {', '.join(issues)}" if issues else ""}

Please improve the test by:
1. Adding missing test cases
2. Improving code coverage
3. Fixing any issues
4. Adding better assertions
5. Improving test organization
6. Adding edge cases

Generate only the improved test code.
"""
        
        result = await self.model_adapter.call_model(
            model="glm5-turbo",
            prompt=prompt,
            temperature=0.3,
            max_tokens=3000
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "模型调用失败")
            }
        
        improved_test = self._extract_code(result["content"])
        
        return {
            "success": True,
            "improved_test": improved_test,
            "original_test": existing_test,
            "usage": result.get("usage", {})
        }


class TestCodeAnalyzer:
    """测试代码分析器"""
    
    @staticmethod
    def analyze_test_quality(test_code: str) -> Dict:
        """分析测试代码质量"""
        metrics = {
            "lines_of_code": len(test_code.split('\n')),
            "test_count": len(re.findall(r'def test_', test_code)),
            "assertion_count": len(re.findall(r'assert ', test_code)),
            "fixture_count": len(re.findall(r'@pytest.fixture', test_code)),
            "has_parametrize": '@pytest.mark.parametrize' in test_code,
            "has_asyncio": '@pytest.mark.asyncio' in test_code,
            "mock_usage": 'Mock(' in test_code or 'patch(' in test_code,
            "docstring_coverage": TestCodeAnalyzer._check_docstring_coverage(test_code)
        }
        
        # 计算质量得分
        score = 0
        score += min(metrics["test_count"] * 10, 50)  # 最多50分
        score += min(metrics["assertion_count"] * 5, 30)  # 最多30分
        score += 10 if metrics["has_parametrize"] else 0
        score += 10 if metrics["mock_usage"] else 0
        
        metrics["quality_score"] = min(score, 100)
        
        return metrics
    
    @staticmethod
    def _check_docstring_coverage(test_code: str) -> float:
        """检查文档字符串覆盖率"""
        test_functions = re.findall(r'def (test_\w+)\(', test_code)
        if not test_functions:
            return 0.0
        
        # 简化检查：统计有多少函数后面紧跟文档字符串
        covered = 0
        for func in test_functions:
            pattern = rf'def {func}\(.*?\):\s*"""'
            if re.search(pattern, test_code, re.DOTALL):
                covered += 1
        
        return covered / len(test_functions) * 100


# 便捷函数
async def generate_test_quick(
    code: str,
    test_type: str = "unit_test",
    model_adapter=None
) -> Dict:
    """快速生成测试用例"""
    if model_adapter is None:
        from model_adapter import ModelAdapter
        model_adapter = ModelAdapter()
    
    generator = TestCaseGenerator(model_adapter)
    return await generator.generate_tests(code, test_type)


if __name__ == "__main__":
    # 测试代码
    async def test():
        from model_adapter import ModelAdapter
        
        adapter = ModelAdapter()
        generator = TestCaseGenerator(adapter)
        
        # 测试代码示例
        sample_code = """
def add(a, b):
    \"\"\"Add two numbers\"\"\"
    return a + b

def divide(a, b):
    \"\"\"Divide two numbers\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        
        # 生成测试
        result = await generator.generate_tests(sample_code, "unit_test")
        
        if result["success"]:
            print("生成的测试代码:")
            print(result["test_code"])
            print(f"\n验证结果: {result['validation']}")
            print(f"\n覆盖分析: {result['coverage_analysis']}")
        else:
            print(f"生成失败: {result['error']}")
        
        # 获取统计
        print(f"\n生成统计: {generator.get_stats()}")
    
    asyncio.run(test())
