#!/usr/bin/env python3
"""
PR管理器基本功能测试
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from pr_manager import PRManager, get_pr_manager


def test_pr_manager_initialization():
    """测试PR管理器初始化"""
    print("\n=== 测试PR管理器初始化 ===")
    
    # 默认配置
    manager1 = PRManager()
    assert manager1.auto_merge_enabled == False
    assert manager1.merge_method == "squash"
    assert manager1.require_review == True
    print("✅ 默认配置正确")
    
    # 自定义配置
    config = {
        "auto_merge": True,
        "merge_method": "merge",
        "require_review": False,
        "min_review_score": 70
    }
    manager2 = PRManager(config)
    assert manager2.auto_merge_enabled == True
    assert manager2.merge_method == "merge"
    assert manager2.require_review == False
    assert manager2.min_review_score == 70
    print("✅ 自定义配置正确")


def test_generate_pr_title():
    """测试PR标题生成"""
    print("\n=== 测试PR标题生成 ===")
    
    manager = PRManager()
    
    # Feature类型
    task1 = {"type": "feature", "description": "实现用户头像上传"}
    title1 = manager.generate_pr_title(task1)
    assert "[Agent] Feature:" in title1
    assert "实现用户头像上传" in title1
    print(f"✅ Feature标题: {title1}")
    
    # Bugfix类型
    task2 = {"type": "bugfix", "description": "修复登录超时"}
    title2 = manager.generate_pr_title(task2)
    assert "[Agent] Bugfix:" in title2
    print(f"✅ Bugfix标题: {title2}")
    
    # 长描述截断
    task3 = {"type": "feature", "description": "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的描述"}
    title3 = manager.generate_pr_title(task3)
    assert len(title3) <= 100
    print(f"✅ 长描述截断: {title3}")


def test_generate_pr_body():
    """测试PR描述生成"""
    print("\n=== 测试PR描述生成 ===")
    
    manager = PRManager()
    
    task = {
        "id": "task_test_001",
        "description": "实现用户头像上传功能",
        "type": "feature",
        "agent": "GLM5-Turbo",
        "complexity": "Medium",
        "priority": "High",
        "review_score": 85,
        "security_passed": True,
        "performance_passed": True,
        "stats": {
            "unit_tests": "15/15 通过",
            "integration_tests": "5/5 通过",
            "coverage": 92
        }
    }
    
    body = manager.generate_pr_body(task)
    
    # 检查必要信息
    assert "task_test_001" in body
    assert "GLM5-Turbo" in body
    assert "实现用户头像上传功能" in body
    assert "Medium" in body
    assert "High" in body
    assert "15/15 通过" in body
    assert "92%" in body
    assert "85/100" in body
    assert "✅ 通过" in body
    print("✅ PR描述生成正确")
    print(f"\n生成的PR描述:\n{'-'*60}")
    print(body[:500] + "...")


def test_get_task_tags():
    """测试标签生成"""
    print("\n=== 测试标签生成 ===")
    
    manager = PRManager()
    
    task = {
        "type": "feature",
        "priority": "high",
        "complexity": "medium",
        "agent": "GLM5-Turbo"
    }
    
    tags = manager._get_task_tags(task)
    
    assert "agent-generated" in tags
    assert "feature" in tags
    assert "priority-high" in tags
    assert "complexity-medium" in tags
    assert "agent-glm5-turbo" in tags
    print(f"✅ 标签生成正确: {tags}")


def test_extract_pr_number():
    """测试PR编号提取"""
    print("\n=== 测试PR编号提取 ===")
    
    manager = PRManager()
    
    # 从URL提取
    url_output = "https://github.com/deepNblue/nanobot-agent-system/pull/123"
    pr_number1 = manager.extract_pr_number(url_output)
    assert pr_number1 == 123
    print(f"✅ 从URL提取: {pr_number1}")
    
    # 从数字提取
    number_output = "456"
    pr_number2 = manager.extract_pr_number(number_output)
    assert pr_number2 == 456
    print(f"✅ 从数字提取: {pr_number2}")
    
    # 无效输入
    try:
        manager.extract_pr_number("invalid")
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"✅ 无效输入正确抛出异常")


def test_get_merge_block_reason():
    """测试合并阻止原因"""
    print("\n=== 测试合并阻止原因 ===")
    
    manager = PRManager()
    
    # Review未通过
    status1 = {
        "review": {"approved": False, "decision": "CHANGES_REQUESTED"},
        "ci": {"success": True},
        "mergeable": True,
        "merge_state": "CLEAN"
    }
    reason1 = manager.get_merge_block_reason(status1)
    assert "Code Review" in reason1
    print(f"✅ Review未通过: {reason1}")
    
    # CI失败
    status2 = {
        "review": {"approved": True},
        "ci": {"success": False},
        "mergeable": True,
        "merge_state": "CLEAN"
    }
    reason2 = manager.get_merge_block_reason(status2)
    assert "CI" in reason2
    print(f"✅ CI失败: {reason2}")
    
    # 合并冲突
    status3 = {
        "review": {"approved": True},
        "ci": {"success": True},
        "mergeable": False,
        "merge_state": "DIRTY"
    }
    reason3 = manager.get_merge_block_reason(status3)
    assert "冲突" in reason3
    print(f"✅ 合并冲突: {reason3}")
    
    # 多个原因
    status4 = {
        "review": {"approved": False, "decision": "PENDING"},
        "ci": {"success": False},
        "mergeable": False,
        "merge_state": "BLOCKED"
    }
    reason4 = manager.get_merge_block_reason(status4)
    assert "Code Review" in reason4
    assert "CI" in reason4
    assert "冲突" in reason4
    print(f"✅ 多个原因: {reason4}")


async def test_save_and_load_task():
    """测试任务保存和加载"""
    print("\n=== 测试任务保存和加载 ===")
    
    manager = PRManager()
    
    task = {
        "id": "test_task_12345",
        "description": "测试任务",
        "status": "completed"
    }
    
    # 保存任务
    await manager.save_task(task)
    print("✅ 任务保存成功")
    
    # 加载任务
    loaded_task = await manager.load_task("test_task_12345")
    assert loaded_task is not None
    assert loaded_task["id"] == "test_task_12345"
    assert loaded_task["description"] == "测试任务"
    print("✅ 任务加载成功")
    
    # 加载不存在的任务
    not_found = await manager.load_task("non_existent_task")
    assert not_found is None
    print("✅ 不存在的任务返回None")


async def test_run_command():
    """测试命令执行"""
    print("\n=== 测试命令执行 ===")
    
    manager = PRManager()
    
    # 成功命令
    result1 = await manager.run_command("echo 'test'")
    assert result1["success"] == True
    assert "test" in result1["output"]
    print("✅ 成功命令执行正确")
    
    # 失败命令
    result2 = await manager.run_command("nonexistent_command_12345")
    assert result2["success"] == False
    assert "error" in result2
    print("✅ 失败命令处理正确")


def test_generate_pr_report():
    """测试PR报告生成"""
    print("\n=== 测试PR报告生成 ===")
    
    manager = PRManager()
    
    # 设置缓存
    pr_number = 123
    manager._pr_cache[pr_number] = {
        "pr_number": pr_number,
        "title": "Test PR",
        "state": "OPEN",
        "branch": "feature/test",
        "base_branch": "main",
        "url": "https://github.com/test/test/pull/123",
        "review": {
            "decision": "APPROVED",
            "approved": True
        },
        "ci": {
            "success": True,
            "total": 5,
            "completed": 5
        },
        "mergeable": True,
        "merge_state": "CLEAN",
        "ready_to_merge": True
    }
    
    report = manager.generate_pr_report(pr_number)
    
    assert "# PR #123" in report
    assert "Test PR" in report
    assert "OPEN" in report
    assert "feature/test" in report
    print("✅ PR报告生成正确")
    print(f"\n生成的报告:\n{'-'*60}")
    print(report[:500])


def test_singleton():
    """测试单例模式"""
    print("\n=== 测试单例模式 ===")
    
    manager1 = get_pr_manager()
    manager2 = get_pr_manager()
    
    assert manager1 is manager2
    print("✅ 单例模式正确")


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("开始运行PR管理器测试")
    print("="*60)
    
    try:
        # 同步测试
        test_pr_manager_initialization()
        test_generate_pr_title()
        test_generate_pr_body()
        test_get_task_tags()
        test_extract_pr_number()
        test_get_merge_block_reason()
        test_generate_pr_report()
        test_singleton()
        
        # 异步测试
        asyncio.run(test_save_and_load_task())
        asyncio.run(test_run_command())
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
