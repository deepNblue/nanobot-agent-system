"""
任务分解模块 - 将需求分解为具体任务

功能：
1. 分析需求复杂度（high/medium/low）
2. 选择合适的Agent类型（GLM5-Plus/Turbo/Lite）
3. 生成精确的prompt
4. 加载相关上下文（相似任务、相关代码）
5. 估算执行时间
"""

import os
import json
import re
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import asyncio


class TaskDecomposer:
    """任务分解器 - 将需求分解为任务"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化任务分解器
        
        Args:
            config_path: 配置文件路径
        """
        self.workspace = Path.home() / ".nanobot" / "workspace"
        self.config_path = config_path or (self.workspace / "skills" / "agent-system" / "config.json")
        
        # GLM5 API配置
        self.api_key = self._get_api_key()
        self.api_base = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.model = "glm-5"
        
        # 任务存储
        self.tasks_dir = self.workspace / "agent_tasks" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # Agent类型映射
        self.agent_mapping = {
            "high": {
                "agent_type": "glm5-plus",
                "description": "复杂任务：架构设计、复杂bug、多文件重构",
                "model": "glm-5-plus",
                "max_tokens": 4000,
                "temperature": 0.1
            },
            "medium": {
                "agent_type": "glm5-turbo",
                "description": "中等任务：功能开发、快速迭代",
                "model": "glm-5-turbo",
                "max_tokens": 3000,
                "temperature": 0.2
            },
            "low": {
                "agent_type": "glm5-lite",
                "description": "简单任务：UI设计、文档、简单修复",
                "model": "glm-5-lite",
                "max_tokens": 2000,
                "temperature": 0.3
            }
        }
        
        # 复杂度评估关键词
        self.complexity_indicators = {
            "high": [
                "架构", "重构", "多文件", "复杂", "性能优化",
                "architecture", "refactor", "complex", "optimization",
                "并发", "安全", "加密", "authentication", "security",
                "集成", "migration", "迁移"
            ],
            "low": [
                "修复", "简单", "文档", "UI", "样式",
                "fix", "simple", "doc", "documentation", "style",
                "文案", "配置", "configuration", "调整"
            ]
        }
        
        # 时间估算映射（基于复杂度）
        self.time_estimates = {
            "high": {"min": 60, "max": 180, "unit": "minutes"},
            "medium": {"min": 20, "max": 60, "unit": "minutes"},
            "low": {"min": 5, "max": 20, "unit": "minutes"}
        }
    
    def _get_api_key(self) -> str:
        """获取GLM5 API密钥"""
        # 优先从环境变量
        api_key = os.getenv("ZHIPU_API_KEY")
        if api_key:
            return api_key
        
        # 从配置文件读取
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("api_keys", {}).get("zhipu", "")
            except Exception:
                pass
        
        # 默认密钥
        return "268cd5516f1547d2a6705ee616ec311a.IIjRJs4bJzrZTpET"
    
    def analyze_complexity(self, requirement: Dict) -> str:
        """
        分析需求复杂度
        
        Args:
            requirement: 需求信息
        
        Returns:
            复杂度级别（high/medium/low）
        """
        description = requirement.get("description", "").lower()
        context = requirement.get("context", "").lower()
        tags = requirement.get("tags", [])
        
        text = f"{description} {context} {' '.join(tags)}"
        
        # 计算复杂度分数
        high_score = sum(1 for keyword in self.complexity_indicators["high"] if keyword in text)
        low_score = sum(1 for keyword in self.complexity_indicators["low"] if keyword in text)
        
        # 根据分数判断
        if high_score >= 2 or (high_score > 0 and low_score == 0):
            return "high"
        elif low_score >= 2 or (low_score > 0 and high_score == 0):
            return "low"
        else:
            return "medium"
    
    def select_agent(self, complexity: str) -> Dict:
        """
        根据复杂度选择Agent
        
        Args:
            complexity: 复杂度级别
        
        Returns:
            Agent配置
        """
        return self.agent_mapping.get(complexity, self.agent_mapping["medium"])
    
    def estimate_time(self, complexity: str) -> str:
        """
        估算执行时间
        
        Args:
            complexity: 复杂度级别
        
        Returns:
            时间估算字符串
        """
        estimate = self.time_estimates.get(complexity, self.time_estimates["medium"])
        avg_time = (estimate["min"] + estimate["max"]) // 2
        return f"{avg_time} {estimate['unit']}"
    
    async def find_similar_tasks(self, requirement: Dict) -> List[Dict]:
        """
        查找相似任务（从历史任务中）
        
        Args:
            requirement: 需求信息
        
        Returns:
            相似任务列表
        """
        similar_tasks = []
        description = requirement.get("description", "").lower()
        tags = set(requirement.get("tags", []))
        
        # 扫描历史任务
        for task_file in self.tasks_dir.glob("task_*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task = json.load(f)
                
                # 计算相似度（简单实现）
                task_desc = task.get("description", "").lower()
                task_tags = set(task.get("tags", []))
                
                # 标签交集
                tag_similarity = len(tags & task_tags) / max(len(tags | task_tags), 1)
                
                # 描述相似度（简单的词重叠）
                desc_words = set(description.split())
                task_words = set(task_desc.split())
                desc_similarity = len(desc_words & task_words) / max(len(desc_words | task_words), 1)
                
                # 综合相似度
                similarity = tag_similarity * 0.6 + desc_similarity * 0.4
                
                if similarity > 0.3:  # 阈值
                    similar_tasks.append({
                        "task_id": task.get("id"),
                        "description": task.get("description"),
                        "similarity": round(similarity, 2)
                    })
            except Exception as e:
                print(f"[TaskDecomposer] 加载任务失败 {task_file}: {e}")
        
        # 按相似度排序
        similar_tasks.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similar_tasks[:5]  # 返回前5个
    
    async def find_related_files(self, requirement: Dict) -> List[str]:
        """
        查找相关文件（从项目代码库）
        
        Args:
            requirement: 需求信息
        
        Returns:
            相关文件列表
        """
        # TODO: 实现基于代码库的文件搜索
        # 可以使用：
        # 1. ripgrep搜索关键词
        # 2. 代码索引
        # 3. Git历史
        
        related_files = []
        description = requirement.get("description", "")
        tags = requirement.get("tags", [])
        
        # 简单实现：基于tags推断文件
        tag_file_mapping = {
            "user": ["src/components/UserProfile.tsx", "src/pages/UserSettings.tsx"],
            "upload": ["src/utils/upload.ts", "src/components/FileUpload.tsx"],
            "auth": ["src/middleware/auth.ts", "src/utils/jwt.ts"],
            "api": ["src/api/", "src/routes/"],
            "ui": ["src/components/", "src/styles/"]
        }
        
        for tag in tags:
            if tag in tag_file_mapping:
                related_files.extend(tag_file_mapping[tag])
        
        return list(set(related_files))[:10]  # 去重并限制数量
    
    async def generate_prompt(self, requirement: Dict, complexity: str, context: Dict) -> str:
        """
        生成精确的任务prompt
        
        Args:
            requirement: 需求信息
            complexity: 复杂度
            context: 上下文信息
        
        Returns:
            生成的prompt
        """
        agent_config = self.select_agent(complexity)
        
        # 使用GLM5生成prompt
        prompt_template = f"""请为以下需求生成一个精确的任务执行prompt。

需求信息：
- 描述：{requirement.get('description')}
- 优先级：{requirement.get('priority')}
- 标签：{', '.join(requirement.get('tags', []))}
- 上下文：{requirement.get('context')}

复杂度：{complexity}
Agent类型：{agent_config['agent_type']}
Agent描述：{agent_config['description']}

相关上下文：
- 相似任务：{json.dumps(context.get('similar_tasks', []), ensure_ascii=False)}
- 相关文件：{', '.join(context.get('related_files', []))}

请生成一个清晰、详细、可执行的任务prompt，要求：
1. 明确任务目标和预期结果
2. 列出具体步骤
3. 指定技术栈和工具
4. 包含验收标准
5. 添加注意事项

直接输出prompt内容，不要包含markdown标记。"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt_template}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        
                        # 清理markdown标记
                        content = re.sub(r'^```.*?\n', '', content)
                        content = re.sub(r'\n```$', '', content)
                        
                        return content.strip()
                    else:
                        error_text = await response.text()
                        print(f"[TaskDecomposer] GLM5 API调用失败: {response.status}")
                        return self._generate_fallback_prompt(requirement)
        except Exception as e:
            print(f"[TaskDecomposer] 生成prompt失败: {e}")
            return self._generate_fallback_prompt(requirement)
    
    def _generate_fallback_prompt(self, requirement: Dict) -> str:
        """生成后备prompt（当API调用失败时）"""
        description = requirement.get("description", "")
        tags = requirement.get("tags", [])
        context = requirement.get("context", "")
        
        prompt = f"""任务：{description}

背景：
{context}

执行步骤：
1. 分析需求，明确目标
2. 设计解决方案
3. 实现代码
4. 测试验证
5. 提交代码

技术要求：
- 标签：{', '.join(tags)}
- 代码质量：遵循最佳实践
- 测试：编写单元测试

验收标准：
- 功能完整
- 测试通过
- 代码审查通过"""
        
        return prompt
    
    def _generate_task_id(self) -> str:
        """生成任务ID：task_YYYYMMDDHHMMSS"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 查找当前秒的序号
        counter = 0
        while True:
            task_id = f"task_{timestamp}_{counter}"
            task_file = self.tasks_dir / f"{task_id}.json"
            if not task_file.exists():
                break
            counter += 1
        
        return task_id
    
    async def decompose_requirement(self, requirement: Dict) -> Dict:
        """
        分解需求为任务（主入口）
        
        Args:
            requirement: 需求信息
        
        Returns:
            任务信息
        """
        print(f"\n[TaskDecomposer] 开始分解需求: {requirement.get('id')}")
        
        # 1. 分析复杂度
        complexity = self.analyze_complexity(requirement)
        print(f"[TaskDecomposer] 复杂度: {complexity}")
        
        # 2. 选择Agent
        agent_config = self.select_agent(complexity)
        print(f"[TaskDecomposer] Agent: {agent_config['agent_type']}")
        
        # 3. 估算时间
        estimated_time = self.estimate_time(complexity)
        print(f"[TaskDecomposer] 预估时间: {estimated_time}")
        
        # 4. 加载上下文
        print(f"[TaskDecomposer] 加载上下文...")
        similar_tasks = await self.find_similar_tasks(requirement)
        related_files = await self.find_related_files(requirement)
        
        context = {
            "similar_tasks": similar_tasks,
            "related_files": related_files
        }
        
        # 5. 生成prompt
        print(f"[TaskDecomposer] 生成prompt...")
        prompt = await self.generate_prompt(requirement, complexity, context)
        
        # 6. 创建任务
        task_id = self._generate_task_id()
        
        task = {
            "id": task_id,
            "requirement_id": requirement.get("id"),
            "description": requirement.get("description"),
            "complexity": complexity,
            "agent_type": agent_config["agent_type"],
            "model": agent_config["model"],
            "estimated_time": estimated_time,
            "prompt": prompt,
            "context": context,
            "tags": requirement.get("tags", []),
            "priority": requirement.get("priority", "medium"),
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # 7. 保存任务
        self._save_task(task)
        
        # 8. 更新需求状态
        requirement["status"] = "decomposed"
        self._update_requirement(requirement)
        
        print(f"[TaskDecomposer] 任务创建成功: {task_id}")
        
        return task
    
    def _save_task(self, task: Dict):
        """保存任务到文件"""
        task_id = task.get("id")
        if not task_id:
            return
        
        task_file = self.tasks_dir / f"{task_id}.json"
        
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
    
    def _update_requirement(self, requirement: Dict):
        """更新需求状态"""
        req_dir = self.workspace / "agent_tasks" / "requirements"
        req_id = requirement.get("id")
        
        if not req_id:
            return
        
        req_file = req_dir / f"{req_id}.json"
        
        with open(req_file, "w", encoding="utf-8") as f:
            json.dump(requirement, f, ensure_ascii=False, indent=2)
    
    def load_task(self, task_id: str) -> Optional[Dict]:
        """加载任务"""
        task_file = self.tasks_dir / f"{task_id}.json"
        
        if not task_file.exists():
            return None
        
        with open(task_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def list_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """
        列出所有任务
        
        Args:
            status: 筛选状态（pending/running/completed/failed）
        
        Returns:
            任务列表
        """
        tasks = []
        
        for task_file in self.tasks_dir.glob("task_*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task = json.load(f)
                
                if status is None or task.get("status") == status:
                    tasks.append(task)
            except Exception as e:
                print(f"[TaskDecomposer] 加载任务失败 {task_file}: {e}")
        
        # 按创建时间排序（新的在前）
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return tasks


# 全局实例
task_decomposer = None

def get_task_decomposer(config_path: Optional[str] = None) -> TaskDecomposer:
    """获取任务分解器单例"""
    global task_decomposer
    if not task_decomposer:
        task_decomposer = TaskDecomposer(config_path)
    return task_decomposer
