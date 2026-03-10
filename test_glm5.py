#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GLM-5集成
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from task_router import analyze_task


def test_glm5_integration():
    """测试GLM-5集成"""
    print("="*60)
    print("测试GLM-5集成")
    print("="*60)

    # 测试用例
    test_cases = [
        "实现用户登录功能",
        "设计支付系统架构",
        "修复登录bug",
        "编写单元测试",
        "代码审查",
        "/opencode-plan 设计数据库",
    ]

    print("\n📋 测试结果：\n")

    for task in test_cases:
        result = analyze_task(task)

        print(f"任务: {task}")
        print(f"  任务类型: {result['task_type']}")
        print(f"  Agent模式: {result['agent_mode']}")
        print(f"  模型: {result['model']}")
        print(f"  模型描述: {result['model_description']}")
        print()

        # 验证所有任务都使用GLM-5
        assert result['model'] == 'glm-5', f"模型应该是glm-5，但得到{result['model']}"
        assert 'zhipu/glm-5' in result['model_description'], "模型描述应该包含zhipu/glm-5"

    print("✅ 所有测试通过！")
    print("✅ 所有任务都使用GLM-5模型")


if __name__ == "__main__":
    test_glm5_integration()
