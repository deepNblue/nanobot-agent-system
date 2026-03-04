"""
CI/CD集成模块
集成GitHub Actions，提供CI状态检查、失败分析、自动重试等功能

功能：
- 检查CI运行状态
- 获取CI日志
- 分析失败原因（使用GLM5）
- 自动重试失败的CI
- 通知CI状态

配置：
- CI检查间隔：10分钟
- 自动重试次数：最多3次
- 通知方式：控制台日志
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
import re


class CICDIntegration:
    """CI/CD集成"""
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        初始化CI/CD集成
        
        Args:
            repo_path: 仓库路径
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        
        # GLM5配置
        self.glm5_api_key = os.getenv("GLM5_API_KEY", "")
        self.glm5_base_url = os.getenv("GLM5_BASE_URL", "https://open.bigmodel.cn/api/paas/v3")
        self.glm5_model = os.getenv("GLM5_MODEL", "glm-4-plus")
        
        # CI配置
        self.max_retry_count = 3
        self.check_interval = 600  # 10分钟
        self.retry_cooldown = 300  # 5分钟冷却
        
        # CI状态缓存
        self._ci_cache: Dict[str, Dict] = {}
        self._last_check: Dict[str, datetime] = {}
    
    async def check_ci_status(self, branch: str) -> Dict:
        """
        检查CI状态
        
        Args:
            branch: 分支名称
        
        Returns:
            CI状态信息
        """
        print(f"\n[CICD] 检查分支 {branch} 的CI状态...")
        
        try:
            # 1. 获取最新的CI运行
            cmd = f"gh run list --branch {branch} --limit 5 --json status,conclusion,id,createdAt,displayTitle,workflowName,htmlUrl"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"获取CI状态失败: {result.stderr}",
                    "branch": branch
                }
            
            runs = json.loads(result.stdout) if result.stdout else []
            
            if not runs:
                return {
                    "success": True,
                    "branch": branch,
                    "status": "no_runs",
                    "message": "未找到CI运行记录"
                }
            
            # 2. 分析最新运行
            latest_run = runs[0]
            
            status_info = {
                "success": True,
                "branch": branch,
                "run_id": latest_run.get("id"),
                "status": latest_run.get("status"),
                "conclusion": latest_run.get("conclusion"),
                "workflow": latest_run.get("workflowName"),
                "title": latest_run.get("displayTitle"),
                "url": latest_run.get("htmlUrl"),
                "created_at": latest_run.get("createdAt"),
                "is_running": latest_run.get("status") in ["queued", "in_progress"],
                "is_success": latest_run.get("conclusion") == "success",
                "is_failed": latest_run.get("conclusion") in ["failure", "cancelled", "timed_out"]
            }
            
            # 3. 更新缓存
            self._ci_cache[branch] = status_info
            self._last_check[branch] = datetime.now()
            
            print(f"[CICD] CI状态: {status_info['status']}, 结论: {status_info.get('conclusion', 'N/A')}")
            
            return status_info
            
        except Exception as e:
            print(f"[CICD] 检查CI状态异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "branch": branch
            }
    
    async def get_ci_logs(self, run_id: int, max_lines: int = 500) -> Dict:
        """
        获取CI日志
        
        Args:
            run_id: 运行ID
            max_lines: 最大行数
        
        Returns:
            日志内容
        """
        print(f"\n[CICD] 获取CI运行 {run_id} 的日志...")
        
        try:
            # 1. 获取运行详情
            cmd = f"gh run view {run_id} --json jobs,conclusion,status"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"获取运行详情失败: {result.stderr}"
                }
            
            run_details = json.loads(result.stdout)
            
            # 2. 获取失败任务的日志
            logs = []
            for job in run_details.get("jobs", []):
                if job.get("conclusion") == "failure":
                    job_name = job.get("name")
                    job_id = job.get("id")
                    
                    print(f"[CICD] 获取失败任务日志: {job_name}")
                    
                    # 获取任务日志
                    cmd = f"gh run view {run_id} --job {job_id} --log 2>&1 | head -n {max_lines}"
                    log_result = subprocess.run(
                        cmd,
                        shell=True,
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    logs.append({
                        "job_name": job_name,
                        "job_id": job_id,
                        "log": log_result.stdout
                    })
            
            return {
                "success": True,
                "run_id": run_id,
                "jobs": logs,
                "total_jobs": len(run_details.get("jobs", [])),
                "failed_jobs": len([j for j in run_details.get("jobs", []) if j.get("conclusion") == "failure"])
            }
            
        except Exception as e:
            print(f"[CICD] 获取日志异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_ci_failure(self, run_id: int) -> Dict:
        """
        分析CI失败原因
        
        Args:
            run_id: 运行ID
        
        Returns:
            失败分析结果
        """
        print(f"\n[CICD] 分析CI运行 {run_id} 的失败原因...")
        
        try:
            # 1. 获取失败日志
            logs_result = await self.get_ci_logs(run_id)
            
            if not logs_result.get("success"):
                return {
                    "success": False,
                    "error": "无法获取CI日志"
                }
            
            # 2. 提取关键错误信息
            error_messages = []
            for job in logs_result.get("jobs", []):
                log_text = job.get("log", "")
                
                # 提取错误行
                error_patterns = [
                    r'ERROR:.*',
                    r'FAILED.*',
                    r'Error:.*',
                    r'Exception:.*',
                    r'Traceback.*',
                    r'fatal:.*'
                ]
                
                for pattern in error_patterns:
                    matches = re.findall(pattern, log_text, re.MULTILINE | re.IGNORECASE)
                    error_messages.extend(matches[:10])  # 每种错误最多10条
            
            # 3. 使用GLM5分析失败原因
            analysis = await self._analyze_with_glm5(error_messages, logs_result)
            
            result = {
                "success": True,
                "run_id": run_id,
                "failure_reason": analysis.get("reason", "未知"),
                "error_type": analysis.get("error_type", "unknown"),
                "suggested_fix": analysis.get("fix", "请检查CI日志"),
                "confidence": analysis.get("confidence", 0.5),
                "error_messages": error_messages[:20],  # 最多返回20条
                "logs": logs_result
            }
            
            print(f"[CICD] 失败原因: {result['failure_reason']}")
            print(f"[CICD] 建议修复: {result['suggested_fix']}")
            
            return result
            
        except Exception as e:
            print(f"[CICD] 分析失败异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _analyze_with_glm5(
        self,
        error_messages: List[str],
        logs_result: Dict
    ) -> Dict:
        """
        使用GLM5分析失败原因
        
        Args:
            error_messages: 错误消息列表
            logs_result: 日志结果
        
        Returns:
            分析结果
        """
        if not self.glm5_api_key:
            # 如果没有API key，使用规则分析
            return self._rule_based_analysis(error_messages)
        
        try:
            # 准备错误信息
            error_text = "\n".join(error_messages[:30])  # 最多30条
            
            prompt = f"""作为一个CI/CD专家，请分析以下CI失败的原因：

