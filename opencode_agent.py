"""
OpenCode代理层 - 负责所有编码工作
架构：nanobot (编排) → OpenCode (编码) → GLM5 (模型)

职责：
1. 代码生成（调用GLM5）
2. 代码执行（使用exec工具）
3. 结果验证
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Optional


class OpenCodeAgent:
    """OpenCode代理 - 负责编码工作"""
    
    def __init__(self):
        self.workspace = Path.home() / ".nanobot" / "workspace"
        
        # GLM5模型配置
        self.models = {
            "complex": "glm-5",      # 复杂任务：架构、重构（统一使用glm-5）
            "medium": "glm-5",      # 中等任务：功能开发
            "simple": "glm-5"        # 简单任务：修复、文档
        }
        
        self.current_model = "glm-5"  # 默认使用GLM5
        self.max_tokens = 2000
        self.temperature = 0.1
        
        # API配置
        self.api_key = os.getenv("ZHIPU_API_KEY", "268cd5516f1547d2a6705ee616ec311a.IIjRJs4bJzrZTpET")
        self.api_base = "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions"
    
    async def generate_code(self, prompt: str, complexity: str = "medium") -> str:
        """
        生成代码 - OpenCode的核心职责
        
        参数:
            prompt: 任务描述
            complexity: 复杂度（complex/medium/simple）
        
        返回:
            生成的代码
        """
        # 根据复杂度选择模型
        model = self.models.get(complexity, "glm-5-turbo")
        
        print(f"[OpenCode] 使用模型: {model}")
        print(f"[OpenCode] 开始生成代码...")
        
        # 调用GLM5 API
        code = await self._call_glm5(prompt, model)
        
        print(f"[OpenCode] 代码生成完成（{len(code)}字符）")
        
        return code
    
    async def _call_glm5(self, prompt: str, model: str = "glm-5-turbo") -> str:
        """调用GLM5模型"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        message = result["choices"][0]["message"]
                        
                        # GLM5返回格式
                        content = message.get("reasoning_content") or message.get("content", "")
                        
                        if not content:
                            return f"// GLM5返回空内容\n// 模型: {model}"
                        
                        return content
                    else:
                        error_text = await response.text()
                        raise Exception(f"API调用失败: {response.status} - {error_text}")
        except asyncio.TimeoutError:
            return f"// GLM5 API调用超时\n// 模型: {model}"
        except Exception as e:
            return f"// GLM5 API调用失败\n// 错误: {str(e)}"
    
    def needs_execution(self, code_result: str) -> bool:
        """判断是否需要执行代码"""
        # 如果包含可执行代码标记
        executable_markers = ["```python", "```bash", "```javascript", "```go"]
        return any(marker in code_result for marker in executable_markers)
    
    async def execute_code(self, code_result: str) -> Dict:
        """
        执行代码 - OpenCode的执行职责
        
        使用nanobot的exec工具执行代码
        """
        import re
        
        # 提取代码块
        code_blocks = re.findall(r'```(\w+)\n(.*?)```', code_result, re.DOTALL)
        
        results = []
        for lang, code in code_blocks:
            try:
                # 使用exec工具执行
                if lang == "python":
                    result = await self._execute_python(code)
                elif lang == "bash":
                    result = await self._execute_bash(code)
                else:
                    result = {"status": "skipped", "reason": f"Unsupported language: {lang}"}
                
                results.append({
                    "language": lang,
                    "code_length": len(code),
                    "result": result
                })
            except Exception as e:
                results.append({
                    "language": lang,
                    "error": str(e)
                })
        
        return {"executions": results}
    
    async def _execute_python(self, code: str) -> Dict:
        """执行Python代码"""
        # 保存到临时文件
        temp_file = self.workspace / "temp_code.py"
        
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
        
        # 使用exec工具执行
        try:
            # 这里应该使用nanobot的exec工具
            # 但为了测试，我们使用subprocess
            import subprocess
            result = subprocess.run(
                ["python3", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "stdout": result.stdout[:1000],  # 限制输出长度
                "stderr": result.stderr[:1000]
            }
        finally:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
    
    async def _execute_bash(self, code: str) -> Dict:
        """执行Bash命令"""
        import subprocess
        
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:1000]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def validate_result(self, result: Dict) -> bool:
        """
        验证结果 - OpenCode的验证职责
        """
        if not result or not result.get("code"):
            return False
        
        code = result.get("code", "")
        
        # 检查错误标记
        error_markers = ["ERROR", "FAILED", "Exception", "Traceback"]
        for marker in error_markers:
            if marker in code:
                return False
        
        # 如果有执行结果，检查执行状态
        execution = result.get("execution")
        if execution and execution.get("executions"):
            for exec_result in execution["executions"]:
                if exec_result.get("result", {}).get("status") == "failed":
                    return False
        
        return True
    
    async def select_model_by_complexity(self, task_description: str) -> str:
        """根据任务复杂度选择模型"""
        # 简单规则（可以改进）
        high_indicators = ["重构", "架构", "多文件", "复杂", "refactor", "architecture"]
        low_indicators = ["修复", "简单", "文档", "fix", "simple", "doc"]
        
        desc_lower = task_description.lower()
        
        for indicator in high_indicators:
            if indicator in desc_lower:
                return "complex"
        
        for indicator in low_indicators:
            if indicator in desc_lower:
                return "simple"
        
        return "medium"


# 全局实例
opencode_agent = OpenCodeAgent()
