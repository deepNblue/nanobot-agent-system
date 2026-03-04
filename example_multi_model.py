"""
多模型支持示例脚本
演示如何使用模型适配器、智能选择器和成本优化器
"""

import asyncio
import sys
from model_adapter import ModelAdapter
from model_selector import ModelSelector
from cost_optimizer import CostOptimizer


async def example1_basic_usage():
    """示例1：基本使用"""
    print("\n" + "=" * 60)
    print("示例1：基本使用 - 模型适配器")
    print("=" * 60)

    # 创建适配器
    adapter = ModelAdapter()

    # 查看可用模型
    models = adapter.get_available_models()
    print(f"\n可用模型 ({len(models)}个):")
    for model in models[:5]:  # 只显示前5个
        print(f"  - {model}")

    # 获取推荐模型
    preferred = adapter.get_preferred_model()
    print(f"\n推荐模型: {preferred}")

    # 计算token
    text = "这是一个测试文本，用于演示token计数功能"
    tokens = await adapter.count_tokens(preferred, text)
    print(f"\n文本 '{text}' 的token数: {tokens}")


async def example2_smart_selection():
    """示例2：智能模型选择"""
    print("\n" + "=" * 60)
    print("示例2：智能模型选择")
    print("=" * 60)

    adapter = ModelAdapter()
    selector = ModelSelector(adapter)

    # 定义不同类型的任务
    tasks = [
        {
            "name": "高复杂度任务",
            "task": {
                "description": "设计一个微服务架构系统，包括用户认证、订单处理和支付模块",
                "type": "architecture",
                "complexity": "high",
            },
        },
        {"name": "快速任务", "task": {"description": "快速修复登录页面的CSS样式问题", "priority": "high"}},
        {"name": "中文文档", "task": {"description": "编写一份详细的中文技术文档", "type": "documentation"}},
        {
            "name": "代码审查",
            "task": {"description": "审查这段代码的安全性和性能", "type": "code_review", "complexity": "medium"},
        },
    ]

    print("\n为不同任务选择最佳模型:\n")

    for task_info in tasks:
        model = await selector.select_best_model(task_info["task"])
        recommendations = await selector.get_model_recommendations(task_info["task"], top_n=2)

        print(f"{task_info['name']}:")
        print(f"  最佳模型: {model}")

        if recommendations:
            print(f"  推荐列表:")
            for i, (m, score, reason) in enumerate(recommendations, 1):
                print(f"    {i}. {m} (得分: {score:.1f}) - {reason}")
        print()


async def example3_cost_optimization():
    """示例3：成本优化"""
    print("\n" + "=" * 60)
    print("示例3：成本优化")
    print("=" * 60)

    # 创建成本优化器（日预算$5，时预算$1）
    optimizer = CostOptimizer(daily_budget=5.0, hourly_budget=1.0, alert_threshold=0.8)

    # 模拟一些使用记录
    print("\n模拟使用记录:")

    usage_records = [
        ("glm5-turbo", 500, "task-001"),
        ("glm5-turbo", 800, "task-002"),
        ("gpt-4-turbo", 600, "task-003"),
        ("glm5-plus", 1000, "task-004"),
        ("deepseek-chat", 400, "task-005"),
    ]

    for model, tokens, task_id in usage_records:
        await optimizer.record_usage(model, tokens, task_id=task_id)
        print(f"  记录: {model}, {tokens} tokens")

    # 获取统计信息
    stats = optimizer.get_daily_stats()

    print(f"\n每日统计:")
    print(f"  预算: ${stats['budget']:.2f}")
    print(f"  已使用: ${stats['spent']:.4f}")
    print(f"  剩余: ${stats['remaining']:.4f}")
    print(f"  使用率: {stats['usage_percentage']:.1f}%")
    print(f"  调用次数: {stats['usage_count']}")

    print(f"\n按模型统计:")
    for model, data in stats["by_model"].items():
        print(f"  {model}:")
        print(f"    调用次数: {data['count']}")
        print(f"    总tokens: {data['total_tokens']}")
        print(f"    总成本: ${data['total_cost']:.4f}")

    # 预算检查
    print(f"\n预算检查:")
    check1 = await optimizer.check_budget("glm5-turbo", 1000)
    print(f"  GLM5-Turbo 1000 tokens: {'✓ 通过' if check1 else '✗ 超预算'}")

    check2 = await optimizer.check_budget("claude-3-opus", 10000)
    print(f"  Claude-3-Opus 10000 tokens: {'✓ 通过' if check2 else '✗ 超预算'}")

    # 获取成本建议
    suggestions = optimizer.get_cost_saving_suggestions()
    if suggestions:
        print(f"\n成本优化建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")


