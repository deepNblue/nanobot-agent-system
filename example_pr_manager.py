#!/usr/bin/env python3
"""
PR管理器完整使用示例
展示如何使用PR自动管理功能
"""

import asyncio
import sys
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from pr_manager import get_pr_manager
from nanobot_scheduler_enhanced import get_orchestrator_enhanced


async def example_1_basic_pr_creation():
    """示例1: 基本PR创建"""
    print("\n" + "="*60)
    print("示例1: 基本PR创建")
    print("="*60)
    
    # 获取PR管理器
    pr_manager = get_pr_manager()
    
    # 模拟一个完成的任务
    task_id = "task_example_001"
    
    # 创建任务记录（实际使用时由编排器创建）
    import json
    from datetime import datetime
    
    task = {
        "id": task_id,
        "description": "实现用户头像上传功能",
        "type": "feature",
        "agent": "GLM5-Turbo",
        "complexity": "Medium",
        "priority": "High",
        "status": "completed",
        "branch": "feature/user-avatar-upload",
        "baseBranch": "main",
        "review_score": 85,
        "ci_passed": True,
        "security_passed": True,
        "performance_passed": True,
        "stats": {
            "unit_tests": "15/15 通过",
            "integration_tests": "5/5 通过",
            "coverage": 92,
            "changed_files": "5 files changed"
        },
        "createdAt": datetime.now().isoformat()
    }
    
    # 保存任务
    await pr_manager.save_task(task)
    print(f"✅ 任务已创建: {task_id}")
    
    # 生成PR标题和描述（不实际创建PR）
    title = pr_manager.generate_pr_title(task)
    body = pr_manager.generate_pr_body(task)
    
    print(f"\n生成的PR标题:")
    print(f"  {title}")
    
    print(f"\n生成的PR描述:")
    print("-" * 60)
    print(body)


async def example_2_pr_monitoring():
    """示例2: PR状态监控"""
    print("\n" + "="*60)
    print("示例2: PR状态监控")
    print("="*60)
    
    pr_manager = get_pr_manager()
    
    # 模拟PR状态
    pr_number = 123
    
    # 模拟缓存数据
    pr_manager._pr_cache[pr_number] = {
        "pr_number": pr_number,
        "state": "OPEN",
        "title": "[Agent] Feature: 实现用户头像上传",
        "branch": "feature/user-avatar-upload",
        "base_branch": "main",
        "url": f"https://github.com/deepNblue/nanobot-agent-system/pull/{pr_number}",
        "review": {
            "approved": True,
            "decision": "APPROVED",
            "required": True
        },
        "ci": {
            "success": True,
            "checks": [],
            "total": 5,
            "completed": 5,
            "required": True
        },
        "mergeable": True,
        "merge_state": "CLEAN",
        "ready_to_merge": True
    }
    
    # 获取状态
    status = pr_manager._pr_cache[pr_number]
    
    print(f"PR #{pr_number} 状态:")
    print(f"  - 标题: {status['title']}")
    print(f"  - 状态: {status['state']}")
    print(f"  - Review: {'✅ 通过' if status['review']['approved'] else '❌ 未通过'}")
    print(f"  - CI: {'✅ 通过' if status['ci']['success'] else '❌ 未通过'}")
    print(f"  - 冲突: {'❌ 有冲突' if not status['mergeable'] else '✅ 无冲突'}")
    print(f"  - 可合并: {'✅ 是' if status['ready_to_merge'] else '❌ 否'}")
    
    # 生成报告
    report = pr_manager.generate_pr_report(pr_number)
    print(f"\nPR报告:")
    print("-" * 60)
    print(report)


