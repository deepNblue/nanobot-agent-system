"""
代码知识图谱 - Code Knowledge Graph

构建和管理代码库的知识图谱，支持代码实体提取、关系分析和智能查询。

Author: Nanobot Agent System
Phase: 4 - Knowledge Base Enhancement
"""

import os
import ast
import json
import logging
import re
import hashlib
from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    """代码实体数据结构"""

    id: str
    name: str
    type: str  # function, class, method, variable, module
    file: str
    line: int
    end_line: int
    docstring: Optional[str] = None
    code: Optional[str] = None
    complexity: int = 0
    args: List[str] = None
    returns: Optional[str] = None
    bases: List[str] = None
    decorators: List[str] = None
    imports: List[str] = None
    calls: List[str] = None
    attributes: List[str] = None
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.bases is None:
            self.bases = []
        if self.decorators is None:
            self.decorators = []
        if self.imports is None:
            self.imports = []
        if self.calls is None:
            self.calls = []
        if self.attributes is None:
            self.attributes = []
        if self.metrics is None:
            self.metrics = {}


@dataclass
class CodeRelation:
    """代码关系数据结构"""

    source: str
    target: str
    type: str  # calls, inherits, imports, contains, uses
    weight: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CodeKnowledgeGraph:
    """代码知识图谱"""

    def __init__(self, storage_path: str = "./knowledge"):
        """
        初始化代码知识图谱

        Args:
            storage_path: 存储路径
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required. Install with: pip install networkx")

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 主图谱
        self.graph = nx.DiGraph()

        # 索引结构
        self.name_index: Dict[str, Set[str]] = defaultdict(set)  # 名称 -> 节点ID集合
        self.file_index: Dict[str, Set[str]] = defaultdict(set)  # 文件 -> 节点ID集合
        self.type_index: Dict[str, Set[str]] = defaultdict(set)  # 类型 -> 节点ID集合

        # 缓存
        self._entity_cache: Dict[str, CodeEntity] = {}
        self._graph_hash: Optional[str] = None

        # 统计信息
        self.stats = {"total_entities": 0, "total_relations": 0, "files_processed": 0, "last_update": None}

        # 尝试加载已有图谱
        self.load_graph()

        logger.info(f"CodeKnowledgeGraph initialized at {storage_path}")

    async def build_graph(
        self, codebase_path: str, exclude_patterns: List[str] = None, max_files: int = 1000
    ) -> Dict[str, Any]:
        """
        构建代码图谱

        Args:
            codebase_path: 代码库路径
            exclude_patterns: 排除模式列表
            max_files: 最大文件数

        Returns:
            构建统计信息
        """
        logger.info(f"Building code graph for {codebase_path}")

        start_time = datetime.now()

        # 默认排除模式
        if exclude_patterns is None:
            exclude_patterns = [
                "*/test_*.py",
                "*/__pycache__/*",
                "*/venv/*",
                "*/.venv/*",
                "*/node_modules/*",
                "*/build/*",
                "*/dist/*",
                "*/.git/*",
            ]

        # 1. 扫描代码库
        python_files = self._scan_codebase(codebase_path, exclude_patterns, max_files)
        logger.info(f"Found {len(python_files)} Python files")

        # 2. 分析每个文件
        entities_created = 0
        for file_path in python_files:
            try:
                file_entities = await self._analyze_file(file_path, codebase_path)
                entities_created += len(file_entities)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")

        # 3. 提取关系
        relations_created = self._extract_relationships()

        # 4. 更新统计
        self.stats["total_entities"] = self.graph.number_of_nodes()
        self.stats["total_relations"] = self.graph.number_of_edges()
        self.stats["files_processed"] = len(python_files)
        self.stats["last_update"] = datetime.now().isoformat()

        # 5. 保存图谱
        await self.save_graph()

        elapsed = (datetime.now() - start_time).total_seconds()

        result = {
            "success": True,
            "files_processed": len(python_files),
            "entities_created": entities_created,
            "relations_created": relations_created,
            "elapsed_seconds": elapsed,
            "stats": self.stats,
        }

        logger.info(f"Graph built: {entities_created} entities, {relations_created} relations in {elapsed:.2f}s")

        return result

    def _scan_codebase(self, codebase_path: str, exclude_patterns: List[str], max_files: int) -> List[Path]:
        """扫描代码库"""
        codebase = Path(codebase_path)
        python_files = []

        for file_path in codebase.rglob("*.py"):
            # 检查排除模式
            excluded = False
            for pattern in exclude_patterns:
                if file_path.match(pattern):
                    excluded = True
                    break

            if not excluded:
                python_files.append(file_path)

                if len(python_files) >= max_files:
                    logger.warning(f"Max files limit reached: {max_files}")
                    break

        return python_files

    async def _analyze_file(self, file_path: Path, codebase_path: str) -> List[CodeEntity]:
        """分析单个文件"""
        entities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # 解析AST
            tree = ast.parse(code, filename=str(file_path))

            # 获取相对路径
            rel_path = file_path.relative_to(codebase_path)

            # 提取模块级导入
            module_imports = self._extract_imports(tree)

            # 提取实体
            for node in ast.walk(tree):
                entity = None

                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    entity = self._extract_function(node, str(rel_path), code, module_imports)
                elif isinstance(node, ast.ClassDef):
                    entity = self._extract_class(node, str(rel_path), code, module_imports)

                if entity:
                    # 添加到图谱
                    self._add_entity(entity)
                    entities.append(entity)

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

        return entities

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入语句"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

        return imports

    def _extract_function(
        self, node: ast.FunctionDef, file_path: str, code: str, module_imports: List[str]
    ) -> Optional[CodeEntity]:
        """提取函数实体"""
        # 获取代码片段
        code_lines = code.split("\n")
        code_snippet = "\n".join(code_lines[node.lineno - 1 : node.end_lineno])

        # 提取函数调用
        calls = self._extract_function_calls(node)

        # 计算复杂度
        complexity = self._calculate_complexity(node)

        # 提取装饰器
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{decorator.value.id}.{decorator.attr}")

        # 推断返回类型
        returns = self._infer_return_type(node)

        entity_id = f"{file_path}::line_{node.lineno}::{node.name}"

        return CodeEntity(
            id=entity_id,
            name=node.name,
            type="function",
            file=file_path,
            line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            code=code_snippet,
            complexity=complexity,
            args=[arg.arg for arg in node.args.args],
            returns=returns,
            decorators=decorators,
            imports=module_imports,
            calls=calls,
            metrics={"arg_count": len(node.args.args), "has_docstring": ast.get_docstring(node) is not None},
        )

    def _extract_class(self, node: ast.ClassDef, file_path: str, code: str, module_imports: List[str]) -> Optional[CodeEntity]:
        """提取类实体"""
        # 获取代码片段
        code_lines = code.split("\n")
        code_snippet = "\n".join(code_lines[node.lineno - 1 : node.end_lineno])

        # 提取基类
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}")

        # 提取方法
        methods = []
        attributes = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)

        # 提取装饰器
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{decorator.value.id}.{decorator.attr}")

        # 计算类复杂度
        complexity = sum(self._calculate_complexity(item) for item in node.body if isinstance(item, ast.FunctionDef))

        entity_id = f"{file_path}::line_{node.lineno}::{node.name}"

        return CodeEntity(
            id=entity_id,
            name=node.name,
            type="class",
            file=file_path,
            line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            code=code_snippet,
            complexity=complexity,
            bases=bases,
            decorators=decorators,
            imports=module_imports,
            attributes=attributes,
            metrics={
                "method_count": len(methods),
                "attribute_count": len(attributes),
                "has_docstring": ast.get_docstring(node) is not None,
                "methods": methods,
            },
        )

    def _extract_function_calls(self, node: ast.AST) -> List[str]:
        """提取函数调用"""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        return list(set(calls))

    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)

        return complexity

    def _infer_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """推断返回类型"""
        # 检查类型注解
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return str(node.returns.value)
            elif isinstance(node.returns, ast.Subscript):
                return ast.unparse(node.returns)

        # 从docstring推断
        docstring = ast.get_docstring(node)
        if docstring:
            # 查找 Returns: 或 :return:
            match = re.search(r":return[s]?:\s*(\w+)", docstring, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _add_entity(self, entity: CodeEntity):
        """添加实体到图谱"""
        # 添加节点
        self.graph.add_node(entity.id, **asdict(entity))

        # 更新索引
        self.name_index[entity.name].add(entity.id)
        self.file_index[entity.file].add(entity.id)
        self.type_index[entity.type].add(entity.id)

        # 更新缓存
        self._entity_cache[entity.id] = entity

    def _extract_relationships(self) -> int:
        """提取实体关系"""
        relations = 0

        # 1. 函数调用关系
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]

            if node_data.get("calls"):
                for called_func in node_data["calls"]:
                    # 查找被调用的函数
                    target_ids = self.name_index.get(called_func, set())

                    for target_id in target_ids:
                        if target_id != node_id:  # 避免自引用
                            self.graph.add_edge(node_id, target_id, type="calls", weight=1.0)
                            relations += 1

        # 2. 类继承关系
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]

            if node_data.get("type") == "class" and node_data.get("bases"):
                for base in node_data["bases"]:
                    # 查找基类
                    target_ids = self.name_index.get(base, set())

                    for target_id in target_ids:
                        if target_id != node_id:
                            self.graph.add_edge(node_id, target_id, type="inherits", weight=2.0)
                            relations += 1

        # 3. 文件包含关系
        for file_path, node_ids in self.file_index.items():
            # 添加虚拟文件节点
            file_node = f"file::{file_path}"
            self.graph.add_node(file_node, type="file", path=file_path)

            for node_id in node_ids:
                self.graph.add_edge(file_node, node_id, type="contains", weight=0.5)
                relations += 1

        return relations

    async def query(self, query: str, model_adapter: Any = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        查询知识图谱

        Args:
            query: 查询字符串
            model_adapter: 模型适配器（用于智能查询理解）
            limit: 返回结果限制

        Returns:
            查询结果列表
        """
        logger.info(f"Querying knowledge graph: {query}")

        # 如果有模型适配器，使用智能查询理解
        if model_adapter:
            intent = await self._understand_query(query, model_adapter)
        else:
            # 简单查询
            intent = {"type": "find_similar", "target": query}

        # 根据意图执行查询
        if intent["type"] == "find_similar":
            results = self._find_similar_code(intent["target"], limit)
        elif intent["type"] == "find_usage":
            results = self._find_usage_examples(intent["target"], limit)
        elif intent["type"] == "find_dependencies":
            results = self._find_dependencies(intent["target"])
        elif intent["type"] == "find_patterns":
            results = self._find_design_patterns(intent["target"], limit)
        elif intent["type"] == "find_complex":
            results = self._find_complex_code(intent.get("threshold", 10), limit)
        else:
            results = self._find_similar_code(intent["target"], limit)

        logger.info(f"Query returned {len(results)} results")

        return results

    async def _understand_query(self, query: str, model_adapter: Any) -> Dict[str, Any]:
        """理解查询意图"""
        prompt = f"""Analyze the following code query and extract the intent:

Query: {query}

Determine the query type:
- find_similar: Find code similar to the target
- find_usage: Find usage examples of the target
- find_dependencies: Find dependency relationships
- find_patterns: Find design patterns
- find_complex: Find complex code

Respond in JSON format:
{{
  "type": "find_similar" | "find_usage" | "find_dependencies" | "find_patterns" | "find_complex",
  "target": "the code element to search for",
  "context": "additional context",
  "threshold": 10
}}

Only respond with the JSON, no other text.
"""

        try:
            result = await model_adapter.call_model(model="glm5-turbo", prompt=prompt, temperature=0.1, max_tokens=200)

            if result.get("success"):
                content = result["content"]
                json_match = re.search(r"\{.*\}", content, re.DOTALL)

                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Error understanding query: {e}")

        # 默认返回
        return {"type": "find_similar", "target": query}

    def _find_similar_code(self, target: str, limit: int = 10) -> List[Dict[str, Any]]:
        """查找相似代码"""
        results = []
        target_lower = target.lower()

        # 搜索名称匹配
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]

            if node_data.get("type") in ["function", "class"]:
                name = node_data.get("name", "")
                docstring = node_data.get("docstring", "")

                # 计算相似度
                similarity = 0.0
                if target_lower in name.lower():
                    similarity = 1.0
                elif docstring and target_lower in docstring.lower():
                    similarity = 0.7

                if similarity > 0:
                    results.append(
                        {
                            "node_id": node_id,
                            "name": name,
                            "type": node_data.get("type"),
                            "file": node_data.get("file"),
                            "line": node_data.get("line"),
                            "docstring": docstring,
                            "similarity": similarity,
                            "code": node_data.get("code", "")[:200],  # 代码片段
                        }
                    )

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:limit]

    def _find_usage_examples(self, target: str, limit: int = 10) -> List[Dict[str, Any]]:
        """查找使用示例"""
        # 找到目标节点
        target_ids = self.name_index.get(target, set())

        results = []

        for target_id in target_ids:
            # 找到所有调用者
            callers = list(self.graph.predecessors(target_id))

            for caller in callers:
                caller_data = self.graph.nodes[caller]

                # 只返回函数调用关系
                if self.graph.edges[caller, target_id].get("type") == "calls":
                    results.append(
                        {
                            "target": target,
                            "used_in": caller_data.get("name"),
                            "file": caller_data.get("file"),
                            "line": caller_data.get("line"),
                            "type": "usage",
                            "code": caller_data.get("code", "")[:200],
                        }
                    )

        return results[:limit]

    def _find_dependencies(self, target: str) -> List[Dict[str, Any]]:
        """查找依赖关系"""
        # 找到目标节点
        target_ids = self.name_index.get(target, set())

        results = []

        for target_id in target_ids:
            # 入度（依赖的）
            dependencies = []
            for pred in self.graph.predecessors(target_id):
                edge_data = self.graph.edges[pred, target_id]
                dependencies.append({"node": pred, "type": edge_data.get("type"), "name": self.graph.nodes[pred].get("name")})

            # 出度（被依赖的）
            dependents = []
            for succ in self.graph.successors(target_id):
                edge_data = self.graph.edges[target_id, succ]
                dependents.append({"node": succ, "type": edge_data.get("type"), "name": self.graph.nodes[succ].get("name")})

            results.append(
                {
                    "target": target_id,
                    "target_name": self.graph.nodes[target_id].get("name"),
                    "dependencies": dependencies,
                    "dependents": dependents,
                    "dependency_count": len(dependencies),
                    "dependent_count": len(dependents),
                }
            )

        return results

    def _find_design_patterns(self, target: str, limit: int = 10) -> List[Dict[str, Any]]:
        """查找设计模式"""
        results = []

        # 简单的模式检测
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]

            if node_data.get("type") == "class":
                pattern = self._detect_design_pattern(node_id, node_data)

                if pattern and target.lower() in pattern.lower():
                    results.append(
                        {
                            "node_id": node_id,
                            "name": node_data.get("name"),
                            "file": node_data.get("file"),
                            "pattern": pattern,
                            "confidence": 0.8,
                        }
                    )

        return results[:limit]

    def _detect_design_pattern(self, node_id: str, node_data: Dict) -> Optional[str]:
        """检测设计模式"""
        name = node_data.get("name", "").lower()
        methods = node_data.get("metrics", {}).get("methods", [])
        bases = node_data.get("bases", [])

        # 单例模式
        if "singleton" in name or "get_instance" in methods:
            return "Singleton"

        # 工厂模式
        if "factory" in name or any(m.startswith("create_") for m in methods):
            return "Factory"

        # 观察者模式
        if "observer" in name or "notify" in methods or "subscribe" in methods:
            return "Observer"

        # 策略模式
        if "strategy" in name or "execute" in methods:
            return "Strategy"

        # 装饰器模式
        if "decorator" in name or len(bases) > 0:
            return "Decorator"

        return None

    def _find_complex_code(self, threshold: int = 10, limit: int = 10) -> List[Dict[str, Any]]:
        """查找复杂代码"""
        results = []

        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            complexity = node_data.get("complexity", 0)

            if complexity >= threshold:
                results.append(
                    {
                        "node_id": node_id,
                        "name": node_data.get("name"),
                        "type": node_data.get("type"),
                        "file": node_data.get("file"),
                        "line": node_data.get("line"),
                        "complexity": complexity,
                        "recommendation": "Consider refactoring to reduce complexity",
                    }
                )

        # 按复杂度排序
        results.sort(key=lambda x: x["complexity"], reverse=True)

        return results[:limit]

    def get_code_metrics(self) -> Dict[str, Any]:
        """获取代码指标"""
        metrics = {
            "total_entities": self.graph.number_of_nodes(),
            "total_relations": self.graph.number_of_edges(),
            "entity_types": {},
            "avg_complexity": 0,
            "max_complexity": 0,
            "most_complex_files": [],
            "most_called_functions": [],
        }

        # 实体类型统计
        for node_id in self.graph.nodes():
            node_type = self.graph.nodes[node_id].get("type", "unknown")
            metrics["entity_types"][node_type] = metrics["entity_types"].get(node_type, 0) + 1

        # 复杂度统计
        complexities = []
        for node_id in self.graph.nodes():
            complexity = self.graph.nodes[node_id].get("complexity", 0)
            if complexity > 0:
                complexities.append(complexity)

        if complexities:
            metrics["avg_complexity"] = sum(complexities) / len(complexities)
            metrics["max_complexity"] = max(complexities)

        # 最多调用的函数
        call_counts = []
        for node_id in self.graph.nodes():
            if self.graph.nodes[node_id].get("type") in ["function", "class"]:
                in_degree = self.graph.in_degree(node_id)
                if in_degree > 0:
                    call_counts.append({"name": self.graph.nodes[node_id].get("name"), "count": in_degree})

        call_counts.sort(key=lambda x: x["count"], reverse=True)
        metrics["most_called_functions"] = call_counts[:5]

        return metrics

    async def save_graph(self) -> bool:
        """保存图谱"""
        try:
            graph_file = self.storage_path / "code_graph.json"

            # 转换为可序列化格式
            data = {"nodes": {}, "edges": [], "stats": self.stats, "timestamp": datetime.now().isoformat()}

            # 序列化节点
            for node_id in self.graph.nodes():
                node_data = self.graph.nodes[node_id]
                # 转换不可序列化的数据
                serializable_data = {}
                for key, value in node_data.items():
                    try:
                        json.dumps({key: value})
                        serializable_data[key] = value
                    except Exception as e:
                        serializable_data[key] = str(value)

                data["nodes"][node_id] = serializable_data

            # 序列化边
            for source, target in self.graph.edges():
                edge_data = self.graph.edges[source, target]
                data["edges"].append({"source": source, "target": target, "data": dict(edge_data)})

            with open(graph_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 保存索引
            index_file = self.storage_path / "code_graph_index.json"
            index_data = {
                "name_index": {k: list(v) for k, v in self.name_index.items()},
                "file_index": {k: list(v) for k, v in self.file_index.items()},
                "type_index": {k: list(v) for k, v in self.type_index.items()},
            }

            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Graph saved to {graph_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving graph: {e}")
            return False

    def load_graph(self) -> bool:
        """加载图谱"""
        try:
            graph_file = self.storage_path / "code_graph.json"
            index_file = self.storage_path / "code_graph_index.json"

            if not graph_file.exists():
                logger.info("No existing graph found, starting fresh")
                return False

            # 加载图谱
            with open(graph_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 恢复节点
            self.graph.clear()
            for node_id, node_data in data["nodes"].items():
                self.graph.add_node(node_id, **node_data)

            # 恢复边
            for edge in data["edges"]:
                self.graph.add_edge(edge["source"], edge["target"], **edge["data"])

            # 恢复统计
            self.stats = data.get("stats", self.stats)

            # 加载索引
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                self.name_index = defaultdict(set, {k: set(v) for k, v in index_data.get("name_index", {}).items()})
                self.file_index = defaultdict(set, {k: set(v) for k, v in index_data.get("file_index", {}).items()})
                self.type_index = defaultdict(set, {k: set(v) for k, v in index_data.get("type_index", {}).items()})

            logger.info(f"Graph loaded: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            return True

        except Exception as e:
            logger.error(f"Error loading graph: {e}")
            return False

    def export_to_format(self, format: str = "json") -> str:
        """
        导出图谱到指定格式

        Args:
            format: 导出格式 (json, gexf, graphml)

        Returns:
            导出文件路径
        """
        output_file = self.storage_path / f"code_graph.{format}"

        try:
            if format == "json":
                # 已经在save_graph中实现
                return str(self.storage_path / "code_graph.json")
            elif format == "gexf":
                nx.write_gexf(self.graph, output_file)
            elif format == "graphml":
                nx.write_graphml(self.graph, output_file)
            else:
                raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Graph exported to {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"Error exporting graph: {e}")
            return ""


# 便捷函数
async def build_knowledge_graph(codebase_path: str, storage_path: str = "./knowledge") -> CodeKnowledgeGraph:
    """
    构建代码知识图谱的便捷函数

    Args:
        codebase_path: 代码库路径
        storage_path: 存储路径

    Returns:
        CodeKnowledgeGraph实例
    """
    kg = CodeKnowledgeGraph(storage_path)
    await kg.build_graph(codebase_path)
    return kg


if __name__ == "__main__":
    import asyncio

    async def main():
        # 示例用法
        kg = CodeKnowledgeGraph("./knowledge")

        # 构建图谱
        result = await kg.build_graph(".")
        print(f"Build result: {result}")

        # 查询
        results = await kg.query("function")
        print(f"Query results: {len(results)}")

        # 获取指标
        metrics = kg.get_code_metrics()
        print(f"Metrics: {metrics}")

    asyncio.run(main())
