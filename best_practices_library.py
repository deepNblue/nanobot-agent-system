"""
最佳实践库 - Best Practices Library

管理和检索编程最佳实践，支持分类、搜索、评分和使用追踪。

Author: Nanobot Agent System
Phase: 4 - Knowledge Base Enhancement
"""

import os
import sqlite3
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Practice:
    """最佳实践数据结构"""
    id: Optional[int]
    title: str
    category: str
    description: str
    code_example: Optional[str] = None
    tags: List[str] = None
    quality_score: float = 0.0
    source: Optional[str] = None
    author: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard
    language: str = "python"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


@dataclass
class PracticeUsage:
    """实践使用记录"""
    id: Optional[int]
    practice_id: int
    used_in_project: str
    used_at: str
    effectiveness_score: float
    notes: Optional[str] = None
    context: Optional[str] = None


class BestPracticesLibrary:
    """最佳实践库"""
    
    # 预定义分类
    CATEGORIES = [
        "design_patterns",
        "code_quality",
        "testing",
        "security",
        "performance",
        "documentation",
        "error_handling",
        "concurrency",
        "database",
        "api_design",
        "logging",
        "configuration",
        "deployment",
        "refactoring",
        "general"
    ]
    
    # 预定义标签
    COMMON_TAGS = [
        "python", "async", "testing", "security", "performance",
        "clean-code", "solid", "dry", "kiss", "yagni",
        "type-hints", "documentation", "error-handling",
        "logging", "caching", "database", "api", "rest",
        "microservices", "docker", "ci-cd", "refactoring"
    ]
    
    def __init__(self, db_path: str = "./knowledge/practices.db"):
        """
        初始化最佳实践库
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置数据库
        self.setup_database()
        
        # 缓存
        self._category_cache: Dict[str, List[Dict]] = {}
        self._tag_cache: Dict[str, List[Dict]] = {}
        
        logger.info(f"BestPracticesLibrary initialized at {db_path}")
    
    def setup_database(self):
        """设置数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 实践表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                code_example TEXT,
                tags TEXT,
                quality_score REAL DEFAULT 0.0,
                source TEXT,
                author TEXT,
                difficulty TEXT DEFAULT 'medium',
                language TEXT DEFAULT 'python',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 使用记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_id INTEGER NOT NULL,
                used_in_project TEXT NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                effectiveness_score REAL,
                notes TEXT,
                context TEXT,
                FOREIGN KEY (practice_id) REFERENCES practices(id) ON DELETE CASCADE
            )
        """)
        
        # 反馈表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_id INTEGER NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (practice_id) REFERENCES practices(id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practices_category 
            ON practices(category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practices_quality 
            ON practices(quality_score DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_practice 
            ON practice_usage(practice_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_project 
            ON practice_usage(used_in_project)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database setup completed")
    
    async def add_practice(self, practice: Dict[str, Any]) -> int:
        """
        添加最佳实践
        
        Args:
            practice: 实践数据
            
        Returns:
            实践ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO practices 
                (title, category, description, code_example, tags, quality_score, 
                 source, author, difficulty, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                practice["title"],
                practice["category"],
                practice.get("description", ""),
                practice.get("code_example", ""),
                json.dumps(practice.get("tags", [])),
                practice.get("quality_score", 0.0),
                practice.get("source"),
                practice.get("author"),
                practice.get("difficulty", "medium"),
                practice.get("language", "python")
            ))
            
            practice_id = cursor.lastrowid
            conn.commit()
            
            # 清除缓存
            self._clear_cache()
            
            logger.info(f"Added practice: {practice['title']} (ID: {practice_id})")
            
            return practice_id
            
        except Exception as e:
            logger.error(f"Error adding practice: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    async def add_practices_batch(self, practices: List[Dict[str, Any]]) -> List[int]:
        """
        批量添加最佳实践
        
        Args:
            practices: 实践列表
            
        Returns:
            实践ID列表
        """
        practice_ids = []
        
        for practice in practices:
            practice_id = await self.add_practice(practice)
            practice_ids.append(practice_id)
        
        return practice_ids
    
    async def get_practice(self, practice_id: int) -> Optional[Dict[str, Any]]:
        """
        获取单个实践
        
        Args:
            practice_id: 实践ID
            
        Returns:
            实践数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM practices WHERE id = ?
            """, (practice_id,))
            
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            
            return None
            
        finally:
            conn.close()
    
    async def update_practice(
        self,
        practice_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新实践
        
        Args:
            practice_id: 实践ID
            updates: 更新数据
            
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建更新语句
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in ["title", "category", "description", "code_example", 
                          "quality_score", "source", "author", "difficulty", "language"]:
                    if key == "tags":
                        value = json.dumps(value)
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            # 添加更新时间
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            params.append(practice_id)
            
            sql = f"UPDATE practices SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, params)
            
            conn.commit()
            
            # 清除缓存
            self._clear_cache()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error updating practice: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def delete_practice(self, practice_id: int) -> bool:
        """
        删除实践
        
        Args:
            practice_id: 实践ID
            
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM practices WHERE id = ?", (practice_id,))
            conn.commit()
            
            # 清除缓存
            self._clear_cache()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting practice: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def search_practices(
        self,
        query: str = None,
        category: str = None,
        tags: List[str] = None,
        difficulty: str = None,
        language: str = None,
        min_quality: float = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        搜索最佳实践
        
        Args:
            query: 搜索关键词
            category: 分类
            tags: 标签列表
            difficulty: 难度
            language: 语言
            min_quality: 最低质量分
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            实践列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            sql = "SELECT * FROM practices WHERE 1=1"
            params = []
            
            # 关键词搜索
            if query:
                sql += " AND (title LIKE ? OR description LIKE ? OR code_example LIKE ?)"
                search_term = f"%{query}%"
                params.extend([search_term, search_term, search_term])
            
            # 分类过滤
            if category:
                sql += " AND category = ?"
                params.append(category)
            
            # 标签过滤
            if tags:
                # 简化版：只检查第一个标签
                sql += " AND tags LIKE ?"
                params.append(f"%{tags[0]}%")
            
            # 难度过滤
            if difficulty:
                sql += " AND difficulty = ?"
                params.append(difficulty)
            
            # 语言过滤
            if language:
                sql += " AND language = ?"
                params.append(language)
            
            # 质量分过滤
            if min_quality is not None:
                sql += " AND quality_score >= ?"
                params.append(min_quality)
            
            # 排序和分页
            sql += " ORDER BY quality_score DESC, created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_dict(row) for row in rows]
            
        finally:
            conn.close()
    
    async def get_practices_by_category(
        self,
        category: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        按分类获取实践
        
        Args:
            category: 分类名称
            limit: 返回数量
            
        Returns:
            实践列表
        """
        # 检查缓存
        cache_key = f"{category}_{limit}"
        if cache_key in self._category_cache:
            return self._category_cache[cache_key]
        
        practices = await self.search_practices(
            category=category,
            limit=limit
        )
        
        # 更新缓存
        self._category_cache[cache_key] = practices
        
        return practices
    
    async def get_practices_by_tags(
        self,
        tags: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        按标签获取实践
        
        Args:
            tags: 标签列表
            limit: 返回数量
            
        Returns:
            实践列表
        """
        return await self.search_practices(tags=tags, limit=limit)
    
    async def record_usage(
        self,
        practice_id: int,
        project: str,
        effectiveness: float = 0.0,
        notes: str = None,
        context: str = None
    ) -> int:
        """
        记录使用情况
        
        Args:
            practice_id: 实践ID
            project: 项目名称
            effectiveness: 有效性评分 (0-1)
            notes: 备注
            context: 上下文
            
        Returns:
            记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO practice_usage 
                (practice_id, used_in_project, effectiveness_score, notes, context)
                VALUES (?, ?, ?, ?, ?)
            """, (practice_id, project, effectiveness, notes, context))
            
            usage_id = cursor.lastrowid
            
            # 更新实践的质量分（基于平均有效性）
            await self._update_quality_score(practice_id)
            
            conn.commit()
            
            logger.info(f"Recorded usage of practice {practice_id} in {project}")
            
            return usage_id
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    async def _update_quality_score(self, practice_id: int):
        """更新实践质量分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 计算平均有效性
            cursor.execute("""
                SELECT AVG(effectiveness_score) 
                FROM practice_usage 
                WHERE practice_id = ?
            """, (practice_id,))
            
            result = cursor.fetchone()
            avg_effectiveness = result[0] if result[0] else 0.0
            
            # 更新质量分
            cursor.execute("""
                UPDATE practices 
                SET quality_score = ? 
                WHERE id = ?
            """, (avg_effectiveness, practice_id))
            
            conn.commit()
            
        finally:
            conn.close()
    
    async def add_feedback(
        self,
        practice_id: int,
        rating: int,
        comment: str = None
    ) -> int:
        """
        添加反馈
        
        Args:
            practice_id: 实践ID
            rating: 评分 (1-5)
            comment: 评论
            
        Returns:
            反馈ID
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO practice_feedback 
                (practice_id, rating, comment)
                VALUES (?, ?, ?)
            """, (practice_id, rating, comment))
            
            feedback_id = cursor.lastrowid
            conn.commit()
            
            return feedback_id
            
        finally:
            conn.close()
    
    async def get_popular_practices(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门最佳实践
        
        Args:
            limit: 返回数量
            
        Returns:
            实践列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    p.*,
                    COUNT(u.id) as usage_count,
                    AVG(u.effectiveness_score) as avg_effectiveness
                FROM practices p
                LEFT JOIN practice_usage u ON p.id = u.practice_id
                GROUP BY p.id
                ORDER BY usage_count DESC, avg_effectiveness DESC, p.quality_score DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            practices = []
            for row in rows:
                practice = self._row_to_dict(row[:13])  # 基础字段
                practice["usage_count"] = row[13] if len(row) > 13 else 0
                practice["avg_effectiveness"] = row[14] if len(row) > 14 and row[14] else 0.0
                practices.append(practice)
            
            return practices
            
        finally:
            conn.close()
    
    async def get_recent_practices(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的实践
        
        Args:
            limit: 返回数量
            
        Returns:
            实践列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM practices
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            return [self._row_to_dict(row) for row in rows]
            
        finally:
            conn.close()
    
    async def get_top_rated_practices(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取评分最高的实践
        
        Args:
            limit: 返回数量
            
        Returns:
            实践列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    p.*,
                    AVG(f.rating) as avg_rating,
                    COUNT(f.id) as rating_count
                FROM practices p
                LEFT JOIN practice_feedback f ON p.id = f.practice_id
                GROUP BY p.id
                HAVING rating_count > 0
                ORDER BY avg_rating DESC, rating_count DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            practices = []
            for row in rows:
                practice = self._row_to_dict(row[:13])
                practice["avg_rating"] = row[13] if len(row) > 13 else 0.0
                practice["rating_count"] = row[14] if len(row) > 14 else 0
                practices.append(practice)
            
            return practices
            
        finally:
            conn.close()
    
    async def get_practice_stats(self, practice_id: int) -> Dict[str, Any]:
        """
        获取实践统计信息
        
        Args:
            practice_id: 实践ID
            
        Returns:
            统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 使用次数
            cursor.execute("""
                SELECT COUNT(*) FROM practice_usage WHERE practice_id = ?
            """, (practice_id,))
            stats["usage_count"] = cursor.fetchone()[0]
            
            # 平均有效性
            cursor.execute("""
                SELECT AVG(effectiveness_score) FROM practice_usage WHERE practice_id = ?
            """, (practice_id,))
            result = cursor.fetchone()
            stats["avg_effectiveness"] = result[0] if result[0] else 0.0
            
            # 平均评分
            cursor.execute("""
                SELECT AVG(rating), COUNT(*) FROM practice_feedback WHERE practice_id = ?
            """, (practice_id,))
            result = cursor.fetchone()
            stats["avg_rating"] = result[0] if result[0] else 0.0
            stats["rating_count"] = result[1]
            
            # 最近使用
            cursor.execute("""
                SELECT used_in_project, used_at 
                FROM practice_usage 
                WHERE practice_id = ?
                ORDER BY used_at DESC
                LIMIT 5
            """, (practice_id,))
            stats["recent_usage"] = [
                {"project": row[0], "used_at": row[1]}
                for row in cursor.fetchall()
            ]
            
            return stats
            
        finally:
            conn.close()
    
    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """获取所有分类及其统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    category,
                    COUNT(*) as practice_count,
                    AVG(quality_score) as avg_quality
                FROM practices
                GROUP BY category
                ORDER BY practice_count DESC
            """)
            
            rows = cursor.fetchall()
            
            return [
                {
                    "category": row[0],
                    "practice_count": row[1],
                    "avg_quality": row[2] if row[2] else 0.0
                }
                for row in rows
            ]
            
        finally:
            conn.close()
    
    async def get_all_tags(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取所有标签及其统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT tags FROM practices")
            rows = cursor.fetchall()
            
            # 统计标签
            tag_counts = defaultdict(int)
            for row in rows:
                if row[0]:
                    tags = json.loads(row[0])
                    for tag in tags:
                        tag_counts[tag] += 1
            
            # 排序
            sorted_tags = sorted(
                tag_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]
            
            return [
                {"tag": tag, "count": count}
                for tag, count in sorted_tags
            ]
            
        finally:
            conn.close()
    
    async def export_practices(
        self,
        category: str = None,
        format: str = "json"
    ) -> str:
        """
        导出实践
        
        Args:
            category: 分类（可选）
            format: 格式 (json, markdown)
            
        Returns:
            导出内容
        """
        practices = await self.search_practices(
            category=category,
            limit=1000
        )
        
        if format == "json":
            return json.dumps(practices, indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            lines = ["# Best Practices Library\n"]
            
            for practice in practices:
                lines.append(f"## {practice['title']}\n")
                lines.append(f"**Category:** {practice['category']}\n")
                lines.append(f"**Description:** {practice['description']}\n")
                
                if practice.get('code_example'):
                    lines.append(f"**Example:**\n```{practice.get('language', 'python')}\n{practice['code_example']}\n```\n")
                
                if practice.get('tags'):
                    lines.append(f"**Tags:** {', '.join(practice['tags'])}\n")
                
                lines.append("\n---\n")
            
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def import_practices(
        self,
        data: str,
        format: str = "json"
    ) -> int:
        """
        导入实践
        
        Args:
            data: 数据内容
            format: 格式
            
        Returns:
            导入数量
        """
        if format == "json":
            practices = json.loads(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        count = 0
        for practice in practices:
            try:
                await self.add_practice(practice)
                count += 1
            except Exception as e:
                logger.error(f"Error importing practice: {e}")
        
        return count
    
    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "id": row[0],
            "title": row[1],
            "category": row[2],
            "description": row[3],
            "code_example": row[4],
            "tags": json.loads(row[5]) if row[5] else [],
            "quality_score": row[6] if row[6] else 0.0,
            "source": row[7],
            "author": row[8],
            "difficulty": row[9],
            "language": row[10],
            "created_at": row[11],
            "updated_at": row[12]
        }
    
    def _clear_cache(self):
        """清除缓存"""
        self._category_cache.clear()
        self._tag_cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取库统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 总实践数
            cursor.execute("SELECT COUNT(*) FROM practices")
            stats["total_practices"] = cursor.fetchone()[0]
            
            # 总使用次数
            cursor.execute("SELECT COUNT(*) FROM practice_usage")
            stats["total_usage"] = cursor.fetchone()[0]
            
            # 总反馈数
            cursor.execute("SELECT COUNT(*) FROM practice_feedback")
            stats["total_feedback"] = cursor.fetchone()[0]
            
            # 平均质量分
            cursor.execute("SELECT AVG(quality_score) FROM practices")
            result = cursor.fetchone()
            stats["avg_quality"] = result[0] if result[0] else 0.0
            
            # 分类数
            cursor.execute("SELECT COUNT(DISTINCT category) FROM practices")
            stats["category_count"] = cursor.fetchone()[0]
            
            return stats
            
        finally:
            conn.close()


# 预定义的最佳实践
DEFAULT_PRACTICES = [
    {
        "title": "Use Type Hints",
        "category": "code_quality",
        "description": "Add type hints to function signatures for better code clarity and IDE support.",
        "code_example": "def greet(name: str) -> str:\n    return f'Hello, {name}'",
        "tags": ["python", "type-hints", "clean-code"],
        "difficulty": "easy",
        "quality_score": 0.9
    },
    {
        "title": "Write Unit Tests",
        "category": "testing",
        "description": "Always write unit tests for critical functionality to ensure code reliability.",
        "code_example": "def test_greet():\n    assert greet('World') == 'Hello, World'",
        "tags": ["testing", "python", "quality"],
        "difficulty": "easy",
        "quality_score": 0.95
    },
    {
        "title": "Use Dependency Injection",
        "category": "design_patterns",
        "description": "Use dependency injection to improve code testability and flexibility.",
        "code_example": "class Service:\n    def __init__(self, repository: Repository):\n        self.repo = repository",
        "tags": ["design-patterns", "testing", "solid"],
        "difficulty": "medium",
        "quality_score": 0.85
    },
    {
        "title": "Handle Exceptions Properly",
        "category": "error_handling",
        "description": "Catch specific exceptions and provide meaningful error messages.",
        "code_example": "try:\n    result = risky_operation()\nexcept ValueError as e:\n    logger.error(f'Invalid value: {e}')\n    raise",
        "tags": ["error-handling", "python", "clean-code"],
        "difficulty": "easy",
        "quality_score": 0.9
    },
    {
        "title": "Use Async for I/O Operations",
        "category": "performance",
        "description": "Use async/await for I/O-bound operations to improve performance.",
        "code_example": "async def fetch_data(url: str) -> dict:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()",
        "tags": ["async", "performance", "python"],
        "difficulty": "medium",
        "quality_score": 0.85
    }
]


async def initialize_default_practices(library: BestPracticesLibrary):
    """初始化默认实践"""
    for practice in DEFAULT_PRACTICES:
        try:
            await library.add_practice(practice)
        except Exception as e:
            logger.warning(f"Could not add default practice: {e}")


if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 示例用法
        library = BestPracticesLibrary("./knowledge/practices.db")
        
        # 初始化默认实践
        await initialize_default_practices(library)
        
        # 搜索实践
        results = await library.search_practices("testing")
        print(f"Found {len(results)} practices about testing")
        
        # 获取热门实践
        popular = await library.get_popular_practices(5)
        print(f"Top 5 popular practices: {[p['title'] for p in popular]}")
        
        # 获取统计
        stats = await library.get_stats()
        print(f"Library stats: {stats}")
    
    asyncio.run(main())
