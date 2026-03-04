"""
需求提取模块 - 从Obsidian会议记录自动提取需求

功能：
1. 扫描Obsidian的"Daily Notes"文件夹
2. 提取最近N天的会议记录
3. 使用GLM5 API分析内容
4. 识别行动项（action items）
5. 分析优先级（high/medium/low）
6. 生成结构化需求列表
"""

import os
import json
import re
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio


class RequirementExtractor:
    """需求提取器 - 从Obsidian提取需求"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化需求提取器
        
        Args:
            config_path: 配置文件路径
        """
        self.workspace = Path.home() / ".nanobot" / "workspace"
        self.config_path = config_path or (self.workspace / "skills" / "agent-system" / "config.json")
        
        # Obsidian配置
        self.vault_path = self._get_vault_path()
        self.daily_notes_folder = "Daily Notes"
        
        # GLM5 API配置
        self.api_key = self._get_api_key()
        self.api_base = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.model = "glm-5"
        
        # 需求存储
        self.requirements_dir = self.workspace / "agent_tasks" / "requirements"
        self.requirements_dir.mkdir(parents=True, exist_ok=True)
        
        # 关键词（用于初步筛选）
        self.action_keywords = [
            "TODO", "FIXME", "需要", "计划", "下一步", "行动项",
            "待办", "任务", "要完成", "必须", "应该",
            "TODO:", "[ ]", "- [ ]", "action item"
        ]
        
        self.priority_keywords = {
            "high": ["紧急", "urgent", "重要", "critical", "高优先级", "P0", "立即"],
            "medium": ["中等", "medium", "正常", "P1", "本周"],
            "low": ["低", "low", "可选", "P2", "有空"]
        }
    
    def _get_vault_path(self) -> Optional[Path]:
        """获取Obsidian vault路径"""
        # 尝试从配置文件读取
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    vault_path = config.get("obsidian", {}).get("vault_path")
                    if vault_path:
                        return Path(vault_path)
            except Exception as e:
                print(f"[RequirementExtractor] 读取配置失败: {e}")
        
        # 尝试常见路径
        common_paths = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "obsidian",
            Path.home() / "Notes" / "Obsidian",
        ]
        
        for path in common_paths:
            if path.exists():
                # 查找vault（包含.obsidian文件夹的目录）
                for vault in path.iterdir():
                    if vault.is_dir() and (vault / ".obsidian").exists():
                        return vault
        
        print("[RequirementExtractor] 未找到Obsidian vault")
        return None
    
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
        
        # 默认密钥（从opencode_agent.py获取）
        return "268cd5516f1547d2a6705ee616ec311a.IIjRJs4bJzrZTpET"
    
    async def scan_daily_notes(self, days: int = 7) -> List[Dict]:
        """
        扫描Daily Notes文件夹
        
        Args:
            days: 扫描最近几天的笔记
        
        Returns:
            笔记列表
        """
        if not self.vault_path:
            print("[RequirementExtractor] Vault路径未配置")
            return []
        
        daily_notes_path = self.vault_path / self.daily_notes_folder
        
        if not daily_notes_path.exists():
            print(f"[RequirementExtractor] Daily Notes文件夹不存在: {daily_notes_path}")
            return []
        
        notes = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 扫描markdown文件
        for note_file in daily_notes_path.glob("*.md"):
            try:
                # 检查文件修改时间
                mtime = datetime.fromtimestamp(note_file.stat().st_mtime)
                if mtime < cutoff_date:
                    continue
                
                # 读取笔记内容
                with open(note_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                notes.append({
                    "path": str(note_file),
                    "title": note_file.stem,
                    "content": content,
                    "modified_at": mtime.isoformat()
                })
                
            except Exception as e:
                print(f"[RequirementExtractor] 读取笔记失败 {note_file}: {e}")
        
        print(f"[RequirementExtractor] 找到 {len(notes)} 篇笔记（最近{days}天）")
        return notes
    
    def _contains_action_items(self, content: str) -> bool:
        """检查内容是否包含行动项关键词"""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in self.action_keywords)
    
    def _extract_priority(self, text: str) -> str:
        """从文本中提取优先级"""
        text_lower = text.lower()
        
        for priority, keywords in self.priority_keywords.items():
            if any(keyword.lower() in text_lower for keyword in keywords):
                return priority
        
        return "medium"  # 默认中等优先级
    
    async def analyze_with_glm5(self, note: Dict) -> List[Dict]:
        """
        使用GLM5分析笔记内容，提取需求
        
        Args:
            note: 笔记信息
        
        Returns:
            需求列表
        """
        prompt = f"""请分析以下会议记录，提取所有需求、任务和行动项。

笔记标题: {note['title']}
笔记内容:
{note['content']}

请按照以下JSON格式输出需求列表：
```json
[
  {{
    "description": "需求描述（简洁明确）",
    "priority": "high/medium/low",
    "tags": ["标签1", "标签2"],
    "context": "相关上下文或背景"
  }}
]
```

提取规则：
1. 识别所有TODO、FIXME、待办、需要、计划等关键词标记的任务
2. 分析每个任务的优先级（紧急/重要/可选）
3. 提取相关标签（如：feature, bug, doc, user等）
4. 保留重要的上下文信息

只输出JSON，不要其他说明。"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
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
                        
                        # 提取JSON
                        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            requirements = json.loads(json_str)
                            return requirements
                        else:
                            # 尝试直接解析
                            return json.loads(content)
                    else:
                        error_text = await response.text()
                        print(f"[RequirementExtractor] GLM5 API调用失败: {response.status} - {error_text}")
                        return []
        except asyncio.TimeoutError:
            print("[RequirementExtractor] GLM5 API调用超时")
            return []
        except json.JSONDecodeError as e:
            print(f"[RequirementExtractor] JSON解析失败: {e}")
            return []
        except Exception as e:
            print(f"[RequirementExtractor] 分析失败: {e}")
            return []
    
    def _generate_requirement_id(self) -> str:
        """生成需求ID：req_YYYYMMDDHHMMSS_N"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 查找当前秒的序号
        counter = 0
        while True:
            req_id = f"req_{timestamp}_{counter}"
            req_file = self.requirements_dir / f"{req_id}.json"
            if not req_file.exists():
                break
            counter += 1
        
        return req_id
    
    async def extract_requirements(self, days: int = 7) -> List[Dict]:
        """
        从Obsidian提取需求（主入口）
        
        Args:
            days: 扫描最近几天的笔记
        
        Returns:
            需求列表
        """
        print(f"\n[RequirementExtractor] 开始提取需求（最近{days}天）")
        
        # 1. 扫描笔记
        notes = await self.scan_daily_notes(days)
        
        if not notes:
            print("[RequirementExtractor] 没有找到笔记")
            return []
        
        # 2. 筛选包含行动项的笔记
        action_notes = [
            note for note in notes
            if self._contains_action_items(note["content"])
        ]
        
        print(f"[RequirementExtractor] 找到 {len(action_notes)} 篇包含行动项的笔记")
        
        # 3. 分析每篇笔记
        all_requirements = []
        
        for note in action_notes:
            print(f"\n[RequirementExtractor] 分析笔记: {note['title']}")
            
            # 使用GLM5分析
            requirements = await self.analyze_with_glm5(note)
            
            # 为每个需求添加元数据
            for req in requirements:
                req_id = self._generate_requirement_id()
                
                requirement = {
                    "id": req_id,
                    "source": "obsidian",
                    "note_title": note["title"],
                    "note_path": note["path"],
                    "description": req.get("description", ""),
                    "priority": req.get("priority", "medium"),
                    "tags": req.get("tags", []),
                    "context": req.get("context", ""),
                    "created_at": datetime.now().isoformat(),
                    "status": "pending"
                }
                
                # 保存需求
                self._save_requirement(requirement)
                all_requirements.append(requirement)
        
        print(f"\n[RequirementExtractor] 提取完成，共 {len(all_requirements)} 个需求")
        return all_requirements
    
    def _save_requirement(self, requirement: Dict):
        """保存需求到文件"""
        req_id = requirement.get("id")
        if not req_id:
            return
        
        req_file = self.requirements_dir / f"{req_id}.json"
        
        with open(req_file, "w", encoding="utf-8") as f:
            json.dump(requirement, f, ensure_ascii=False, indent=2)
    
    def load_requirement(self, req_id: str) -> Optional[Dict]:
        """加载需求"""
        req_file = self.requirements_dir / f"{req_id}.json"
        
        if not req_file.exists():
            return None
        
        with open(req_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def list_requirements(self, status: Optional[str] = None) -> List[Dict]:
        """
        列出所有需求
        
        Args:
            status: 筛选状态（pending/decomposed/completed）
        
        Returns:
            需求列表
        """
        requirements = []
        
        for req_file in self.requirements_dir.glob("req_*.json"):
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    req = json.load(f)
                
                if status is None or req.get("status") == status:
                    requirements.append(req)
            except Exception as e:
                print(f"[RequirementExtractor] 加载需求失败 {req_file}: {e}")
        
        # 按创建时间排序（新的在前）
        requirements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return requirements


# 全局实例
requirement_extractor = None

def get_requirement_extractor(config_path: Optional[str] = None) -> RequirementExtractor:
    """获取需求提取器单例"""
    global requirement_extractor
    if not requirement_extractor:
        requirement_extractor = RequirementExtractor(config_path)
    return requirement_extractor
