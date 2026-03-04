# Agent系统 Phase 3 - 多模型支持使用文档

## 概述

Phase 3为Nanobot AI Agent系统实现了完整的多模型支持和智能选择功能，包括：

- **多模型适配器**：统一接口支持GLM5、Claude、GPT-4、DeepSeek、通义千问等多种模型
- **智能模型选择器**：根据任务特征自动选择最佳模型
- **成本优化器**：预算管理和成本优化，确保在预算内获得最佳性能

## 快速开始

### 1. 基本配置

创建配置文件 `~/.nanobot/config.json`：

```json
{
  "zhipu_api_key": "your-zhipu-api-key",
  "anthropic_api_key": "your-anthropic-api-key",
  "openai_api_key": "your-openai-api-key",
  "deepseek_api_key": "your-deepseek-api-key",
  "qwen_api_key": "your-qwen-api-key"
}
```

或者使用环境变量：

```bash
export ZHIPU_API_KEY="your-zhipu-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. 快速调用

```python
from model_adapter import quick_call
import asyncio

async def main():
    # 自动选择最佳模型
    result = await quick_call("你好，请介绍一下你自己")
    
    if result["success"]:
        print(result["content"])
    else:
        print(f"错误: {result['error']}")

asyncio.run(main())
```

### 3. 指定模型调用

```python
from model_adapter import ModelAdapter
import asyncio

async def main():
    adapter = ModelAdapter()
    
    # 查看可用模型
    print("可用模型:", adapter.get_available_models())
    
    # 调用指定模型
    result = await adapter.call_model(
        model="glm5-turbo",
        prompt="用Python写一个快速排序算法",
        temperature=0.7,
        max_tokens=1000
    )
    
    print(result["content"])

asyncio.run(main())
```

## 模型适配器 (ModelAdapter)

### 功能特性

- ✅ 支持15+种模型
- ✅ 自动重试机制（3次）
- ✅ 超时控制（30秒）
- ✅ 详细错误日志
- ✅ 统计信息追踪

### 支持的模型

#### GLM5系列（智谱AI）
- `glm5-plus`: 高质量，适合复杂任务
- `glm5-turbo`: 平衡性能，性价比高
- `glm5-lite`: 低成本，快速响应

#### Claude系列（Anthropic）
- `claude-3-opus`: 顶级质量，适合创意和分析
- `claude-3-sonnet`: 平衡性能
- `claude-3-haiku`: 快速响应

#### GPT系列（OpenAI）
- `gpt-4-turbo`: 高质量，快速
- `gpt-4`: 深度推理
- `gpt-3.5-turbo`: 低成本

#### DeepSeek系列
- `deepseek-chat`: 中文理解强，低成本
- `deepseek-coder`: 代码专用

#### 通义千问系列（阿里云）
- `qwen-max`: 高质量中文支持
- `qwen-plus`: 平衡性能
- `qwen-turbo`: 快速响应

### API参考

#### 初始化

```python
adapter = ModelAdapter(config_path="path/to/config.json")
```

#### 调用模型

```python
result = await adapter.call_model(
    model="glm5-turbo",
    prompt="你的提示词",
    temperature=0.7,          # 温度（0-1）
    max_tokens=2000,          # 最大token数
    system_prompt="系统提示",  # 可选
    messages=[...]            # 可选，对话历史
)
```

#### 返回格式

```python
{
    "success": True,
    "content": "生成的文本",
    "usage": {
        "total_tokens": 100,
        "prompt_tokens": 50,
        "completion_tokens": 50
    },
    "model": "glm5-turbo",
    "provider": "zhipu"
}
```

#### 其他方法

```python
# 获取可用模型
models = adapter.get_available_models()

# 获取推荐模型（优先GLM5）
preferred = adapter.get_preferred_model()

# 计算token数
tokens = await adapter.count_tokens("glm5-turbo", "文本")

# 获取统计信息
stats = adapter.get_model_stats("glm5-turbo")
all_stats = adapter.get_all_stats()