错误信息：
```
{error_text}
```

失败任务数: {logs_result.get('failed_jobs', 0)}
总任务数: {logs_result.get('total_jobs', 0)}

请以JSON格式返回分析结果：
{{
  "reason": "<失败的主要原因>",
  "error_type": "<错误类型: dependency|test|build|config|network|other>",
  "fix": "<建议的修复方法>",
  "confidence": <0.0-1.0的置信度>
}}

只返回JSON，不要包含其他内容。"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.glm5_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.glm5_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.glm5_model,
                        "messages": [
                            {"role": "system", "content": "你是一个CI/CD专家，擅长分析CI失败原因并提供修复建议。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # 尝试解析JSON
                    try:
                        json_match = re.search(r'\{[\s\S]*\}', content)
                        if json_match:
                            analysis = json.loads(json_match.group())
                            return analysis
                    except:
                        pass
                
                # 如果GLM5分析失败，使用规则分析
                return self._rule_based_analysis(error_messages)
                
        except Exception as e:
            print(f"[CICD] GLM5分析异常: {e}")
            return self._rule_based_analysis(error_messages)
    
    def _rule_based_analysis(self, error_messages: List[str]) -> Dict:
        """
        基于规则的失败分析
        
        Args:
            error_messages: 错误消息列表
        
        Returns:
            分析结果
        """
        error_text = "\n".join(error_messages).lower()
        
        # 常见错误模式
        patterns = {
            "dependency": [
                ("modulenotfounderror", "缺少依赖包"),
                ("importerror", "导入错误"),
                ("requirement", "依赖版本问题"),
                ("pip install", "需要安装依赖")
            ],
            "test": [
                ("assertionerror", "断言失败"),
                ("test failed", "测试失败"),
                ("pytest", "测试执行错误"),
                ("coverage", "覆盖率不足")
            ],
            "build": [
                ("compile", "编译错误"),
                ("syntaxerror", "语法错误"),
                ("typeerror", "类型错误"),
                ("nameerror", "变量未定义")
            ],
            "config": [
                ("yaml", "配置文件错误"),
                ("json", "JSON格式错误"),
                ("environment", "环境变量缺失"),
                ("permission", "权限问题")
            ],
            "network": [
                ("timeout", "网络超时"),
                ("connection", "连接失败"),
                ("503", "服务不可用"),
                ("502", "网关错误")
            ]
        }
        
        # 匹配错误类型
        for error_type, type_patterns in patterns.items():
            for pattern, message in type_patterns:
                if pattern in error_text:
                    return {
                        "reason": message,
                        "error_type": error_type,
                        "fix": self._get_fix_suggestion(error_type),
                        "confidence": 0.7
                    }
        
        # 默认分析
        return {
            "reason": "未知错误，请检查CI日志",
            "error_type": "other",
            "fix": "请查看详细的CI日志进行排查",
            "confidence": 0.3
        }
    
    def _get_fix_suggestion(self, error_type: str) -> str:
        """获取修复建议"""
        suggestions = {
            "dependency": "检查requirements.txt或pyproject.toml，确保所有依赖都已正确声明",
            "test": "检查测试用例，确保断言正确，必要时更新测试数据",
            "build": "修复语法错误或类型错误，确保代码符合规范",
            "config": "检查CI配置文件和环境变量设置",
            "network": "检查网络连接，考虑添加重试机制或使用镜像源"
        }
        
        return suggestions.get(error_type, "请查看详细的CI日志进行排查")
    
    async def trigger_ci_retry(self, run_id: int) -> Dict:
        """
        触发CI重试
        
        Args:
            run_id: 运行ID
        
        Returns:
            重试结果
        """
        print(f"\n[CICD] 触发CI运行 {run_id} 重试...")
        
        try:
            # 1. 检查是否可以重试
            cmd = f"gh run view {run_id} --json status,conclusion"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"获取运行状态失败: {result.stderr}"
                }
            
            run_info = json.loads(result.stdout)
            
            # 只能重试失败或完成的运行
            if run_info.get("status") not in ["completed"]:
                return {
                    "success": False,
                    "error": f"运行状态不允许重试: {run_info.get('status')}"
                }
            
            # 2. 触发重试
            cmd = f"gh run rerun {run_id}"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"[CICD] ✅ CI重试已触发")
                
                return {
                    "success": True,
                    "run_id": run_id,
                    "message": "CI重试已触发",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"触发重试失败: {result.stderr}"
                }
                
        except Exception as e:
            print(f"[CICD] 触发重试异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def monitor_ci_until_complete(
        self,
        branch: str,
        timeout: int = 3600,
        interval: int = 60
    ) -> Dict:
        """
        监控CI直到完成
        
        Args:
            branch: 分支名称
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
        
        Returns:
            最终CI状态
        """
        print(f"\n[CICD] 开始监控分支 {branch} 的CI状态...")
        print(f"[CICD] 超时: {timeout}秒, 检查间隔: {interval}秒")
        
        start_time = datetime.now()
        
        while True:
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                return {
                    "success": False,
                    "error": "监控超时",
                    "elapsed_time": elapsed
                }
            
            # 检查CI状态
            status = await self.check_ci_status(branch)
            
            if not status.get("success"):
                await asyncio.sleep(interval)
                continue
            
            # 如果CI完成，返回结果
            if not status.get("is_running"):
                print(f"[CICD] CI已完成，结论: {status.get('conclusion')}")
                
                return {
                    "success": True,
                    "branch": branch,
                    "conclusion": status.get("conclusion"),
                    "is_success": status.get("is_success"),
                    "elapsed_time": elapsed,
                    "run_id": status.get("run_id"),
                    "url": status.get("url")
                }
            
            # 等待下一次检查
            print(f"[CICD] CI仍在运行，{interval}秒后再次检查... (已耗时: {int(elapsed)}秒)")
            await asyncio.sleep(interval)
    
    async def auto_retry_failed_ci(
        self,
        branch: str,
        max_retries: int = 3
    ) -> Dict:
        """
        自动重试失败的CI
        
        Args:
            branch: 分支名称
            max_retries: 最大重试次数
        
        Returns:
            重试结果
        """
        print(f"\n[CICD] 自动重试分支 {branch} 的失败CI...")
        
        retry_count = 0
        
        while retry_count < max_retries:
            # 1. 检查CI状态
            status = await self.check_ci_status(branch)
            
            if not status.get("success"):
                return {
                    "success": False,
                    "error": "无法获取CI状态"
                }
            
            # 2. 如果CI成功，直接返回
            if status.get("is_success"):
                return {
                    "success": True,
                    "message": "CI已成功",
                    "retry_count": retry_count
                }
            
            # 3. 如果CI失败，尝试重试
            if status.get("is_failed"):
                run_id = status.get("run_id")
                
                # 分析失败原因
                analysis = await self.analyze_ci_failure(run_id)
                
                # 某些错误不适合重试
                if analysis.get("error_type") in ["build", "config"]:
                    return {
                        "success": False,
                        "error": "CI失败原因不适合自动重试",
                        "analysis": analysis,
                        "retry_count": retry_count
                    }
                
                # 触发重试
                retry_result = await self.trigger_ci_retry(run_id)
                
                if not retry_result.get("success"):
                    return {
                        "success": False,
                        "error": "触发重试失败",
                        "retry_count": retry_count
                    }
                
                retry_count += 1
                print(f"[CICD] 已触发第 {retry_count} 次重试")
                
                # 等待CI完成
                monitor_result = await self.monitor_ci_until_complete(
                    branch,
                    timeout=1800,  # 30分钟
                    interval=60
                )
                
                if monitor_result.get("is_success"):
                    return {
                        "success": True,
                        "message": f"CI在第{retry_count}次重试后成功",
                        "retry_count": retry_count
                    }
                
                # 冷却时间
                if retry_count < max_retries:
                    print(f"[CICD] 等待 {self.retry_cooldown} 秒后重试...")
                    await asyncio.sleep(self.retry_cooldown)
            
            else:
                # CI正在运行，等待完成
                monitor_result = await self.monitor_ci_until_complete(
                    branch,
                    timeout=1800,
                    interval=60
                )
                
                if monitor_result.get("is_success"):
                    return {
                        "success": True,
                        "message": "CI成功",
                        "retry_count": retry_count
                    }
        
        return {
            "success": False,
            "error": f"已达到最大重试次数 {max_retries}",
            "retry_count": retry_count
        }
    
    async def get_workflow_runs(
        self,
        workflow_name: Optional[str] = None,
        limit: int = 20
    ) -> Dict:
        """
        获取工作流运行列表
        
        Args:
            workflow_name: 工作流名称（可选）
            limit: 返回数量限制
        
        Returns:
            工作流运行列表
        """
        try:
            cmd = f"gh run list --limit {limit} --json id,status,conclusion,createdAt,displayTitle,workflowName,headBranch,htmlUrl"
            
            if workflow_name:
                cmd += f" --workflow {workflow_name}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                
                return {
                    "success": True,
                    "runs": runs,
                    "total": len(runs)
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def notify_ci_status(
        self,
        branch: str,
        status: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """
        通知CI状态
        
        Args:
            branch: 分支名称
            status: CI状态
            details: 详细信息
        
        Returns:
            通知结果
        """
        # TODO: 实现邮件、Webhook等通知方式
        # 目前只打印到控制台
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
╔═══════════════════════════════════════════════════════════════╗
║ CI/CD 状态通知                                                ║
╠═══════════════════════════════════════════════════════════════╣
║ 时间: {timestamp}                                        ║
║ 分支: {branch:50s} ║
║ 状态: {status:50s} ║
"""
        
        if details:
            for key, value in details.items():
                if isinstance(value, str) and len(value) < 50:
                    message += f"║ {key}: {value:48s} ║\n"
        
        message += "╚═══════════════════════════════════════════════════════════════╝"
        
        print(message)
        
        return {
            "success": True,
            "message": "通知已发送",
            "timestamp": timestamp
        }
    
    def generate_ci_report(self, branch: Optional[str] = None) -> str:
        """
        生成CI报告
        
        Args:
            branch: 分支名称（可选）
        
        Returns:
            Markdown格式的报告
        """
        report = f"""# CI/CD 状态报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 概览

"""
        
        # 添加缓存的状态
        if branch and branch in self._ci_cache:
            status = self._ci_cache[branch]
            report += f"""### 分支: {branch}

- **状态**: {status.get('status', 'unknown')}
- **结论**: {status.get('conclusion', 'N/A')}
- **工作流**: {status.get('workflow', 'unknown')}
- **URL**: {status.get('url', 'N/A')}

"""
        
        return report


# 全局实例
cicd_integration = None

def get_cicd_integration(repo_path: Optional[str] = None) -> CICDIntegration:
    """
    获取CI/CD集成单例
    
    Args:
        repo_path: 仓库路径
    
    Returns:
        CICDIntegration实例
    """
    global cicd_integration
    if not cicd_integration:
        cicd_integration = CICDIntegration(repo_path)
    return cicd_integration
