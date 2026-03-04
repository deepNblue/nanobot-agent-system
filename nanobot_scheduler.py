"""
Nanobot AI Agent系统 - 编排层（只负责调度）
架构：nanobot (编排) → OpenCode (编码) → GLM5 (模型)

铁律：nanobot绝不直接生成代码，必须通过OpenCode！
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class NanobotOrchestrator:
    """nanobot编排层 - 只负责任务调度和上下文管理"""

    def __init__(self):
        self.workspace = Path.home() / ".nanobot" / "workspace"
        self.tasks_dir = self.workspace / "agent_tasks"
        self.tasks_dir.mkdir(exist_ok=True)

        # OpenCode代理配置
        self.opencode_agent = None  # 将在后面初始化

        # 任务记录
        self.current_task: Optional[Dict] = None
        self.task_history: List[Dict] = []

    async def extract_requirements_from_obsidian(self, days: int = 7) -> List[Dict]:
        """从Obsidian会议记录提取需求"""
        from skills.obsidian_kb import obsidian_kb

        # 读取最近7天的会议记录
        notes = await obsidian_kb.search(query="", folder="Daily Notes", date_range=f"last_{days}_days")

        requirements = []
        for note in notes:
            # 提取行动项
            action_items = self._extract_action_items(note.get("content", ""))

            for item in action_items:
                requirement = {
                    "id": f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(requirements)}",
                    "source": "obsidian",
                    "note_title": note.get("title", ""),
                    "note_date": note.get("created", ""),
                    "description": item,
                    "priority": self._assess_priority(item),
                    "created_at": datetime.now().isoformat(),
                }
                requirements.append(requirement)

        return requirements

    def _extract_action_items(self, content: str) -> List[str]:
        """从会议记录中提取行动项"""
        # 简单的关键词匹配（可以用GLM5改进）
        keywords = ["TODO", "待办", "需要", "要做", "Action Item", "下一步"]
        action_items = []

        lines = content.split("\n")
        for line in lines:
            for keyword in keywords:
                if keyword in line:
                    # 提取这一行作为行动项
                    item = line.replace(keyword, "").strip()
                    if item and len(item) > 5:
                        action_items.append(item)

        return action_items

    def _assess_priority(self, item: str) -> str:
        """评估优先级"""
        high_keywords = ["紧急", "urgent", "重要", "critical", "ASAP"]
        low_keywords = ["可以", "maybe", "有空", "optional"]

        item_lower = item.lower()

        for keyword in high_keywords:
            if keyword in item_lower:
                return "high"

        for keyword in low_keywords:
            if keyword in item_lower:
                return "low"

        return "medium"

    async def decompose_task(self, requirement: Dict) -> Dict:
        """任务分解"""
        # 分析复杂度
        complexity = await self._analyze_complexity(requirement["description"])

        # 生成精确prompt
        prompt = await self._generate_prompt(requirement, complexity)

        # 创建任务记录
        task = {
            "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "requirement_id": requirement["id"],
            "requirement": requirement["description"],
            "complexity": complexity,
            "prompt": prompt,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }

        # 保存任务
        self._save_task(task)

        return task

    async def _analyze_complexity(self, description: str) -> str:
        """分析任务复杂度"""
        # 简单规则（可以用GLM5改进）
        high_indicators = ["重构", "架构", "多文件", "复杂", "refactor", "architecture"]
        low_indicators = ["修复", "简单", "文档", "fix", "simple", "doc"]

        desc_lower = description.lower()

        for indicator in high_indicators:
            if indicator in desc_lower:
                return "high"

        for indicator in low_indicators:
            if indicator in desc_lower:
                return "low"

        return "medium"

    async def _generate_prompt(self, requirement: Dict, complexity: str) -> str:
        """生成精确prompt"""
        # 加载上下文
        context = await self._load_context()

        # 根据复杂度调整prompt
        if complexity == "high":
            detail_level = "详细的"
        elif complexity == "low":
            detail_level = "简洁的"
        else:
            detail_level = "适度的"

        prompt = f"""# 任务：{requirement['description']}

## 背景
- 来源：{requirement['source']}
- 优先级：{requirement['priority']}
- 复杂度：{complexity}

## 上下文
{context}

## 要求
请提供{detail_level}实现方案，包括：
1. 实现步骤
2. 代码示例
3. 测试方法
4. 注意事项