async def example_3_merge_block_analysis():
    """示例3: 合并阻止原因分析"""
    print("\n" + "="*60)
    print("示例3: 合并阻止原因分析")
    print("="*60)
    
    pr_manager = get_pr_manager()
    
    # 场景1: Review未通过
    status1 = {
        "review": {"approved": False, "decision": "CHANGES_REQUESTED"},
        "ci": {"success": True},
        "mergeable": True,
        "merge_state": "CLEAN"
    }
    reason1 = pr_manager.get_merge_block_reason(status1)
    print(f"场景1 - Review未通过:")
    print(f"  阻止原因: {reason1}\n")
    
    # 场景2: CI失败
    status2 = {
        "review": {"approved": True},
        "ci": {"success": False},
        "mergeable": True,
        "merge_state": "CLEAN"
    }
    reason2 = pr_manager.get_merge_block_reason(status2)
    print(f"场景2 - CI失败:")
    print(f"  阻止原因: {reason2}\n")
    
    # 场景3: 合并冲突
    status3 = {
        "review": {"approved": True},
        "ci": {"success": True},
        "mergeable": False,
        "merge_state": "DIRTY"
    }
    reason3 = pr_manager.get_merge_block_reason(status3)
    print(f"场景3 - 合并冲突:")
    print(f"  阻止原因: {reason3}\n")
    
    # 场景4: 多个问题
    status4 = {
        "review": {"approved": False, "decision": "PENDING"},
        "ci": {"success": False},
        "mergeable": False,
        "merge_state": "BLOCKED"
    }
    reason4 = pr_manager.get_merge_block_reason(status4)
    print(f"场景4 - 多个问题:")
    print(f"  阻止原因: {reason4}\n")


async def example_4_orchestrator_integration():
    """示例4: 与编排器集成"""
    print("\n" + "="*60)
    print("示例4: 与编排器集成")
    print("="*60)
    
    # 获取编排器
    orchestrator = get_orchestrator_enhanced()
    
    print("编排器配置:")
    print(f"  - 自动代码审查: {orchestrator.auto_review_enabled}")
    print(f"  - 自动CI检查: {orchestrator.auto_ci_check_enabled}")
    print(f"  - 自动重试CI: {orchestrator.auto_retry_ci_enabled}")
    print(f"  - 自动创建PR: {orchestrator.auto_pr_enabled}")
    print(f"  - 自动合并PR: {orchestrator.auto_merge_enabled}")
    
    print("\n可用方法:")
    print("  - create_agent_task(): 创建任务")
    print("  - monitor_task(): 监控任务")
    print("  - complete_task_with_pr(): 完成任务并创建PR")
    print("  - auto_create_pr(): 自动创建PR")
    print("  - monitor_pr(): 监控PR状态")
    print("  - auto_merge_pr(): 自动合并PR")
    print("  - list_prs(): 列出PR列表")


async def example_5_full_workflow():
    """示例5: 完整工作流"""
    print("\n" + "="*60)
    print("示例5: 完整工作流演示")
    print("="*60)
    
    pr_manager = get_pr_manager()
    
    # 步骤1: 创建任务
    print("步骤1: 创建任务")
    task_id = "task_full_workflow"
    task = {
        "id": task_id,
        "description": "实现完整的PR管理工作流",
        "type": "feature",
        "agent": "GLM5-Turbo",
        "complexity": "High",
        "priority": "High",
        "status": "running",
        "branch": "feature/pr-workflow",
        "baseBranch": "main",
        "createdAt": "2026-03-04T12:00:00"
    }
    await pr_manager.save_task(task)
    print(f"  ✅ 任务创建成功: {task_id}")
    
    # 步骤2: 模拟任务完成
    print("\n步骤2: 任务完成")
    task["status"] = "completed"
    task["review_score"] = 88
    task["ci_passed"] = True
    task["security_passed"] = True
    task["performance_passed"] = True
    task["stats"] = {
        "unit_tests": "20/20 通过",
        "integration_tests": "8/8 通过",
        "coverage": 95,
        "changed_files": "8 files changed"
    }
    await pr_manager.save_task(task)
    print(f"  ✅ 任务状态更新为: completed")
    
    # 步骤3: 生成PR内容
    print("\n步骤3: 生成PR内容")
    title = pr_manager.generate_pr_title(task)
    body = pr_manager.generate_pr_body(task)
    tags = pr_manager._get_task_tags(task)
    
    print(f"  ✅ PR标题: {title}")
    print(f"  ✅ PR标签: {', '.join(tags)}")
    
    # 步骤4: 模拟PR创建
    print("\n步骤4: 创建PR")
    # 注意: 实际使用时会调用 gh pr create
    print(f"  ⚠️  实际使用时会执行: gh pr create --base main --head {task['branch']}")
    print(f"  ✅ PR #456 创建成功（模拟）")
    
    # 更新任务
    task["pr"] = {
        "number": 456,
        "url": "https://github.com/deepNblue/nanobot-agent-system/pull/456",
        "created_at": "2026-03-04T12:30:00",
        "title": title
    }
    await pr_manager.save_task(task)
    
    # 步骤5: 监控PR状态
    print("\n步骤5: 监控PR状态")
    # 模拟PR状态
    pr_manager._pr_cache[456] = {
        "pr_number": 456,
        "state": "OPEN",
        "title": title,
        "branch": task["branch"],
        "base_branch": "main",
        "url": task["pr"]["url"],
        "review": {"approved": True, "decision": "APPROVED"},
        "ci": {"success": True, "total": 5, "completed": 5},
        "mergeable": True,
        "merge_state": "CLEAN",
        "ready_to_merge": True
    }
    
    status = pr_manager._pr_cache[456]
    print(f"  ✅ Review: {'通过' if status['review']['approved'] else '未通过'}")
    print(f"  ✅ CI: {'通过' if status['ci']['success'] else '未通过'}")
    print(f"  ✅ 冲突: {'无' if status['mergeable'] else '有'}")
    print(f"  ✅ 可合并: {'是' if status['ready_to_merge'] else '否'}")
    
    # 步骤6: 自动合并
    print("\n步骤6: 自动合并PR")
    if status["ready_to_merge"]:
        print(f"  ⚠️  实际使用时会执行: gh pr merge 456 --squash --delete-branch")
        print(f"  ✅ PR #456 合并成功（模拟）")
        
        task["status"] = "merged"
        task["merged_at"] = "2026-03-04T13:00:00"
        await pr_manager.save_task(task)
        print(f"  ✅ 任务状态更新为: merged")
    
    # 步骤7: 生成报告
    print("\n步骤7: 生成PR报告")
    report = pr_manager.generate_pr_report(456)
    print(report[:300] + "...")
    
    print("\n✅ 完整工作流演示完成！")


