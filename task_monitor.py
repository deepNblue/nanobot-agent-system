"""
任务监控器
监控Agent任务的执行状态，包括git提交、CI状态、tmux会话等
"""

import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import re


class TaskMonitor:
    """任务监控器"""
    
    def __init__(self, tasks_dir: Optional[str] = None):
        """
        初始化任务监控器
        
        Args:
            tasks_dir: 任务记录目录
        """
        self.tasks_dir = Path(tasks_dir) if tasks_dir else \
            Path.home() / ".nanobot" / "workspace" / "agent_tasks"
        self.tasks_dir.mkdir(exist_ok=True)
    
    def check_task_status(self, task_id: str) -> Dict:
        """
        检查任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        task_info = self._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}",
                "status": "not_found"
            }
        
        # 综合检查
        result = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {}
        }
        
        # 1. 检查tmux会话
        if task_info.get("tmuxSession"):
            tmux_status = self._check_tmux_session(task_info["tmuxSession"])
            result["checks"]["tmux"] = tmux_status
        
        # 2. 检查git提交
        if task_info.get("worktree"):
            git_status = self._check_git_commits(
                task_info["worktree"],
                task_info.get("branch"),
                task_info.get("startedAt")
            )
            result["checks"]["git"] = git_status
        
        # 3. 检查CI状态（如果配置了）
        if task_info.get("checkCI", False):
            ci_status = self._check_ci_status(task_info.get("branch"))
            result["checks"]["ci"] = ci_status
        
        # 4. 检查进程存活
        if task_info.get("tmuxSession"):
            process_alive = self._check_process_alive(task_info["tmuxSession"])
            result["checks"]["process"] = {
                "alive": process_alive
            }
        
        # 综合判断整体状态
        result["overall_status"] = self._determine_overall_status(result["checks"])
        
        return result
    
    def _check_tmux_session(self, session_name: str) -> Dict:
        """
        检查tmux会话状态
        
        Args:
            session_name: 会话名称
        
        Returns:
            会话状态
        """
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 获取会话信息
                info_result = subprocess.run(
                    ["tmux", "list-sessions", "-F", 
                     "#{session_name}|#{session_windows}|#{session_attached}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                for line in info_result.stdout.strip().split("\n"):
                    if line.startswith(f"{session_name}|"):
                        parts = line.split("|")
                        return {
                            "exists": True,
                            "running": True,
                            "windows": int(parts[1]) if len(parts) > 1 else 1,
                            "attached": parts[2] == "1" if len(parts) > 2 else False,
                            "status": "running"
                        }
                
                return {
                    "exists": True,
                    "running": True,
                    "status": "running"
                }
            else:
                return {
                    "exists": False,
                    "running": False,
                    "status": "ended"
                }
                
        except Exception as e:
            return {
                "exists": False,
                "running": False,
                "status": "error",
                "error": str(e)
            }
    
    def _check_git_commits(
        self,
        worktree_path: str,
        branch: Optional[str],
        since_timestamp: Optional[int]
    ) -> Dict:
        """
        检查git提交状态
        
        Args:
            worktree_path: Worktree路径
            branch: 分支名称
            since_timestamp: 起始时间戳（毫秒）
        
        Returns:
            Git提交状态
        """
        worktree = Path(worktree_path)
        if not worktree.exists():
            return {
                "success": False,
                "error": "Worktree不存在",
                "has_commits": False
            }
        
        try:
            # 1. 检查是否有新提交
            cmd = ["git", "log", "--oneline", "-10"]
            if since_timestamp:
                since_date = datetime.fromtimestamp(since_timestamp / 1000)
                cmd.extend(["--since", since_date.isoformat()])
            
            result = subprocess.run(
                cmd,
                cwd=worktree,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            commits = [line for line in result.stdout.strip().split("\n") if line]
            
            # 2. 检查是否已推送到远程
            if branch:
                push_result = subprocess.run(
                    ["git", "branch", "-vv"],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                ahead = 0
                behind = 0
                
                for line in push_result.stdout.split("\n"):
                    if line.startswith(f"  {branch}"):
                        # 提取ahead/behind信息
                        match = re.search(r'ahead (\d+)', line)
                        if match:
                            ahead = int(match.group(1))
                        
                        match = re.search(r'behind (\d+)', line)
                        if match:
                            behind = int(match.group(1))
                        break
                
                return {
                    "success": True,
                    "has_commits": len(commits) > 0,
                    "commit_count": len(commits),
                    "commits": commits[:5],  # 只返回最近5条
                    "ahead": ahead,
                    "behind": behind,
                    "pushed": ahead == 0 and len(commits) > 0
                }
            
            return {
                "success": True,
                "has_commits": len(commits) > 0,
                "commit_count": len(commits),
                "commits": commits[:5]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "has_commits": False
            }
    
    def _check_ci_status(self, branch: Optional[str]) -> Dict:
        """
        检查CI状态（GitHub Actions / GitLab CI等）
        
        Args:
            branch: 分支名称
        
        Returns:
            CI状态
        """
        if not branch:
            return {
                "success": False,
                "error": "未指定分支",
                "ci_status": "unknown"
            }
        
        try:
            # 尝试使用gh CLI检查GitHub Actions
            result = subprocess.run(
                ["gh", "run", "list", "--branch", branch, "--limit", "1", "--json", 
                 "status,conclusion,createdAt"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                import json as json_lib
                runs = json_lib.loads(result.stdout)
                
                if runs:
                    latest_run = runs[0]
                    status = latest_run.get("status", "unknown")
                    conclusion = latest_run.get("conclusion")
                    
                    return {
                        "success": True,
                        "ci_status": conclusion or status,
                        "is_running": status in ["queued", "in_progress"],
                        "is_success": conclusion == "success",
                        "is_failed": conclusion in ["failure", "cancelled", "timed_out"],
                        "details": latest_run
                    }
            
            return {
                "success": True,
                "ci_status": "no_runs",
                "message": "未找到CI运行记录"
            }
            
        except FileNotFoundError:
            # gh CLI未安装
            return {
                "success": False,
                "error": "gh CLI未安装",
                "ci_status": "unknown"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "ci_status": "unknown"
            }
    
    def _check_process_alive(self, session_name: str) -> bool:
        """
        检查进程是否存活
        
        Args:
            session_name: 会话名称
        
        Returns:
            进程是否存活
        """
        try:
            # 获取会话的PID
            result = subprocess.run(
                ["tmux", "list-panes", "-s", "-t", session_name, "-F", 
                 "#{pane_pid}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            pids = [line for line in result.stdout.strip().split("\n") if line]
            
            if not pids:
                return False
            
            # 检查每个PID是否存活
            for pid in pids:
                try:
                    proc_path = Path(f"/proc/{pid}")
                    if proc_path.exists():
                        return True
                except:
                    pass
            
            return False
            
        except:
            return False
    
    def _determine_overall_status(self, checks: Dict) -> str:
        """
        根据各项检查确定整体状态
        
        Args:
            checks: 各项检查结果
        
        Returns:
            整体状态
        """
        # 如果tmux会话已结束，检查其他指标
        tmux_check = checks.get("tmux", {})
        if tmux_check.get("status") == "ended":
            # 检查是否有git提交
            git_check = checks.get("git", {})
            if git_check.get("has_commits"):
                # 检查CI状态
                ci_check = checks.get("ci", {})
                if ci_check.get("is_success"):
                    return "completed"
                elif ci_check.get("is_failed"):
                    return "failed"
                else:
                    return "needs_review"
            else:
                return "failed"
        
        # tmux会话还在运行
        if tmux_check.get("running"):
            process_check = checks.get("process", {})
            if process_check.get("alive"):
                return "running"
            else:
                return "stuck"  # 会话在但进程已死
        
        return "unknown"
    
    def monitor_all_tasks(self) -> List[Dict]:
        """
        监控所有任务
        
        Returns:
            所有任务的状态列表
        """
        tasks = []
        
        for task_file in self.tasks_dir.glob("*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task_info = json.load(f)
                
                task_id = task_info.get("id") or task_file.stem
                status = self.check_task_status(task_id)
                
                tasks.append({
                    "task_id": task_id,
                    "status": status["overall_status"],
                    "checks": status["checks"],
                    "task_info": task_info
                })
                
            except Exception as e:
                tasks.append({
                    "task_id": task_file.stem,
                    "status": "error",
                    "error": str(e)
                })
        
        return tasks
    
    def get_failed_tasks(self) -> List[Dict]:
        """
        获取失败的任务
        
        Returns:
            失败任务列表
        """
        all_tasks = self.monitor_all_tasks()
        return [t for t in all_tasks if t.get("status") in ["failed", "stuck"]]
    
    def get_running_tasks(self) -> List[Dict]:
        """
        获取正在运行的任务
        
        Returns:
            运行中的任务列表
        """
        all_tasks = self.monitor_all_tasks()
        return [t for t in all_tasks if t.get("status") == "running"]
    
    def retry_task(self, task_id: str) -> Dict:
        """
        重试失败的任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            重试结果
        """
        task_info = self._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}"
            }
        
        # 检查任务状态
        status = self.check_task_status(task_id)
        if status["overall_status"] not in ["failed", "stuck"]:
            return {
                "success": False,
                "error": f"任务状态不允许重试: {status['overall_status']}"
            }
        
        # 更新任务状态为重试
        task_info["status"] = "retrying"
        task_info["retry_count"] = task_info.get("retry_count", 0) + 1
        task_info["last_retry_at"] = datetime.now().isoformat()
        
        self._save_task(task_info)
        
        return {
            "success": True,
            "task_id": task_id,
            "retry_count": task_info["retry_count"],
            "message": "任务已标记为重试"
        }
    
    def _load_task(self, task_id: str) -> Optional[Dict]:
        """
        加载任务信息
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务信息
        """
        # 尝试多种文件名格式
        possible_files = [
            self.tasks_dir / f"{task_id}.json",
            self.tasks_dir / f"task_{task_id}.json"
        ]
        
        for task_file in possible_files:
            if task_file.exists():
                try:
                    with open(task_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except:
                    pass
        
        return None
    
    def _save_task(self, task_info: Dict):
        """
        保存任务信息
        
        Args:
            task_info: 任务信息
        """
        task_id = task_info.get("id")
        if not task_id:
            return
        
        task_file = self.tasks_dir / f"{task_id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)
    
    def generate_report(self) -> str:
        """
        生成任务监控报告
        
        Returns:
            Markdown格式的报告
        """
        all_tasks = self.monitor_all_tasks()
        
        # 统计
        status_counts = {}
        for task in all_tasks:
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 生成报告
        report = f"""# 任务监控报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 统计概览

