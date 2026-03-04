"""
三层Code Review系统
实现自动化代码审查：LLM审查 + 静态分析 + 测试覆盖率检查

架构：
- 第一层：GLM5-Plus自动审查（代码质量、安全、性能）
- 第二层：静态分析（Lint + 类型检查）
- 第三层：测试覆盖率检查

评分标准：
- 90-100: 优秀（自动批准）
- 80-89: 良好（建议通过）
- 70-79: 一般（需要改进）
- <70: 差（建议拒绝）
"""

import os
import json
import asyncio
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx


class CodeReviewer:
    """三层Code Review系统"""

    def __init__(self, repo_path: Optional[str] = None):
        """
        初始化Code Reviewer

        Args:
            repo_path: 仓库路径
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

        # GLM5配置
        self.glm5_api_key = os.getenv("GLM5_API_KEY", "")
        self.glm5_base_url = os.getenv("GLM5_BASE_URL", "https://open.bigmodel.cn/api/paas/v3")
        self.glm5_model = os.getenv("GLM5_MODEL", "glm-4-plus")

        # 评分权重
        self.weights = {"llm": 0.5, "static": 0.3, "test": 0.2}  # LLM审查权重  # 静态分析权重  # 测试覆盖率权重

        # 审查规则
        self.security_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "硬编码密码", "high"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "硬编码API密钥", "high"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "硬编码密钥", "high"),
            (r"eval\s*\(", "使用eval()可能存在代码注入风险", "medium"),
            (r"exec\s*\(", "使用exec()可能存在代码注入风险", "medium"),
            (r"__import__\s*\(", "动态导入可能存在安全风险", "medium"),
            (r"subprocess\..*shell\s*=\s*True", "shell=True可能导致命令注入", "high"),
            (r"cursor\.execute\s*\([^%]*%s", "可能存在SQL注入风险", "high"),
            (r"\.format\s*\([^)]*\+.*\+", "字符串拼接可能导致注入", "medium"),
        ]

        self.performance_patterns = [
            (r"for\s+\w+\s+in\s+range\(len\(", "建议使用enumerate()代替range(len())", "low"),
            (r'\+\s*=\s*["\']', "循环中字符串拼接建议使用list.join()", "medium"),
            (r"import\s+\*", "避免使用import *，可能影响性能", "low"),
            (r"while\s+True:", "确保while True有退出条件", "medium"),
        ]

    async def review_pull_request(self, pr_number: int) -> Dict:
        """
        审查Pull Request

        Args:
            pr_number: PR编号

        Returns:
            审查结果
        """
        print(f"\n[CodeReviewer] 开始审查PR #{pr_number}")

        try:
            # 1. 获取PR的diff
            diff = await self.get_pr_diff(pr_number)
            if not diff:
                return {"success": False, "error": "无法获取PR diff", "pr_number": pr_number}

            print(f"[CodeReviewer] 获取到diff，长度: {len(diff)} 字符")

            # 2. 第一层：GLM5-Plus自动审查
            print(f"[CodeReviewer] 第一层：LLM审查...")
            llm_review = await self.llm_review(diff)

            # 3. 第二层：静态分析
            print(f"[CodeReviewer] 第二层：静态分析...")
            static_review = await self.static_analysis(diff)

            # 4. 第三层：测试覆盖率检查
            print(f"[CodeReviewer] 第三层：测试覆盖率检查...")
            test_review = await self.check_test_coverage(pr_number)

            # 5. 综合评分
            score = self.calculate_score(llm_review, static_review, test_review)

            # 6. 生成评论
            comments = self.generate_comments(llm_review, static_review, test_review)

            # 7. 生成总结
            summary = self.generate_summary(score, llm_review, static_review, test_review)

            result = {
                "success": True,
                "pr_number": pr_number,
                "score": score,
                "approved": score >= 80,
                "layers": {"llm_review": llm_review, "static_review": static_review, "test_review": test_review},
                "comments": comments,
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
            }

            print(f"[CodeReviewer] 审查完成，总分: {score}")

            return result

        except Exception as e:
            print(f"[CodeReviewer] 审查失败: {e}")
            return {"success": False, "error": str(e), "pr_number": pr_number}

    async def get_pr_diff(self, pr_number: int) -> str:
        """
        获取PR的diff

        Args:
            pr_number: PR编号

        Returns:
            diff内容
        """
        try:
            cmd = f"gh pr diff {pr_number}"
            result = subprocess.run(cmd, shell=True, cwd=self.repo_path, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                return result.stdout
            else:
                print(f"[CodeReviewer] 获取diff失败: {result.stderr}")
                return ""

        except Exception as e:
            print(f"[CodeReviewer] 获取diff异常: {e}")
            return ""

    async def llm_review(self, diff: str) -> Dict:
        """
        第一层：GLM5-Plus自动审查

        Args:
            diff: 代码差异

        Returns:
            审查结果
        """
        result = {"score": 0, "issues": [], "suggestions": [], "details": {}}

        try:
            # 1. 安全检查
            security_issues = self._check_security(diff)
            result["details"]["security"] = security_issues

            # 2. 性能检查
            performance_issues = self._check_performance(diff)
            result["details"]["performance"] = performance_issues

            # 3. 代码质量检查
            quality_issues = self._check_code_quality(diff)
            result["details"]["quality"] = quality_issues

            # 4. 如果配置了GLM5 API，进行深度分析
            if self.glm5_api_key:
                deep_analysis = await self._deep_analysis_with_glm5(diff)
                result["details"]["deep_analysis"] = deep_analysis
                result["suggestions"].extend(deep_analysis.get("suggestions", []))

            # 5. 计算分数
            total_issues = len(security_issues) + len(performance_issues) + len(quality_issues)
            high_issues = len([i for i in security_issues if i.get("severity") == "high"])

            # 基础分
            base_score = 100

            # 扣分规则
            score = base_score
            score -= high_issues * 15  # 高危问题每个扣15分
            score -= len([i for i in security_issues if i.get("severity") == "medium"]) * 8
            score -= len(performance_issues) * 3
            score -= len(quality_issues) * 2

            result["score"] = max(0, min(100, score))
            result["issues"] = security_issues + performance_issues + quality_issues

        except Exception as e:
            result["error"] = str(e)
            result["score"] = 70  # 默认分数

        return result

    def _check_security(self, code: str) -> List[Dict]:
        """检查安全问题"""
        issues = []

        for pattern, message, severity in self.security_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                # 获取行号
                line_num = code[: match.start()].count("\n") + 1
                issues.append(
                    {"type": "security", "severity": severity, "message": message, "line": line_num, "code": match.group()}
                )

        return issues

    def _check_performance(self, code: str) -> List[Dict]:
        """检查性能问题"""
        issues = []

        for pattern, message, severity in self.performance_patterns:
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                line_num = code[: match.start()].count("\n") + 1
                issues.append(
                    {"type": "performance", "severity": severity, "message": message, "line": line_num, "code": match.group()}
                )

        return issues

    def _check_code_quality(self, code: str) -> List[Dict]:
        """检查代码质量"""
        issues = []

        # 检查行长度
        for i, line in enumerate(code.split("\n"), 1):
            if len(line) > 100:
                issues.append({"type": "quality", "severity": "low", "message": f"行长度超过100字符 ({len(line)})", "line": i})

        # 检查TODO和FIXME
        todo_pattern = r"#\s*(TODO|FIXME|HACK|XXX):?\s*(.+)"
        matches = re.finditer(todo_pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[: match.start()].count("\n") + 1
            issues.append(
                {"type": "quality", "severity": "low", "message": f"发现待办项: {match.group(2).strip()}", "line": line_num}
            )

        return issues

    async def _deep_analysis_with_glm5(self, diff: str) -> Dict:
        """
        使用GLM5进行深度分析

        Args:
            diff: 代码差异

        Returns:
            分析结果
        """
        try:
            # 限制diff长度
            max_chars = 8000
            if len(diff) > max_chars:
                diff = diff[:max_chars] + "\n... (truncated)"

            prompt = f"""作为一个资深的代码审查专家，请分析以下代码变更：

