#!/usr/bin/env python3
"""
Agent任务管理CLI工具
提供命令行接口管理Agent任务
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from nanobot_scheduler_enhanced import get_orchestrator_enhanced
from task_monitor import get_task_monitor
from tmux_manager import get_tmux_manager


class AgentCLI:
    """Agent任务管理CLI"""
    
    def __init__(self, base_repo: str = None):
        self.orchestrator = get_orchestrator_enhanced(base_repo)
        self.monitor = get_task_monitor()
        self.tmux = get_tmux_manager()
    
    async def create(self, args):
        """创建新任务"""
        print(f"🚀 创建任务: {args.task_id}")
        print(f"   描述: {args.description}")
        print(f"   Agent: {args.agent}")
        print()
        
        result = await self.orchestrator.create_agent_task(
            task_id=args.task_id,
            description=args.description,
            agent_type=args.agent,
            priority=args.priority,
            base_branch=args.base_branch,
            command_template=args.command
        )
        
        if result.get("success"):
            print("✅ 任务创建成功！")
            print(f"   Tmux会话: {result['tmux_session']}")
            print(f"   Worktree: {result['worktree']}")
            print(f"   分支: {result['branch']}")
            print()
            print(f"💡 查看输出: agent-cli capture {args.task_id}")
            print(f"💡 连接会话: tmux attach -t {result['tmux_session']}")
        else:
            print(f"❌ 任务创建失败: {result.get('error')}")
    
    async def status(self, args):
        """查看任务状态"""
        if args.task_id:
            # 查看单个任务
            status = await self.orchestrator.monitor_task(args.task_id)
            
            print(f"📋 任务: {args.task_id}")
            print(f"   状态: {status.get('overall_status', 'unknown')}")
            print()
            
            checks = status.get("checks", {})
            if checks:
                print("   检查项:")
                for name, result in checks.items():
                    if isinstance(result, dict):
                        check_status = result.get("status") or result.get("ci_status") or "unknown"
                        print(f"     - {name}: {check_status}")
        else:
            # 查看所有任务
            tasks = await self.orchestrator.list_all_tasks()
            
            print(f"📋 所有任务 ({len(tasks)}个)")
            print()
            
            for task in tasks:
                status_icon = {
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "needs_review": "⚠️"
                }.get(task.get("status", "unknown"), "❓")
                
                print(f"{status_icon} {task['task_id']}")
                print(f"   状态: {task.get('status', 'unknown')}")
                print(f"   Agent: {task.get('agent', 'unknown')}")
                print(f"   分支: {task.get('branch', 'unknown')}")
                print()
    
    async def capture(self, args):
        """捕获任务输出"""
        result = await self.orchestrator.capture_task_output(
            task_id=args.task_id,
            lines=args.lines
        )
        
        if result.get("success"):
            print(f"📝 任务输出 (最近{args.lines}行)")
            print("=" * 60)
            print(result["output"])
        else:
            print(f"❌ 捕获失败: {result.get('error')}")
    
    async def intervene(self, args):
        """干预任务"""
        print(f"🎯 发送命令到任务: {args.task_id}")
        print(f"   命令: {args.command}")
        print()
        
        result = await self.orchestrator.intervene_task(
            task_id=args.task_id,
            command=args.command,
            enter=not args.no_enter
        )
        
        if result.get("success"):
            print("✅ 命令发送成功！")
            print()
            print(f"💡 查看输出: agent-cli capture {args.task_id}")
        else:
            print(f"❌ 命令发送失败: {result.get('error')}")
    
    async def complete(self, args):
        """完成任务"""
        print(f"✅ 完成任务: {args.task_id}")
        
        result = await self.orchestrator.complete_task(
            task_id=args.task_id,
            cleanup=args.cleanup
        )
        
        if result.get("success"):
            print("✅ 任务已完成！")
            if args.cleanup:
                print("   Worktree已清理")
        else:
            print(f"❌ 完成失败: {result.get('error')}")
    
    async def report(self, args):
        """生成报告"""
        report = await self.orchestrator.generate_status_report()
        print(report)
        
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding="utf-8")
            print(f"\n✅ 报告已保存到: {output_path}")
    
    def sessions(self, args):
        """列出tmux会话"""
        sessions = self.tmux.list_sessions()
        
        print(f"🖥️  Tmux会话 ({len(sessions)}个)")
        print()
        
        for session in sessions:
            attach_status = "📎 已连接" if session.get("attached") else "💤 未连接"
            print(f"  {session['name']}")
            print(f"    窗口数: {session.get('windows', 1)}")
            print(f"    状态: {attach_status}")
            print()
    
    def attach(self, args):
        """连接到tmux会话"""
        session_name = args.session
        
        if not self.tmux.session_exists(session_name):
            print(f"❌ 会话不存在: {session_name}")
            return
        
        print(f"📎 连接到会话: {session_name}")
        print("   按 Ctrl+B 然后 D 退出（会话继续运行）")
        print()
        
        import os
        os.system(f"tmux attach -t {session_name}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Agent任务管理CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 创建任务
  agent-cli create feat-xxx "实现新功能" --agent codex
  
  # 查看所有任务
  agent-cli status
  
  # 查看任务输出
  agent-cli capture feat-xxx --lines 100
  
  # 干预任务
  agent-cli intervene feat-xxx "调整方向"
  
  # 完成任务
  agent-cli complete feat-xxx --cleanup
  
  # 生成报告
  agent-cli report --output report.md
  
  # 列出tmux会话
  agent-cli sessions
  
  # 连接到会话
  agent-cli attach codex-feat-xxx
        """
    )
    
    parser.add_argument(
        "--repo",
        help="Git仓库路径（默认：当前目录）"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # create命令
    create_parser = subparsers.add_parser("create", help="创建新任务")
    create_parser.add_argument("task_id", help="任务ID")
    create_parser.add_argument("description", help="任务描述")
    create_parser.add_argument("--agent", default="codex", help="Agent类型")
    create_parser.add_argument("--priority", default="medium", help="优先级")
    create_parser.add_argument("--base-branch", default="main", help="基础分支")
    create_parser.add_argument("--command", help="自定义命令模板")
    
    # status命令
    status_parser = subparsers.add_parser("status", help="查看任务状态")
    status_parser.add_argument("task_id", nargs="?", help="任务ID（可选）")
    
    # capture命令
    capture_parser = subparsers.add_parser("capture", help="捕获任务输出")
    capture_parser.add_argument("task_id", help="任务ID")
    capture_parser.add_argument("--lines", type=int, default=100, help="捕获行数")
    
    # intervene命令
    intervene_parser = subparsers.add_parser("intervene", help="干预任务")
    intervene_parser.add_argument("task_id", help="任务ID")
    intervene_parser.add_argument("command", help="要发送的命令")
    intervene_parser.add_argument("--no-enter", action="store_true", help="不自动按回车")
    
    # complete命令
    complete_parser = subparsers.add_parser("complete", help="完成任务")
    complete_parser.add_argument("task_id", help="任务ID")
    complete_parser.add_argument("--cleanup", action="store_true", help="清理worktree")
    
    # report命令
    report_parser = subparsers.add_parser("report", help="生成报告")
    report_parser.add_argument("--output", help="输出文件路径")
    
    # sessions命令
    sessions_parser = subparsers.add_parser("sessions", help="列出tmux会话")
    
    # attach命令
    attach_parser = subparsers.add_parser("attach", help="连接到tmux会话")
    attach_parser.add_argument("session", help="会话名称")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建CLI实例
    cli = AgentCLI(args.repo)
    
    # 执行命令
    if args.command == "sessions":
        cli.sessions(args)
    elif args.command == "attach":
        cli.attach(args)
    else:
        # 异步命令
        async def run():
            if args.command == "create":
                await cli.create(args)
            elif args.command == "status":
                await cli.status(args)
            elif args.command == "capture":
                await cli.capture(args)
            elif args.command == "intervene":
                await cli.intervene(args)
            elif args.command == "complete":
                await cli.complete(args)
            elif args.command == "report":
                await cli.report(args)
        
        asyncio.run(run())


if __name__ == "__main__":
    main()