# 批量调用
results = await adapter.batch_call([
    {"model": "glm5-turbo", "prompt": "任务1"},
    {"model": "gpt-4", "prompt": "任务2"}
], max_concurrent=5)
```

## 智能模型选择器 (ModelSelector)

### 功能特性

- ✅ 自动分析任务复杂度
- ✅ 识别任务类型
- ✅ 语言检测
- ✅ 多维度评分
- ✅ 约束条件支持

### 使用示例

#### 基本选择

```python
from model_adapter import ModelAdapter
from model_selector import ModelSelector
import asyncio

async def main():
    adapter = ModelAdapter()
    selector = ModelSelector(adapter)
    
    # 定义任务
    task = {
        "description": "设计一个微服务架构系统",
        "type": "architecture",
        "complexity": "high"
    }
    
    # 自动选择最佳模型
    model = await selector.select_best_model(task)
    print(f"推荐模型: {model}")

asyncio.run(main())
```

#### 带约束选择

```python
task = {
    "description": "快速修复bug",
    "priority": "high"
}

constraints = {
    "max_cost": 0.01,           # 最大成本（$/1k tokens）
    "requires_fast": True,       # 需要快速响应
    "requires_high_quality": False,
    "exclude_models": ["gpt-4"]  # 排除特定模型
}

model = await selector.select_best_model(task, constraints)
```

#### 获取推荐列表

```python
recommendations = await selector.get_model_recommendations(task, top_n=3)

for model, score, reason in recommendations:
    print(f"{model}: {score:.2f} - {reason}")
```

### 任务特征分析

#### 复杂度级别

- `low`: 简单任务（快速修复、简单查询）
- `medium`: 中等任务（功能开发、重构）
- `high`: 复杂任务（架构设计、深度分析）
- `very_high`: 超复杂任务（系统重构、复杂推理）

#### 任务类型

- `feature`: 功能开发
- `bug_fix`: Bug修复
- `refactor`: 代码重构
- `architecture`: 架构设计
- `analysis`: 分析任务
- `translation`: 翻译
- `documentation`: 文档编写
- `code_review`: 代码审查
- `test`: 测试
- `general`: 通用任务

### 评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 复杂度匹配 | 35% | 模型质量与任务复杂度的匹配度 |
| 任务类型匹配 | 25% | 模型专长与任务类型的匹配度 |
| 速度需求 | 20% | 响应速度是否满足需求 |
| 成本优化 | 15% | 成本效益 |
| 语言支持 | 5% | 是否支持所需语言 |

## 成本优化器 (CostOptimizer)

### 功能特性

- ✅ 日预算和时预算管理
- ✅ 自动成本计算
- ✅ 使用历史记录
- ✅ 预算告警
- ✅ 成本优化建议

### 使用示例

#### 基本使用

```python
from cost_optimizer import CostOptimizer
import asyncio

async def main():
    # 初始化（日预算$10，时预算$1）
    optimizer = CostOptimizer(
        daily_budget=10.0,
        hourly_budget=1.0,
        alert_threshold=0.8  # 80%时告警
    )
    
    # 检查预算
    can_afford = await optimizer.check_budget("glm5-turbo", 1000)
    print(f"预算充足: {can_afford}")
    
    # 记录使用
    await optimizer.record_usage(
        model="glm5-turbo",
        tokens=500,
        task_id="task-001"
    )
    
    # 查看统计
    stats = optimizer.get_daily_stats()
    print(f"今日花费: ${stats['spent']:.4f}")

asyncio.run(main())
```

#### 优化模型选择

```python
from model_adapter import ModelAdapter
from model_selector import ModelSelector
from cost_optimizer import CostOptimizer

async def main():
    adapter = ModelAdapter()
    selector = ModelSelector(adapter)
    optimizer = CostOptimizer(daily_budget=5.0)
    
    task = {
        "description": "设计系统架构",
        "complexity": "high"
    }
    
    # 智能选择（考虑成本）
    model, reason = await optimizer.optimize_model_selection(task, selector)
    print(f"选择模型: {model}")
    print(f"理由: {reason}")

asyncio.run(main())
```

#### 预算告警

```python
from cost_optimizer import BudgetAlert

