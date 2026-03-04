"""
智能模型选择器 - 根据任务特征自动选择最佳模型
"""

from typing import Dict, List, Optional, Tuple
import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TaskType(Enum):
    """任务类型"""
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    ARCHITECTURE = "architecture"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    TEST = "test"
    GENERAL = "general"


# 模型配置
MODEL_CONFIGS = {
    # GLM5系列
    "glm5-plus": {
        "provider": "zhipu",
        "max_tokens": 8000,
        "cost_per_1k_tokens": 0.05,
        "strengths": ["逻辑推理", "复杂分析", "架构设计", "中文理解"],
        "best_for": ["high_complexity", "architecture", "bug_fix", "analysis"],
        "speed": "medium",
        "quality": "high",
        "languages": ["zh", "en"],
        "context_window": 32000
    },
    "glm5-turbo": {
        "provider": "zhipu",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.01,
        "strengths": ["快速迭代", "功能开发", "中文理解"],
        "best_for": ["medium_complexity", "feature", "refactor", "general"],
        "speed": "fast",
        "quality": "medium",
        "languages": ["zh", "en"],
        "context_window": 16000
    },
    "glm5-lite": {
        "provider": "zhipu",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.001,
        "strengths": ["低成本", "快速响应"],
        "best_for": ["low_complexity", "general", "translation"],
        "speed": "very_fast",
        "quality": "low",
        "languages": ["zh", "en"],
        "context_window": 8000
    },
    
    # Claude系列
    "claude-3-opus": {
        "provider": "anthropic",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.15,
        "strengths": ["创意思考", "复杂推理", "长文本理解", "安全分析"],
        "best_for": ["very_high_complexity", "architecture", "analysis", "code_review"],
        "speed": "slow",
        "quality": "very_high",
        "languages": ["en"],
        "context_window": 200000
    },
    "claude-3-sonnet": {
        "provider": "anthropic",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.03,
        "strengths": ["平衡性能", "多任务处理"],
        "best_for": ["medium_complexity", "feature", "refactor", "documentation"],
        "speed": "medium",
        "quality": "high",
        "languages": ["en"],
        "context_window": 200000
    },
    "claude-3-haiku": {
        "provider": "anthropic",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.0025,
        "strengths": ["快速响应", "简单任务"],
        "best_for": ["low_complexity", "general", "translation"],
        "speed": "very_fast",
        "quality": "medium",
        "languages": ["en"],
        "context_window": 200000
    },
    
    # GPT系列
    "gpt-4-turbo": {
        "provider": "openai",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.01,
        "strengths": ["快速响应", "多语言支持", "代码生成"],
        "best_for": ["medium_complexity", "feature", "translation", "general"],
        "speed": "fast",
        "quality": "high",
        "languages": ["zh", "en", "multi"],
        "context_window": 128000
    },
    "gpt-4": {
        "provider": "openai",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.03,
        "strengths": ["深度推理", "复杂分析"],
        "best_for": ["high_complexity", "architecture", "analysis"],
        "speed": "medium",
        "quality": "very_high",
        "languages": ["zh", "en", "multi"],
        "context_window": 8192
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.0015,
        "strengths": ["低成本", "快速响应"],
        "best_for": ["low_complexity", "general", "simple_tasks"],
        "speed": "very_fast",
        "quality": "medium",
        "languages": ["zh", "en", "multi"],
        "context_window": 16385
    },
    
    # DeepSeek系列
    "deepseek-chat": {
        "provider": "deepseek",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.001,
        "strengths": ["中文理解", "低成本", "快速响应"],
        "best_for": ["medium_complexity", "feature", "general", "refactor"],
        "speed": "fast",
        "quality": "medium",
        "languages": ["zh", "en"],
        "context_window": 32000
    },
    "deepseek-coder": {
        "provider": "deepseek",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.001,
        "strengths": ["代码生成", "代码理解", "调试"],
        "best_for": ["medium_complexity", "feature", "bug_fix", "code_review"],
        "speed": "fast",
        "quality": "high",
        "languages": ["zh", "en"],
        "context_window": 16000
    },
    
    # 通义千问系列
    "qwen-max": {
        "provider": "alibaba",
        "max_tokens": 6000,
        "cost_per_1k_tokens": 0.12,
        "strengths": ["中文理解", "长文本", "复杂推理"],
        "best_for": ["high_complexity", "analysis", "architecture"],
        "speed": "medium",
        "quality": "high",
        "languages": ["zh", "en"],
        "context_window": 32000
    },
    "qwen-plus": {
        "provider": "alibaba",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.004,
        "strengths": ["中文理解", "平衡性能"],
        "best_for": ["medium_complexity", "feature", "general"],
        "speed": "fast",
        "quality": "medium",
        "languages": ["zh", "en"],
        "context_window": 32000
    },
    "qwen-turbo": {
        "provider": "alibaba",
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.002,
        "strengths": ["快速响应", "低成本"],
        "best_for": ["low_complexity", "general", "translation"],
        "speed": "very_fast",
        "quality": "low",
        "languages": ["zh", "en"],
        "context_window": 8192
    }
}