async def example4_integrated_workflow():
    """示例4：完整工作流"""
    print("\n" + "=" * 60)
    print("示例4：完整工作流 - 智能代码助手")
    print("=" * 60)

    # 初始化所有组件
    adapter = ModelAdapter()
    selector = ModelSelector(adapter)
    optimizer = CostOptimizer(daily_budget=10.0)

    # 定义任务
    task = {
        "description": "实现一个Python函数，计算斐波那契数列的第n项，要求优化性能",
        "type": "feature",
        "complexity": "medium",
        "priority": "medium",
    }

    print(f"\n任务: {task['description']}\n")

    # 步骤1：分析任务特征
    print("步骤1：分析任务特征")
    features = selector.analyze_task(task)
    print(f"  复杂度: {features.complexity.value}")
    print(f"  类型: {features.type.value}")
    print(f"  语言: {features.language}")
    print(f"  估算tokens: {features.estimated_tokens}")

    # 步骤2：获取模型推荐
    print("\n步骤2：获取模型推荐")
    recommendations = await selector.get_model_recommendations(task, top_n=3)
    for i, (model, score, reason) in enumerate(recommendations, 1):
        print(f"  {i}. {model} (得分: {score:.1f})")
        print(f"     理由: {reason}")

    # 步骤3：选择模型（考虑成本）
    print("\n步骤3：选择模型（考虑成本）")
    selected_model, reason = await optimizer.optimize_model_selection(task, selector)
    print(f"  选择的模型: {selected_model}")
    print(f"  选择理由: {reason}")

    # 步骤4：检查预算
    print("\n步骤4：检查预算")
    estimated_tokens = features.estimated_tokens
    budget_ok = await optimizer.check_budget(selected_model, estimated_tokens)
    print(f"  预算检查: {'✓ 通过' if budget_ok else '✗ 超预算'}")

    if budget_ok and selected_model:
        print(f"\n步骤5：准备调用模型")
        print(f"  模型: {selected_model}")
        print(f"  提示词长度: {len(task['description'])} 字符")
        print(f"  估算tokens: {estimated_tokens}")

        # 注意：这里只是演示，不实际调用API
        print(f"\n  (实际使用时会调用API生成代码)")

        # 模拟记录使用
        await optimizer.record_usage(model=selected_model, tokens=estimated_tokens, task_id="example-task-001")
        print(f"\n步骤6：记录使用情况")

        # 显示最终统计
        status = optimizer.get_budget_status()
        print(f"\n当前预算状态:")
        print(f"  日预算: ${status.daily_budget:.2f}")
        print(f"  已使用: ${status.daily_spent:.4f}")
        print(f"  剩余: ${status.daily_remaining:.4f}")


async def example5_batch_operations():
    """示例5：批量操作"""
    print("\n" + "=" * 60)
    print("示例5：批量操作")
    print("=" * 60)

    adapter = ModelAdapter()

    # 准备批量请求
    requests = [
        {"model": "glm5-turbo", "prompt": "计算1+1", "max_tokens": 50},
        {"model": "glm5-turbo", "prompt": "计算2+2", "max_tokens": 50},
        {"model": "glm5-turbo", "prompt": "计算3+3", "max_tokens": 50},
    ]

    print(f"\n准备批量调用 {len(requests)} 个请求")
    print("(注意：这里只是演示，不实际调用API)")

    # 实际使用时取消注释
    # results = await adapter.batch_call(requests, max_concurrent=2)
    # for i, result in enumerate(results, 1):
    #     if result["success"]:
    #         print(f"请求 {i}: {result['content'][:50]}...")
    #     else:
    #         print(f"请求 {i}: 失败 - {result['error']}")


async def example6_constraint_based_selection():
    """示例6：基于约束的选择"""
    print("\n" + "=" * 60)
    print("示例6：基于约束的模型选择")
    print("=" * 60)

    adapter = ModelAdapter()
    selector = ModelSelector(adapter)

    task = {"description": "翻译技术文档", "type": "translation", "complexity": "low"}

    # 不同的约束条件
    constraints_list = [
        {"name": "成本优先", "constraints": {"max_cost": 0.005}},
        {"name": "速度优先", "constraints": {"requires_fast": True}},
        {"name": "质量优先", "constraints": {"requires_high_quality": True}},
        {"name": "排除特定模型", "constraints": {"exclude_models": ["gpt-4", "claude-3-opus"]}},
    ]

    print(f"\n任务: {task['description']}\n")

    for constraint_info in constraints_list:
        model = await selector.select_best_model(task, constraint_info["constraints"])
        print(f"{constraint_info['name']}:")
        print(f"  约束: {constraint_info['constraints']}")
        print(f"  选择: {model}\n")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Nanobot AI Agent - 多模型支持示例")
    print("=" * 60)

    # 运行所有示例
    await example1_basic_usage()
    await example2_smart_selection()
    await example3_cost_optimization()
    await example4_integrated_workflow()
    await example5_batch_operations()
    await example6_constraint_based_selection()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
    print("\n提示：")
    print("1. 配置API密钥到 ~/.nanobot/config.json 或环境变量")
    print("2. 查看文档: MULTI_MODEL_USAGE.md")
    print("3. 运行测试: pytest test_multi_model.py -v")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已中断")
        sys.exit(0)
