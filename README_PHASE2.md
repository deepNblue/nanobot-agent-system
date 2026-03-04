# Agent System Skill - Phase 2: Code Review & CI/CD Integration

> **版本**: 2.0.0  
> **更新日期**: 2026-03-04  
> **架构**: nanobot (编排+执行) → GLM5 (模型) + GitHub Actions (CI/CD)

---

## 📋 Phase 2 新功能

### 1. 三层Code Review系统

自动化代码审查，结合LLM、静态分析和测试覆盖率：

#### 第一层：GLM5-Plus自动审查
- **安全检查**: SQL注入、XSS、硬编码密钥等
- **性能检查**: 循环优化、内存泄漏等
- **代码质量**: 命名规范、复杂度、TODO标记
- **深度分析**: 使用GLM5 API进行语义分析

#### 第二层：静态分析
- **Flake8**: Python代码风格检查
- **MyPy**: 类型检查
- **Black/isort**: 代码格式检查

#### 第三层：测试覆盖率
- **Pytest**: 单元测试执行
- **Coverage**: 代码覆盖率统计
- **新代码覆盖**: 新增代码的覆盖率检查

#### 评分标准
- **90-100**: 优秀 ⭐⭐⭐⭐⭐ (自动批准)
- **80-89**: 良好 ⭐⭐⭐⭐ (建议通过)
- **70-79**: 一般 ⭐⭐⭐ (需要改进)
- **<70**: 差 ⭐⭐ (建议拒绝)

### 2. CI/CD集成

完整的GitHub Actions集成：

#### 功能
- ✅ CI状态检查
- ✅ 失败日志获取
- ✅ 智能失败分析（GLM5）
- ✅ 自动重试（最多3次）
- ✅ 状态通知

#### 自动化流程
```
代码提交 → Code Review → CI检查 → 失败分析 → 自动重试 → 合并
```

### 3. 增强编排器

新增方法：

```python
# 代码审查
await orchestrator.review_code(task_id)

# CI状态检查
await orchestrator.check_ci(task_id)

# 处理CI失败
await orchestrator.handle_ci_failure(task_id)

# 自动合并
await orchestrator.auto_merge_on_success(task_id, pr_number)

# 完整生命周期
await orchestrator.full_task_lifecycle(task_id, description)
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
# GLM5配置（用于深度分析）
export GLM5_API_KEY="your-api-key"
export GLM5_BASE_URL="https://open.bigmodel.cn/api/paas/v3"
export GLM5_MODEL="glm-4-plus"

# GitHub配置
export GITHUB_TOKEN="your-github-token"
```

### 使用示例

#### 1. Code Review

```python
from code_reviewer import get_code_reviewer

reviewer = get_code_reviewer()

# 审查Pull Request
result = await reviewer.review_pull_request(pr_number=42)

print(f"评分: {result['score']}/100")
print(f"是否批准: {result['approved']}")
print(result['summary'])
```

#### 2. CI/CD集成

```python
from cicd_integration import get_cicd_integration

cicd = get_cicd_integration()

# 检查CI状态
status = await cicd.check_ci_status(branch="feature-branch")

if status['is_failed']:
    # 分析失败原因
    analysis = await cicd.analyze_ci_failure(status['run_id'])
    print(f"失败原因: {analysis['failure_reason']}")
    print(f"建议修复: {analysis['suggested_fix']}")
    
    # 自动重试
    retry_result = await cicd.trigger_ci_retry(status['run_id'])
```

#### 3. 完整工作流

```python
from nanobot_scheduler_enhanced import get_orchestrator_enhanced

orchestrator = get_orchestrator_enhanced()

# 启用自动化功能
orchestrator.auto_review_enabled = True
orchestrator.auto_ci_check_enabled = True
orchestrator.auto_retry_ci_enabled = True
orchestrator.auto_merge_enabled = False  # 谨慎启用

# 运行完整生命周期
result = await orchestrator.full_task_lifecycle(
    task_id="task_001",
    description="实现用户认证功能",
    agent_type="codex"
)

if result['success']:
    print("任务完成！")
else:
    print(f"任务失败: {result.get('error')}")
```

---

## 📊 GitHub Actions工作流

### 工作流文件

`.github/workflows/agent-ci.yml` 包含以下jobs：

1. **lint**: 代码风格检查（flake8, black, isort, mypy）
2. **test**: 单元测试（pytest + coverage）
3. **security**: 安全检查（bandit, safety）
4. **code-review**: 自动化Code Review
5. **build**: 构建检查
6. **notify**: 状态通知

### 触发条件

- **Pull Request**: main, develop分支
- **Push**: main, develop分支

### 查看CI状态

```bash
# 使用gh CLI
gh run list --branch your-branch

# 查看运行详情
gh run view <run-id>

# 查看失败日志
gh run view <run-id> --log-failed
```

---

## 🧪 测试

### 运行测试

```bash
python test_code_review.py
```

### 测试覆盖

- ✅ 安全检查逻辑
- ✅ 性能检查逻辑
- ✅ 代码质量检查
- ✅ 评分计算
- ✅ 评论生成
- ✅ CI状态检查
- ✅ 失败分析
- ✅ 重试逻辑
- ✅ 通知功能
- ✅ 完整工作流

### 测试目标

- 测试通过率 > 90%
- 代码覆盖率 > 80%