- 总任务数: {len(all_tasks)}
- 运行中: {status_counts.get('running', 0)}
- 已完成: {status_counts.get('completed', 0)}
- 失败: {status_counts.get('failed', 0)}
- 需要审核: {status_counts.get('needs_review', 0)}

## 任务详情

"""
        
        for task in all_tasks:
            task_id = task.get("task_id", "unknown")
            status = task.get("status", "unknown")
            task_info = task.get("task_info", {})
            
            report += f"""### {task_id}

- 状态: **{status}**
- Agent: {task_info.get('agent', 'unknown')}
- 分支: {task_info.get('branch', 'unknown')}
- 开始时间: {task_info.get('startedAt', 'unknown')}

"""
            
            # 添加检查详情
            checks = task.get("checks", {})
            if checks:
                report += "**检查项:**\n"
                for check_name, check_result in checks.items():
                    if isinstance(check_result, dict):
                        check_status = check_result.get("status") or check_result.get("ci_status") or "unknown"
                        report += f"- {check_name}: {check_status}\n"
                
                report += "\n"
        
        return report


# 全局实例
task_monitor = None

def get_task_monitor(tasks_dir: Optional[str] = None) -> TaskMonitor:
    """
    获取任务监控器单例
    
    Args:
        tasks_dir: 任务记录目录
    
    Returns:
        TaskMonitor实例
    """
    global task_monitor
    if not task_monitor:
        task_monitor = TaskMonitor(tasks_dir)
    return task_monitor
