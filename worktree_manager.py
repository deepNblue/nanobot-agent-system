"""
Git Worktree管理器
为每个Agent任务创建独立的worktree，保证隔离性
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple


class WorktreeManager:
    """Git Worktree管理器"""

    def __init__(self, base_repo: Optional[str] = None):
        """
        初始化Worktree管理器

        Args:
            base_repo: 基础仓库路径，如果不提供则使用当前目录
        """
        self.base_repo = Path(base_repo).resolve() if base_repo else Path.cwd()
        # worktrees目录在仓库内的.worktrees目录
        self.worktrees_dir = self.base_repo / ".worktrees"
        self.worktrees_dir.mkdir(exist_ok=True)

        # 验证是否是git仓库
        if not (self.base_repo / ".git").exists():
            raise ValueError(f"{self.base_repo} 不是有效的Git仓库")

    def create_worktree(
        self, task_id: str, branch_name: Optional[str] = None, base_branch: str = "main", description: str = ""
    ) -> Dict:
        """
        为任务创建独立的worktree

        Args:
            task_id: 任务ID
            branch_name: 分支名称，如果不提供则自动生成
            base_branch: 基础分支
            description: 任务描述（用于生成分支名）

        Returns:
            创建结果，包含worktree路径、分支名等信息
        """
        # 生成分支名
        if not branch_name:
            branch_name = self._generate_branch_name(task_id, description)

        # worktree路径
        worktree_path = self.worktrees_dir / task_id

        # 检查是否已存在
        if worktree_path.exists():
            return {"success": False, "error": f"Worktree已存在: {worktree_path}", "path": str(worktree_path)}

        try:
            # 1. 确保基础分支是最新的
            self._fetch_and_update_base(base_branch)

            # 2. 创建worktree和新分支
            cmd = ["git", "worktree", "add", str(worktree_path), "-b", branch_name, f"origin/{base_branch}"]

            result = subprocess.run(cmd, cwd=self.base_repo, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                # 如果分支已存在，尝试使用现有分支
                if "already exists" in result.stderr:
                    cmd = ["git", "worktree", "add", str(worktree_path), branch_name]
                    result = subprocess.run(cmd, cwd=self.base_repo, capture_output=True, text=True, timeout=60)

                    if result.returncode != 0:
                        return {"success": False, "error": f"创建worktree失败: {result.stderr}", "path": str(worktree_path)}

            # 3. 安装依赖（如果存在package.json或requirements.txt）
            self._install_dependencies(worktree_path)

            # 4. 记录worktree信息
            worktree_info = {
                "task_id": task_id,
                "path": str(worktree_path),
                "branch": branch_name,
                "base_branch": base_branch,
                "created_at": datetime.now().isoformat(),
                "status": "active",
            }

            self._save_worktree_info(worktree_info)

            return {
                "success": True,
                "path": str(worktree_path),
                "branch": branch_name,
                "message": f"Worktree创建成功: {worktree_path}",
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "创建worktree超时"}
        except Exception as e:
            return {"success": False, "error": f"创建worktree异常: {str(e)}"}

    def remove_worktree(self, task_id: str, force: bool = False) -> Dict:
        """
        移除worktree

        Args:
            task_id: 任务ID
            force: 是否强制移除（即使有未提交的更改）

        Returns:
            移除结果
        """
        worktree_path = self.worktrees_dir / task_id

        if not worktree_path.exists():
            return {"success": False, "error": f"Worktree不存在: {worktree_path}"}

        try:
            # 1. 检查是否有未提交的更改
            if not force:
                status = self._get_worktree_status(worktree_path)
                if status["has_changes"]:
                    return {
                        "success": False,
                        "error": "Worktree有未提交的更改，请先提交或使用force=True",
                        "changes": status["changes"],
                    }

            # 2. 移除worktree
            cmd = ["git", "worktree", "remove", str(worktree_path)]
            if force:
                cmd.append("--force")

            result = subprocess.run(cmd, cwd=self.base_repo, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                # 手动删除目录
                import shutil

                shutil.rmtree(worktree_path)

            # 3. 删除分支（可选）
            worktree_info = self._load_worktree_info(task_id)
            if worktree_info and worktree_info.get("branch"):
                branch = worktree_info["branch"]
                # 不自动删除分支，保留以便查看历史

            # 4. 清理记录
            self._remove_worktree_info(task_id)

            return {"success": True, "message": f"Worktree已移除: {worktree_path}"}

        except Exception as e:
            return {"success": False, "error": f"移除worktree异常: {str(e)}"}

    def list_worktrees(self) -> List[Dict]:
        """
        列出所有worktree

        Returns:
            worktree列表
        """
        cmd = ["git", "worktree", "list", "--porcelain"]

        result = subprocess.run(cmd, cwd=self.base_repo, capture_output=True, text=True)

        worktrees = []
        current_worktree = {}

        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                if current_worktree:
                    worktrees.append(current_worktree)
                current_worktree = {"path": line.split(" ", 1)[1]}
            elif line.startswith("HEAD "):
                current_worktree["head"] = line.split(" ", 1)[1]
            elif line.startswith("branch "):
                current_worktree["branch"] = line.split(" ", 1)[1]

        if current_worktree:
            worktrees.append(current_worktree)

        return worktrees

    def get_worktree_path(self, task_id: str) -> Optional[Path]:
        """
        获取任务的worktree路径

        Args:
            task_id: 任务ID

        Returns:
            worktree路径，不存在返回None
        """
        worktree_path = self.worktrees_dir / task_id
        return worktree_path if worktree_path.exists() else None

    def _generate_branch_name(self, task_id: str, description: str) -> str:
        """
        生成分支名称

        Args:
            task_id: 任务ID
            description: 任务描述

        Returns:
            分支名称
        """
        # 从描述中提取关键词
        if description:
            # 简化描述：去除特殊字符，转为kebab-case
            import re

            slug = re.sub(r"[^\w\s-]", "", description.lower())
            slug = re.sub(r"[\s_]+", "-", slug)
            slug = slug[:30]  # 限制长度
            return f"agent/{task_id}-{slug}"
        else:
            return f"agent/{task_id}"

    def _fetch_and_update_base(self, base_branch: str):
        """
        获取并更新基础分支

        Args:
            base_branch: 基础分支名
        """
        try:
            # Fetch最新代码
            subprocess.run(["git", "fetch", "origin"], cwd=self.base_repo, capture_output=True, timeout=60)
        except Exception as e:
            pass  # 忽略fetch失败

    def _install_dependencies(self, worktree_path: Path):
        """
        安装依赖

        Args:
            worktree_path: worktree路径
        """
        try:
            # 检测项目类型并安装依赖
            if (worktree_path / "package.json").exists():
                # Node.js项目
                subprocess.run(["pnpm", "install"], cwd=worktree_path, capture_output=True, timeout=300)  # 5分钟超时
            elif (worktree_path / "requirements.txt").exists():
                # Python项目
                subprocess.run(
                    ["pip", "install", "-r", "requirements.txt"], cwd=worktree_path, capture_output=True, timeout=300
                )
        except Exception as e:
            pass  # 忽略依赖安装失败

    def _get_worktree_status(self, worktree_path: Path) -> Dict:
        """
        获取worktree状态

        Args:
            worktree_path: worktree路径

        Returns:
            状态信息
        """
        try:
            result = subprocess.run(["git", "status", "--porcelain"], cwd=worktree_path, capture_output=True, text=True)

            changes = [line for line in result.stdout.split("\n") if line]

            return {"has_changes": len(changes) > 0, "changes": changes}
        except Exception as e:
            return {"has_changes": False, "changes": [], "error": str(e)}

    def _save_worktree_info(self, info: Dict):
        """
        保存worktree信息

        Args:
            info: worktree信息
        """
        info_file = self.worktrees_dir / f"{info['task_id']}.json"
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    def _load_worktree_info(self, task_id: str) -> Optional[Dict]:
        """
        加载worktree信息

        Args:
            task_id: 任务ID

        Returns:
            worktree信息，不存在返回None
        """
        info_file = self.worktrees_dir / f"{task_id}.json"
        if info_file.exists():
            with open(info_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _remove_worktree_info(self, task_id: str):
        """
        移除worktree信息

        Args:
            task_id: 任务ID
        """
        info_file = self.worktrees_dir / f"{task_id}.json"
        if info_file.exists():
            info_file.unlink()


# 全局实例
worktree_manager = None


def get_worktree_manager(base_repo: Optional[str] = None) -> WorktreeManager:
    """
    获取Worktree管理器单例

    Args:
        base_repo: 基础仓库路径

    Returns:
        WorktreeManager实例
    """
    global worktree_manager
    if not worktree_manager:
        worktree_manager = WorktreeManager(base_repo)
    return worktree_manager