async def example_6_configuration_options():
    """示例6: 配置选项"""
    print("\n" + "="*60)
    print("示例6: 配置选项演示")
    print("="*60)
    
    # 配置1: 保守配置（推荐生产环境）
    print("配置1: 保守配置（推荐生产环境）")
    config1 = {
        "auto_merge": False,  # 不自动合并
        "merge_method": "squash",
        "require_review": True,  # 需要Review
        "require_ci": True,  # 需要CI
        "min_review_score": 80  # 最低分数80
    }
    manager1 = get_pr_manager(config1)
    print(f"  - 自动合并: {manager1.auto_merge_enabled}")
    print(f"  - 需要Review: {manager1.require_review}")
    print(f"  - 需要CI: {manager1.require_ci}")
    print(f"  - 最低分数: {manager1.min_review_score}")
    
    # 配置2: 激进配置（仅用于测试）
    print("\n配置2: 激进配置（仅用于测试环境）")
    config2 = {
        "auto_merge": True,  # 自动合并
        "merge_method": "merge",  # 保留提交历史
        "require_review": False,  # 不需要Review
        "require_ci": False,  # 不需要CI
        "min_review_score": 60  # 降低分数要求
    }
    from pr_manager import PRManager
    manager2 = PRManager(config2)
    print(f"  - 自动合并: {manager2.auto_merge_enabled}")
    print(f"  - 需要Review: {manager2.require_review}")
    print(f"  - 需要CI: {manager2.require_ci}")
    print(f"  - 最低分数: {manager2.min_review_score}")
    
    print("\n⚠️  警告: 激进配置仅用于测试环境，生产环境请使用保守配置！")


async def main():
    """运行所有示例"""
    print("="*60)
    print("PR管理器使用示例")
    print("="*60)
    
    await example_1_basic_pr_creation()
    await example_2_pr_monitoring()
    await example_3_merge_block_analysis()
    await example_4_orchestrator_integration()
    await example_5_full_workflow()
    await example_6_configuration_options()
    
    print("\n" + "="*60)
    print("✅ 所有示例运行完成！")
    print("="*60)
    
    print("\n下一步:")
    print("1. 配置GitHub CLI: gh auth login")
    print("2. 创建测试任务: python agent_cli.py create --description '测试任务'")
    print("3. 运行完整工作流: python agent_cli.py complete --task-id <task_id> --create-pr")
    print("4. 查看PR状态: python agent_cli.py pr-status --pr-number <number>")
    print("\n详细文档请参考: PR_MANAGER_GUIDE.md")


if __name__ == "__main__":
    asyncio.run(main())
