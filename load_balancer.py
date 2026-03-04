"""
负载均衡器 - 为分布式任务调度选择最佳节点

功能：
- 多维度评分算法（CPU、内存、任务数、网络延迟）
- 任务匹配度检查（GPU、环境依赖）
- 加权轮询和最少连接算法
- 健康节点过滤
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


class LoadBalancer:
    """负载均衡器 - 选择最佳节点执行任务"""
    
    def __init__(self, strategy: str = "weighted_score"):
        """
        初始化负载均衡器
        
        Args:
            strategy: 负载均衡策略
                - "weighted_score": 加权评分（默认）
                - "round_robin": 轮询
                - "least_connections": 最少连接
                - "random": 随机
        """
        self.strategy = strategy
        self.current_index = 0  # 用于轮询
        self.node_history = {}  # 节点历史记录
        
        # 评分权重配置
        self.weights = {
            "cpu": 0.5,          # CPU权重
            "memory": 0.3,       # 内存权重
            "tasks": 3.0,        # 活跃任务权重
            "latency": 0.1,      # 网络延迟权重
            "match": 10.0        # 任务匹配度奖励
        }
    
    def select_node(self, task: Dict, nodes: Dict) -> Optional[str]:
        """
        选择最佳节点执行任务
        
        Args:
            task: 任务信息
            nodes: 节点状态字典 {node_url: status_dict}
        
        Returns:
            最佳节点URL，如果没有可用节点则返回None
        """
        # 1. 过滤健康节点
        healthy_nodes = self._filter_healthy_nodes(nodes)
        
        if not healthy_nodes:
            logger.warning("No healthy nodes available")
            return None
        
        # 2. 根据策略选择节点
        if self.strategy == "weighted_score":
            return self._select_by_score(task, healthy_nodes)
        elif self.strategy == "round_robin":
            return self._select_by_round_robin(healthy_nodes)
        elif self.strategy == "least_connections":
            return self._select_by_least_connections(healthy_nodes)
        elif self.strategy == "random":
            return self._select_by_random(healthy_nodes)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, using weighted_score")
            return self._select_by_score(task, healthy_nodes)
    
    def _filter_healthy_nodes(self, nodes: Dict) -> Dict:
        """过滤健康节点"""
        healthy = {}
        
        for node_url, status in nodes.items():
            # 检查节点状态
            if status.get("status") != "healthy":
                continue
            
            # 检查是否响应超时
            last_check = status.get("last_check")
            if last_check:
                try:
                    check_time = datetime.fromisoformat(last_check)
                    if datetime.now() - check_time > timedelta(minutes=5):
                        logger.warning(f"Node {node_url} last check too old")
                        continue
                except:
                    pass
            
            # 检查资源是否耗尽
            if status.get("cpu_usage", 100) > 95:
                logger.warning(f"Node {node_url} CPU overloaded")
                continue
            
            if status.get("memory_usage", 100) > 95:
                logger.warning(f"Node {node_url} memory overloaded")
                continue
            
            healthy[node_url] = status
        
        return healthy
    
    def _select_by_score(self, task: Dict, nodes: Dict) -> str:
        """基于加权评分选择节点"""
        scores = {}
        
        for node_url, status in nodes.items():
            score = self.calculate_score(status, task)
            scores[node_url] = score
            
            logger.debug(f"Node {node_url} score: {score:.2f}")
        
        # 选择得分最高的节点
        best_node = max(scores, key=scores.get)
        
        # 记录选择历史
        self._record_selection(best_node, task)
        
        logger.info(f"Selected node {best_node} with score {scores[best_node]:.2f}")
        
        return best_node
    
    def _select_by_round_robin(self, nodes: Dict) -> str:
        """轮询选择"""
        node_list = list(nodes.keys())
        
        selected = node_list[self.current_index % len(node_list)]
        self.current_index += 1
        
        self._record_selection(selected, {})
        
        return selected
    
    def _select_by_least_connections(self, nodes: Dict) -> str:
        """最少连接选择"""
        min_tasks = float('inf')
        best_node = None
        
        for node_url, status in nodes.items():
            active_tasks = status.get("active_tasks", 0)
            
            if active_tasks < min_tasks:
                min_tasks = active_tasks
                best_node = node_url
        
        self._record_selection(best_node, {})
        
        return best_node
    
    def _select_by_random(self, nodes: Dict) -> str:
        """随机选择"""
        import random
        return random.choice(list(nodes.keys()))
    
    def calculate_score(self, status: Dict, task: Dict) -> float:
        """
        计算节点得分（100分制）
        
        Args:
            status: 节点状态
            task: 任务信息
        
        Returns:
            节点得分（0-100）
        """
        score = 100.0
        
        # 1. CPU使用率（-0.5分/%）
        cpu_usage = status.get("cpu_usage", 50)
        cpu_penalty = max(0, (cpu_usage - 50) * self.weights["cpu"])
        score -= cpu_penalty
        
        # 2. 内存使用率（-0.3分/%）
        memory_usage = status.get("memory_usage", 50)
        memory_penalty = max(0, (memory_usage - 50) * self.weights["memory"])
        score -= memory_penalty
        
        # 3. 活跃任务数（-3分/任务）
        active_tasks = status.get("active_tasks", 0)
        tasks_penalty = active_tasks * self.weights["tasks"]
        score -= tasks_penalty
        
        # 4. 网络延迟（-0.1分/ms）
        network_latency = status.get("network_latency", 0)
        latency_penalty = network_latency * self.weights["latency"]
        score -= latency_penalty
        
        # 5. 历史成功率奖励
        success_rate = self._get_success_rate(status.get("node_url"))
        if success_rate > 0.9:
            score += 5
        elif success_rate > 0.8:
            score += 3
        
        # 6. 任务匹配度检查
        if self.check_task_match(status, task):
            score += self.weights["match"]
        else:
            # 不匹配则大幅扣分
            score -= 50
        
        # 7. 特殊能力奖励
        score += self._calculate_special_bonuses(status, task)
        
        return max(score, 0)
    
    def _calculate_special_bonuses(self, status: Dict, task: Dict) -> float:
        """计算特殊能力奖励"""
        bonus = 0.0
        
        # GPU任务奖励
        if task.get("requires_gpu") and status.get("has_gpu"):
            gpu_memory = status.get("gpu_memory", 0)
            if gpu_memory > 8:  # 8GB+
                bonus += 5
            elif gpu_memory > 4:  # 4GB+
                bonus += 3
        
        # 高内存任务奖励
        if task.get("requires_high_memory"):
            available_memory = status.get("available_memory", 0)
            if available_memory > 16:  # 16GB+
                bonus += 4
        
        # 特定环境奖励
        required_env = task.get("required_env", [])
        available_env = status.get("available_env", [])
        
        matched_env = sum(1 for env in required_env if env in available_env)
        if matched_env == len(required_env) and len(required_env) > 0:
            bonus += 3
        
        return bonus
    
    def check_task_match(self, status: Dict, task: Dict) -> bool:
        """
        检查任务是否匹配节点能力
        
        Args:
            status: 节点状态
            task: 任务信息
        
        Returns:
            是否匹配
        """
        # 检查GPU需求
        if task.get("requires_gpu") and not status.get("has_gpu"):
            logger.debug(f"Task requires GPU but node has no GPU")
            return False
        
        # 检查高内存需求
        if task.get("requires_high_memory"):
            available_memory = status.get("available_memory", 0)
            if available_memory < 8:  # 小于8GB
                logger.debug(f"Task requires high memory but node has only {available_memory}GB")
                return False
        
        # 检查特殊环境
        required_env = task.get("required_env", [])
        available_env = status.get("available_env", [])
        
        for env in required_env:
            if env not in available_env:
                logger.debug(f"Task requires {env} but node doesn't have it")
                return False
        
        # 检查磁盘空间
        required_disk = task.get("required_disk_gb", 0)
        available_disk = status.get("disk_available_gb", 0)
        
        if required_disk > available_disk:
            logger.debug(f"Task requires {required_disk}GB disk but node has only {available_disk}GB")
            return False
        
        return True
    
    def _record_selection(self, node_url: str, task: Dict):
        """记录节点选择历史"""
        if node_url not in self.node_history:
            self.node_history[node_url] = {
                "total_selections": 0,
                "recent_selections": []
            }
        
        history = self.node_history[node_url]
        history["total_selections"] += 1
        history["recent_selections"].append({
            "task_id": task.get("id"),
            "timestamp": datetime.now().isoformat()
        })
        
        # 只保留最近100条记录
        if len(history["recent_selections"]) > 100:
            history["recent_selections"] = history["recent_selections"][-100:]
    
    def _get_success_rate(self, node_url: Optional[str]) -> float:
        """获取节点历史成功率"""
        if not node_url or node_url not in self.node_history:
            return 0.5  # 默认中等成功率
        
        history = self.node_history[node_url]
        
        # 这里可以扩展为从数据库读取实际成功率
        # 暂时返回基于选择次数的虚拟值
        total = history.get("total_selections", 0)
        if total < 5:
            return 0.5
        elif total < 20:
            return 0.7
        else:
            return 0.85
    
    def get_node_ranking(self, nodes: Dict, task: Dict = None) -> List[Dict]:
        """
        获取节点排名
        
        Args:
            nodes: 节点状态
            task: 任务信息（可选）
        
        Returns:
            排名列表 [{"node": url, "score": score, "status": status}]
        """
        if task is None:
            task = {}
        
        ranking = []
        
        for node_url, status in nodes.items():
            score = self.calculate_score(status, task)
            is_healthy = status.get("status") == "healthy"
            
            ranking.append({
                "node": node_url,
                "score": score,
                "status": "healthy" if is_healthy else "unhealthy",
                "cpu_usage": status.get("cpu_usage", 0),
                "memory_usage": status.get("memory_usage", 0),
                "active_tasks": status.get("active_tasks", 0)
            })
        
        # 按得分排序
        ranking.sort(key=lambda x: x["score"], reverse=True)
        
        return ranking
    
    def update_weights(self, new_weights: Dict):
        """更新评分权重"""
        self.weights.update(new_weights)
        logger.info(f"Updated weights: {self.weights}")
    
    def get_statistics(self) -> Dict:
        """获取负载均衡统计信息"""
        total_selections = sum(
            h["total_selections"] 
            for h in self.node_history.values()
        )
        
        return {
            "strategy": self.strategy,
            "total_selections": total_selections,
            "node_count": len(self.node_history),
            "weights": self.weights,
            "current_index": self.current_index
        }


class AdvancedLoadBalancer(LoadBalancer):
    """高级负载均衡器 - 支持预测和自适应"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 预测模型参数
        self.prediction_window = 5  # 预测窗口（分钟）
        self.adaptive_learning_rate = 0.1
        
        # 节点性能历史
        self.performance_history = {}
    
    def predict_node_load(self, node_url: str) -> Dict:
        """预测节点未来负载"""
        if node_url not in self.performance_history:
            return {"predicted_cpu": 50, "predicted_memory": 50, "confidence": 0}
        
        history = self.performance_history[node_url]
        
        # 简单的线性预测（可以替换为更复杂的模型）
        recent_cpu = [h["cpu_usage"] for h in history[-10:]]
        recent_memory = [h["memory_usage"] for h in history[-10:]]
        
        if len(recent_cpu) < 3:
            return {"predicted_cpu": 50, "predicted_memory": 50, "confidence": 0.3}
        
        # 计算趋势
        cpu_trend = (recent_cpu[-1] - recent_cpu[0]) / len(recent_cpu)
        memory_trend = (recent_memory[-1] - recent_memory[0]) / len(recent_memory)
        
        predicted_cpu = recent_cpu[-1] + cpu_trend * 5
        predicted_memory = recent_memory[-1] + memory_trend * 5
        
        return {
            "predicted_cpu": max(0, min(100, predicted_cpu)),
            "predicted_memory": max(0, min(100, predicted_memory)),
            "confidence": min(1.0, len(recent_cpu) / 10)
        }
    
    def select_node_with_prediction(self, task: Dict, nodes: Dict) -> Optional[str]:
        """基于预测的节点选择"""
        healthy_nodes = self._filter_healthy_nodes(nodes)
        
        if not healthy_nodes:
            return None
        
        scores = {}
        
        for node_url, status in healthy_nodes.items():
            # 当前得分
            current_score = self.calculate_score(status, task)
            
            # 预测得分
            prediction = self.predict_node_load(node_url)
            
            if prediction["confidence"] > 0.5:
                # 根据预测调整得分
                predicted_status = status.copy()
                predicted_status["cpu_usage"] = prediction["predicted_cpu"]
                predicted_status["memory_usage"] = prediction["predicted_memory"]
                
                predicted_score = self.calculate_score(predicted_status, task)
                
                # 加权平均
                final_score = (
                    current_score * (1 - prediction["confidence"]) +
                    predicted_score * prediction["confidence"]
                )
            else:
                final_score = current_score
            
            scores[node_url] = final_score
        
        best_node = max(scores, key=scores.get)
        
        return best_node
    
    def update_performance_history(self, node_url: str, status: Dict):
        """更新节点性能历史"""
        if node_url not in self.performance_history:
            self.performance_history[node_url] = []
        
        self.performance_history[node_url].append({
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": status.get("cpu_usage", 50),
            "memory_usage": status.get("memory_usage", 50),
            "active_tasks": status.get("active_tasks", 0)
        })
        
        # 只保留最近100条记录
        if len(self.performance_history[node_url]) > 100:
            self.performance_history[node_url] = self.performance_history[node_url][-100:]
    
    def adaptive_weight_adjustment(self):
        """自适应权重调整"""
        # 根据历史性能调整权重
        for node_url, history in self.performance_history.items():
            if len(history) < 10:
                continue
            
            # 计算平均CPU和内存使用率
            avg_cpu = sum(h["cpu_usage"] for h in history[-10:]) / 10
            avg_memory = sum(h["memory_usage"] for h in history[-10:]) / 10
            
            # 如果某个资源经常高负载，增加其权重
            if avg_cpu > 70:
                self.weights["cpu"] = min(1.0, self.weights["cpu"] + self.adaptive_learning_rate)
            
            if avg_memory > 70:
                self.weights["memory"] = min(0.6, self.weights["memory"] + self.adaptive_learning_rate)


