#!/usr/bin/env python3
"""
测试Tmux + Worktree + Monitor功能
全面验证Agent系统的核心功能
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from worktree_manager import WorktreeManager, get_worktree_manager
from tmux_manager import TmuxManager, get_tmux_manager
from task_monitor import TaskMonitor, get_task_monitor


class TestResult:
    """测试结果收集器"""

    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0

    def add_result(self, name: str, success: bool, message: str = ""):
        self.tests.append({"name": name, "success": success, "message": message, "timestamp": datetime.now().isoformat()})

        if success:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed += 1
            print(f"❌ {name}: {message}")

    def print_summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试总结: {self.passed}/{total} 通过")
        print(f"{'='*60}")

        if self.failed > 0:
            print("\n失败的测试:")
            for test in self.tests:
                if not test["success"]:
                    print(f"  - {test['name']}: {test['message']}")


def test_tmux_available():
    """测试Tmux是否可用"""
    try:
        result = subprocess.run(["tmux", "-V"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def test_git_available():
    """测试Git是否可用"""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def create_test_repo():
    """创建测试Git仓库"""
    test_dir = Path(tempfile.mkdtemp(prefix="test_repo_"))

    # 初始化仓库
    subprocess.run(["git", "init"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=test_dir, capture_output=True)

    # 创建初始文件
    (test_dir / "README.md").write_text("# Test Repository\n")
    subprocess.run(["git", "add", "."], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_dir, capture_output=True)

    # 创建main分支
    subprocess.run(["git", "branch", "-M", "main"], cwd=test_dir, capture_output=True)

    return test_dir


def run_tests():
    """运行所有测试"""
    results = TestResult()

    print("=" * 60)
    print("开始测试 Tmux + Worktree + Monitor 功能")
    print("=" * 60)
    print()

    # ========== 基础环境测试 ==========
    print("【阶段1】基础环境检查")
    print("-" * 60)

    # 测试tmux
    success, message = test_tmux_available()
    results.add_result("Tmux可用性", success, message)

    # 测试git
    success, message = test_git_available()
    results.add_result("Git可用性", success, message)

    # 如果基础工具不可用，直接返回
    if results.failed > 0:
        print("\n⚠️  基础工具不可用，无法继续测试")
        results.print_summary()
        return results

    print()

    # ========== TmuxManager测试 ==========
    print("【阶段2】Tmux管理器测试")
    print("-" * 60)

    try:
        tmux_manager = TmuxManager()
        results.add_result("TmuxManager初始化", True)
    except Exception as e:
        results.add_result("TmuxManager初始化", False, str(e))
        results.print_summary()
        return results

    # 测试创建会话
    test_session = f"test-session-{int(time.time())}"
    test_dir = Path(tempfile.mkdtemp(prefix="tmux_test_"))

    create_result = tmux_manager.create_session(
        session_name=test_session, working_dir=str(test_dir), command="echo 'Hello from tmux'"
    )
    results.add_result("创建Tmux会话", create_result.get("success", False), create_result.get("error", ""))

    # 测试会话存在检查
    exists = tmux_manager.session_exists(test_session)
    results.add_result("会话存在检查", exists)

    # 测试发送命令
    if exists:
        send_result = tmux_manager.send_command(session_name=test_session, command="echo 'Test command'")
        results.add_result("发送命令到会话", send_result.get("success", False), send_result.get("error", ""))

        # 等待命令执行
        time.sleep(1)

        # 测试捕获输出
        capture_result = tmux_manager.capture_pane(session_name=test_session, lines=50)
        has_output = capture_result.get("success", False) and len(capture_result.get("output", "")) > 0
        results.add_result("捕获会话输出", has_output, capture_result.get("error", ""))

        # 测试列出会话
        sessions = tmux_manager.list_sessions()
        session_names = [s["name"] for s in sessions]
        results.add_result("列出所有会话", test_session in session_names, f"找到的会话: {', '.join(session_names)}")

        # 测试终止会话
        kill_result = tmux_manager.kill_session(test_session)
        results.add_result("终止会话", kill_result.get("success", False), kill_result.get("error", ""))

    print()

    # ========== WorktreeManager测试 ==========
    print("【阶段3】Worktree管理器测试")
    print("-" * 60)

    # 创建测试仓库
    test_repo = create_test_repo()

    try:
        worktree_manager = WorktreeManager(base_repo=str(test_repo))
        results.add_result("WorktreeManager初始化", True)
    except Exception as e:
        results.add_result("WorktreeManager初始化", False, str(e))
        results.print_summary()
        return results

    # 测试创建worktree
    test_task_id = f"test-task-{int(time.time())}"

    create_result = worktree_manager.create_worktree(task_id=test_task_id, description="Test task for worktree")
    results.add_result("创建Worktree", create_result.get("success", False), create_result.get("error", ""))

    # 测试worktree路径
    if create_result.get("success"):
        worktree_path = Path(create_result["path"])
        results.add_result("Worktree路径存在", worktree_path.exists(), str(worktree_path))

        # 测试分支创建
        branch = create_result.get("branch", "")
        results.add_result("分支创建", "agent/" in branch, f"分支: {branch}")

        # 测试列出worktree
        worktrees = worktree_manager.list_worktrees()
        worktree_paths = [w["path"] for w in worktrees]
        results.add_result("列出所有Worktree", str(worktree_path) in worktree_paths, f"找到 {len(worktrees)} 个worktree")

        # 测试移除worktree
        remove_result = worktree_manager.remove_worktree(test_task_id, force=True)
        results.add_result("移除Worktree", remove_result.get("success", False), remove_result.get("error", ""))

        # 验证worktree已移除
        results.add_result("Worktree已清理", not worktree_path.exists(), f"路径: {worktree_path}")

    print()

    # ========== TaskMonitor测试 ==========
    print("【阶段4】任务监控器测试")
    print("-" * 60)

    # 创建临时任务目录
    test_tasks_dir = Path(tempfile.mkdtemp(prefix="test_tasks_"))

    try:
        task_monitor = TaskMonitor(tasks_dir=str(test_tasks_dir))
        results.add_result("TaskMonitor初始化", True)
    except Exception as e:
        results.add_result("TaskMonitor初始化", False, str(e))
        results.print_summary()
        return results

    # 创建测试任务
    test_task = {
        "id": "test-monitor-task",
        "description": "Test task for monitoring",
        "agent": "test-agent",
        "tmuxSession": test_session,
        "worktree": str(test_repo),
        "branch": "test-branch",
        "status": "running",
        "startedAt": int(datetime.now().timestamp() * 1000),
        "checkCI": False,
    }

    # 保存测试任务
    task_file = test_tasks_dir / f"{test_task['id']}.json"
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(test_task, f, indent=2)

    # 测试检查任务状态
    status_result = task_monitor.check_task_status(test_task["id"])
    results.add_result(
        "检查任务状态",
        status_result.get("success", False) or "overall_status" in status_result,
        f"状态: {status_result.get('overall_status', 'unknown')}",
    )

    # 测试列出所有任务
    all_tasks = task_monitor.monitor_all_tasks()
    results.add_result("监控所有任务", len(all_tasks) > 0, f"找到 {len(all_tasks)} 个任务")

    # 测试生成报告
    report = task_monitor.generate_report()
    results.add_result("生成监控报告", len(report) > 0 and "任务监控报告" in report, f"报告长度: {len(report)} 字符")

    print()

    # ========== 集成测试 ==========
    print("【阶段5】集成测试")
    print("-" * 60)

    # 创建完整的Agent任务
    integration_task_id = f"integration-test-{int(time.time())}"

    # 1. 创建worktree
    worktree_result = worktree_manager.create_worktree(task_id=integration_task_id, description="Integration test task")

    if worktree_result.get("success"):
        results.add_result("集成-创建Worktree", True)

        worktree_path = worktree_result["path"]

        # 2. 创建tmux会话
        tmux_result = tmux_manager.create_session(
            session_name=f"test-{integration_task_id}", working_dir=worktree_path, command="echo 'Integration test started'"
        )

        if tmux_result.get("success"):
            results.add_result("集成-创建Tmux会话", True)

            session_name = tmux_result["session_name"]

            # 3. 保存任务记录
            integration_task = {
                "id": integration_task_id,
                "description": "Integration test task",
                "agent": "test",
                "tmuxSession": session_name,
                "worktree": worktree_path,
                "branch": worktree_result["branch"],
                "status": "running",
                "startedAt": int(datetime.now().timestamp() * 1000),
                "checkCI": False,
            }

            task_file = test_tasks_dir / f"{integration_task_id}.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(integration_task, f, indent=2)

            results.add_result("集成-保存任务记录", True)

            # 4. 监控任务
            time.sleep(2)
            monitor_result = task_monitor.check_task_status(integration_task_id)
            results.add_result(
                "集成-监控任务", "overall_status" in monitor_result, f"状态: {monitor_result.get('overall_status')}"
            )

            # 5. 发送干预命令
            intervene_result = tmux_manager.send_command(session_name=session_name, command="echo 'Intervention test'")
            results.add_result("集成-干预命令", intervene_result.get("success", False), intervene_result.get("error", ""))

            # 6. 捕获输出
            time.sleep(1)
            capture_result = tmux_manager.capture_pane(session_name=session_name)
            results.add_result(
                "集成-捕获输出",
                capture_result.get("success", False) and "Integration test" in capture_result.get("output", ""),
                capture_result.get("error", ""),
            )

            # 7. 清理
            tmux_manager.kill_session(session_name)
            worktree_manager.remove_worktree(integration_task_id, force=True)
            results.add_result("集成-清理资源", True)
        else:
            results.add_result("集成-创建Tmux会话", False, tmux_result.get("error", ""))
    else:
        results.add_result("集成-创建Worktree", False, worktree_result.get("error", ""))

    print()

    # ========== 清理测试环境 ==========
    print("【清理】清理测试环境")
    print("-" * 60)

    try:
        # 清理测试仓库
        import shutil

        if test_repo.exists():
            shutil.rmtree(test_repo)
            print(f"✅ 清理测试仓库: {test_repo}")

        # 清理测试目录
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"✅ 清理测试目录: {test_dir}")

        # 清理任务目录
        if test_tasks_dir.exists():
            shutil.rmtree(test_tasks_dir)
            print(f"✅ 清理任务目录: {test_tasks_dir}")

        # 清理worktrees目录
        worktrees_dir = test_repo.parent / "worktrees"
        if worktrees_dir.exists():
            shutil.rmtree(worktrees_dir)
            print(f"✅ 清理worktrees目录: {worktrees_dir}")
    except Exception as e:
        print(f"⚠️  清理时出错: {e}")

    print()

    # ========== 打印总结 ==========
    results.print_summary()

    return results


if __name__ == "__main__":
    results = run_tests()

    # 返回退出码
    sys.exit(0 if results.failed == 0 else 1)
