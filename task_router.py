"""
任务路由器 - 根据任务描述自动选择Agent模式和模型

功能：
1. 任务类型识别（开发/规划/调试/测试/审查）
2. 复杂度评估（high/medium/low）
3. Agent模式选择（build/plan/explore/debug/test/review）
4. 模型选择（free/fast/premium）
5. 斜杠命令解析
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    DEVELOPMENT = "development"  # 开发任务
    PLANNING = "planning"  # 规划任务
    EXPLORATION = "exploration"  # 探索任务
    DEBUGGING = "debugging"  # 调试任务
    TESTING = "testing"  # 测试任务
    REVIEW = "review"  # 代码审查


class Complexity(Enum):
    """任务复杂度"""
    HIGH = "high"  # 高复杂度
    MEDIUM = "medium"  # 中等复杂度
    LOW = "low"  # 低复杂度


class AgentMode(Enum):
    """Agent模式"""
    BUILD = "build"  # 代码生成和开发
    PLAN = "plan"  # 项目规划和架构
    EXPLORE = "explore"  # 代码探索和分析
    DEBUG = "debug"  # 调试和问题修复
    TEST = "test"  # 测试生成
    REVIEW = "review"  # 代码审查


# 统一使用GLM-5模型（从nanobot配置文件）
# GLM-5配置：
# - 模型：zhipu/glm-5
# - API：https://open.bigmodel.cn/api/coding/paas/v4
# - 最大Token：8192
DEFAULT_MODEL = "glm-5"  # 统一使用GLM-5


@dataclass
class TaskInfo:
    """任务信息"""
    task_type: TaskType
    complexity: Complexity
    agent_mode: AgentMode
    model: str = DEFAULT_MODEL  # 统一使用GLM-5
    estimated_time: int = 60  # 预估时间（秒）
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class TaskRouter:
    """任务路由器"""

    def __init__(self):
        # 任务类型关键词
        self.task_keywords = {
            TaskType.DEVELOPMENT: [
                "实现", "开发", "创建", "编写", "添加", "增加", "构建",
                "implement", "develop", "create", "build", "add"
            ],
            TaskType.PLANNING: [
                "规划", "设计", "架构", "方案", "分析", "设计文档",
                "plan", "design", "architecture", "scheme", "analyze"
            ],
            TaskType.EXPLORATION: [
                "探索", "理解", "阅读", "分析代码", "查看", "查找",
                "explore", "understand", "read", "analyze", "search"
            ],
            TaskType.DEBUGGING: [
                "修复", "调试", "bug", "错误", "问题", "异常", "解决",
                "fix", "debug", "bug", "error", "issue", "exception", "solve"
            ],
            TaskType.TESTING: [
                "测试", "单元测试", "集成测试", "测试用例", "覆盖率",
                "test", "unit test", "integration test", "coverage"
            ],
            TaskType.REVIEW: [
                "审查", "检查", "review", "代码审查", "优化", "重构",
                "review", "check", "optimize", "refactor"
            ],
        }

        # 复杂度指示词
        self.complexity_indicators = {
            Complexity.HIGH: [
                "重构", "架构", "多文件", "复杂", "系统", "完整",
                "refactor", "architecture", "multi-file", "complex", "system", "complete"
            ],
            Complexity.LOW: [
                "简单", "修复", "文档", "注释", "小", "快速",
                "simple", "fix", "doc", "comment", "small", "quick"
            ],
        }

        # Agent模式映射
        self.agent_mode_mapping = {
            TaskType.DEVELOPMENT: AgentMode.BUILD,
            TaskType.PLANNING: AgentMode.PLAN,
            TaskType.EXPLORATION: AgentMode.EXPLORE,
            TaskType.DEBUGGING: AgentMode.DEBUG,
            TaskType.TESTING: AgentMode.TEST,
            TaskType.REVIEW: AgentMode.REVIEW,
        }

        # 统一使用GLM-5模型
        # 不再根据复杂度选择不同模型
        self.default_model = DEFAULT_MODEL

        # 斜杠命令映射
        self.slash_commands = {
            "/opencode-gen": AgentMode.BUILD,
            "/opencode-plan": AgentMode.PLAN,
            "/opencode-explore": AgentMode.EXPLORE,
            "/opencode-debug": AgentMode.DEBUG,
            "/opencode-test": AgentMode.TEST,
            "/opencode-review": AgentMode.REVIEW,
        }

    def analyze(self, task_description: str) -> TaskInfo:
        """
        分析任务描述，返回任务信息

        Args:
            task_description: 任务描述

        Returns:
            TaskInfo对象
        """
        # 1. 检查斜杠命令
        agent_mode = self._parse_slash_command(task_description)

        # 2. 识别任务类型
        task_type, keywords = self._identify_task_type(task_description)

        # 3. 评估复杂度
        complexity = self._assess_complexity(task_description)

        # 4. 选择Agent模式
        if agent_mode:
            # 如果有斜杠命令，使用命令指定的模式
            final_agent_mode = agent_mode
        else:
            # 否则根据任务类型选择
            final_agent_mode = self.agent_mode_mapping[task_type]

        # 5. 选择模型（统一使用GLM-5）
        model = self.default_model

        # 6. 估算时间
        estimated_time = self._estimate_time(complexity)

        return TaskInfo(
            task_type=task_type,
            complexity=complexity,
            agent_mode=final_agent_mode,
            model=model,
            estimated_time=estimated_time,
            keywords=keywords,
        )

    def _parse_slash_command(self, text: str) -> AgentMode:
        """解析斜杠命令"""
        for command, mode in self.slash_commands.items():
            if command in text:
                return mode
        return None

    def _identify_task_type(self, text: str) -> Tuple[TaskType, List[str]]:
        """识别任务类型"""
        text_lower = text.lower()
        scores = {}
        matched_keywords = []

        for task_type, keywords in self.task_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 1
                    matched_keywords.append(keyword)
            scores[task_type] = score

        # 选择得分最高的任务类型
        if max(scores.values()) == 0:
            # 如果没有匹配，默认为开发任务
            return TaskType.DEVELOPMENT, []

        best_type = max(scores, key=scores.get)
        return best_type, matched_keywords

    def _assess_complexity(self, text: str) -> Complexity:
        """评估任务复杂度"""
        text_lower = text.lower()

        # 检查高复杂度指示词
        high_score = sum(1 for keyword in self.complexity_indicators[Complexity.HIGH]
                        if keyword.lower() in text_lower)

        # 检查低复杂度指示词
        low_score = sum(1 for keyword in self.complexity_indicators[Complexity.LOW]
                       if keyword.lower() in text_lower)

        # 根据得分判断复杂度
        if high_score > low_score:
            return Complexity.HIGH
        elif low_score > high_score:
            return Complexity.LOW
        else:
            # 根据文本长度判断
            if len(text) > 200:
                return Complexity.HIGH
            elif len(text) < 50:
                return Complexity.LOW
            else:
                return Complexity.MEDIUM

    def _estimate_time(self, complexity: Complexity) -> int:
        """估算执行时间（秒）"""
        time_estimates = {
            Complexity.HIGH: 120,  # 2分钟
            Complexity.MEDIUM: 60,  # 1分钟
            Complexity.LOW: 30,  # 30秒
        }
        return time_estimates[complexity]

    def get_agent_mode_description(self, mode: AgentMode) -> str:
        """获取Agent模式描述"""
        descriptions = {
            AgentMode.BUILD: "代码生成和开发 - 适合实现新功能、创建文件",
            AgentMode.PLAN: "项目规划和架构 - 适合设计系统、制定方案",
            AgentMode.EXPLORE: "代码探索和分析 - 适合理解代码库、查找信息",
            AgentMode.DEBUG: "调试和问题修复 - 适合修复bug、解决错误",
            AgentMode.TEST: "测试生成 - 适合创建测试用例、提高覆盖率",
            AgentMode.REVIEW: "代码审查 - 适合代码优化、质量检查",
        }
        return descriptions.get(mode, "未知模式")

    def get_model_description(self, model: str) -> str:
        """获取模型描述"""
        if model == DEFAULT_MODEL:
            return "zhipu/glm-5 - 智谱AI GLM-5模型（nanobot配置）"
        else:
            return f"{model} - 自定义模型"


# 全局实例
router = TaskRouter()


# 便捷函数
def analyze_task(task_description: str) -> Dict:
    """
    分析任务并返回字典格式

    Args:
        task_description: 任务描述

    Returns:
        {
            "task_type": "development",
            "complexity": "medium",
            "agent_mode": "build",
            "model": "free",
            "estimated_time": 60,
            "keywords": ["实现", "创建"]
        }
    """
    task_info = router.analyze(task_description)

    return {
        "task_type": task_info.task_type.value,
        "complexity": task_info.complexity.value,
        "agent_mode": task_info.agent_mode.value,
        "model": task_info.model,  # 已经是字符串，不需要.value
        "estimated_time": task_info.estimated_time,
        "keywords": task_info.keywords,
        "agent_description": router.get_agent_mode_description(task_info.agent_mode),
        "model_description": router.get_model_description(task_info.model),
    }


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "实现一个简单的TODO列表API",
        "修复登录页面的bug",
        "重构用户认证系统架构",
        "为订单模块编写单元测试",
        "分析现有代码库的性能瓶颈",
        "/opencode-plan 设计支付系统",
    ]

    print("=" * 60)
    print("任务路由器测试")
    print("=" * 60)

    for task in test_cases:
        print(f"\n任务: {task}")
        result = analyze_task(task)
        print(f"  类型: {result['task_type']}")
        print(f"  复杂度: {result['complexity']}")
        print(f"  Agent模式: {result['agent_mode']} - {result['agent_description']}")
        print(f"  模型: {result['model']} - {result['model_description']}")
        print(f"  预估时间: {result['estimated_time']}秒")
        print(f"  关键词: {result['keywords']}")