@dataclass
class TaskFeatures:
    """任务特征"""
    complexity: TaskComplexity
    type: TaskType
    language: str
    estimated_tokens: int
    requires_creativity: bool
    requires_speed: bool
    requires_chinese: bool
    requires_code: bool
    priority: str
    description: str


class ModelSelector:
    """智能模型选择器"""
    
    def __init__(self, model_adapter):
        self.adapter = model_adapter
        self.available_models = model_adapter.get_available_models()
        logger.info(f"ModelSelector初始化，可用模型: {self.available_models}")
    
    async def select_best_model(
        self,
        task: Dict,
        constraints: Dict = None
    ) -> str:
        """选择最佳模型
        
        Args:
            task: 任务描述
            constraints: 约束条件
        
        Returns:
            最佳模型名称
        """
        # 1. 分析任务特征
        features = self.analyze_task(task)
        logger.info(f"任务特征: {features}")
        
        # 2. 应用约束过滤
        candidates = self.apply_constraints(features, constraints)
        logger.info(f"候选模型: {candidates}")
        
        # 3. 如果没有候选模型
        if not candidates:
            logger.warning("没有满足约束的模型，使用默认模型")
            return self.adapter.get_preferred_model() or "glm5-turbo"
        
        # 4. 如果只有1个候选，直接返回
        if len(candidates) == 1:
            logger.info(f"唯一候选模型: {candidates[0]}")
            return candidates[0]
        
        # 5. 计算得分并排序
        scores = {}
        for model in candidates:
            scores[model] = self.calculate_score(model, features, constraints)
            logger.debug(f"模型 {model} 得分: {scores[model]}")
        
        # 6. 返回得分最高的模型
        best_model = max(scores, key=scores.get)
        logger.info(f"选择最佳模型: {best_model} (得分: {scores[best_model]})")
        
        return best_model
    
    def analyze_task(self, task: Dict) -> TaskFeatures:
        """分析任务特征"""
        description = task.get("description", "")
        context = task.get("context", "")
        
        # 分析复杂度
        complexity = self.analyze_complexity(task)
        
        # 分析类型
        task_type = self.analyze_type(task)
        
        # 分析语言
        language = self.detect_language(description + context)
        
        # 估算token数
        estimated_tokens = self.estimate_tokens(task)
        
        # 是否需要创意
        requires_creativity = self.needs_creativity(task)
        
        # 是否需要速度
        requires_speed = self.needs_speed(task)
        
        # 是否需要中文支持
        requires_chinese = language == "zh" or self.has_chinese(description)
        
        # 是否涉及代码
        requires_code = self.involves_code(task)
        
        return TaskFeatures(
            complexity=complexity,
            type=task_type,
            language=language,
            estimated_tokens=estimated_tokens,
            requires_creativity=requires_creativity,
            requires_speed=requires_speed,
            requires_chinese=requires_chinese,
            requires_code=requires_code,
            priority=task.get("priority", "medium"),
            description=description
        )
    
    def analyze_complexity(self, task: Dict) -> TaskComplexity:
        """分析任务复杂度"""
        # 1. 直接指定
        if "complexity" in task:
            complexity_map = {
                "low": TaskComplexity.LOW,
                "medium": TaskComplexity.MEDIUM,
                "high": TaskComplexity.HIGH,
                "very_high": TaskComplexity.VERY_HIGH
            }
            return complexity_map.get(task["complexity"].lower(), TaskComplexity.MEDIUM)
        
        # 2. 根据类型推断
        task_type = task.get("type", "").lower()
        if task_type in ["architecture", "analysis", "design"]:
            return TaskComplexity.HIGH
        
        # 3. 根据描述关键词推断
        description = task.get("description", "").lower()
        
        high_keywords = ["架构", "设计", "重构", "优化", "复杂", "architecture", "refactor", "optimize"]
        medium_keywords = ["功能", "实现", "开发", "feature", "implement", "develop"]
        low_keywords = ["简单", "快速", "修复", "simple", "quick", "fix"]
        
        if any(kw in description for kw in high_keywords):
            return TaskComplexity.HIGH
        elif any(kw in description for kw in low_keywords):
            return TaskComplexity.LOW
        else:
            return TaskComplexity.MEDIUM
    
    def analyze_type(self, task: Dict) -> TaskType:
        """分析任务类型"""
        task_type = task.get("type", "").lower()
        
        type_map = {
            "feature": TaskType.FEATURE,
            "bug_fix": TaskType.BUG_FIX,
            "bug": TaskType.BUG_FIX,
            "refactor": TaskType.REFACTOR,
            "architecture": TaskType.ARCHITECTURE,
            "design": TaskType.ARCHITECTURE,
            "analysis": TaskType.ANALYSIS,
            "translate": TaskType.TRANSLATION,
            "translation": TaskType.TRANSLATION,
            "doc": TaskType.DOCUMENTATION,
            "documentation": TaskType.DOCUMENTATION,
            "review": TaskType.CODE_REVIEW,
            "test": TaskType.TEST,
            "general": TaskType.GENERAL
        }
        
        if task_type in type_map:
            return type_map[task_type]
        
        # 根据描述推断
        description = task.get("description", "").lower()
        
        if "bug" in description or "修复" in description:
            return TaskType.BUG_FIX
        elif "架构" in description or "设计" in description:
            return TaskType.ARCHITECTURE
        elif "重构" in description or "refactor" in description:
            return TaskType.REFACTOR
        elif "文档" in description or "document" in description:
            return TaskType.DOCUMENTATION
        elif "测试" in description or "test" in description:
            return TaskType.TEST
        elif "分析" in description or "analysis" in description:
            return TaskType.ANALYSIS
        else:
            return TaskType.GENERAL
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        if not text:
            return "en"
        
        # 简单的中英文检测
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        
        if chinese_chars > len(text) * 0.3:
            return "zh"
        else:
            return "en"
    
    def has_chinese(self, text: str) -> bool:
        """是否包含中文"""
        return any('\u4e00' <= c <= '\u9fff' for c in text)
    
    def estimate_tokens(self, task: Dict) -> int:
        """估算token数"""
        description = task.get("description", "")
        context = task.get("context", "")
        code = task.get("code", "")
        
        # 混合文本估算
        total_text = description + context + code
        
        # 中文：约1.5字符/token，英文：约4字符/token
        chinese_chars = sum(1 for c in total_text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(total_text) - chinese_chars
        
        tokens = int(chinese_chars / 1.5) + int(english_chars / 4)
        
        # 添加安全边际（20%）
        return int(tokens * 1.2)
    
    def needs_creativity(self, task: Dict) -> bool:
        """是否需要创意"""
        creative_keywords = [
            "设计", "创意", "优化", "改进", "创新",
            "design", "creative", "optimize", "improve", "innovate"
        ]
        description = task.get("description", "").lower()
        
        return any(kw in description for kw in creative_keywords)
    
    def needs_speed(self, task: Dict) -> bool:
        """是否需要速度"""
        priority = task.get("priority", "medium")
        
        if priority == "high":
            return True
        
        description = task.get("description", "").lower()
        speed_keywords = ["快速", "紧急", "立即", "quick", "urgent", "immediately"]
        
        return any(kw in description for kw in speed_keywords)
    
    def involves_code(self, task: Dict) -> bool:
        """是否涉及代码"""
        description = task.get("description", "").lower()
        context = task.get("context", "").lower()
        
        code_keywords = [
            "代码", "函数", "类", "模块", "api", "bug", "功能",
            "code", "function", "class", "module", "bug", "feature"
        ]
        
        return any(kw in description or kw in context for kw in code_keywords)
    
    def apply_constraints(
        self,
        features: TaskFeatures,
        constraints: Dict
    ) -> List[str]:
        """应用约束条件"""
        candidates = self.available_models.copy()
        
        if not constraints:
            return candidates
        
        # 成本约束
        if constraints.get("max_cost"):
            max_cost = constraints["max_cost"]
            candidates = [
                m for m in candidates
                if MODEL_CONFIGS.get(m, {}).get("cost_per_1k_tokens", 999) <= max_cost
            ]
        
        # 速度约束
        if constraints.get("requires_fast") or features.requires_speed:
            candidates = [
                m for m in candidates
                if MODEL_CONFIGS.get(m, {}).get("speed") in ["fast", "very_fast"]
            ]
        
        # 质量约束
        if constraints.get("requires_high_quality"):
            candidates = [
                m for m in candidates
                if MODEL_CONFIGS.get(m, {}).get("quality") in ["high", "very_high"]
            ]
        
        # 语言约束
        if features.requires_chinese:
            candidates = [
                m for m in candidates
                if "zh" in MODEL_CONFIGS.get(m, {}).get("languages", [])
            ]
        
        # 上下文窗口约束
        if features.estimated_tokens > 0:
            min_context = features.estimated_tokens * 2  # 至少2倍空间
            candidates = [
                m for m in candidates
                if MODEL_CONFIGS.get(m, {}).get("context_window", 0) >= min_context
            ]
        
        # 排除特定模型
        if constraints.get("exclude_models"):
            candidates = [
                m for m in candidates
                if m not in constraints["exclude_models"]
            ]
        
        # 只使用特定模型
        if constraints.get("include_models"):
            candidates = [
                m for m in candidates
                if m in constraints["include_models"]
            ]
        
        return candidates
    
    def calculate_score(
        self,
        model: str,
        features: TaskFeatures,
        constraints: Dict
    ) -> float:
        """计算模型得分"""
        config = MODEL_CONFIGS.get(model, {})
        
        if not config:
            return 0.0
        
        score = 0.0
        
        # 1. 复杂度匹配 (35%)
        complexity_score = self._score_complexity(features.complexity, config.get("quality", "medium"))
        score += complexity_score * 35
        
        # 2. 任务类型匹配 (25%)
        type_score = self._score_task_type(features.type, config.get("best_for", []))
        score += type_score * 25
        
        # 3. 速度需求 (20%)
        speed_score = self._score_speed(features.requires_speed, config.get("speed", "medium"))
        score += speed_score * 20
        
        # 4. 成本优化 (15%)
        cost_score = self._score_cost(config.get("cost_per_1k_tokens", 999))
        score += cost_score * 15
        
        # 5. 语言支持 (5%)
        language_score = self._score_language(features.requires_chinese, config.get("languages", []))
        score += language_score * 5
        
        return score
    
    def _score_complexity(self, complexity: TaskComplexity, quality: str) -> float:
        """复杂度匹配得分"""
        quality_scores = {
            "very_high": {"low": 0.3, "medium": 0.7, "high": 0.9, "very_high": 1.0},
            "high": {"low": 0.5, "medium": 0.8, "high": 1.0, "very_high": 0.9},
            "medium": {"low": 0.8, "medium": 1.0, "high": 0.7, "very_high": 0.5},
            "low": {"low": 1.0, "medium": 0.8, "high": 0.5, "very_high": 0.3}
        }
        
        return quality_scores.get(quality, {}).get(complexity.value, 0.5)
    
    def _score_task_type(self, task_type: TaskType, best_for: List[str]) -> float:
        """任务类型匹配得分"""
        type_mapping = {
            TaskType.FEATURE: "feature",
            TaskType.BUG_FIX: "bug_fix",
            TaskType.REFACTOR: "refactor",
            TaskType.ARCHITECTURE: "architecture",
            TaskType.ANALYSIS: "analysis",
            TaskType.TRANSLATION: "translation",
            TaskType.DOCUMENTATION: "documentation",
            TaskType.CODE_REVIEW: "code_review",
            TaskType.TEST: "test",
            TaskType.GENERAL: "general"
        }
        
        type_str = type_mapping.get(task_type, "general")
        
        # 完全匹配
        if type_str in best_for:
            return 1.0
        
        # 部分匹配
        complexity_map = {
            TaskType.ARCHITECTURE: "high_complexity",
            TaskType.ANALYSIS: ["high_complexity", "medium_complexity"],
            TaskType.BUG_FIX: ["high_complexity", "medium_complexity"],
            TaskType.FEATURE: "medium_complexity",
            TaskType.REFACTOR: "medium_complexity",
            TaskType.GENERAL: ["low_complexity", "medium_complexity"],
            TaskType.TRANSLATION: "low_complexity"
        }
        
        expected_complexity = complexity_map.get(task_type)
        if isinstance(expected_complexity, list):
            if any(ec in best_for for ec in expected_complexity):
                return 0.7
        elif expected_complexity and expected_complexity in best_for:
            return 0.7
        
        return 0.3
    
    def _score_speed(self, requires_speed: bool, speed: str) -> float:
        """速度需求得分"""
        if not requires_speed:
            return 0.7  # 不需要速度时，所有模型都可以
        
        speed_scores = {
            "very_fast": 1.0,
            "fast": 0.9,
            "medium": 0.5,
            "slow": 0.2
        }
        
        return speed_scores.get(speed, 0.5)
    
    def _score_cost(self, cost_per_1k: float) -> float:
        """成本优化得分"""
        if cost_per_1k < 0.002:
            return 1.0
        elif cost_per_1k < 0.01:
            return 0.9
        elif cost_per_1k < 0.05:
            return 0.7
        elif cost_per_1k < 0.1:
            return 0.5
        else:
            return 0.3
    
    def _score_language(self, requires_chinese: bool, languages: List[str]) -> float:
        """语言支持得分"""
        if not requires_chinese:
            return 0.8  # 不需要中文时，所有模型都可以
        
        if "zh" in languages:
            return 1.0
        else:
            return 0.3
    
    async def get_model_recommendations(
        self,
        task: Dict,
        top_n: int = 3
    ) -> List[Tuple[str, float, str]]:
        """获取模型推荐列表
        
        Returns:
            [(model_name, score, reason), ...]
        """
        features = self.analyze_task(task)
        candidates = self.apply_constraints(features, None)
        
        if not candidates:
            return []
        
        # 计算所有候选模型的得分
        scores = []
        for model in candidates:
            score = self.calculate_score(model, features, None)
            reason = self._get_reason(model, features)
            scores.append((model, score, reason))
        
        # 排序并返回top_n
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_n]
    
    def _get_reason(self, model: str, features: TaskFeatures) -> str:
        """获取选择理由"""
        config = MODEL_CONFIGS.get(model, {})
        reasons = []
        
        # 质量匹配
        quality = config.get("quality", "medium")
        if features.complexity == TaskComplexity.HIGH and quality in ["high", "very_high"]:
            reasons.append(f"高质量模型适合复杂任务")
        
        # 速度匹配
        speed = config.get("speed", "medium")
        if features.requires_speed and speed in ["fast", "very_fast"]:
            reasons.append(f"快速响应")
        
        # 成本优势
        cost = config.get("cost_per_1k_tokens", 999)
        if cost < 0.01:
            reasons.append(f"成本低(${cost}/1k tokens)")
        
        # 语言支持
        if features.requires_chinese and "zh" in config.get("languages", []):
            reasons.append(f"优秀的中文支持")
        
        # 专长匹配
        strengths = config.get("strengths", [])
        if strengths:
            reasons.append(f"擅长: {', '.join(strengths[:2])}")
        
        return "; ".join(reasons) if reasons else "综合性能平衡"