async def main():
    optimizer = CostOptimizer(daily_budget=10.0)
    alert = BudgetAlert(
        optimizer,
        webhook_url="https://your-webhook-url"  # 可选
    )
    
    # 检查并发送告警
    await alert.check_and_alert()

asyncio.run(main())
```

### API参考

#### 初始化

```python
optimizer = CostOptimizer(
    daily_budget=10.0,          # 日预算
    hourly_budget=1.0,          # 时预算
    alert_threshold=0.8,        # 告警阈值
    history_file="path/to/file" # 历史文件路径（可选）
)
```

#### 主要方法

```python
# 检查预算
can_afford = await optimizer.check_budget(model, estimated_tokens)

# 记录使用
await optimizer.record_usage(
    model="glm5-turbo",
    tokens=500,
    cost=0.01,              # 可选，不提供则自动计算
    task_id="task-001",     # 可选
    success=True            # 可选
)

# 获取预算状态
status = optimizer.get_budget_status()

# 获取统计信息
stats = optimizer.get_daily_stats()

# 获取成本建议
suggestions = optimizer.get_cost_saving_suggestions()

# 设置预算
optimizer.set_budget(daily=20.0, hourly=2.0)

# 重置预算计数
optimizer.reset_budget()
```

## 完整示例

### 示例1：智能代码助手

```python
from model_adapter import ModelAdapter
from model_selector import ModelSelector
from cost_optimizer import CostOptimizer
import asyncio

class CodeAssistant:
    def __init__(self):
        self.adapter = ModelAdapter()
        self.selector = ModelSelector(self.adapter)
        self.optimizer = CostOptimizer(daily_budget=10.0)
    
    async def help(self, task_description: str):
        # 1. 分析任务
        task = {
            "description": task_description,
            "type": "feature" if "实现" in task_description else "bug_fix"
        }
        
        # 2. 选择模型（考虑成本）
        model, reason = await self.optimizer.optimize_model_selection(
            task, self.selector
        )
        
        if not model:
            return {"success": False, "error": "预算不足"}
        
        # 3. 调用模型
        result = await self.adapter.call_model(
            model=model,
            prompt=task_description,
            temperature=0.7
        )
        
        # 4. 记录使用
        if result["success"]:
            usage = result.get("usage", {})
            await self.optimizer.record_usage(
                model=model,
                tokens=usage.get("total_tokens", 0)
            )
        
        return result

async def main():
    assistant = CodeAssistant()
    
    result = await assistant.help(
        "实现一个Python函数，计算斐波那契数列的第n项"
    )
    
    if result["success"]:
        print(result["content"])
    else:
        print(f"错误: {result['error']}")

asyncio.run(main())
```

### 示例2：批量文档翻译

```python
async def batch_translate(documents: list):
    adapter = ModelAdapter()
    selector = ModelSelector(adapter)
    
    results = []
    
    for doc in documents:
        # 选择翻译模型
        task = {
            "description": f"翻译文档: {doc[:50]}",
            "type": "translation",
            "complexity": "low"
        }
        
        constraints = {
            "requires_fast": True,
            "max_cost": 0.005
        }
        
        model = await selector.select_best_model(task, constraints)
        
        # 调用模型
        result = await adapter.call_model(
            model=model,
            prompt=f"翻译以下文档为英文:\n\n{doc}"
        )
        
        results.append(result)
    
    return results
```

### 示例3：成本监控仪表板

```python
from cost_optimizer import CostOptimizer
import asyncio

