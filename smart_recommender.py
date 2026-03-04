"""
智能推荐器 - Smart Recommender

基于代码知识图谱和最佳实践库，为开发任务提供智能推荐。

Author: Nanobot Agent System
Phase: 4 - Knowledge Base Enhancement
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """任务上下文"""

    description: str
    language: str = "python"
    framework: Optional[str] = None
    category: Optional[str] = None
    requirements: List[str] = None
    constraints: List[str] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.constraints is None:
            self.constraints = []


@dataclass
class Recommendation:
    """推荐结果"""

    type: str  # practice, code, pattern, suggestion
    title: str
    description: str
    relevance: float  # 0-1
    source: str
    details: Dict[str, Any] = None
    code_example: Optional[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SmartRecommender:
    """智能推荐器"""

    # 任务类型关键词映射
    TASK_KEYWORDS = {
        "testing": ["test", "testing", "unit test", "integration", "mock", "assert"],
        "security": ["security", "auth", "authentication", "authorization", "encrypt", "hash", "password"],
        "performance": ["performance", "optimize", "speed", "fast", "cache", "async", "concurrent"],
        "database": ["database", "sql", "query", "orm", "migration", "model"],
        "api": ["api", "rest", "endpoint", "http", "request", "response", "json"],
        "error_handling": ["error", "exception", "try", "catch", "handle", "raise"],
        "logging": ["log", "logging", "debug", "trace", "monitor"],
        "refactoring": ["refactor", "clean", "improve", "restructure", "optimize"],
        "documentation": ["document", "docstring", "readme", "comment", "explain"],
        "design": ["design", "pattern", "architecture", "structure", "class", "interface"],
    }

    # 技术栈映射
    TECH_STACK = {
        "python": ["django", "flask", "fastapi", "asyncio", "sqlalchemy", "pytest"],
        "javascript": ["react", "vue", "angular", "node", "express", "jest"],
        "database": ["postgresql", "mysql", "mongodb", "redis", "sqlite"],
        "tools": ["docker", "kubernetes", "git", "ci", "cd"],
    }

    def __init__(self, knowledge_graph, practices_library, model_adapter=None):
        """
        初始化智能推荐器

        Args:
            knowledge_graph: 代码知识图谱实例
            practices_library: 最佳实践库实例
            model_adapter: 模型适配器（可选，用于高级推荐）
        """
        self.knowledge_graph = knowledge_graph
        self.practices_library = practices_library
        self.model_adapter = model_adapter

        # 推荐历史
        self.recommendation_history: List[Dict] = []

        # 用户偏好（可学习）
        self.user_preferences: Dict[str, float] = defaultdict(float)

        logger.info("SmartRecommender initialized")

    async def recommend_for_task(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        为任务推荐最佳实践和代码

        Args:
            task: 任务描述
            context: 额外上下文

        Returns:
            推荐结果
        """
        logger.info(f"Generating recommendations for task: {task.get('description', '')[:50]}")

        start_time = datetime.now()

        # 1. 分析任务需求
        requirements = await self._analyze_task_requirements(task, context)

        # 2. 搜索相关实践
        practices = await self._search_practices(requirements)

        # 3. 查找相似代码
        similar_code = await self._find_similar_code(requirements)

        # 4. 查找设计模式
        patterns = await self._find_patterns(requirements)

        # 5. 生成建议
        suggestions = await self._generate_suggestions(task, requirements, practices)

        # 6. 个性化排序
        all_recommendations = self._merge_and_rank(
            practices=practices,
            similar_code=similar_code,
            patterns=patterns,
            suggestions=suggestions,
            requirements=requirements,
        )

        # 7. 记录推荐历史
        recommendation_result = {
            "task": task,
            "requirements": requirements,
            "recommendations": all_recommendations,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "elapsed_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "total_recommendations": len(all_recommendations),
            },
        }

        self.recommendation_history.append(recommendation_result)

        logger.info(f"Generated {len(all_recommendations)} recommendations")

        return recommendation_result

    async def _analyze_task_requirements(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """分析任务需求"""
        description = task.get("description", "")

        # 如果有模型适配器，使用LLM分析
        if self.model_adapter:
            try:
                return await self._analyze_with_llm(description, context)
            except Exception as e:
                logger.warning(f"LLM analysis failed, falling back to rule-based: {e}")

        # 基于规则的分析
        return self._analyze_with_rules(description, context)

    async def _analyze_with_llm(self, description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用LLM分析任务"""
        prompt = f"""Analyze the following development task and extract requirements:

Task: {description}

Context: {json.dumps(context) if context else 'None'}

Extract:
1. Keywords (for searching)
2. Category (e.g., "testing", "security", "performance", "api", "database")
3. Required technologies/tools
4. Design patterns needed
5. Priority level (high/medium/low)

Respond in JSON format only:
{{
  "keywords": ["keyword1", "keyword2"],
  "category": "category",
  "tags": ["tag1", "tag2"],
  "technologies": ["tech1", "tech2"],
  "patterns": ["pattern1"],
  "priority": "medium",
  "complexity": "medium",
  "estimated_time": "1 hour"
}}
"""

        result = await self.model_adapter.call_model(model="glm5-turbo", prompt=prompt, temperature=0.1, max_tokens=300)

        if result.get("success"):
            content = result["content"]
            json_match = re.search(r"\{.*\}", content, re.DOTALL)

            if json_match:
                return json.loads(json_match.group())

        # 返回默认值
        return self._analyze_with_rules(description, context)

    def _analyze_with_rules(self, description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """基于规则分析任务"""
        description_lower = description.lower()

        # 提取关键词
        keywords = re.findall(r"\b\w+\b", description_lower)
        keywords = [k for k in keywords if len(k) > 3][:10]

        # 识别类别
        category = "general"
        for cat, cat_keywords in self.TASK_KEYWORDS.items():
            if any(kw in description_lower for kw in cat_keywords):
                category = cat
                break

        # 识别技术栈
        technologies = []
        for tech, tech_list in self.TECH_STACK.items():
            for t in tech_list:
                if t in description_lower:
                    technologies.append(t)

        # 识别设计模式
        patterns = []
        pattern_keywords = {
            "singleton": ["singleton", "single instance"],
            "factory": ["factory", "create object"],
            "observer": ["observer", "event", "listener"],
            "strategy": ["strategy", "algorithm", " interchangeable"],
            "decorator": ["decorator", "wrap", "enhance"],
        }

        for pattern, p_keywords in pattern_keywords.items():
            if any(pk in description_lower for pk in p_keywords):
                patterns.append(pattern)

        # 估算复杂度
        complexity = "medium"
        if any(word in description_lower for word in ["simple", "basic", "easy"]):
            complexity = "easy"
        elif any(word in description_lower for word in ["complex", "advanced", "sophisticated"]):
            complexity = "hard"

        return {
            "keywords": keywords,
            "category": category,
            "tags": keywords[:5],
            "technologies": technologies,
            "patterns": patterns,
            "priority": "medium",
            "complexity": complexity,
            "estimated_time": "1 hour",
        }

    async def _search_practices(self, requirements: Dict[str, Any]) -> List[Recommendation]:
        """搜索相关实践"""
        recommendations = []

        # 按关键词搜索
        for keyword in requirements.get("keywords", [])[:3]:
            practices = await self.practices_library.search_practices(
                query=keyword, category=requirements.get("category"), limit=5
            )

            for practice in practices:
                recommendations.append(
                    Recommendation(
                        type="practice",
                        title=practice["title"],
                        description=practice["description"],
                        relevance=self._calculate_relevance(practice, requirements),
                        source="practices_library",
                        details={
                            "category": practice["category"],
                            "tags": practice.get("tags", []),
                            "quality_score": practice.get("quality_score", 0),
                        },
                        code_example=practice.get("code_example"),
                    )
                )

        # 去重并排序
        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations.sort(key=lambda x: x.relevance, reverse=True)

        return recommendations[:10]

    async def _find_similar_code(self, requirements: Dict[str, Any]) -> List[Recommendation]:
        """查找相似代码"""
        recommendations = []

        # 从知识图谱查询
        for keyword in requirements.get("keywords", [])[:2]:
            try:
                results = await self.knowledge_graph.query(query=keyword, limit=5)

                for result in results:
                    recommendations.append(
                        Recommendation(
                            type="code",
                            title=f"Similar: {result.get('name', 'Unknown')}",
                            description=result.get("docstring", "No description"),
                            relevance=result.get("similarity", 0.5),
                            source="knowledge_graph",
                            details={"file": result.get("file"), "line": result.get("line"), "type": result.get("type")},
                            code_example=result.get("code"),
                        )
                    )
            except Exception as e:
                logger.warning(f"Error querying knowledge graph: {e}")

        # 去重并排序
        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations.sort(key=lambda x: x.relevance, reverse=True)

        return recommendations[:5]

    async def _find_patterns(self, requirements: Dict[str, Any]) -> List[Recommendation]:
        """查找设计模式"""
        recommendations = []

        patterns_needed = requirements.get("patterns", [])

        for pattern in patterns_needed:
            # 从最佳实践库搜索
            practices = await self.practices_library.search_practices(query=pattern, category="design_patterns", limit=3)

            for practice in practices:
                recommendations.append(
                    Recommendation(
                        type="pattern",
                        title=f"Pattern: {practice['title']}",
                        description=practice["description"],
                        relevance=0.9,
                        source="practices_library",
                        details={"pattern": pattern, "category": practice["category"]},
                        code_example=practice.get("code_example"),
                    )
                )

        return recommendations[:5]

    async def _generate_suggestions(
        self, task: Dict[str, Any], requirements: Dict[str, Any], practices: List[Recommendation]
    ) -> List[Recommendation]:
        """生成建议"""
        suggestions = []
        description = task.get("description", "").lower()

        # 基于类别的建议
        category = requirements.get("category", "general")

        if category == "testing":
            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="Add Comprehensive Tests",
                    description="Consider adding unit tests, integration tests, and edge case coverage",
                    relevance=0.85,
                    source="rule_based",
                )
            )

            if "pytest" not in requirements.get("technologies", []):
                suggestions.append(
                    Recommendation(
                        type="suggestion",
                        title="Use pytest Framework",
                        description="pytest provides powerful testing features with simple syntax",
                        relevance=0.8,
                        source="rule_based",
                        code_example="def test_example():\n    assert function() == expected",
                    )
                )

        elif category == "security":
            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="Security Best Practices",
                    description="Implement input validation, use parameterized queries, and hash passwords",
                    relevance=0.9,
                    source="rule_based",
                )
            )

            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="Add Security Headers",
                    description="Configure appropriate security headers for web applications",
                    relevance=0.75,
                    source="rule_based",
                )
            )

        elif category == "performance":
            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="Performance Optimization",
                    description="Consider caching, async operations, and database query optimization",
                    relevance=0.85,
                    source="rule_based",
                )
            )

            if "async" not in description:
                suggestions.append(
                    Recommendation(
                        type="suggestion",
                        title="Use Async/Await",
                        description="For I/O-bound operations, async can significantly improve performance",
                        relevance=0.8,
                        source="rule_based",
                    )
                )

        elif category == "api":
            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="API Design Guidelines",
                    description="Follow RESTful principles, use proper HTTP methods and status codes",
                    relevance=0.85,
                    source="rule_based",
                )
            )

            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="Add API Documentation",
                    description="Document your API endpoints with OpenAPI/Swagger",
                    relevance=0.8,
                    source="rule_based",
                )
            )

        # 基于复杂度的建议
        complexity = requirements.get("complexity", "medium")

        if complexity == "hard":
            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title="Break Down Complex Tasks",
                    description="Consider decomposing into smaller, manageable components",
                    relevance=0.75,
                    source="rule_based",
                )
            )

        # 基于实践的建议
        if practices:
            top_practice = practices[0]
            suggestions.append(
                Recommendation(
                    type="suggestion",
                    title=f"Apply: {top_practice.title}",
                    description=f"Based on your task, consider applying this practice: {top_practice.description}",
                    relevance=top_practice.relevance * 0.9,
                    source="practice_based",
                    code_example=top_practice.code_example,
                )
            )

        return suggestions

    def _calculate_relevance(self, practice: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        """计算相关性分数"""
        score = 0.0

        # 类别匹配
        if practice.get("category") == requirements.get("category"):
            score += 0.4

        # 关键词匹配
        practice_text = f"{practice.get('title', '')} {practice.get('description', '')}".lower()
        keywords = requirements.get("keywords", [])

        matched_keywords = sum(1 for kw in keywords if kw in practice_text)
        score += (matched_keywords / max(len(keywords), 1)) * 0.3

        # 质量分
        score += practice.get("quality_score", 0) * 0.2

        # 用户偏好
        for tag in practice.get("tags", []):
            score += self.user_preferences.get(tag, 0) * 0.1

        return min(score, 1.0)

    def _merge_and_rank(
        self,
        practices: List[Recommendation],
        similar_code: List[Recommendation],
        patterns: List[Recommendation],
        suggestions: List[Recommendation],
        requirements: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """合并并排序推荐结果"""
        all_recommendations = []

        # 添加各类推荐
        for rec in practices[:5]:
            all_recommendations.append(self._recommendation_to_dict(rec))

        for rec in similar_code[:3]:
            all_recommendations.append(self._recommendation_to_dict(rec))

        for rec in patterns[:3]:
            all_recommendations.append(self._recommendation_to_dict(rec))

        for rec in suggestions[:5]:
            all_recommendations.append(self._recommendation_to_dict(rec))

        # 按相关性排序
        all_recommendations.sort(key=lambda x: x["relevance"], reverse=True)

        return all_recommendations

    def _recommendation_to_dict(self, rec: Recommendation) -> Dict[str, Any]:
        """将推荐对象转换为字典"""
        return {
            "type": rec.type,
            "title": rec.title,
            "description": rec.description,
            "relevance": round(rec.relevance, 2),
            "source": rec.source,
            "details": rec.details,
            "code_example": rec.code_example,
        }

    def _deduplicate_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """去重推荐"""
        seen = set()
        unique = []

        for rec in recommendations:
            key = (rec.type, rec.title)
            if key not in seen:
                seen.add(key)
                unique.append(rec)

        return unique

    async def provide_feedback(self, recommendation_id: str, rating: int, comment: str = None):
        """
        提供反馈以改进推荐

        Args:
            recommendation_id: 推荐ID
            rating: 评分 (1-5)
            comment: 评论
        """
        # 记录反馈
        feedback = {
            "recommendation_id": recommendation_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        }

        # 更新用户偏好
        if rating >= 4:
            # 正面反馈，增加相关标签的权重
            pass  # 可以根据推荐内容更新偏好

        logger.info(f"Received feedback for recommendation: {rating}/5")

    def learn_from_history(self):
        """从历史推荐中学习"""
        if not self.recommendation_history:
            return

        # 分析最近的推荐
        recent = self.recommendation_history[-10:]

        # 可以实现更复杂的学习算法
        logger.info(f"Learning from {len(recent)} recent recommendations")

    async def get_personalized_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取个性化推荐"""
        # 基于用户偏好和历史
        recommendations = []

        # 获取热门实践
        popular = await self.practices_library.get_popular_practices(limit)

        for practice in popular:
            recommendations.append(
                {
                    "type": "practice",
                    "title": practice["title"],
                    "description": practice["description"],
                    "relevance": practice.get("avg_effectiveness", 0.5),
                    "source": "popular",
                    "usage_count": practice.get("usage_count", 0),
                }
            )

        return recommendations[:limit]

    async def explain_recommendation(self, recommendation: Dict[str, Any]) -> str:
        """解释推荐原因"""
        explanation = f"推荐 '{recommendation['title']}' 的原因：\n\n"

        # 相关性
        relevance = recommendation.get("relevance", 0)
        if relevance > 0.8:
            explanation += "• 高度相关：与您的任务需求匹配度很高\n"
        elif relevance > 0.6:
            explanation += "• 中度相关：与您的任务有一定关联\n"

        # 来源
        source = recommendation.get("source")
        if source == "practices_library":
            explanation += "• 来源：最佳实践库（经过验证的实践）\n"
        elif source == "knowledge_graph":
            explanation += "• 来源：代码知识图谱（项目中已有的代码）\n"
        elif source == "rule_based":
            explanation += "• 来源：基于规则的建议\n"

        # 类型
        rec_type = recommendation.get("type")
        if rec_type == "practice":
            explanation += "• 类型：最佳实践（建议采用）\n"
        elif rec_type == "code":
            explanation += "• 类型：代码示例（可参考）\n"
        elif rec_type == "pattern":
            explanation += "• 类型：设计模式（架构建议）\n"
        elif rec_type == "suggestion":
            explanation += "• 类型：建议（考虑采用）\n"

        return explanation

    def get_recommendation_stats(self) -> Dict[str, Any]:
        """获取推荐统计"""
        if not self.recommendation_history:
            return {"total_recommendations": 0, "avg_recommendations_per_task": 0}

        total = sum(len(rec.get("recommendations", [])) for rec in self.recommendation_history)

        return {
            "total_tasks": len(self.recommendation_history),
            "total_recommendations": total,
            "avg_recommendations_per_task": total / len(self.recommendation_history),
            "recent_tasks": len([r for r in self.recommendation_history[-5:]]),
        }


# 便捷函数
async def get_smart_recommendations(
    task_description: str, knowledge_graph, practices_library, model_adapter=None
) -> Dict[str, Any]:
    """
    获取智能推荐的便捷函数

    Args:
        task_description: 任务描述
        knowledge_graph: 知识图谱
        practices_library: 实践库
        model_adapter: 模型适配器

    Returns:
        推荐结果
    """
    recommender = SmartRecommender(knowledge_graph, practices_library, model_adapter)

    task = {"description": task_description}

    return await recommender.recommend_for_task(task)


if __name__ == "__main__":
    import asyncio

    async def main():
        # 示例用法（需要实际的knowledge_graph和practices_library实例）
        print("SmartRecommender example")

        # 创建推荐器
        # recommender = SmartRecommender(kg, pl, model)

        # 获取推荐
        # task = {"description": "Add authentication to my API"}
        # result = await recommender.recommend_for_task(task)
        # print(f"Recommendations: {result}")

    asyncio.run(main())
