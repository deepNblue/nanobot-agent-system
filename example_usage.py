#!/usr/bin/env python3
"""
使用示例：展示如何使用Tmux + Worktree + Monitor功能
"""

import asyncio
import sys
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from nanobot_scheduler_enhanced import get_orchestrator_enhanced


async def example_create_task():
    """示例1：创建Agent任务"""
    print("=" * 60)
    print("示例1：创建Agent任务")
    print("=" * 60)
    print()

    # 初始化编排器
    orchestrator = get_orchestrator_enhanced(base_repo="/path/to/your/repo")

    # 创建任务
    result = await orchestrator.create_agent_task(
        task_id="feat-custom-templates",
        description="实现自定义模板功能",
        agent_type="codex",
        priority="high",
        base_branch="main",
        command_template="codex --task {task_id} --description '{description}'",
    )

    if result["success"]:
        print("✅ 任务创建成功！")
        print(f"  - Task ID: {result['task_id']}")
        print(f"  - Tmux Session: {result['tmux_session']}")
        print(f"  - Worktree: {result['worktree']}")
        print(f"  - Branch: {result['branch']}")
    else:
        print(f"❌ 任务创建失败: {result.get('error')}")

    return result


async def example_monitor_task():
    """示例2：监控任务"""
    print("\n" + "=" * 60)
    print("示例2：监控任务")
    print("=" * 60)
    print()

    orchestrator = get_orchestrator_enhanced()

    # 监控任务状态
    status = await orchestrator.monitor_task("feat-custom-templates")

    print(f"任务状态: {status.get('overall_status')}")
    print("\n检查详情:")

    checks = status.get("checks", {})
    for check_name, check_result in checks.items():
        if isinstance(check_result, dict):
            check_status = check_result.get("status") or check_result.get("ci_status") or "unknown"
            print(f"  - {check_name}: {check_status}")

    return status


async def example_intervene_task():
    """示例3：干预任务"""
    print("\n" + "=" * 60)
    print("示例3：干预任务")
    print("=" * 60)
    print()

    orchestrator = get_orchestrator_enhanced()

    # 发送干预命令
    result = await orchestrator.intervene_task(task_id="feat-custom-templates", command="echo '请优先处理性能优化'")

    if result.get("success"):
        print("✅ 命令发送成功！")
    else:
        print(f"❌ 命令发送失败: {result.get('error')}")

    return result


async def example_capture_output():
    """示例4：捕获任务输出"""
    print("\n" + "=" * 60)
    print("示例4：捕获任务输出")
    print("=" * 60)
    print()

    orchestrator = get_orchestrator_enhanced()

    # 捕获输出
    result = await orchestrator.capture_task_output(task_id="feat-custom-templates", lines=50)

    if result.get("success"):
        print("✅ 捕获成功！")
        print("\n最近50行输出:")
        print("-" * 60)
        print(result["output"])
    else:
        print(f"❌ 捕获失败: {result.get('error')}")

    return result


async def example_list_tasks():
    """示例5：列出所有任务"""
    print("\n" + "=" * 60)
    print("示例5：列出所有任务")
    print("=" * 60)
    print()

    orchestrator = get_orchestrator_enhanced()

    # 列出所有任务
    tasks = await orchestrator.list_all_tasks()

    print(f"找到 {len(tasks)} 个任务:\n")

    for task in tasks:
        print(f"  📋 {task['task_id']}")
        print(f"     - 状态: {task['status']}")
        print(f"     - Agent: {task['agent']}")
        print(f"     - 分支: {task['branch']}")
        print()

    return tasks


async def example_generate_report():
    """示例6：生成状态报告"""
    print("\n" + "=" * 60)
    print("示例6：生成状态报告")
    print("=" * 60)
    print()

    orchestrator = get_orchestrator_enhanced()

    # 生成报告
    report = await orchestrator.generate_status_report()

    print(report)

    return report


async def example_complete_task():
    """示例7：完成任务"""
    print("\n" + "=" * 60)
    print("示例7：完成任务")
    print("=" * 60)
    print()

    orchestrator = get_orchestrator_enhanced()

    # 完成任务（不清理worktree）
    result = await orchestrator.complete_task(task_id="feat-custom-templates", cleanup=False)  # 保留worktree以便查看

    if result.get("success"):
        print("✅ 任务已完成！")
        print(f"  - Worktree清理: {result.get('cleanup')}")
    else:
        print(f"❌ 完成失败: {result.get('error')}")

    return result


async def run_all_examples():
    """运行所有示例"""
    print("\n" + "🚀 " * 20)
    print("Tmux + Worktree + Monitor 功能演示")
    print("🚀 " * 20 + "\n")

    # 注意：这些示例需要实际的Git仓库才能运行
    print("⚠️  注意：这些示例需要实际的Git仓库才能运行")
    print("⚠️  请修改 example_create_task() 中的 base_repo 路径")
    print()

    # 如果要实际运行，取消下面的注释：

    # await example_create_task()
    # await example_monitor_task()
    # await example_intervene_task()
    # await example_capture_output()
    # await example_list_tasks()
    # await example_generate_report()
    # await example_complete_task()

    print("\n✅ 演示完成！")


def print_quick_reference():
    """打印快速参考"""
    print("""
╔════════════════════════════════════════════════════════════╗
║            快速参考：Agent任务管理                          ║
╚════════════════════════════════════════════════════════════╝

1️⃣  创建任务：
    orchestrator.create_agent_task(
        task_id="feat-xxx",
        description="功能描述",
        agent_type="codex"
    )

2️⃣  监控任务：
    orchestrator.monitor_task(task_id="feat-xxx")

3️⃣  干预任务：
    orchestrator.intervene_task(
        task_id="feat-xxx",
        command="调整方向命令"
    )

4️⃣  捕获输出：
    orchestrator.capture_task_output(
        task_id="feat-xxx",
        lines=100
    )

5️⃣  列出任务：
    orchestrator.list_all_tasks()

6️⃣  生成报告：
    orchestrator.generate_status_report()

7️⃣  完成任务：
    orchestrator.complete_task(
        task_id="feat-xxx",
        cleanup=True
    )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 任务记录格式：
{
  "id": "feat-custom-templates",
  "tmuxSession": "codex-templates",
  "agent": "codex",
  "worktree": "/path/to/worktrees/feat-custom-templates",
  "branch": "agent/feat-custom-templates",
  "startedAt": 1740268800000,
  "status": "running",
  "checkCI": true,
  "notifyOnComplete": true
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 命令行工具：

# 查看所有tmux会话
tmux list-sessions

# 连接到特定会话
tmux attach -t codex-templates

# 查看所有worktree
git worktree list

# 查看任务状态
python -c "from task_monitor import *; print(get_task_monitor().generate_report())"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    # 打印快速参考
    print_quick_reference()

    # 运行示例（需要实际仓库）
    # asyncio.run(run_all_examples())
