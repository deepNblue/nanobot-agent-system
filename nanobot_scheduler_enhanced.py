"""
Nanobot AI Agent系统 - 增强版编排层
整合Worktree、Tmux和Monitor功能

架构：
- Worktree: 每个任务独立隔离的git worktree
- Tmux: 每个任务独立的tmux会话
- Monitor: 自动监控任务状态
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 导入管理器
try:
    # 尝试相对导入（作为包使用时）
    from .worktree_manager import get_worktree_manager, WorktreeManager
    from .tmux_manager import get_tmux_manager, TmuxManager
    from .task_monitor import get_task_monitor, TaskMonitor
except ImportError:
    # 回退到绝对导入（直接运行时）
    from worktree_manager import get_worktree_manager, WorktreeManager
    from tmux_manager import get_tmux_manager, TmuxManager
    from task_monitor import get_task_monitor, TaskMonitor


class NanobotOrchestratorEnhanced:
    """增强版nanobot编排层 - 整合Worktree、Tmux、Monitor"""
    
    def __init__(self, base_repo: Optional[str] = None):
        """
        初始化增强版编排器
        
        Args:
            base_repo: 基础仓库路径
        """
        self.workspace = Path.home() / ".nanobot" / "workspace"
        self.tasks_dir = self.workspace / "agent_tasks"
        self.tasks_dir.mkdir(exist_ok=True)
        
        # 初始化管理器
        self.worktree_manager = get_worktree_manager(base_repo)
        self.tmux_manager = get_tmux_manager()
        self.task_monitor = get_task_monitor(str(self.tasks_dir))
        
        # OpenCode代理配置
        self.opencode_agent = None  # 将在后面初始化
        
        # 任务记录
        self.current_task: Optional[Dict] = None
        self.task_history: List[Dict] = []
    
    async def create_agent_task(
        self,
        task_id: str,
        description: str,
        agent_type: str = "codex",
        priority: str = "medium",
        base_branch: str = "main",
        command_template: str = None
    ) -> Dict:
        """
        创建Agent任务（整合Worktree + Tmux）
        
        Args:
            task_id: 任务ID
            description: 任务描述
            agent_type: Agent类型（codex, claude等）
            priority: 优先级
            base_branch: 基础分支
            command_template: 命令模板（支持变量替换）
        
        Returns:
            创建结果，包含worktree和tmux信息
        """
        print(f"\n[Orchestrator] 创建任务: {task_id}")
        print(f"[Orchestrator] 描述: {description}")
        
        # 1. 创建Worktree
        print(f"\n[Orchestrator] 步骤1: 创建Worktree...")
        worktree_result = self.worktree_manager.create_worktree(
            task_id=task_id,
            base_branch=base_branch,
            description=description
        )
        
        if not worktree_result.get("success"):
            return {
                "success": False,
                "error": f"创建Worktree失败: {worktree_result.get('error')}",
                "step": "worktree"
            }
        
        worktree_path = worktree_result["path"]
        branch = worktree_result["branch"]
        
        print(f"[Orchestrator] ✅ Worktree创建成功: {worktree_path}")
        print(f"[Orchestrator] ✅ 分支: {branch}")
        
        # 2. 生成执行命令
        if not command_template:
            command_template = self._get_default_command_template(agent_type)
        
        command = self._render_command_template(
            command_template,
            task_id=task_id,
            worktree_path=worktree_path,
            description=description
        )
        
        # 3. 创建Tmux会话
        print(f"\n[Orchestrator] 步骤2: 创建Tmux会话...")
        session_name = f"{agent_type}-{task_id}"
        
        tmux_result = self.tmux_manager.create_agent_session(
            task_id=task_id,
            agent_type=agent_type,
            worktree_path=worktree_path,
            command=command
        )
        
        if not tmux_result.get("success"):
            # 清理worktree
            self.worktree_manager.remove_worktree(task_id, force=True)
            
            return {
                "success": False,
                "error": f"创建Tmux会话失败: {tmux_result.get('error')}",
                "step": "tmux"
            }
        
        print(f"[Orchestrator] ✅ Tmux会话创建成功: {session_name}")
        
        # 4. 保存任务记录
        task_record = {
            "id": task_id,
            "description": description,
            "agent": agent_type,
            "priority": priority,
            "tmuxSession": session_name,
            "worktree": worktree_path,
            "branch": branch,
            "baseBranch": base_branch,
            "command": command,
            "startedAt": int(datetime.now().timestamp() * 1000),
            "status": "running",
            "checkCI": True,
            "notifyOnComplete": True,
            "retryCount": 0,
            "createdAt": datetime.now().isoformat()
        }
        
        self._save_task(task_record)
        
        print(f"\n[Orchestrator] ✅ 任务创建完成！")
        
        return {
            "success": True,
            "task_id": task_id,
            "tmux_session": session_name,
            "worktree": worktree_path,
            "branch": branch,
            "message": "任务创建成功，Agent开始执行"
        }
    
    async def monitor_task(self, task_id: str) -> Dict:
        """
        监控任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态
        """
        status = self.task_monitor.check_task_status(task_id)
        
        # 如果任务完成，发送通知
        if status.get("overall_status") in ["completed", "failed"]:
            task_info = self.task_monitor._load_task(task_id)
            if task_info and task_info.get("notifyOnComplete"):
                await self._send_notification(task_id, status)
        
        return status
    
    async def intervene_task(
        self,
        task_id: str,
        command: str,
        enter: bool = True
    ) -> Dict:
        """
        干预任务（向运行中的任务发送命令）
        
        Args:
            task_id: 任务ID
            command: 要发送的命令
            enter: 是否自动按回车
        
        Returns:
            干预结果
        """
        task_info = self.task_monitor._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}"
            }
        
        session_name = task_info.get("tmuxSession")
        if not session_name:
            return {
                "success": False,
                "error": "任务没有关联的Tmux会话"
            }
        
        # 发送命令
        result = self.tmux_manager.send_command(
            session_name=session_name,
            command=command,
            enter=enter
        )
        
        # 记录干预操作
        intervention = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "result": result
        }
        
        if "interventions" not in task_info:
            task_info["interventions"] = []
        task_info["interventions"].append(intervention)
        self._save_task(task_info)
        
        return result
    
    async def capture_task_output(
        self,
        task_id: str,
        lines: int = 100
    ) -> Dict:
        """
        捕获任务输出
        
        Args:
            task_id: 任务ID
            lines: 捕获的行数
        
        Returns:
            任务输出
        """
        task_info = self.task_monitor._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}"
            }
        
        session_name = task_info.get("tmuxSession")
        if not session_name:
            return {
                "success": False,
                "error": "任务没有关联的Tmux会话"
            }
        
        return self.tmux_manager.capture_pane(
            session_name=session_name,
            lines=lines
        )
    
    async def complete_task(
        self,
        task_id: str,
        cleanup: bool = False
    ) -> Dict:
        """
        完成任务（可选清理worktree）
        
        Args:
            task_id: 任务ID
            cleanup: 是否清理worktree
        
        Returns:
            完成结果
        """
        task_info = self.task_monitor._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}"
            }
        
        # 更新状态
        task_info["status"] = "completed"
        task_info["completedAt"] = datetime.now().isoformat()
        self._save_task(task_info)
        
        # 清理Tmux会话
        session_name = task_info.get("tmuxSession")
        if session_name:
            self.tmux_manager.kill_session(session_name)
        
        # 清理Worktree
        if cleanup:
            self.worktree_manager.remove_worktree(task_id, force=True)
        
        return {
            "success": True,
            "message": f"任务已完成: {task_id}",
            "cleanup": cleanup
        }
    
    async def list_all_tasks(self) -> List[Dict]:
        """
        列出所有任务
        
        Returns:
            任务列表
        """
        tasks = []
        
        for task_file in self.tasks_dir.glob("*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task_info = json.load(f)
                
                # 获取实时状态
                status = await self.monitor_task(task_info.get("id", task_file.stem))
                
                tasks.append({
                    "task_id": task_info.get("id", task_file.stem),
                    "description": task_info.get("description", ""),
                    "agent": task_info.get("agent", "unknown"),
                    "status": status.get("overall_status", "unknown"),
                    "branch": task_info.get("branch", ""),
                    "started_at": task_info.get("startedAt"),
                    "created_at": task_info.get("createdAt")
                })
            except Exception as e:
                tasks.append({
                    "task_id": task_file.stem,
                    "status": "error",
                    "error": str(e)
                })
        
        return tasks
    
    async def generate_status_report(self) -> str:
        """
        生成状态报告
        
        Returns:
            Markdown格式的报告
        """
        report = self.task_monitor.generate_report()
        return report
    
    def _get_default_command_template(self, agent_type: str) -> str:
        """
        获取默认命令模板
        
        Args:
            agent_type: Agent类型
        
        Returns:
            命令模板
        """
        templates = {
            "codex": "codex --task {task_id} --description '{description}'",
            "claude": "claude-agent run --task {task_id}",
            "opencode": "opencode execute --task {task_id}",
            "custom": "echo 'Starting task {task_id}' && bash run.sh {task_id}"
        }
        
        return templates.get(agent_type, templates["custom"])
    
    def _render_command_template(
        self,
        template: str,
        task_id: str,
        worktree_path: str,
        description: str
    ) -> str:
        """
        渲染命令模板
        
        Args:
            template: 命令模板
            task_id: 任务ID
            worktree_path: Worktree路径
            description: 任务描述
        
        Returns:
            渲染后的命令
        """
        command = template.format(
            task_id=task_id,
            worktree_path=worktree_path,
            description=description.replace("'", "'\"'\"'")
        )
        
        return command
    
    async def _send_notification(self, task_id: str, status: Dict):
        """
        发送通知
        
        Args:
            task_id: 任务ID
            status: 任务状态
        """
        # TODO: 实现通知功能（邮件、webhook等）
        print(f"\n[Notification] 任务 {task_id} 状态更新: {status.get('overall_status')}")
    
    def _save_task(self, task: Dict):
        """保存任务记录"""
        task_id = task.get("id")
        if not task_id:
            return
        
        task_file = self.tasks_dir / f"{task_id}.json"
        
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        
        # 更新当前任务
        self.current_task = task
        
        # 添加到历史
        if task not in self.task_history:
            self.task_history.append(task)


# 全局实例
orchestrator_enhanced = None

def get_orchestrator_enhanced(base_repo: Optional[str] = None) -> NanobotOrchestratorEnhanced:
    """
    获取增强版编排器单例
    
    Args:
        base_repo: 基础仓库路径
    
    Returns:
        NanobotOrchestratorEnhanced实例
    """
    global orchestrator_enhanced
    if not orchestrator_enhanced:
        orchestrator_enhanced = NanobotOrchestratorEnhanced(base_repo)
    return orchestrator_enhanced
