"""
Nanobot AI Agent系统 - 增强版编排层（Phase 2）
整合Worktree、Tmux、Monitor、Code Review、CI/CD和自动化工作流

架构：
- Worktree: 每个任务独立隔离的git worktree
- Tmux: 每个任务独立的tmux会话
- Monitor: 自动监控任务状态
- Code Review: 三层代码审查（LLM + 静态分析 + 测试覆盖率）
- CI/CD: GitHub Actions集成（状态检查、失败分析、自动重试）
- Requirement Extraction: 从Obsidian自动提取需求
- Task Decomposition: 智能任务分解和Agent分配

Phase 2 新增功能：
- review_code(): 代码审查
- check_ci(): CI状态检查
- handle_ci_failure(): CI失败处理
- auto_merge_on_success(): 成功后自动合并
- extract_requirements_from_obsidian(): 从Obsidian提取需求
- decompose_requirement(): 分解需求为任务
- run_automated_workflow(): 运行自动化工作流
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
    from .code_reviewer import get_code_reviewer, CodeReviewer
    from .cicd_integration import get_cicd_integration, CICDIntegration
    from .requirement_extractor import get_requirement_extractor, RequirementExtractor
    from .task_decomposer import get_task_decomposer, TaskDecomposer
except ImportError:
    # 回退到绝对导入（直接运行时）
    from worktree_manager import get_worktree_manager, WorktreeManager
    from tmux_manager import get_tmux_manager, TmuxManager
    from task_monitor import get_task_monitor, TaskMonitor
    from code_reviewer import get_code_reviewer, CodeReviewer
    from cicd_integration import get_cicd_integration, CICDIntegration
    from requirement_extractor import get_requirement_extractor, RequirementExtractor
    from task_decomposer import get_task_decomposer, TaskDecomposer


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
        
        # Phase 2: 初始化Code Review和CI/CD模块
        try:
            self.code_reviewer = get_code_reviewer(base_repo)
            self.cicd_integration = get_cicd_integration(base_repo)
        except Exception as e:
            print(f"[Orchestrator] 警告: Code Review或CI/CD模块初始化失败: {e}")
            self.code_reviewer = None
            self.cicd_integration = None
        
        # Phase 2: 初始化需求提取和任务分解模块
        try:
            self.requirement_extractor = get_requirement_extractor()
            self.task_decomposer = get_task_decomposer()
        except Exception as e:
            print(f"[Orchestrator] 警告: 需求提取或任务分解模块初始化失败: {e}")
            self.requirement_extractor = None
            self.task_decomposer = None
        
        # OpenCode代理配置
        self.opencode_agent = None  # 将在后面初始化
        
        # 任务记录
        self.current_task: Optional[Dict] = None
        self.task_history: List[Dict] = []
        
        # Phase 2: 自动化配置
        self.auto_review_enabled = True  # 自动代码审查
        self.auto_ci_check_enabled = True  # 自动CI检查
        self.auto_retry_ci_enabled = True  # 自动重试CI
        self.auto_merge_enabled = False  # 自动合并（默认关闭，需要手动启用）
    
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
    
    # ==================== Phase 2: Code Review 和 CI/CD 集成 ====================
    
    async def review_code(self, task_id: str) -> Dict:
        """
        审查任务代码（三层Code Review）
        
        Args:
            task_id: 任务ID
        
        Returns:
            审查结果
        """
        print(f"\n[Orchestrator] 开始代码审查: {task_id}")
        
        # 1. 加载任务信息
        task_info = self.task_monitor._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}"
            }
        
        # 2. 获取PR编号（如果有）
        pr_number = task_info.get("pr_number")
        
        if not pr_number:
            # 尝试查找对应的PR
            branch = task_info.get("branch")
            if branch:
                pr_number = await self._find_pr_for_branch(branch)
        
        if not pr_number:
            return {
                "success": False,
                "error": "未找到对应的Pull Request",
                "task_id": task_id
            }
        
        # 3. 执行三层Code Review
        review_result = await self.code_reviewer.review_pull_request(pr_number)
        
        # 4. 保存审查结果到任务记录
        if review_result.get("success"):
            task_info["code_review"] = {
                "pr_number": pr_number,
                "score": review_result.get("score"),
                "approved": review_result.get("approved"),
                "timestamp": datetime.now().isoformat(),
                "summary": review_result.get("summary")
            }
            self._save_task(task_info)
            
            # 5. 如果审查通过且启用了自动合并，触发合并流程
            if review_result.get("approved") and self.auto_merge_enabled:
                print(f"[Orchestrator] 代码审查通过，准备自动合并...")
                # 等待CI通过后再合并
                await self.auto_merge_on_success(task_id, pr_number)
        
        return review_result
    
    async def check_ci(self, task_id: str) -> Dict:
        """
        检查任务CI状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            CI状态
        """
        print(f"\n[Orchestrator] 检查CI状态: {task_id}")
        
        # 1. 加载任务信息
        task_info = self.task_monitor._load_task(task_id)
        if not task_info:
            return {
                "success": False,
                "error": f"任务不存在: {task_id}"
            }
        
        # 2. 获取分支名称
        branch = task_info.get("branch")
        if not branch:
            return {
                "success": False,
                "error": "任务没有关联的分支"
            }
        
        # 3. 检查CI状态
        ci_status = await self.cicd_integration.check_ci_status(branch)
        
        # 4. 更新任务记录
        if ci_status.get("success"):
            task_info["ci_status"] = {
                "status": ci_status.get("status"),
                "conclusion": ci_status.get("conclusion"),
                "run_id": ci_status.get("run_id"),
                "url": ci_status.get("url"),
                "checked_at": datetime.now().isoformat()
            }
            self._save_task(task_info)
        
        return ci_status
    
    async def handle_ci_failure(self, task_id: str) -> Dict:
        """
        处理CI失败
        
        Args:
            task_id: 任务ID
        
        Returns:
            处理结果
        """
        print(f"\n[Orchestrator] 处理CI失败: {task_id}")
        
        # 1. 检查CI状态
        ci_status = await self.check_ci(task_id)
        
        if not ci_status.get("success"):
            return ci_status
        
        # 2. 如果CI没有失败，返回
        if not ci_status.get("is_failed"):
            return {
                "success": True,
                "message": "CI未失败，无需处理",
                "ci_status": ci_status
            }
        
        # 3. 获取运行ID
        run_id = ci_status.get("run_id")
        if not run_id:
            return {
                "success": False,
                "error": "无法获取CI运行ID"
            }
        
        # 4. 分析失败原因
        print(f"[Orchestrator] 分析CI失败原因...")
        analysis = await self.cicd_integration.analyze_ci_failure(run_id)
        
        # 5. 决定是否重试
        should_retry = self._should_retry_ci(analysis)
        
        if should_retry and self.auto_retry_ci_enabled:
            # 检查重试次数
            task_info = self.task_monitor._load_task(task_id)
            retry_count = task_info.get("ci_retry_count", 0)
            
            if retry_count < 3:  # 最多重试3次
                print(f"[Orchestrator] 触发CI重试 (第{retry_count + 1}次)...")
                
                retry_result = await self.cicd_integration.trigger_ci_retry(run_id)
                
                if retry_result.get("success"):
                    # 更新重试次数
                    task_info["ci_retry_count"] = retry_count + 1
                    task_info["last_ci_retry"] = datetime.now().isoformat()
                    self._save_task(task_info)
                    
                    # 监控CI直到完成
                    branch = task_info.get("branch")
                    monitor_result = await self.cicd_integration.monitor_ci_until_complete(
                        branch,
                        timeout=1800,
                        interval=60
                    )
                    
                    return {
                        "success": True,
                        "action": "retry",
                        "retry_count": retry_count + 1,
                        "analysis": analysis,
                        "monitor_result": monitor_result
                    }
        
        # 6. 如果不适合重试或重试失败，返回分析结果
        return {
            "success": False,
            "action": "manual_fix_required",
            "analysis": analysis,
            "suggested_fix": analysis.get("suggested_fix"),
            "message": "CI失败需要手动修复"
        }
    
    def _should_retry_ci(self, analysis: Dict) -> bool:
        """
        判断是否应该重试CI
        
        Args:
            analysis: CI失败分析结果
        
        Returns:
            是否应该重试
        """
        # 某些错误类型不适合重试
        no_retry_types = ["build", "config", "test"]
        
        error_type = analysis.get("error_type")
        if error_type in no_retry_types:
            return False
        
        # 置信度太低也不重试
        if analysis.get("confidence", 0) < 0.5:
            return False
        
        return True
    
    async def auto_merge_on_success(
        self,
        task_id: str,
        pr_number: int
    ) -> Dict:
        """
        成功后自动合并PR
        
        Args:
            task_id: 任务ID
            pr_number: PR编号
        
        Returns:
            合并结果
        """
        print(f"\n[Orchestrator] 准备自动合并PR #{pr_number}")
        
        # 1. 检查代码审查状态
        task_info = self.task_monitor._load_task(task_id)
        code_review = task_info.get("code_review", {})
        
        if not code_review.get("approved"):
            return {
                "success": False,
                "error": "代码审查未通过"
            }
        
        # 2. 检查CI状态
        branch = task_info.get("branch")
        ci_status = await self.cicd_integration.check_ci_status(branch)
        
        if not ci_status.get("is_success"):
            return {
                "success": False,
                "error": "CI未通过",
                "ci_status": ci_status
            }
        
        # 3. 执行合并
        try:
            import subprocess
            
            cmd = f"gh pr merge {pr_number} --squash --delete-branch"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.worktree_manager.base_repo,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"[Orchestrator] ✅ PR #{pr_number} 已自动合并")
                
                # 更新任务状态
                task_info["status"] = "merged"
                task_info["merged_at"] = datetime.now().isoformat()
                task_info["pr_number"] = pr_number
                self._save_task(task_info)
                
                return {
                    "success": True,
                    "message": f"PR #{pr_number} 已自动合并",
                    "pr_number": pr_number
                }
            else:
                return {
                    "success": False,
                    "error": f"合并失败: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _find_pr_for_branch(self, branch: str) -> Optional[int]:
        """
        查找分支对应的PR编号
        
        Args:
            branch: 分支名称
        
        Returns:
            PR编号或None
        """
        try:
            import subprocess
            
            cmd = f"gh pr list --head {branch} --json number --jq '.[0].number'"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.worktree_manager.base_repo,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
                
        except Exception as e:
            print(f"[Orchestrator] 查找PR失败: {e}")
        
        return None
    
    async def full_task_lifecycle(
        self,
        task_id: str,
        description: str,
        agent_type: str = "codex",
        base_branch: str = "main"
    ) -> Dict:
        """
        完整的任务生命周期（创建 -> 执行 -> 审查 -> CI -> 合并）
        
        Args:
            task_id: 任务ID
            description: 任务描述
            agent_type: Agent类型
            base_branch: 基础分支
        
        Returns:
            完整生命周期结果
        """
        print(f"\n[Orchestrator] 启动完整任务生命周期: {task_id}")
        
        lifecycle_result = {
            "task_id": task_id,
            "stages": {},
            "success": False
        }
        
        try:
            # 1. 创建任务
            print(f"\n[Orchestrator] 阶段1: 创建任务...")
            create_result = await self.create_agent_task(
                task_id=task_id,
                description=description,
                agent_type=agent_type,
                base_branch=base_branch
            )
            lifecycle_result["stages"]["create"] = create_result
            
            if not create_result.get("success"):
                return lifecycle_result
            
            # 2. 监控任务执行
            print(f"\n[Orchestrator] 阶段2: 监控任务执行...")
            await asyncio.sleep(10)  # 等待任务开始
            
            # 轮询任务状态
            max_wait = 3600  # 最多等待1小时
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < max_wait:
                status = await self.monitor_task(task_id)
                lifecycle_result["stages"]["execution"] = status
                
                if status.get("overall_status") in ["completed", "failed", "needs_review"]:
                    break
                
                await asyncio.sleep(60)  # 每分钟检查一次
            
            # 3. 代码审查
            if self.auto_review_enabled:
                print(f"\n[Orchestrator] 阶段3: 代码审查...")
                review_result = await self.review_code(task_id)
                lifecycle_result["stages"]["review"] = review_result
                
                if not review_result.get("approved"):
                    lifecycle_result["success"] = False
                    lifecycle_result["error"] = "代码审查未通过"
                    return lifecycle_result
            
            # 4. CI检查
            if self.auto_ci_check_enabled:
                print(f"\n[Orchestrator] 阶段4: CI检查...")
                
                # 等待CI开始
                await asyncio.sleep(30)
                
                ci_result = await self.check_ci(task_id)
                lifecycle_result["stages"]["ci"] = ci_result
                
                # 如果CI失败，尝试处理
                if ci_result.get("is_failed"):
                    print(f"[Orchestrator] CI失败，尝试处理...")
                    handle_result = await self.handle_ci_failure(task_id)
                    lifecycle_result["stages"]["ci_handling"] = handle_result
                    
                    # 重新检查CI状态
                    ci_result = await self.check_ci(task_id)
                    lifecycle_result["stages"]["ci_final"] = ci_result
                
                if not ci_result.get("is_success"):
                    lifecycle_result["success"] = False
                    lifecycle_result["error"] = "CI未通过"
                    return lifecycle_result
            
            # 5. 自动合并（如果启用）
            if self.auto_merge_enabled:
                print(f"\n[Orchestrator] 阶段5: 自动合并...")
                
                # 查找PR
                pr_number = await self._find_pr_for_branch(
                    lifecycle_result["stages"]["create"].get("branch")
                )
                
                if pr_number:
                    merge_result = await self.auto_merge_on_success(task_id, pr_number)
                    lifecycle_result["stages"]["merge"] = merge_result
                    
                    if merge_result.get("success"):
                        lifecycle_result["success"] = True
                        lifecycle_result["message"] = "任务完整生命周期执行成功"
                    else:
                        lifecycle_result["error"] = "自动合并失败"
                else:
                    lifecycle_result["error"] = "未找到对应的PR"
            else:
                lifecycle_result["success"] = True
                lifecycle_result["message"] = "任务执行成功，等待手动合并"
            
        except Exception as e:
            lifecycle_result["error"] = str(e)
            print(f"[Orchestrator] 生命周期执行异常: {e}")
        
        return lifecycle_result
    
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
    
    # ==================== Phase 2: 需求提取和任务分解 ====================
    
    async def extract_requirements_from_obsidian(self, days: int = 7) -> List[Dict]:
        """
        从Obsidian提取需求
        
        Args:
            days: 扫描最近几天的笔记（默认7天）
        
        Returns:
            需求列表
        """
        if not self.requirement_extractor:
            print("[Orchestrator] 需求提取模块未初始化")
            return []
        
        print(f"\n[Orchestrator] 从Obsidian提取需求（最近{days}天）")
        
        try:
            requirements = await self.requirement_extractor.extract_requirements(days)
            
            print(f"[Orchestrator] 提取完成，共 {len(requirements)} 个需求")
            
            return requirements
        except Exception as e:
            print(f"[Orchestrator] 需求提取失败: {e}")
            return []
    
    async def decompose_requirement(self, requirement: Dict) -> Optional[Dict]:
        """
        分解需求为任务
        
        Args:
            requirement: 需求信息
        
        Returns:
            任务信息
        """
        if not self.task_decomposer:
            print("[Orchestrator] 任务分解模块未初始化")
            return None
        
        print(f"\n[Orchestrator] 分解需求: {requirement.get('id')}")
        
        try:
            task = await self.task_decomposer.decompose_requirement(requirement)
            
            print(f"[Orchestrator] 分解完成，任务ID: {task.get('id')}")
            print(f"[Orchestrator] 复杂度: {task.get('complexity')}")
            print(f"[Orchestrator] Agent类型: {task.get('agent_type')}")
            print(f"[Orchestrator] 预估时间: {task.get('estimated_time')}")
            
            return task
        except Exception as e:
            print(f"[Orchestrator] 任务分解失败: {e}")
            return None
    
    async def run_automated_workflow(self, days: int = 7) -> Dict:
        """
        运行自动化工作流：提取需求 → 分解任务 → 创建Agent任务
        
        Args:
            days: 扫描最近几天的笔记（默认7天）
        
        Returns:
            工作流执行结果
        """
        print("\n" + "="*60)
        print("[Orchestrator] 开始自动化工作流")
        print("="*60)
        
        result = {
            "started_at": datetime.now().isoformat(),
            "requirements": [],
            "tasks": [],
            "agent_tasks": [],
            "errors": []
        }
        
        # 步骤1: 提取需求
        print("\n[Orchestrator] 步骤1: 提取需求")
        print("-"*60)
        
        try:
            requirements = await self.extract_requirements_from_obsidian(days)
            result["requirements"] = requirements
            
            if not requirements:
                print("[Orchestrator] 没有找到需求，工作流结束")
                result["message"] = "没有找到需求"
                result["completed_at"] = datetime.now().isoformat()
                return result
        except Exception as e:
            error_msg = f"需求提取失败: {e}"
            print(f"[Orchestrator] ❌ {error_msg}")
            result["errors"].append(error_msg)
            result["completed_at"] = datetime.now().isoformat()
            return result
        
        # 步骤2: 分解任务
        print("\n[Orchestrator] 步骤2: 分解任务")
        print("-"*60)
        
        tasks = []
        for requirement in requirements:
            try:
                task = await self.decompose_requirement(requirement)
                if task:
                    tasks.append(task)
                    result["tasks"].append({
                        "task_id": task.get("id"),
                        "requirement_id": requirement.get("id"),
                        "complexity": task.get("complexity"),
                        "agent_type": task.get("agent_type")
                    })
            except Exception as e:
                error_msg = f"任务分解失败（需求: {requirement.get('id')}）: {e}"
                print(f"[Orchestrator] ❌ {error_msg}")
                result["errors"].append(error_msg)
        
        if not tasks:
            print("[Orchestrator] 没有成功分解的任务，工作流结束")
            result["message"] = "没有成功分解的任务"
            result["completed_at"] = datetime.now().isoformat()
            return result
        
        # 步骤3: 创建Agent任务（可选）
        print("\n[Orchestrator] 步骤3: 创建Agent任务")
        print("-"*60)
        
        for task in tasks:
            try:
                # 使用分解的任务信息创建Agent任务
                agent_task_result = await self.create_agent_task(
                    task_id=task.get("id"),
                    description=task.get("description"),
                    agent_type=task.get("agent_type", "opencode"),
                    priority=task.get("priority", "medium"),
                    base_branch="main"
                )
                
                if agent_task_result.get("success"):
                    result["agent_tasks"].append({
                        "task_id": task.get("id"),
                        "tmux_session": agent_task_result.get("tmux_session"),
                        "worktree": agent_task_result.get("worktree")
                    })
                    print(f"[Orchestrator] ✅ Agent任务创建成功: {task.get('id')}")
                else:
                    error_msg = f"Agent任务创建失败: {agent_task_result.get('error')}"
                    print(f"[Orchestrator] ❌ {error_msg}")
                    result["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Agent任务创建异常（任务: {task.get('id')}）: {e}"
                print(f"[Orchestrator] ❌ {error_msg}")
                result["errors"].append(error_msg)
        
        # 生成总结
        result["completed_at"] = datetime.now().isoformat()
        result["summary"] = {
            "total_requirements": len(requirements),
            "total_tasks": len(tasks),
            "total_agent_tasks": len(result["agent_tasks"]),
            "total_errors": len(result["errors"])
        }
        
        print("\n" + "="*60)
        print("[Orchestrator] 自动化工作流完成")
        print("="*60)
        print(f"[Orchestrator] 需求数量: {result['summary']['total_requirements']}")
        print(f"[Orchestrator] 任务数量: {result['summary']['total_tasks']}")
        print(f"[Orchestrator] Agent任务数量: {result['summary']['total_agent_tasks']}")
        print(f"[Orchestrator] 错误数量: {result['summary']['total_errors']}")
        print("="*60)
        
        return result
    
    async def list_requirements(self, status: Optional[str] = None) -> List[Dict]:
        """
        列出所有需求
        
        Args:
            status: 筛选状态（pending/decomposed/completed）
        
        Returns:
            需求列表
        """
        if not self.requirement_extractor:
            return []
        
        return self.requirement_extractor.list_requirements(status)
    
    async def list_decomposed_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """
        列出所有分解的任务
        
        Args:
            status: 筛选状态（pending/running/completed/failed）
        
        Returns:
            任务列表
        """
        if not self.task_decomposer:
            return []
        
        return self.task_decomposer.list_tasks(status)


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