if __name__ == "__main__":
    # 测试代码
    import asyncio
    from model_adapter import ModelAdapter
    
    async def test():
        adapter = ModelAdapter()
        selector = ModelSelector(adapter)
        
        # 测试1：高复杂度任务
        task1 = {
            "description": "设计一个微服务架构，包括用户认证、订单处理和支付系统",
            "type": "architecture",
            "complexity": "high"
        }
        
        print("任务1:", task1["description"])
        model1 = await selector.select_best_model(task1)
        print(f"推荐模型: {model1}\n")
        
        # 测试2：快速任务
        task2 = {
            "description": "快速修复登录页面的样式问题",
            "priority": "high"
        }
        
        print("任务2:", task2["description"])
        model2 = await selector.select_best_model(task2)
        print(f"推荐模型: {model2}\n")
        
        # 测试3：中文任务
        task3 = {
            "description": "编写一份中文技术文档",
            "type": "documentation"
        }
        
        print("任务3:", task3["description"])
        model3 = await selector.select_best_model(task3)
        print(f"推荐模型: {model3}\n")
        
        # 测试4：获取推荐列表
        print("任务1的推荐列表:")
        recommendations = await selector.get_model_recommendations(task1, top_n=3)
        for i, (model, score, reason) in enumerate(recommendations, 1):
            print(f"{i}. {model} (得分: {score:.2f}) - {reason}")
    
    asyncio.run(test())