## 格式
使用Markdown格式输出。
"""

        return prompt

    async def _load_context(self) -> str:
        """加载上下文"""
        # 从OpenViking记忆系统加载
        try:
            # 尝试导入openviking_memory
            import importlib.util

            workspace = Path.home() / ".nanobot" / "workspace"
            spec = importlib.util.spec_from_file_location(
                "openviking_memory", workspace / "skills/openviking-memory/openviking_memory.py"
            )
            if spec and spec.loader:
                openviking_memory = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(openviking_memory)

                # 读取L1层记忆（概览）
                context = await openviking_memory.read("viking://memory/projects/L1")
                return context
        except Exception as e:
            # 如果失败，返回默认上下文
            pass

        return "无相关上下文"

    async def execute_task(self, task: Dict) -> Dict:
        """执行任务 - 通过OpenCode代理"""
        # 更新状态
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        self._save_task(task)

        try:
            # ⚠️ 铁律：nanobot不直接生成代码，必须通过OpenCode！

            # 1. 初始化OpenCode代理
            if not self.opencode_agent:
                from .opencode_agent import OpenCodeAgent

                self.opencode_agent = OpenCodeAgent()

            # 2. 调用OpenCode代理执行编码任务
            code_result = await self.opencode_agent.generate_code(task["prompt"])

            # 3. OpenCode代理执行代码（如果需要）
            if self.opencode_agent.needs_execution(code_result):
                execution_result = await self.opencode_agent.execute_code(code_result)
                task["result"] = {"code": code_result, "execution": execution_result}
            else:
                task["result"] = {"code": code_result, "execution": None}

            # 4. OpenCode代理验证结果
            if await self.opencode_agent.validate_result(task["result"]):
                task["status"] = "completed"
            else:
                task["status"] = "needs_review"

        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)

        finally:
            task["completed_at"] = datetime.now().isoformat()
            self._save_task(task)

        return task

    async def _call_glm5(self, prompt: str) -> str:
        """调用GLM5模型"""
        import aiohttp
        import os

        # 从环境变量或配置文件读取API密钥
        api_key = os.getenv("ZHIPU_API_KEY", "268cd5516f1547d2a6705ee616ec311a.IIjRJs4bJzrZTpET")
        api_base = "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions"

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        data = {
            "model": "glm-5",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(self.max_tokens, 2000),  # 限制最大2000 tokens
            "temperature": self.temperature,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_base, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=120)  # 2分钟超时
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        message = result["choices"][0]["message"]

                        # GLM5返回格式：优先使用reasoning_content，如果为空则使用content
                        content = message.get("reasoning_content") or message.get("content", "")

                        # 如果还是空的，返回错误信息
                        if not content:
                            return f"// GLM5返回空内容\n// 完整响应: {result}"

                        return content
                    else:
                        error_text = await response.text()
                        raise Exception(f"API调用失败: {response.status} - {error_text}")
        except asyncio.TimeoutError:
            return f"// GLM5 API调用超时（120秒）\n// Prompt: {prompt[:100]}...\n\nconsole.log('超时');"
        except Exception as e:
            # 如果失败，返回错误信息
            return f"// GLM5 API调用失败\n// 错误: {str(e)}\n// Prompt: {prompt[:100]}...\n\nconsole.log('API调用失败');"

    def _needs_execution(self, code_result: str) -> bool:
        """判断是否需要执行代码"""
        # 如果包含可执行代码标记
        executable_markers = ["```python", "```bash", "```javascript", "```go"]
        return any(marker in code_result for marker in executable_markers)

    async def _execute_code(self, code_result: str) -> Dict:
        """执行代码"""
        # 提取代码块
        import re

        code_blocks = re.findall(r"```(\w+)\n(.*?)```", code_result, re.DOTALL)

        results = []
        for lang, code in code_blocks:
            # 使用exec工具执行（实际实现）
            # result = await exec_command(code, lang)
            results.append({"language": lang, "code": code[:100], "status": "simulated"})  # 截断显示

        return {"executions": results}

    async def _validate_result(self, result: Dict) -> bool:
        """验证结果"""
        # 简单验证（可以添加更多规则）
        if not result or not result.get("code"):
            return False

        # 检查是否包含错误标记
        error_markers = ["ERROR", "FAILED", "Exception"]
        code = result.get("code", "")

        for marker in error_markers:
            if marker in code:
                return False

        return True

    def _save_task(self, task: Dict):
        """保存任务记录"""
        task_file = self.tasks_dir / f"{task['id']}.json"

        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

        # 更新当前任务
        self.current_task = task

        # 添加到历史
        if task not in self.task_history:
            self.task_history.append(task)

    def load_task(self, task_id: str) -> Optional[Dict]:
        """加载任务记录"""
        task_file = self.tasks_dir / f"{task_id}.json"

        if task_file.exists():
            with open(task_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    async def run_workflow(self, requirement_text: str = None) -> Dict:
        """运行完整工作流 - 只负责编排，编码交给OpenCode"""
        # 1. 提取需求（如果提供了文本）
        if requirement_text:
            requirement = {
                "id": f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "source": "manual",
                "description": requirement_text,
                "priority": "medium",
                "created_at": datetime.now().isoformat(),
            }
        else:
            # 从Obsidian提取
            requirements = await self.extract_requirements_from_obsidian()
            if not requirements:
                return {"status": "error", "message": "No requirements found"}
            requirement = requirements[0]

        # 2. 分解任务（nanobot负责）
        task = await self.decompose_task(requirement)

        # 3. 执行任务（OpenCode负责，nanobot只调度）
        task = await self.execute_task(task)

        # 4. 返回结果
        return {"status": task["status"], "requirement": requirement, "task": task, "result": task.get("result")}


# 全局实例（改名，强调编排角色）
orchestrator = NanobotOrchestrator()
# 保留旧名称兼容
agent_system = orchestrator