---

## 📁 文件结构

```
agent-system/
├── code_reviewer.py          # 三层Code Review系统
├── cicd_integration.py        # CI/CD集成模块
├── nanobot_scheduler_enhanced.py  # 增强版编排器
├── task_monitor.py            # 任务监控器（增强版）
├── test_code_review.py        # 测试脚本
├── .github/
│   └── workflows/
│       └── agent-ci.yml       # GitHub Actions工作流
├── README_PHASE2.md           # 本文档
└── requirements.txt           # 依赖列表
```

---

## ⚙️ 配置选项

### Code Review配置

```python
reviewer = CodeReviewer()

# 评分权重
reviewer.weights = {
    "llm": 0.5,      # LLM审查权重
    "static": 0.3,   # 静态分析权重
    "test": 0.2      # 测试覆盖率权重
}
```

### CI/CD配置

```python
cicd = CICDIntegration()

# 重试配置
cicd.max_retry_count = 3        # 最大重试次数
cicd.check_interval = 600       # 检查间隔（秒）
cicd.retry_cooldown = 300       # 重试冷却时间（秒）
```

### 编排器配置

```python
orchestrator = get_orchestrator_enhanced()

# 自动化开关
orchestrator.auto_review_enabled = True       # 自动Code Review
orchestrator.auto_ci_check_enabled = True     # 自动CI检查
orchestrator.auto_retry_ci_enabled = True     # 自动重试CI
orchestrator.auto_merge_enabled = False       # 自动合并（谨慎启用）
```

---

## 🔍 监控和日志

### 生成报告

```python
# 任务监控报告
report = orchestrator.generate_status_report()
print(report)

# CI/CD报告
ci_report = cicd.generate_ci_report(branch="feature-branch")
print(ci_report)
```

### 持续监控

```python
# 启动持续监控（5分钟检查一次，最长2小时）
result = await orchestrator.task_monitor.continuous_monitoring(
    interval=300,
    max_duration=7200
)

print(f"执行了 {result['checks_performed']} 次检查")
```

---

## 🎯 最佳实践

### 1. 代码审查

- 定期检查审查结果，优化审查规则
- 对高优先级问题（安全、性能）及时响应
- 保持测试覆盖率在80%以上

### 2. CI/CD

- 不要过度依赖自动重试，优先修复根本问题
- 配置合理的超时和重试次数
- 监控CI失败率，及时优化

### 3. 自动化

- 先在测试环境验证自动化流程
- 谨慎启用自动合并功能
- 保留人工审核的关键节点

---

## 🐛 故障排查

### Code Review失败

```bash
# 检查GLM5 API配置
echo $GLM5_API_KEY

# 测试API连接
python -c "
from code_reviewer import get_code_reviewer
import asyncio
reviewer = get_code_reviewer()
result = asyncio.run(reviewer._deep_analysis_with_glm5('test code'))
print(result)
"
```

### CI检查失败

```bash
# 检查gh CLI认证
gh auth status

# 测试CI状态检查
gh run list --limit 5

# 查看失败日志
gh run view <run-id> --log-failed
```

### 任务监控异常

```bash
# 查看任务文件
ls ~/.nanobot/workspace/agent_tasks/

# 检查任务状态
cat ~/.nanobot/workspace/agent_tasks/<task-id>.json
```

---

## 📈 性能优化

### 1. 缓存CI状态

```python
# CI状态会自动缓存10分钟
# 避免频繁调用GitHub API
```

### 2. 并行检查

```python
# 并行执行Code Review和CI检查
import asyncio

review_task = orchestrator.review_code(task_id)
ci_task = orchestrator.check_ci(task_id)

results = await asyncio.gather(review_task, ci_task)
```

### 3. 批量操作

```python
# 批量检查多个任务的CI状态
tasks = await orchestrator.list_all_tasks()
running_tasks = [t for t in tasks if t['status'] == 'running']

for task in running_tasks:
    await orchestrator.check_ci(task['task_id'])
```

---

## 🔐 安全考虑

### 1. API密钥保护

- 不要在代码中硬编码API密钥
- 使用环境变量或密钥管理服务
- 定期轮换密钥

### 2. 权限控制

- 使用最小权限原则配置GitHub Token
- 限制自动合并的分支
- 审查自动执行的命令

### 3. 日志安全

- 不要在日志中输出敏感信息
- 定期清理旧的日志文件
- 使用安全的日志存储

---

## 📝 更新日志

### v2.0.0 (2026-03-04) - Phase 2

**新增功能**
- ✅ 三层Code Review系统
- ✅ CI/CD集成模块
- ✅ 智能失败分析
- ✅ 自动重试机制
- ✅ GitHub Actions工作流
- ✅ 完整测试套件

**改进**
- ✅ 增强任务监控
- ✅ 自动化工作流
- ✅ 详细报告生成

**Bug修复**
- 无

---

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

---

## 📞 支持

- **文档**: 本README和代码注释
- **问题**: 创建GitHub Issue
- **讨论**: GitHub Discussions

---

**下一步计划 (Phase 3)**:
1. 多模型支持（Claude, GPT-4）
2. 分布式任务执行
3. 可视化Dashboard
4. 性能分析和优化建议
5. 自动化测试生成

---

*Happy Coding! 🚀*
