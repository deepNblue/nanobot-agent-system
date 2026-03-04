"""
Tmux会话管理器
为每个Agent任务创建独立的tmux会话，支持中途干预和监控
"""

import os
import json
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple


class TmuxManager:
    """Tmux会话管理器"""

    def __init__(self):
        """初始化Tmux管理器"""
        # 检查tmux是否可用
        if not self._check_tmux_available():
            raise RuntimeError("Tmux未安装或不可用")

    def create_session(
        self, session_name: str, working_dir: str, command: Optional[str] = None, window_name: str = "main"
    ) -> Dict:
        """
        创建新的tmux会话

        Args:
            session_name: 会话名称
            working_dir: 工作目录
            command: 初始执行的命令
            window_name: 窗口名称

        Returns:
            创建结果
        """
        # 检查会话是否已存在
        if self.session_exists(session_name):
            return {"success": False, "error": f"会话已存在: {session_name}", "session_name": session_name}

        try:
            # 创建会话
            cmd = ["tmux", "new-session", "-d", "-s", session_name, "-c", working_dir, "-n", window_name]  # detached模式

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {"success": False, "error": f"创建会话失败: {result.stderr}", "session_name": session_name}

            # 执行初始命令
            if command:
                self.send_command(session_name, command)

            return {
                "success": True,
                "session_name": session_name,
                "working_dir": working_dir,
                "message": f"会话创建成功: {session_name}",
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "创建会话超时", "session_name": session_name}
        except Exception as e:
            return {"success": False, "error": f"创建会话异常: {str(e)}", "session_name": session_name}

    def session_exists(self, session_name: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_name: 会话名称

        Returns:
            是否存在
        """
        try:
            result = subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            return False

    def send_command(
        self, session_name: str, command: str, window_name: str = "main", pane_index: int = 0, enter: bool = True
    ) -> Dict:
        """
        向会话发送命令

        Args:
            session_name: 会话名称
            command: 命令内容
            window_name: 窗口名称
            pane_index: 面板索引
            enter: 是否自动按回车

        Returns:
            发送结果
        """
        if not self.session_exists(session_name):
            return {"success": False, "error": f"会话不存在: {session_name}"}

        try:
            # 目标：session:window.pane
            target = f"{session_name}:{window_name}.{pane_index}"

            # 发送命令
            cmd = ["tmux", "send-keys", "-t", target, command]
            if enter:
                cmd.append("Enter")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {"success": False, "error": f"发送命令失败: {result.stderr}"}

            return {"success": True, "command": command, "target": target}

        except Exception as e:
            return {"success": False, "error": f"发送命令异常: {str(e)}"}

    def capture_pane(self, session_name: str, window_name: str = "main", pane_index: int = 0, lines: int = 100) -> Dict:
        """
        捕获会话输出

        Args:
            session_name: 会话名称
            window_name: 窗口名称
            pane_index: 面板索引
            lines: 捕获的行数

        Returns:
            捕获结果，包含输出内容
        """
        if not self.session_exists(session_name):
            return {"success": False, "error": f"会话不存在: {session_name}", "output": ""}

        try:
            target = f"{session_name}:{window_name}.{pane_index}"

            cmd = [
                "tmux",
                "capture-pane",
                "-t",
                target,
                "-p",  # 输出到stdout
                "-S",
                f"-{lines}",  # 起始行
                "-E",
                "-1",  # 结束行
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {"success": False, "error": f"捕获输出失败: {result.stderr}", "output": ""}

            return {"success": True, "output": result.stdout, "lines": len(result.stdout.split("\n"))}

        except Exception as e:
            return {"success": False, "error": f"捕获输出异常: {str(e)}", "output": ""}

    def kill_session(self, session_name: str) -> Dict:
        """
        终止会话

        Args:
            session_name: 会话名称

        Returns:
            终止结果
        """
        if not self.session_exists(session_name):
            return {"success": False, "error": f"会话不存在: {session_name}"}

        try:
            result = subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {"success": False, "error": f"终止会话失败: {result.stderr}"}

            return {"success": True, "message": f"会话已终止: {session_name}"}

        except Exception as e:
            return {"success": False, "error": f"终止会话异常: {str(e)}"}

    def list_sessions(self) -> List[Dict]:
        """
        列出所有会话

        Returns:
            会话列表
        """
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            sessions = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        sessions.append(
                            {"name": parts[0], "windows": int(parts[1]), "created": int(parts[2]), "attached": parts[3] == "1"}
                        )

            return sessions

        except Exception as e:
            return []

    def get_session_status(self, session_name: str) -> Dict:
        """
        获取会话状态

        Args:
            session_name: 会话名称

        Returns:
            会话状态信息
        """
        if not self.session_exists(session_name):
            return {"exists": False, "running": False, "status": "not_found"}

        try:
            # 获取会话信息
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}|#{session_windows}|#{session_attached}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.strip().split("\n"):
                if line.startswith(f"{session_name}|"):
                    parts = line.split("|")
                    return {
                        "exists": True,
                        "running": True,
                        "windows": int(parts[1]),
                        "attached": parts[2] == "1",
                        "status": "running",
                    }

            return {"exists": True, "running": False, "status": "unknown"}

        except Exception as e:
            return {"exists": True, "running": False, "status": "error", "error": str(e)}

    def check_process_alive(self, session_name: str) -> bool:
        """
        检查会话中的进程是否存活

        Args:
            session_name: 会话名称

        Returns:
            进程是否存活
        """
        if not self.session_exists(session_name):
            return False

        try:
            # 获取会话的PID
            result = subprocess.run(
                ["tmux", "list-panes", "-s", "-t", session_name, "-F", "#{pane_pid}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            pids = [line for line in result.stdout.strip().split("\n") if line]

            if not pids:
                return False

            # 检查每个PID是否存活
            for pid in pids:
                try:
                    # 检查/proc/{pid}是否存在
                    proc_path = Path(f"/proc/{pid}")
                    if proc_path.exists():
                        return True
                except Exception as e:
                    pass

            return False

        except Exception as e:
            return False

    def _check_tmux_available(self) -> bool:
        """
        检查tmux是否可用

        Returns:
            tmux是否可用
        """
        try:
            result = subprocess.run(["tmux", "-V"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            return False

    def create_agent_session(self, task_id: str, agent_type: str, worktree_path: str, command: str) -> Dict:
        """
        为Agent任务创建专用tmux会话

        Args:
            task_id: 任务ID
            agent_type: Agent类型（如codex, claude等）
            worktree_path: Worktree路径
            command: 要执行的命令

        Returns:
            创建结果
        """
        # 生成会话名称
        session_name = f"{agent_type}-{task_id}"

        # 创建会话
        result = self.create_session(
            session_name=session_name, working_dir=worktree_path, command=command, window_name="agent"
        )

        if result["success"]:
            result["session_name"] = session_name
            result["task_id"] = task_id
            result["agent_type"] = agent_type

        return result

    def monitor_session(
        self,
        session_name: str,
        check_interval: int = 10,
        max_checks: int = 100,
        completion_patterns: List[str] = None,
        failure_patterns: List[str] = None,
    ) -> Dict:
        """
        监控会话执行状态

        Args:
            session_name: 会话名称
            check_interval: 检查间隔（秒）
            max_checks: 最大检查次数
            completion_patterns: 完成模式列表（正则表达式）
            failure_patterns: 失败模式列表（正则表达式）

        Returns:
            监控结果
        """
        if not completion_patterns:
            completion_patterns = [r"任务完成", r"Task completed", r"DONE", r"SUCCESS", r"Finished"]

        if not failure_patterns:
            failure_patterns = [r"ERROR", r"FAILED", r"Exception", r"Traceback", r"错误"]

        checks = 0
        while checks < max_checks:
            checks += 1

            # 检查会话是否存在
            if not self.session_exists(session_name):
                return {"status": "session_ended", "checks": checks, "message": "会话已结束"}

            # 捕获输出
            capture_result = self.capture_pane(session_name, lines=200)
            if capture_result["success"]:
                output = capture_result["output"]

                # 检查完成模式
                for pattern in completion_patterns:
                    if re.search(pattern, output, re.IGNORECASE):
                        return {"status": "completed", "checks": checks, "output": output, "pattern": pattern}

                # 检查失败模式
                for pattern in failure_patterns:
                    if re.search(pattern, output, re.IGNORECASE):
                        return {"status": "failed", "checks": checks, "output": output, "pattern": pattern}

            # 等待下一次检查
            time.sleep(check_interval)

        return {"status": "timeout", "checks": checks, "message": f"监控超时（{max_checks * check_interval}秒）"}


# 全局实例
tmux_manager = None


def get_tmux_manager() -> TmuxManager:
    """
    获取Tmux管理器单例

    Returns:
        TmuxManager实例
    """
    global tmux_manager
    if not tmux_manager:
        tmux_manager = TmuxManager()
    return tmux_manager
