"""
成本优化器 - 预算管理和成本优化
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """使用记录"""
    model: str
    tokens: int
    cost: float
    timestamp: str
    task_id: Optional[str] = None
    success: bool = True


@dataclass
class BudgetStatus:
    """预算状态"""
    daily_budget: float
    daily_spent: float
    daily_remaining: float
    hourly_budget: float
    hourly_spent: float
    hourly_remaining: float
    usage_percentage: float
    is_over_budget: bool


class CostOptimizer:
    """成本优化器"""
    
    def __init__(
        self,
        daily_budget: float = 10.0,
        hourly_budget: float = 1.0,
        alert_threshold: float = 0.8,
        history_file: str = None
    ):
        self.daily_budget = daily_budget
        self.hourly_budget = hourly_budget
        self.alert_threshold = alert_threshold
        
        self.daily_spend = 0.0
        self.hourly_spend = 0.0
        self.usage_log: List[UsageRecord] = []
        
        self.reset_time = datetime.now()
        self.hour_reset_time = datetime.now()
        
        self.history_file = history_file or os.path.expanduser("~/.nanobot/cost_history.json")
        
        # 加载历史数据
        self._load_history()
        
        logger.info(f"CostOptimizer初始化: 日预算=${daily_budget}, 时预算=${hourly_budget}")
    
    def _load_history(self):
        """加载历史数据"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                
                # 只加载今天的数据
                today = datetime.now().date()
                for record in data.get("usage_log", []):
                    record_time = datetime.fromisoformat(record["timestamp"])
                    if record_time.date() == today:
                        self.usage_log.append(UsageRecord(**record))
                        self.daily_spend += record["cost"]
                        
                        # 检查是否是这一小时
                        if record_time > datetime.now() - timedelta(hours=1):
                            self.hourly_spend += record["cost"]
                
                logger.info(f"加载历史数据: {len(self.usage_log)}条记录, 今日花费=${self.daily_spend:.4f}")
            except Exception as e:
                logger.error(f"加载历史数据失败: {e}")
    
    def _save_history(self):
        """保存历史数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            data = {
                "daily_budget": self.daily_budget,
                "last_updated": datetime.now().isoformat(),
                "usage_log": [
                    {
                        "model": r.model,
                        "tokens": r.tokens,
                        "cost": r.cost,
                        "timestamp": r.timestamp,
                        "task_id": r.task_id,
                        "success": r.success
                    }
                    for r in self.usage_log
                ]
            }
            
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")
    
    def _check_reset(self):
        """检查是否需要重置"""
        now = datetime.now()
        
        # 每天重置
        if now - self.reset_time > timedelta(days=1):
            logger.info("日预算重置")
            self.daily_spend = 0.0
            self.reset_time = now
            self.usage_log = []  # 清空日志
        
        # 每小时重置
        if now - self.hour_reset_time > timedelta(hours=1):
            logger.info("时预算重置")
            self.hourly_spend = 0.0
            self.hour_reset_time = now
    
    async def check_budget(
        self,
        model: str,
        estimated_tokens: int,
        model_configs: Dict = None
    ) -> bool:
        """检查预算是否充足
        
        Args:
            model: 模型名称
            estimated_tokens: 估算的token数
            model_configs: 模型配置（可选）
        
        Returns:
            是否通过预算检查
        """
        self._check_reset()
        
        # 获取模型成本
        cost_per_1k = self._get_model_cost(model, model_configs)
        estimated_cost = (estimated_tokens / 1000) * cost_per_1k
        
        # 检查日预算
        if self.daily_spend + estimated_cost > self.daily_budget:
            logger.warning(
                f"日预算不足: 当前${self.daily_spend:.4f} + "
                f"预估${estimated_cost:.4f} > 预算${self.daily_budget:.2f}"
            )
            return False
        
        # 检查时预算
        if self.hourly_spend + estimated_cost > self.hourly_budget:
            logger.warning(
                f"时预算不足: 当前${self.hourly_spend:.4f} + "
                f"预估${estimated_cost:.4f} > 预算${self.hourly_budget:.2f}"
            )
            return False
        
        # 检查警告阈值
        usage_percentage = (self.daily_spend + estimated_cost) / self.daily_budget
        if usage_percentage >= self.alert_threshold:
            logger.warning(
                f"预算使用率达到 {usage_percentage*100:.1f}% "
                f"(阈值: {self.alert_threshold*100:.1f}%)"
            )
        
        return True
    
    def _get_model_cost(self, model: str, model_configs: Dict = None) -> float:
        """获取模型成本"""
        # 优先使用传入的配置
        if model_configs and model in model_configs:
            return model_configs[model].get("cost_per_1k_tokens", 0.01)
        
        # 默认成本配置
        default_costs = {
            "glm5-plus": 0.05,
            "glm5-turbo": 0.01,
            "glm5-lite": 0.001,
            "claude-3-opus": 0.15,
            "claude-3-sonnet": 0.03,
            "claude-3-haiku": 0.0025,
            "gpt-4-turbo": 0.01,
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0015,
            "deepseek-chat": 0.001,
            "deepseek-coder": 0.001,
            "qwen-max": 0.12,
            "qwen-plus": 0.004,
            "qwen-turbo": 0.002
        }
        
        return default_costs.get(model, 0.01)
    
    async def record_usage(
        self,
        model: str,
        tokens: int,
        cost: float = None,
        task_id: str = None,
        success: bool = True,
        model_configs: Dict = None
    ):
        """记录使用情况
        
        Args:
            model: 模型名称
            tokens: 使用的token数
            cost: 实际成本（可选，不提供则自动计算）
            task_id: 任务ID
            success: 是否成功
            model_configs: 模型配置
        """
        self._check_reset()
        
        # 计算成本
        if cost is None:
            cost_per_1k = self._get_model_cost(model, model_configs)
            cost = (tokens / 1000) * cost_per_1k
        
        # 记录
        record = UsageRecord(
            model=model,
            tokens=tokens,
            cost=cost,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            success=success
        )
        
        self.usage_log.append(record)
        self.daily_spend += cost
        self.hourly_spend += cost
        
        logger.info(
            f"记录使用: {model}, tokens={tokens}, cost=${cost:.4f}, "
            f"今日总计=${self.daily_spend:.4f}"
        )
        
        # 保存历史
        self._save_history()
    
    def get_budget_status(self) -> BudgetStatus:
        """获取预算状态"""
        self._check_reset()
        
        usage_percentage = self.daily_spend / self.daily_budget if self.daily_budget > 0 else 0
        
        return BudgetStatus(
            daily_budget=self.daily_budget,
            daily_spent=self.daily_spend,
            daily_remaining=max(0, self.daily_budget - self.daily_spend),
            hourly_budget=self.hourly_budget,
            hourly_spent=self.hourly_spend,
            hourly_remaining=max(0, self.hourly_budget - self.hourly_spend),
            usage_percentage=usage_percentage,
            is_over_budget=self.daily_spend > self.daily_budget
        )
    
    def get_daily_stats(self) -> Dict:
        """获取每日统计"""
        self._check_reset()
        
        return {
            "budget": self.daily_budget,
            "spent": self.daily_spend,
            "remaining": self.daily_budget - self.daily_spend,
            "usage_percentage": (self.daily_spend / self.daily_budget * 100) if self.daily_budget > 0 else 0,
            "usage_count": len(self.usage_log),
            "by_model": self._group_by_model(),
            "by_hour": self._group_by_hour()
        }
    
    def _group_by_model(self) -> Dict:
        """按模型分组统计"""
        result = {}
        
        for record in self.usage_log:
            if record.model not in result:
                result[record.model] = {
                    "count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "success_count": 0,
                    "failure_count": 0
                }
            
            result[record.model]["count"] += 1
            result[record.model]["total_cost"] += record.cost
            result[record.model]["total_tokens"] += record.tokens
            
            if record.success:
                result[record.model]["success_count"] += 1
            else:
                result[record.model]["failure_count"] += 1
        
        return result
    
    def _group_by_hour(self) -> Dict:
        """按小时分组统计"""
        result = {}
        
        for record in self.usage_log:
            hour = datetime.fromisoformat(record.timestamp).hour
            hour_key = f"{hour:02d}:00"
            
            if hour_key not in result:
                result[hour_key] = {"count": 0, "total_cost": 0.0, "total_tokens": 0}
            
            result[hour_key]["count"] += 1
            result[hour_key]["total_cost"] += record.cost
            result[hour_key]["total_tokens"] += record.tokens
        
        return result
    
    async def optimize_model_selection(
        self,
        task: Dict,
        selector,
        model_configs: Dict = None
    ) -> Tuple[str, str]:
        """优化模型选择（考虑成本）
        
        Args:
            task: 任务描述
            selector: 模型选择器
            model_configs: 模型配置
        
        Returns:
            (选择的模型, 选择理由)
        """
        self._check_reset()
        
        # 1. 获取推荐模型
        recommended = await selector.select_best_model(task)
        
        # 2. 估算成本
        estimated_tokens = selector.estimate_tokens(task)
        
        # 3. 检查预算
        if await self.check_budget(recommended, estimated_tokens, model_configs):
            cost_per_1k = self._get_model_cost(recommended, model_configs)
            estimated_cost = (estimated_tokens / 1000) * cost_per_1k
            
            logger.info(f"推荐模型 {recommended} 预算充足，预估成本=${estimated_cost:.4f}")
            return recommended, "最佳性能匹配"
        
        # 4. 如果超预算，选择最便宜的可用模型
        logger.warning(f"推荐模型 {recommended} 超预算，寻找替代方案")
        
        available = selector.available_models
        if not available:
            return None, "没有可用模型"
        
        # 按成本排序
        models_by_cost = sorted(
            available,
            key=lambda m: self._get_model_cost(m, model_configs)
        )
        
        # 找到第一个在预算内的模型
        for model in models_by_cost:
            if await self.check_budget(model, estimated_tokens, model_configs):
                cost_per_1k = self._get_model_cost(model, model_configs)
                estimated_cost = (estimated_tokens / 1000) * cost_per_1k
                
                logger.info(f"选择低成本模型 {model}, 预估成本=${estimated_cost:.4f}")
                return model, f"成本优化选择（节省预算）"
        
        # 5. 如果所有模型都超预算
        logger.error("所有模型都超出预算")
        return None, "预算不足，无法执行任务"
    
    def get_cost_saving_suggestions(self) -> List[str]:
        """获取成本节约建议"""
        suggestions = []
        stats = self.get_daily_stats()
        
        # 检查使用频率
        if stats["usage_count"] > 50:
            suggestions.append(
                f"今日调用次数较多({stats['usage_count']}次)，"
                "考虑批量处理或使用缓存"
            )
        
        # 检查模型使用分布
        by_model = stats["by_model"]
        if by_model:
            # 找到最贵的模型
            expensive_models = [
                (model, data["total_cost"])
                for model, data in by_model.items()
                if self._get_model_cost(model) > 0.05
            ]
            
            if expensive_models:
                expensive_models.sort(key=lambda x: x[1], reverse=True)
                model, cost = expensive_models[0]
                suggestions.append(
                    f"模型 {model} 花费较高(${cost:.2f})，"
                    "考虑使用GLM5-Turbo等低成本替代方案"
                )
        
        # 检查失败率
        total_failures = sum(
            data["failure_count"]
            for data in by_model.values()
        )
        
        if total_failures > 5:
            suggestions.append(
                f"有{total_failures}次失败调用，"
                "建议检查提示词质量或增加重试机制"
            )
        
        return suggestions
    
    def set_budget(self, daily: float = None, hourly: float = None):
        """设置预算"""
        if daily is not None:
            self.daily_budget = daily
            logger.info(f"日预算设置为: ${daily:.2f}")
        
        if hourly is not None:
            self.hourly_budget = hourly
            logger.info(f"时预算设置为: ${hourly:.2f}")
    
    def reset_budget(self):
        """重置预算计数"""
        self.daily_spend = 0.0
        self.hourly_spend = 0.0
        self.reset_time = datetime.now()
        self.hour_reset_time = datetime.now()
        logger.info("预算计数已重置")


class BudgetAlert:
    """预算告警"""
    
    def __init__(
        self,
        optimizer: CostOptimizer,
        webhook_url: str = None,
        email: str = None
    ):
        self.optimizer = optimizer
        self.webhook_url = webhook_url
        self.email = email
        self.alert_sent = False
    
    async def check_and_alert(self):
        """检查并发送告警"""
        status = self.optimizer.get_budget_status()
        
        # 检查是否需要告警
        if status.usage_percentage >= self.optimizer.alert_threshold and not self.alert_sent:
            await self._send_alert(status)
            self.alert_sent = True
        
        # 每天重置告警状态
        if status.usage_percentage < 0.1:
            self.alert_sent = False
    
    async def _send_alert(self, status: BudgetStatus):
        """发送告警"""
        message = (
            f"⚠️ 预算告警\n\n"
            f"日预算: ${status.daily_budget:.2f}\n"
            f"已使用: ${status.daily_spent:.2f} ({status.usage_percentage*100:.1f}%)\n"
            f"剩余: ${status.daily_remaining:.2f}\n\n"
            f"请关注成本控制！"
        )
        
        logger.warning(message)
        
        # 发送webhook
        if self.webhook_url:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        self.webhook_url,
                        json={"text": message}
                    )
                    logger.info("预算告警已发送到webhook")
            except Exception as e:
                logger.error(f"发送webhook失败: {e}")
        
        # TODO: 发送邮件


if __name__ == "__main__":
    # 测试代码
    import asyncio
    
    async def test():
        optimizer = CostOptimizer(daily_budget=1.0, hourly_budget=0.2)
        
        print("=== 测试1: 预算检查 ===")
        # 小额应该通过
        result1 = await optimizer.check_budget("glm5-turbo", 1000)
        print(f"GLM5-Turbo 1000 tokens: {result1}")
        
        # 大额应该拒绝
        result2 = await optimizer.check_budget("claude-3-opus", 10000)
        print(f"Claude-3-Opus 10000 tokens: {result2}")
        
        print("\n=== 测试2: 记录使用 ===")
        await optimizer.record_usage("glm5-turbo", 500, task_id="test-001")
        await optimizer.record_usage("glm5-turbo", 800, task_id="test-002")
        await optimizer.record_usage("gpt-4-turbo", 600, task_id="test-003")
        
        print("\n=== 测试3: 获取统计 ===")
        stats = optimizer.get_daily_stats()
        print(f"预算: ${stats['budget']:.2f}")
        print(f"已使用: ${stats['spent']:.4f}")
        print(f"使用率: {stats['usage_percentage']:.1f}%")
        print(f"调用次数: {stats['usage_count']}")
        print(f"按模型分组: {stats['by_model']}")
        
        print("\n=== 测试4: 预算状态 ===")
        status = optimizer.get_budget_status()
        print(f"日预算: ${status.daily_budget:.2f}")
        print(f"日花费: ${status.daily_spent:.4f}")
        print(f"日剩余: ${status.daily_remaining:.4f}")
        print(f"时预算: ${status.hourly_budget:.2f}")
        print(f"时花费: ${status.hourly_spend:.4f}")
        
        print("\n=== 测试5: 成本建议 ===")
        suggestions = optimizer.get_cost_saving_suggestions()
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    
    asyncio.run(test())