```diff
{diff}
```

请从以下几个方面进行评价：
1. 代码可读性和可维护性
2. 是否遵循最佳实践
3. 潜在的bug或逻辑错误
4. 改进建议

请以JSON格式返回分析结果：
{{
  "score": <0-100的评分>,
  "readability": "<可读性评价>",
  "best_practices": "<最佳实践评价>",
  "potential_bugs": ["<潜在bug列表>"],
  "suggestions": ["<改进建议列表>"]
}}

只返回JSON，不要包含其他内容。"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.glm5_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.glm5_api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.glm5_model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的代码审查助手，擅长分析代码质量并提供改进建议。"},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # 尝试解析JSON
                    try:
                        # 提取JSON部分
                        json_match = re.search(r"\{[\s\S]*\}", content)
                        if json_match:
                            analysis = json.loads(json_match.group())
                            return analysis
                    except Exception as e:
                        pass

                return {"error": "GLM5分析失败", "suggestions": []}

        except Exception as e:
            print(f"[CodeReviewer] GLM5分析异常: {e}")
            return {"error": str(e), "suggestions": []}

    async def static_analysis(self, diff: str) -> Dict:
        """
        第二层：静态分析（Lint + 类型检查）

        Args:
            diff: 代码差异

        Returns:
            静态分析结果
        """
        result = {"score": 0, "lint_errors": 0, "type_errors": 0, "details": []}

        try:
            # 1. 检查是否是Python代码
            if not self._is_python_diff(diff):
                result["score"] = 85  # 非Python代码给默认分
                result["message"] = "非Python代码，跳过静态分析"
                return result

            # 2. 提取变更的文件
            changed_files = self._extract_changed_files(diff)

            # 3. 运行flake8
            lint_result = await self._run_flake8(changed_files)
            result["details"].append(lint_result)
            result["lint_errors"] = lint_result.get("error_count", 0)

            # 4. 运行mypy
            type_result = await self._run_mypy(changed_files)
            result["details"].append(type_result)
            result["type_errors"] = type_result.get("error_count", 0)

            # 5. 计算分数
            total_errors = result["lint_errors"] + result["type_errors"]

            if total_errors == 0:
                result["score"] = 100
            elif total_errors <= 3:
                result["score"] = 90
            elif total_errors <= 10:
                result["score"] = 80
            elif total_errors <= 20:
                result["score"] = 70
            else:
                result["score"] = max(50, 100 - total_errors * 2)

        except Exception as e:
            result["error"] = str(e)
            result["score"] = 75  # 默认分数

        return result

    def _is_python_diff(self, diff: str) -> bool:
        """检查是否是Python代码"""
        return "def " in diff or "class " in diff or ".py" in diff

    def _extract_changed_files(self, diff: str) -> List[str]:
        """提取变更的文件列表"""
        files = []
        pattern = r"^\+\+\+ b/(.+)$"

        for match in re.finditer(pattern, diff, re.MULTILINE):
            file_path = match.group(1)
            if file_path.endswith(".py"):
                files.append(file_path)

        return files

    async def _run_flake8(self, files: List[str]) -> Dict:
        """运行flake8检查"""
        result = {"tool": "flake8", "error_count": 0, "errors": []}

        if not files:
            return result

        try:
            # 创建临时检查
            for file in files:
                file_path = self.repo_path / file
                if not file_path.exists():
                    continue

                cmd = f"flake8 {file} --max-line-length=100 --format=json"
                proc = subprocess.run(cmd, shell=True, cwd=self.repo_path, capture_output=True, text=True, timeout=30)

                if proc.stdout:
                    try:
                        errors = json.loads(proc.stdout)
                        for file_name, file_errors in errors.items():
                            result["errors"].extend(file_errors)
                            result["error_count"] += len(file_errors)
                    except Exception as e:
                        # 如果不是JSON格式，解析文本
                        lines = proc.stdout.strip().split("\n")
                        result["error_count"] += len([l for l in lines if l])
                        result["errors"] = lines

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _run_mypy(self, files: List[str]) -> Dict:
        """运行mypy类型检查"""
        result = {"tool": "mypy", "error_count": 0, "errors": []}

        if not files:
            return result

        try:
            for file in files:
                file_path = self.repo_path / file
                if not file_path.exists():
                    continue

                cmd = f"mypy {file} --no-error-summary 2>&1"
                proc = subprocess.run(cmd, shell=True, cwd=self.repo_path, capture_output=True, text=True, timeout=30)

                output = proc.stdout + proc.stderr
                error_lines = [line for line in output.split("\n") if "error:" in line.lower()]

                result["errors"].extend(error_lines)
                result["error_count"] += len(error_lines)

        except Exception as e:
            result["error"] = str(e)

        return result

    async def check_test_coverage(self, pr_number: int) -> Dict:
        """
        第三层：测试覆盖率检查

        Args:
            pr_number: PR编号

        Returns:
            测试覆盖率结果
        """
        result = {"score": 0, "coverage": 0, "new_coverage": 0, "details": {}}

        try:
            # 1. 获取PR的变更文件
            changed_files = await self._get_pr_changed_files(pr_number)

            # 2. 运行pytest with coverage
            coverage_result = await self._run_pytest_coverage()

            if coverage_result.get("success"):
                result["coverage"] = coverage_result.get("total_coverage", 0)
                result["new_coverage"] = coverage_result.get("new_coverage", 0)
                result["details"] = coverage_result

                # 3. 计算分数
                # 基础覆盖率分数
                base_score = result["coverage"]

                # 新代码覆盖率奖励
                if result["new_coverage"] >= 90:
                    base_score += 10
                elif result["new_coverage"] >= 80:
                    base_score += 5

                result["score"] = min(100, base_score)
            else:
                # 如果没有测试，给默认分
                result["score"] = 70
                result["message"] = "未找到测试文件"

        except Exception as e:
            result["error"] = str(e)
            result["score"] = 70  # 默认分数

        return result

    async def _get_pr_changed_files(self, pr_number: int) -> List[str]:
        """获取PR变更的文件列表"""
        try:
            cmd = f"gh pr view {pr_number} --json files --jq '.files[].path'"
            result = subprocess.run(cmd, shell=True, cwd=self.repo_path, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return result.stdout.strip().split("\n")

        except Exception as e:
            print(f"[CodeReviewer] 获取PR文件失败: {e}")

        return []

    async def _run_pytest_coverage(self) -> Dict:
        """运行pytest覆盖率检查"""
        result = {"success": False, "total_coverage": 0, "new_coverage": 0}

        try:
            # 检查是否有tests目录
            tests_dir = self.repo_path / "tests"
            if not tests_dir.exists():
                return result

            # 运行pytest
            cmd = "pytest tests/ --cov=. --cov-report=json --cov-report=term-missing -v"
            proc = subprocess.run(cmd, shell=True, cwd=self.repo_path, capture_output=True, text=True, timeout=120)

            # 解析覆盖率报告
            coverage_file = self.repo_path / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    coverage_data = json.load(f)

                result["total_coverage"] = coverage_data.get("totals", {}).get("percent_covered", 0)
                result["success"] = True

            # 从输出中提取覆盖率
            if "TOTAL" in proc.stdout:
                match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+%)", proc.stdout)
                if match:
                    result["total_coverage"] = int(match.group(1).replace("%", ""))
                    result["success"] = True

        except Exception as e:
            result["error"] = str(e)

        return result

    def calculate_score(self, llm_review: Dict, static_review: Dict, test_review: Dict) -> int:
        """
        计算综合评分

        Args:
            llm_review: LLM审查结果
            static_review: 静态分析结果
            test_review: 测试覆盖率结果

        Returns:
            综合评分
        """
        llm_score = llm_review.get("score", 70)
        static_score = static_review.get("score", 70)
        test_score = test_review.get("score", 70)

        # 加权平均
        total_score = (
            llm_score * self.weights["llm"] + static_score * self.weights["static"] + test_score * self.weights["test"]
        )

        return int(round(total_score))

    def generate_comments(self, llm_review: Dict, static_review: Dict, test_review: Dict) -> List[Dict]:
        """
        生成审查评论

        Args:
            llm_review: LLM审查结果
            static_review: 静态分析结果
            test_review: 测试覆盖率结果

        Returns:
            评论列表
        """
        comments = []

        # 1. 安全问题评论（高优先级）
        security_issues = llm_review.get("details", {}).get("security", [])
        for issue in security_issues:
            if issue.get("severity") == "high":
                comments.append(
                    {
                        "type": "security",
                        "severity": "high",
                        "message": f"🔒 **安全问题**: {issue['message']}",
                        "line": issue.get("line"),
                        "suggestion": "请立即修复此安全问题",
                    }
                )

        # 2. 性能问题评论
        performance_issues = llm_review.get("details", {}).get("performance", [])
        for issue in performance_issues[:5]:  # 只显示前5个
            comments.append(
                {
                    "type": "performance",
                    "severity": issue.get("severity", "low"),
                    "message": f"⚡ **性能建议**: {issue['message']}",
                    "line": issue.get("line"),
                }
            )

        # 3. 静态分析错误
        for detail in static_review.get("details", []):
            if detail.get("error_count", 0) > 0:
                tool = detail.get("tool", "unknown")
                comments.append(
                    {
                        "type": "static_analysis",
                        "severity": "medium",
                        "message": f"🔍 **{tool}**: 发现 {detail['error_count']} 个问题",
                        "details": detail.get("errors", [])[:3],  # 只显示前3个
                    }
                )

        # 4. 测试覆盖率评论
        if test_review.get("new_coverage", 0) < 80:
            comments.append(
                {
                    "type": "test_coverage",
                    "severity": "medium",
                    "message": f"🧪 **测试覆盖率**: 新代码覆盖率为 {test_review.get('new_coverage', 0)}%，建议提升至80%以上",
                }
            )

        # 5. 改进建议
        suggestions = llm_review.get("suggestions", [])
        for suggestion in suggestions[:3]:  # 只显示前3个
            comments.append({"type": "suggestion", "severity": "low", "message": f"💡 **建议**: {suggestion}"})

        return comments

    def generate_summary(self, score: int, llm_review: Dict, static_review: Dict, test_review: Dict) -> str:
        """
        生成审查总结

        Args:
            score: 综合评分
            llm_review: LLM审查结果
            static_review: 静态分析结果
            test_review: 测试覆盖率结果

        Returns:
            总结文本
        """
        # 确定评级
        if score >= 90:
            grade = "优秀 ⭐⭐⭐⭐⭐"
            emoji = "🎉"
        elif score >= 80:
            grade = "良好 ⭐⭐⭐⭐"
            emoji = "✅"
        elif score >= 70:
            grade = "一般 ⭐⭐⭐"
            emoji = "⚠️"
        else:
            grade = "需要改进 ⭐⭐"
            emoji = "❌"

        summary = f"""## Code Review 总结 {emoji}

**综合评分**: {score}/100 - {grade}

### 各层审查结果：

1. **🤖 LLM审查** ({llm_review.get('score', 0)}/100)
   - 安全问题: {len(llm_review.get('details', {}).get('security', []))} 个
   - 性能问题: {len(llm_review.get('details', {}).get('performance', []))} 个
   - 代码质量: {len(llm_review.get('details', {}).get('quality', []))} 个问题

2. **🔍 静态分析** ({static_review.get('score', 0)}/100)
   - Lint错误: {static_review.get('lint_errors', 0)} 个
   - 类型错误: {static_review.get('type_errors', 0)} 个

3. **🧪 测试覆盖率** ({test_review.get('score', 0)}/100)
   - 总覆盖率: {test_review.get('coverage', 0)}%
   - 新代码覆盖率: {test_review.get('new_coverage', 0)}%

### 建议：
"""

        if score >= 80:
            summary += "✅ 代码质量良好，建议通过审查\n"
        elif score >= 70:
            summary += "⚠️ 代码质量一般，建议进行改进后再合并\n"
        else:
            summary += "❌ 代码质量较差，建议重新审查后再提交\n"

        # 添加主要问题
        if llm_review.get("issues"):
            summary += "\n**主要问题**:\n"
            for issue in llm_review["issues"][:3]:
                summary += f"- {issue['message']}\n"

        return summary


# 全局实例
code_reviewer = None


def get_code_reviewer(repo_path: Optional[str] = None) -> CodeReviewer:
    """
    获取Code Reviewer单例

    Args:
        repo_path: 仓库路径

    Returns:
        CodeReviewer实例
    """
    global code_reviewer
    if not code_reviewer:
        code_reviewer = CodeReviewer(repo_path)
    return code_reviewer