async def cost_dashboard():
    optimizer = CostOptimizer(daily_budget=50.0)
    
    while True:
        # 获取状态
        status = optimizer.get_budget_status()
        stats = optimizer.get_daily_stats()
        
        # 清屏
        print("\033[2J\033[H")
        
        # 显示信息
        print("=" * 50)
        print("成本监控仪表板")
        print("=" * 50)
        print(f"\n日预算: ${status.daily_budget:.2f}")
        print(f"已使用: ${status.daily_spent:.4f} ({status.usage_percentage*100:.1f}%)")
        print(f"剩余: ${status.daily_remaining:.4f}")
        print(f"时预算: ${status.hourly_budget:.2f}")
        print(f"时使用: ${status.hourly_spend:.4f}")
        
        print(f"\n调用次数: {stats['usage_count']}")
        
        print("\n按模型统计:")
        for model, data in stats['by_model'].items():
            print(f"  {model}: {data['count']}次, ${data['total_cost']:.4f}")
        
        # 成本建议
        suggestions = optimizer.get_cost_saving_suggestions()
        if suggestions:
            print("\n优化建议:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
        
        # 等待10秒
        await asyncio.sleep(10)

asyncio.run(cost_dashboard())
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest test_multi_model.py -v

# 运行特定测试
pytest test_multi_model.py::TestModelAdapter -v
pytest test_multi_model.py::TestModelSelector -v
pytest test_multi_model.py::TestCostOptimizer -v

# 生成覆盖率报告
pytest test_multi_model.py --cov=. --cov-report=html
```

### 测试覆盖率目标

- ✅ 模型适配器: > 85%
- ✅ 智能选择器: > 85%
- ✅ 成本优化器: > 85%
- ✅ 集成测试: > 80%

## 最佳实践

### 1. 模型选择

- **优先使用GLM5**: 成本低，中文支持好
- **复杂任务选高质量模型**: 架构设计、深度分析
- **简单任务选快速模型**: 快速修复、简单查询
- **考虑成本效益**: 不总是选最好的，选最合适的

### 2. 成本控制

- **设置合理预算**: 根据实际需求设置日/时预算
- **监控使用情况**: 定期查看统计信息
- **使用告警**: 在达到阈值时及时通知
- **优化提示词**: 减少不必要的token消耗

### 3. 错误处理

- **检查success字段**: 始终检查返回结果
- **实现重试逻辑**: 对于临时错误进行重试
- **记录错误日志**: 便于问题排查
- **提供降级方案**: 当首选模型失败时有备选

### 4. 性能优化

- **使用批量调用**: 减少API调用次数
- **缓存结果**: 避免重复调用
- **并发控制**: 使用semaphore限制并发数
- **超时设置**: 避免长时间等待

## 故障排查

### 常见问题

#### 1. 模型不可用

**症状**: `模型 xxx 不可用或未配置`

**解决方案**:
- 检查API密钥是否正确配置
- 确认模型名称拼写正确
- 查看可用模型列表

#### 2. 预算不足

**症状**: `预算不足，无法执行任务`

**解决方案**:
- 增加预算: `optimizer.set_budget(daily=20.0)`
- 选择低成本模型
- 优化提示词减少token

#### 3. 请求超时

**症状**: `请求超时，请稍后重试`

**解决方案**:
- 检查网络连接
- 增加超时时间: `adapter.timeout = 60`
- 使用重试机制

#### 4. API错误

**症状**: `API错误 401/403/429`

**解决方案**:
- 401/403: 检查API密钥
- 429: 降低请求频率
- 查看API文档了解限制

## 性能指标

### 模型响应时间

| 模型 | 平均响应时间 | 相对速度 |
|------|-------------|----------|
| glm5-lite | 1-2秒 | ⚡⚡⚡ |
| glm5-turbo | 2-3秒 | ⚡⚡ |
| glm5-plus | 3-5秒 | ⚡ |
| claude-3-haiku | 1-2秒 | ⚡⚡⚡ |
| claude-3-sonnet | 3-5秒 | ⚡ |
| gpt-3.5-turbo | 1-2秒 | ⚡⚡⚡ |
| gpt-4-turbo | 2-4秒 | ⚡⚡ |

### 成本对比

| 模型 | 成本（$/1k tokens） | 相对成本 |
|------|-------------------|----------|
| glm5-lite | $0.001 | 💰 |
| glm5-turbo | $0.01 | 💰💰 |
| glm5-plus | $0.05 | 💰💰💰 |
| claude-3-opus | $0.15 | 💰💰💰💰💰 |
| gpt-4-turbo | $0.01 | 💰💰 |

## 更新日志

### v1.0.0 (2024-01-XX)

- ✅ 实现15+种模型支持
- ✅ 智能模型选择器
- ✅ 成本优化器
- ✅ 完整测试套件
- ✅ 详细文档

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

## 许可证

MIT License
