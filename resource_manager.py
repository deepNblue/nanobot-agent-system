"""
资源管理器 - 管理Worktree、Tmux等资源

功能：
1. 资源生命周期管理
2. 自动清理空闲资源
3. 资源使用统计
4. 资源限制和配额
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ResourceInfo:
    """资源信息"""
    id: str
    type: str  # worktree, tmux_session, temp_file
    created_at: datetime
    last_accessed: datetime
    path: str
    task_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class ResourceManager:
    """资源管理器"""
    
    def __init__(
        self,
        max_worktrees: int = 20,
        max_tmux_sessions: int = 20,
        idle_timeout: int = 3600,  # 1小时
        cleanup_interval: int = 300  # 5分钟
    ):
        """
        初始化资源管理器
        
        Args:
            max_worktrees: 最大worktree数量
            max_tmux_sessions: 最大tmux会话数量
            idle_timeout: 空闲超时时间（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self.max_worktrees = max_worktrees
        self.max_tmux_sessions = max_tmux_sessions
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval
        
        # 资源追踪
        self.worktrees: Dict[str, ResourceInfo] = {}
        self.tmux_sessions: Dict[str, ResourceInfo] = {}
        self.temp_files: Dict[str, ResourceInfo] = {}
        
        # 统计
        self.stats = {
            "worktrees_created": 0,
            "worktrees_removed": 0,
            "sessions_created": 0,
            "sessions_killed": 0,
            "files_cleaned": 0
        }
        
        # 工作目录
        self.base_dir = os.path.expanduser("~/.nanobot/workspace/skills/agent-system")
        self.worktrees_dir = os.path.join(self.base_dir, ".worktrees")
        self.temp_dir = os.path.join(self.base_dir, ".temp")
        
        # 创建目录
        os.makedirs(self.worktrees_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 加载现有资源
        self._load_existing_resources()
        
        # 启动清理任务
        self._cleanup_task = None
    
    def _load_existing_resources(self):
        """加载现有资源"""
        # 加载worktrees
        if os.path.exists(self.worktrees_dir):
            for item in os.listdir(self.worktrees_dir):
                worktree_path = os.path.join(self.worktrees_dir, item)
                if os.path.isdir(worktree_path):
                    task_file = os.path.join(worktree_path, "task.json")
                    if os.path.exists(task_file):
                        try:
                            with open(task_file) as f:
                                task_data = json.load(f)
                            
                            self.worktrees[item] = ResourceInfo(
                                id=item,
                                type="worktree",
                                created_at=datetime.fromisoformat(task_data.get("createdAt", datetime.now().isoformat())),
                                last_accessed=datetime.now(),
                                path=worktree_path,
                                task_id=item,
                                metadata=task_data
                            )
                        except:
                            pass
    
    async def register_worktree(self, task_id: str, path: str, metadata: Dict = None) -> bool:
        """
        注册worktree
        
        Args:
            task_id: 任务ID
            path: worktree路径
            metadata: 元数据
        
        Returns:
            是否成功
        """
        # 检查限制
        if len(self.worktrees) >= self.max_worktrees:
            # 尝试清理空闲资源
            await self.cleanup_idle_resources()
            
            if len(self.worktrees) >= self.max_worktrees:
                print(f"Maximum worktrees limit reached: {self.max_worktrees}")
                return False
        
        self.worktrees[task_id] = ResourceInfo(
            id=task_id,
            type="worktree",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            path=path,
            task_id=task_id,
            metadata=metadata or {}
        )
        
        self.stats["worktrees_created"] += 1
        
        return True
    
    async def register_tmux_session(self, session_name: str, metadata: Dict = None) -> bool:
        """
        注册tmux会话
        
        Args:
            session_name: 会话名称
            metadata: 元数据
        
        Returns:
            是否成功
        """
        # 检查限制
        if len(self.tmux_sessions) >= self.max_tmux_sessions:
            # 尝试清理空闲资源
            await self.cleanup_idle_resources()
            
            if len(self.tmux_sessions) >= self.max_tmux_sessions:
                print(f"Maximum tmux sessions limit reached: {self.max_tmux_sessions}")
                return False
        
        self.tmux_sessions[session_name] = ResourceInfo(
            id=session_name,
            type="tmux_session",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            path="",  # tmux会话没有路径
            metadata=metadata or {}
        )
        
        self.stats["sessions_created"] += 1
        
        return True
    
    async def register_temp_file(self, file_path: str, metadata: Dict = None) -> bool:
        """
        注册临时文件
        
        Args:
            file_path: 文件路径
            metadata: 元数据
        """
        file_id = os.path.basename(file_path)
        
        self.temp_files[file_id] = ResourceInfo(
            id=file_id,
            type="temp_file",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            path=file_path,
            metadata=metadata or {}
        )
    
    async def unregister_worktree(self, task_id: str) -> bool:
        """注销worktree"""
        if task_id in self.worktrees:
            del self.worktrees[task_id]
            self.stats["worktrees_removed"] += 1
            return True
        return False
    
    async def unregister_tmux_session(self, session_name: str) -> bool:
        """注销tmux会话"""
        if session_name in self.tmux_sessions:
            del self.tmux_sessions[session_name]
            self.stats["sessions_killed"] += 1
            return True
        return False
    
    def update_access_time(self, resource_id: str, resource_type: str = "worktree"):
        """更新资源访问时间"""
        resource_map = {
            "worktree": self.worktrees,
            "tmux_session": self.tmux_sessions,
            "temp_file": self.temp_files
        }
        
        resources = resource_map.get(resource_type)
        if resources and resource_id in resources:
            resources[resource_id].last_accessed = datetime.now()
    
    async def is_idle(self, resource_id: str, resource_type: str = "worktree") -> bool:
        """
        检查资源是否空闲
        
        Args:
            resource_id: 资源ID
            resource_type: 资源类型
        
        Returns:
            是否空闲
        """
        resource_map = {
            "worktree": self.worktrees,
            "tmux_session": self.tmux_sessions,
            "temp_file": self.temp_files
        }
        
        resources = resource_map.get(resource_type)
        if not resources or resource_id not in resources:
            return False
        
        resource = resources[resource_id]
        idle_time = datetime.now() - resource.last_accessed
        
        return idle_time > timedelta(seconds=self.idle_timeout)
    
    async def cleanup_idle_resources(self) -> Dict:
        """
        清理空闲资源
        
        Returns:
            清理统计
        """
        cleanup_stats = {
            "worktrees_removed": 0,
            "sessions_killed": 0,
            "files_cleaned": 0
        }
        
        # 清理空闲worktrees
        for task_id in list(self.worktrees.keys()):
            if await self.is_idle(task_id, "worktree"):
                worktree = self.worktrees[task_id]
                
                # 删除worktree
                if os.path.exists(worktree.path):
                    try:
                        # 使用git worktree remove
                        cmd = f"git worktree remove {worktree.path} --force"
                        process = await asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        await process.communicate()
                        
                        # 如果还有残留，直接删除
                        if os.path.exists(worktree.path):
                            import shutil
                            shutil.rmtree(worktree.path)
                        
                        await self.unregister_worktree(task_id)
                        cleanup_stats["worktrees_removed"] += 1
                    except Exception as e:
                        print(f"Error removing worktree {task_id}: {e}")
        
        # 清理空闲tmux会话
        for session_name in list(self.tmux_sessions.keys()):
            if await self.is_idle(session_name, "tmux_session"):
                try:
                    # 杀死tmux会话
                    cmd = f"tmux kill-session -t {session_name}"
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    
                    await self.unregister_tmux_session(session_name)
                    cleanup_stats["sessions_killed"] += 1
                except Exception as e:
                    print(f"Error killing tmux session {session_name}: {e}")
        
        # 清理临时文件
        for file_id in list(self.temp_files.keys()):
            if await self.is_idle(file_id, "temp_file"):
                temp_file = self.temp_files[file_id]
                
                if os.path.exists(temp_file.path):
                    try:
                        os.remove(temp_file.path)
                        del self.temp_files[file_id]
                        cleanup_stats["files_cleaned"] += 1
                    except Exception as e:
                        print(f"Error removing temp file {file_id}: {e}")
        
        # 更新统计
        self.stats["worktrees_removed"] += cleanup_stats["worktrees_removed"]
        self.stats["sessions_killed"] += cleanup_stats["sessions_killed"]
        self.stats["files_cleaned"] += cleanup_stats["files_cleaned"]
        
        return cleanup_stats
    
    async def start_cleanup_task(self):
        """启动自动清理任务"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(self.cleanup_interval)
                stats = await self.cleanup_idle_resources()
                if any(stats.values()):
                    print(f"Cleanup completed: {stats}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    def stop_cleanup_task(self):
        """停止自动清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    def get_resource_status(self) -> Dict:
        """获取资源状态"""
        return {
            "worktrees": {
                "active": len(self.worktrees),
                "max": self.max_worktrees,
                "available": self.max_worktrees - len(self.worktrees)
            },
            "tmux_sessions": {
                "active": len(self.tmux_sessions),
                "max": self.max_tmux_sessions,
                "available": self.max_tmux_sessions - len(self.tmux_sessions)
            },
            "temp_files": {
                "active": len(self.temp_files)
            },
            "stats": self.stats.copy()
        }
    
    def get_all_resources(self) -> List[Dict]:
        """获取所有资源"""
        resources = []
        
        for resource_id, resource in self.worktrees.items():
            resources.append({
                "id": resource_id,
                "type": "worktree",
                "path": resource.path,
                "created_at": resource.created_at.isoformat(),
                "last_accessed": resource.last_accessed.isoformat(),
                "task_id": resource.task_id
            })
        
        for session_name, resource in self.tmux_sessions.items():
            resources.append({
                "id": session_name,
                "type": "tmux_session",
                "created_at": resource.created_at.isoformat(),
                "last_accessed": resource.last_accessed.isoformat()
            })
        
        for file_id, resource in self.temp_files.items():
            resources.append({
                "id": file_id,
                "type": "temp_file",
                "path": resource.path,
                "created_at": resource.created_at.isoformat(),
                "last_accessed": resource.last_accessed.isoformat()
            })
        
        return resources


# 全局资源管理器
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """获取全局资源管理器"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def main():
        manager = get_resource_manager()
        
        # 注册资源
        await manager.register_worktree("task_123", "/path/to/worktree")
        await manager.register_tmux_session("session_123")
        
        # 获取状态
        status = manager.get_resource_status()
        print(f"Resource status: {status}")
        
        # 获取所有资源
        resources = manager.get_all_resources()
        print(f"All resources: {resources}")
    
    asyncio.run(main())
