# PR自动管理使用指南

> **版本**: v3.0.0  
> **更新时间**: 2026-03-04  
> **适用范围**: Nanobot AI Agent系统Phase 3

---

## 📋 目录

1. [功能概述](#功能概述)
2. [快速开始](#快速开始)
3. [配置说明](#配置说明)
4. [API参考](#api参考)
5. [使用示例](#使用示例)
6. [最佳实践](#最佳实践)
7. [故障排查](#故障排查)

---

## 功能概述

PR自动管理模块为Nanobot AI Agent系统提供完整的Pull Request自动化能力。

### 核心功能

#### 1. 自动创建PR

- ✅ 任务完成后自动创建PR
- ✅ 自动生成PR标题和描述
- ✅ 自动添加标签
- ✅ 检查前置条件（任务完成、Code Review、CI）

#### 2. PR状态监控

- ✅ 实时监控PR状态
- ✅ 检查Review状态
- ✅ 检查CI状态
- ✅ 检查合并冲突
- ✅ 判断是否可以合并

#### 3. 自动合并PR

- ✅ 满足条件时自动合并
- ✅ 支持多种合并方式（squash/merge/rebase）
- ✅ 自动删除分支
- ✅ 更新任务状态

#### 4. 其他功能

- ✅ PR列表查询
- ✅ PR关闭/重新打开
- ✅ 请求Review
- ✅ 生成PR报告

---

## 快速开始

### 前置条件

1. **安装GitHub CLI**
   ```bash
   # macOS
   brew install gh
   
   # Linux
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update
   sudo apt install gh
   ```

2. **认证GitHub CLI**
   ```bash
   gh auth login
   ```

3. **验证认证**
   ```bash
   gh auth status
   ```

### 基本使用

#### 方式1：使用编排器（推荐）

```python
from nanobot_scheduler_enhanced import get_orchestrator_enhanced

# 获取编排器
orchestrator = get_orchestrator_enhanced()

# 完成任务并自动创建PR
result = await orchestrator.complete_task_with_pr(
    task_id="task_20260304120000",
    cleanup=False  # 不清理worktree
)

print(f"PR创建结果: {result}")
```

#### 方式2：直接使用PR管理器

```python
from pr_manager import get_pr_manager

# 获取PR管理器
pr_manager = get_pr_manager()

# 自动创建PR
result = await pr_manager.auto_create_pr("task_20260304120000")

if result["success"]:
    print(f"PR #{result['pr_number']} 创建成功")
    print(f"URL: {result['url']}")
else:
    print(f"创建失败: {result['error']}")
```

---

## 配置说明

### 配置项

```python
config = {
    # 是否启用自动合并
    "auto_merge": False,  # 默认: False
    
    # 合并方式
    "merge_method": "squash",  # 选项: squash, merge, rebase
    
    # 是否需要Code Review
    "require_review": True,  # 默认: True
    
    # 是否需要CI通过
    "require_ci": True,  # 默认: True
    
    # 最低Review分数
    "min_review_score": 80  # 默认: 80
}
```

### 合并方式对比

| 方式 | 说明 | 适用场景 | 提交历史 |
|------|------|----------|----------|
| `squash` | 压缩为单个提交 | Feature分支 | ✅ 简洁 |
| `merge` | 保留所有提交 | Release分支 | ✅ 完整 |
| `rebase` | 线性历史 | 长期分支 | ✅ 线性 |

### 环境变量

```bash
# GLM5 API配置（用于生成PR描述）
export GLM5_API_KEY="your_api_key"
export GLM5_BASE_URL="https://open.bigmodel.cn/api/paas/v3"
export GLM5_MODEL="glm-4-plus"
```

---

## API参考

### PRManager类

#### 初始化

```python
from pr_manager import PRManager

pr_manager = PRManager(
    config={
        "auto_merge": False,
        "merge_method": "squash"
    },
    repo_path="/path/to/repo"
)
```

#### 主要方法

##### 1. auto_create_pr()

自动创建PR。

```python
result = await pr_manager.auto_create_pr(task_id)
```

**参数**:
- `task_id` (str): 任务ID

**返回**:
```python
{
    "success": True,
    "pr_number": 123,
    "url": "https://github.com/owner/repo/pull/123",
    "title": "[Agent] Feature: 实现用户头像上传"
}
```

**前置条件**:
1. 任务状态为 `completed`
2. Code Review分数 >= `min_review_score`
3. CI已通过（如果 `require_ci=True`）
4. 分支有变更

##### 2. monitor_pr_status()

监控PR状态。

```python
status = await pr_manager.monitor_pr_status(pr_number)
```

**参数**:
- `pr_number` (int): PR编号

**返回**:
```python
{
    "success": True,
    "pr_number": 123,
    "state": "OPEN",
    "review": {
        "approved": True,
        "decision": "APPROVED"
    },
    "ci": {
        "success": True,
        "total": 5,
        "completed": 5
    },
    "mergeable": True,
    "ready_to_merge": True
}
```

##### 3. auto_merge_pr()

自动合并PR。

```python
result = await pr_manager.auto_merge_pr(pr_number)
```

**参数**:
- `pr_number` (int): PR编号

**返回**:
```python
{
    "success": True,
    "pr_number": 123,
    "method": "squash",
    "merged_at": "2026-03-04T12:00:00"
}
```

**合并条件**:
1. Review已通过（如果 `require_review=True`）
2. CI已通过（如果 `require_ci=True`）
3. 无合并冲突
4. PR状态为 `OPEN`

##### 4. list_prs()

列出PR列表。

```python
result = await pr_manager.list_prs(state="open", limit=20)
```

**参数**:
- `state` (str): PR状态（open/closed/all）
- `limit` (int): 数量限制

**返回**:
```python
{
    "success": True,
    "prs": [
        {
            "number": 123,
            "title": "[Agent] Feature: xxx",
            "state": "OPEN",
            "headRefName": "feature/xxx"
        }
    ]
}
```

##### 5. close_pr()

关闭PR。

```python
result = await pr_manager.close_pr(
    pr_number=123,
    comment="不再需要此PR"
)
```

##### 6. generate_pr_report()

生成PR报告。

```python
report = pr_manager.generate_pr_report(pr_number)
print(report)  # Markdown格式
```

---

## 使用示例

### 示例1：完整工作流

```python
import asyncio
from nanobot_scheduler_enhanced import get_orchestrator_enhanced

async def main():
    # 1. 获取编排器
    orchestrator = get_orchestrator_enhanced()
    
    # 2. 创建任务
    task_result = await orchestrator.create_agent_task(
        task_id="task_example",
        description="实现用户登录功能",
        agent_type="opencode",
        priority="high"
    )
    
    # 3. 等待任务完成（模拟）
    await asyncio.sleep(60)
    
    # 4. 完成任务并创建PR
    complete_result = await orchestrator.complete_task_with_pr(
        task_id="task_example",
        cleanup=True
    )
    
    print(f"完成结果: {complete_result}")
    
    # 5. 监控PR（如果创建成功）
    if complete_result.get("pr_number"):
        pr_status = await orchestrator.monitor_pr(
            complete_result["pr_number"]
        )
        
        print(f"PR状态: {pr_status}")

asyncio.run(main())
```

### 示例2：手动控制PR流程

```python
from pr_manager import get_pr_manager

async def manual_pr_workflow():
    pr_manager = get_pr_manager()
    
    # 1. 创建PR
    create_result = await pr_manager.auto_create_pr("task_123")
    
    if not create_result["success"]:
        print(f"创建失败: {create_result['error']}")
        return
    
    pr_number = create_result["pr_number"]
    print(f"PR #{pr_number} 已创建")
    
    # 2. 等待Review和CI
    import asyncio
    await asyncio.sleep(300)  # 等待5分钟
    
    # 3. 检查状态
    status = await pr_manager.monitor_pr_status(pr_number)
    
    print(f"Review状态: {status['review']['decision']}")
    print(f"CI状态: {status['ci']['success']}")
    print(f"可合并: {status['ready_to_merge']}")
    
    # 4. 如果满足条件，合并PR
    if status["ready_to_merge"]:
        merge_result = await pr_manager.auto_merge_pr(pr_number)
        
        if merge_result["success"]:
            print("PR已合并")
        else:
            print(f"合并失败: {merge_result['reason']}")
    else:
        print(f"不能合并: {pr_manager.get_merge_block_reason(status)}")
```

### 示例3：批量处理PR

```python
from pr_manager import get_pr_manager

async def batch_process_prs():
    pr_manager = get_pr_manager()
    
    # 1. 列出所有打开的PR
    result = await pr_manager.list_prs(state="open", limit=50)
    
    if not result["success"]:
        print("获取PR列表失败")
        return
    
    # 2. 检查每个PR的状态
    for pr in result["prs"]:
        pr_number = pr["number"]
        
        status = await pr_manager.monitor_pr_status(pr_number)
        
        print(f"\nPR #{pr_number}: {pr['title']}")
        print(f"  可合并: {status['ready_to_merge']}")
        
        # 3. 如果可以合并，自动合并
        if status["ready_to_merge"]:
            merge_result = await pr_manager.auto_merge_pr(pr_number)
            
            if merge_result["success"]:
                print(f"  ✅ 已合并")
            else:
                print(f"  ❌ 合并失败: {merge_result['reason']}")
```

### 示例4：生成PR报告

```python
from pr_manager import get_pr_manager

async def generate_report():
    pr_manager = get_pr_manager()
    
    # 监控PR状态（会更新缓存）
    await pr_manager.monitor_pr_status(123)
    
    # 生成报告
    report = pr_manager.generate_pr_report(123)
    
    # 保存到文件
    with open("pr_123_report.md", "w") as f:
        f.write(report)
    
    print("报告已生成: pr_123_report.md")
```

---

## 最佳实践

### 1. PR创建时机

**推荐**:
- ✅ 任务完成后立即创建PR
- ✅ Code Review通过后创建
- ✅ CI通过后创建

**不推荐**:
- ❌ 任务未完成时创建
- ❌ 强制创建（跳过检查）

### 2. 合并策略

```python
# 推荐配置
config = {
    "auto_merge": False,  # 谨慎启用自动合并
    "merge_method": "squash",  # Feature分支使用squash
    "require_review": True,  # 必须Review
    "require_ci": True,  # 必须CI通过
    "min_review_score": 80  # 最低分数80
}
```

### 3. 标签管理

自动添加的标签：
- `agent-generated`: AI生成的PR
- `feature`/`bugfix`/`refactor`: 任务类型
- `priority-high`: 高优先级
- `complexity-medium`: 复杂度
- `agent-glm5-turbo`: 使用的Agent

### 4. 错误处理

```python
result = await pr_manager.auto_create_pr(task_id)

if not result["success"]:
    # 记录错误
    print(f"创建PR失败: {result['error']}")
    
    # 根据错误类型采取行动
    if "Code Review" in result["error"]:
        # 触发重新Review
        pass
    elif "CI" in result["error"]:
        # 检查CI日志
        pass
    else:
        # 手动处理
        pass
```

### 5. 监控和通知

```python
# 定期监控PR状态
async def monitor_pr_loop(pr_number, interval=300):
    while True:
        status = await pr_manager.monitor_pr_status(pr_number)
        
        if status["ready_to_merge"]:
            # 发送通知
            await notify_team(f"PR #{pr_number} 已准备好合并")
        
        await asyncio.sleep(interval)
```

---

## 故障排查

### 问题1: gh命令未找到

**症状**:
```
命令执行失败: gh: command not found
```

**解决**:
```bash
# 安装GitHub CLI
brew install gh  # macOS
sudo apt install gh  # Linux

# 验证安装
gh --version
```

### 问题2: GitHub认证失败

**症状**:
```
错误: authentication required
```

**解决**:
```bash
# 重新认证
gh auth login

# 验证认证
gh auth status
```

### 问题3: PR创建失败 - 任务未完成

**症状**:
```python
{
    "success": False,
    "error": "任务未完成，当前状态: running"
}
```

**解决**:
```python
# 等待任务完成
await asyncio.sleep(60)

# 重新尝试创建PR
result = await pr_manager.auto_create_pr(task_id)
```

### 问题4: PR创建失败 - Code Review未通过

**症状**:
```python
{
    "success": False,
    "error": "Code Review未通过（得分: 70 < 80）"
}
```

**解决**:
```python
# 选项1: 提高代码质量后重新Review
await orchestrator.review_code(task_id)

# 选项2: 降低Review分数要求（不推荐）
config["min_review_score"] = 70
```

### 问题5: 合并失败 - 存在冲突

**症状**:
```python
{
    "success": False,
    "reason": "存在合并冲突"
}
```

**解决**:
```bash
# 手动解决冲突
git checkout feature/xxx
git fetch origin
git rebase origin/main

# 解决冲突后
git add .
git rebase --continue
git push -f

# 重新尝试合并
```

### 问题6: 标签创建失败

**症状**:
```
添加标签失败: label not found
```

**解决**:
```bash
# 手动创建标签
gh label create "agent-generated" --color "0E8A16"
```

### 问题7: PR描述乱码

**症状**:
PR描述中包含乱码或格式错误

**解决**:
```python
# 确保使用UTF-8编码
task = {
    "description": "中文描述"  # 确保正确编码
}

# 检查环境变量
import locale
print(locale.getpreferredencoding())  # 应该是UTF-8
```

---

## 附录

### A. PR标题格式

```
[Agent] {Type}: {Description}

Type选项:
- Feature: 新功能
- Bugfix: Bug修复
- Refactor: 代码重构
- Test: 测试相关
- Docs: 文档更新
- Chore: 杂项

示例:
- [Agent] Feature: 实现用户头像上传
- [Agent] Bugfix: 修复登录超时问题
- [Agent] Refactor: 优化数据库查询
```

### B. PR描述模板

PR描述自动包含以下部分：

1. **基本信息**
   - 任务ID
   - Agent类型
   - 复杂度
   - 优先级

2. **变更内容**
   - 任务描述

3. **测试结果**
   - 单元测试
   - 集成测试
   - 代码覆盖率

4. **Code Review**
   - 安全检查
   - 性能检查
   - 代码质量分数

5. **相关链接**
   - 任务详情
   - 测试报告

### C. 相关文档

- [Phase 2完成报告](./PHASE2_COMPLETION_REPORT.md)
- [Phase 3开发计划](./PHASE3_PLAN.md)
- [GitHub CLI文档](https://cli.github.com/manual/)
- [GitHub API文档](https://docs.github.com/en/rest)

---

**更新时间**: 2026-03-04  
**维护者**: Nanobot AI Agent系统