# 便捷函数
def create_load_balancer(strategy: str = "weighted_score", advanced: bool = False) -> LoadBalancer:
    """
    创建负载均衡器
    
    Args:
        strategy: 负载均衡策略
        advanced: 是否使用高级负载均衡器
    
    Returns:
        负载均衡器实例
    """
    if advanced:
        return AdvancedLoadBalancer(strategy=strategy)
    else:
        return LoadBalancer(strategy=strategy)


if __name__ == "__main__":
    # 测试负载均衡器
    lb = LoadBalancer()
    
    # 模拟节点状态
    nodes = {
        "http://node1:8000": {
            "status": "healthy",
            "cpu_usage": 30,
            "memory_usage": 40,
            "active_tasks": 2,
            "network_latency": 10,
            "has_gpu": False,
            "available_env": ["python3.11", "nodejs"]
        },
        "http://node2:8000": {
            "status": "healthy",
            "cpu_usage": 60,
            "memory_usage": 70,
            "active_tasks": 5,
            "network_latency": 20,
            "has_gpu": True,
            "gpu_memory": 8,
            "available_env": ["python3.11", "cuda"]
        },
        "http://node3:8000": {
            "status": "healthy",
            "cpu_usage": 20,
            "memory_usage": 30,
            "active_tasks": 1,
            "network_latency": 5,
            "has_gpu": False,
            "available_env": ["python3.11", "nodejs", "go"]
        }
    }
    
    # 测试普通任务
    task1 = {
        "id": "task_1",
        "description": "Normal task"
    }
    
    best_node = lb.select_node(task1, nodes)
    print(f"Best node for task1: {best_node}")
    
    # 测试GPU任务
    task2 = {
        "id": "task_2",
        "description": "GPU task",
        "requires_gpu": True
    }
    
    best_node = lb.select_node(task2, nodes)
    print(f"Best node for task2 (GPU): {best_node}")
    
    # 获取排名
    ranking = lb.get_node_ranking(nodes, task1)
    print("\nNode ranking:")
    for r in ranking:
        print(f"  {r['node']}: score={r['score']:.2f}, status={r['status']}")
    
    # 统计信息
    stats = lb.get_statistics()
    print(f"\nStatistics: {stats}")
