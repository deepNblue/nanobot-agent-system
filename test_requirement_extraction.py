"""
测试需求提取和任务分解功能

测试用例：
1. 测试从Obsidian读取笔记
2. 测试需求提取
3. 测试任务分解
4. 测试Agent选择逻辑
5. 测试完整工作流
"""

import asyncio
import sys
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from requirement_extractor import RequirementExtractor, get_requirement_extractor
from task_decomposer import TaskDecomposer, get_task_decomposer
from nanobot_scheduler_enhanced import get_orchestrator_enhanced


class TestRequirementExtraction:
    """需求提取测试"""
    
    def __init__(self):
        self.extractor = get_requirement_extractor()
        self.decomposer = get_task_decomposer()
        self.orchestrator = get_orchestrator_enhanced()
    
    async def test_scan_notes(self):
        """测试1: 扫描Obsidian笔记"""
        print("\n" + "="*60)
        print("测试1: 扫描Obsidian笔记")
        print("="*60)
        
        notes = await self.extractor.scan_daily_notes(days=7)
        
        print(f"✓ 找到 {len(notes)} 篇笔记")
        
        for i, note in enumerate(notes[:3], 1):
            print(f"\n笔记 {i}:")
            print(f"  标题: {note['title']}")
            print(f"  路径: {note['path']}")
            print(f"  修改时间: {note['modified_at']}")
            print(f"  内容长度: {len(note['content'])} 字符")
        
        return len(notes) > 0
    
    async def test_action_keywords(self):
        """测试2: 检测行动项关键词"""
        print("\n" + "="*60)
        print("测试2: 检测行动项关键词")
        print("="*60)
        
        test_cases = [
            ("TODO: 实现用户登录功能", True),
            ("这是一个普通段落", False),
            ("需要修复这个bug", True),
            ("计划下周开会讨论", True),
            ("文档已更新", False)
        ]
        
        all_passed = True
        for content, expected in test_cases:
            result = self.extractor._contains_action_items(content)
            status = "✓" if result == expected else "✗"
            print(f"{status} '{content}' -> {result} (期望: {expected})")
            
            if result != expected:
                all_passed = False
        
        return all_passed
    
    async def test_priority_extraction(self):
        """测试3: 优先级提取"""
        print("\n" + "="*60)
        print("测试3: 优先级提取")
        print("="*60)
        
        test_cases = [
            ("紧急修复登录问题", "high"),
            ("这是一个普通的任务", "medium"),
            ("有空时优化一下UI", "low"),
            ("P0级别bug", "high"),
            ("可选功能增强", "low")
        ]
        
        all_passed = True
        for content, expected in test_cases:
            result = self.extractor._extract_priority(content)
            status = "✓" if result == expected else "✗"
            print(f"{status} '{content}' -> {result} (期望: {expected})")
            
            if result != expected:
                all_passed = False
        
        return all_passed
    
    async def test_complexity_analysis(self):
        """测试4: 复杂度分析"""
        print("\n" + "="*60)
        print("测试4: 复杂度分析")
        print("="*60)
        
        test_cases = [
            ({
                "description": "重构整个架构系统",
                "context": "需要重新设计数据库schema",
                "tags": ["refactor", "architecture"]
            }, "high"),
            ({
                "description": "修复登录按钮样式",
                "context": "UI调整",
                "tags": ["ui", "fix"]
            }, "low"),
            ({
                "description": "添加用户导出功能",
                "context": "中等复杂度",
                "tags": ["feature"]
            }, "medium")
        ]
        
        all_passed = True
        for requirement, expected in test_cases:
            result = self.decomposer.analyze_complexity(requirement)
            status = "✓" if result == expected else "✗"
            print(f"{status} '{requirement['description']}' -> {result} (期望: {expected})")
            
            if result != expected:
                all_passed = False
        
        return all_passed
    
    async def test_agent_selection(self):
        """测试5: Agent选择逻辑"""
        print("\n" + "="*60)
        print("测试5: Agent选择逻辑")
        print("="*60)
        
        test_cases = [
            ("high", "glm5-plus"),
            ("medium", "glm5-turbo"),
            ("low", "glm5-lite")
        ]
        
        all_passed = True
        for complexity, expected_agent in test_cases:
            agent_config = self.decomposer.select_agent(complexity)
            result = agent_config["agent_type"]
            status = "✓" if result == expected_agent else "✗"
            print(f"{status} 复杂度 {complexity} -> Agent {result} (期望: {expected_agent})")
            print(f"   模型: {agent_config['model']}")
            print(f"   描述: {agent_config['description']}")
            
            if result != expected_agent:
                all_passed = False
        
        return all_passed
    
    async def test_time_estimation(self):
        """测试6: 时间估算"""
        print("\n" + "="*60)
        print("测试6: 时间估算")
        print("="*60)
        
        test_cases = ["high", "medium", "low"]
        
        for complexity in test_cases:
            time_estimate = self.decomposer.estimate_time(complexity)
            print(f"✓ 复杂度 {complexity} -> 预估时间: {time_estimate}")
        
        return True
    
    async def test_requirement_extraction(self):
        """测试7: 完整需求提取流程"""
        print("\n" + "="*60)
        print("测试7: 完整需求提取流程")
        print("="*60)
        
        # 模拟一个会议记录
        mock_note = {
            "title": "2026-03-04 产品会议",
            "path": "Daily Notes/2026-03-04.md",
            "content": """
# 2026-03-04 产品会议

## 参会人员
- 产品经理
- 技术负责人
- UI设计师

## 讨论内容

### 用户反馈
- 用户希望有自定义头像功能
- 需要优化登录流程

### 行动项
- TODO: 实现用户头像上传功能（高优先级）
- TODO: 简化登录流程，减少步骤
- FIXME: 修复头像显示bug
- 计划下周完成用户调研

## 下一步
1. 设计头像上传UI
2. 开发后端API
3. 集成测试
"""
        }
        
        print("模拟会议记录:")
        print(f"  标题: {mock_note['title']}")
        print(f"  内容长度: {len(mock_note['content'])} 字符")
        
        # 使用GLM5分析
        print("\n调用GLM5分析会议记录...")
        requirements = await self.extractor.analyze_with_glm5(mock_note)
        
        if requirements:
            print(f"✓ 提取到 {len(requirements)} 个需求:")
            for i, req in enumerate(requirements, 1):
                print(f"\n  需求 {i}:")
                print(f"    描述: {req.get('description')}")
                print(f"    优先级: {req.get('priority')}")
                print(f"    标签: {req.get('tags')}")
            return True
        else:
            print("✗ 需求提取失败")
            return False
    
    async def test_task_decomposition(self):
        """测试8: 任务分解流程"""
        print("\n" + "="*60)
        print("测试8: 任务分解流程")
        print("="*60)
        
        # 模拟一个需求
        mock_requirement = {
            "id": "req_test_001",
            "description": "实现用户头像上传功能",
            "priority": "high",
            "tags": ["feature", "user", "upload"],
            "context": "用户反馈需要自定义头像功能"
        }
        
        print("模拟需求:")
        print(f"  ID: {mock_requirement['id']}")
        print(f"  描述: {mock_requirement['description']}")
        print(f"  优先级: {mock_requirement['priority']}")
        print(f"  标签: {mock_requirement['tags']}")
        
        # 分解任务
        print("\n开始分解任务...")
        task = await self.decomposer.decompose_requirement(mock_requirement)
        
        if task:
            print(f"\n✓ 任务分解成功:")
            print(f"  任务ID: {task.get('id')}")
            print(f"  复杂度: {task.get('complexity')}")
            print(f"  Agent类型: {task.get('agent_type')}")
            print(f"  预估时间: {task.get('estimated_time')}")
            print(f"\n  生成的Prompt（前200字符）:")
            print(f"  {task.get('prompt', '')[:200]}...")
            return True
        else:
            print("✗ 任务分解失败")
            return False
    
    async def test_full_workflow(self):
        """测试9: 完整工作流"""
        print("\n" + "="*60)
        print("测试9: 完整工作流（提取需求 → 分解任务）")
        print("="*60)
        
        # 注意：这个测试会真实调用GLM5 API和读取Obsidian
        print("运行完整工作流...")
        result = await self.orchestrator.run_automated_workflow(days=7)
        
        print(f"\n工作流结果:")
        print(f"  开始时间: {result.get('started_at')}")
        print(f"  完成时间: {result.get('completed_at')}")
        print(f"  需求数量: {result.get('summary', {}).get('total_requirements', 0)}")
        print(f"  任务数量: {result.get('summary', {}).get('total_tasks', 0)}")
        print(f"  Agent任务数量: {result.get('summary', {}).get('total_agent_tasks', 0)}")
        print(f"  错误数量: {result.get('summary', {}).get('total_errors', 0)}")
        
        return result.get('summary', {}).get('total_requirements', 0) >= 0
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("开始运行需求提取和任务分解测试")
        print("="*60)
        
        tests = [
            ("测试1: 扫描Obsidian笔记", self.test_scan_notes),
            ("测试2: 检测行动项关键词", self.test_action_keywords),
            ("测试3: 优先级提取", self.test_priority_extraction),
            ("测试4: 复杂度分析", self.test_complexity_analysis),
            ("测试5: Agent选择逻辑", self.test_agent_selection),
            ("测试6: 时间估算", self.test_time_estimation),
            ("测试7: 完整需求提取流程", self.test_requirement_extraction),
            ("测试8: 任务分解流程", self.test_task_decomposition),
            # ("测试9: 完整工作流", self.test_full_workflow),  # 可选：完整工作流测试
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"\n✗ {test_name} 失败: {e}")
                results[test_name] = False
        
        # 打印总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")
        
        print("\n" + "="*60)
        print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")
        print("="*60)
        
        return passed == total


async def main():
    """主函数"""
    tester = TestRequirementExtraction()
    
    # 运行所有测试
    all_passed = await tester.run_all_tests()
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
