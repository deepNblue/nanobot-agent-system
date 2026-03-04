# Agent System Skill

> **创建日期**: 2026-03-04
> **版本**: 2.0.0 (Phase 2)
> **架构**: nanobot (编排+执行) → GLM5 (模型)

---

## 📋 功能概述

### 核心功能

1. **需求提取** ✨ Phase 2
   - 从Obsidian会议记录自动提取需求
   - 使用GLM5 API智能分析内容
   - 识别行动项和优先级
   - 关联原始会议记录

2. **任务分解** ✨ Phase 2
   - 智能分析任务复杂度（high/medium/low）
   - 自动选择合适的Agent类型（GLM5-Plus/Turbo/Lite）
   - 生成精确的执行prompt
   - 加载相关上下文（相似任务、相关代码）
   - 估算执行时间

3. **代码生成**
   - 调用GLM5生成代码
   - 支持多种编程语言
   - 包含实现步骤和测试方法

4. **代码执行**
   - 自动执行生成的代码
   - 捕获执行结果
   - 错误处理和重试

5. **结果验证**
   - 自动验证代码质量
   - 检查错误标记
   - 生成验证报告

6. **自动化工作流** ✨ Phase 2
   - 提取需求 → 分解任务 → 创建Agent任务
   - 一键启动完整工作流
   - 自动生成任务报告

---

## 🚀 快速开始

### 方法1：完整工作流

```python
from skills.agent_system.nanobot_scheduler import agent_system

# 运行完整工作流
result = await agent_system.run_workflow(
    requirement_text="实现一个简单的TODO列表API"
)

print(result["status"])  # completed
print(result["result"]["code"])  # 生成的代码
```

### 方法2：从Obsidian提取需求

```python
# 从最近7天的会议记录提取需求
requirements = await agent_system.extract_requirements_from_obsidian(days=7)

for req in requirements:
    print(f"需求: {req['description']}")
    print(f"优先级: {req['priority']}")
```

### 方法3：分步执行

```python
# 1. 定义需求
requirement = {
    "id": "req_001",
    "source": "manual",
    "description": "实现用户认证功能",
    "priority": "high"
}

# 2. 分解任务
task = await agent_system.decompose_task(requirement)

# 3. 执行任务
task = await agent_system.execute_task(task)

# 4. 查看结果
print(task["result"])
```

---

## 🔧 配置

### 模型配置

```json
{
  "model": "zhipu/glm-5",
  "max_tokens": 8192,
  "temperature": 0.1
}
```

### Obsidian配置

```json
{
  "vault_path": "/home/dudu/Obsidian-Vault",
  "meeting_notes_folder": "Daily Notes",
  "auto_sync": true
}
```

---

## 📊 使用场景

### 场景1：自动化开发

```
会议记录 → 提取需求 → 生成代码 → 执行测试 → 提交PR
```

### 场景2：Bug修复

```
Sentry错误 → 生成修复代码 → 自动测试 → 合并修复
```

### 场景3：文档生成

```
代码库分析 → 生成文档 → 更新Obsidian → 同步到团队
```

---

## 🎯 成功指标

| 指标 | 目标 | 当前 |
|------|------|------|
| 需求提取准确率 | >90% | - |
| 代码生成成功率 | >85% | - |
| 自动执行成功率 | >80% | - |
| 端到端完成时间 | <10分钟 | - |

---

## 🔗 相关技能

- **obsidian-kb**: Obsidian知识库集成
- **openviking-memory**: 三层记忆系统
- **gitnexus**: Git操作集成

---

## 📝 示例输出

### 需求提取

```json
{
  "id": "req_20260304102000_0",
  "source": "obsidian",
  "note_title": "2026-03-04 产品会议",
  "description": "实现用户头像上传功能",
  "priority": "high",
  "created_at": "2026-03-04T10:20:00"
}
```

### 任务执行

```json
{
  "id": "task_20260304102005",
  "status": "completed",
  "result": {
    "code": "// GLM5生成的代码\n...",
    "execution": {
      "status": "success",
      "output": "..."
    }
  }
}
```

---

## 🚧 已知限制

1. **代码执行**: 目前仅支持模拟执行，需要配置沙箱环境
2. **需求提取**: 简单关键词匹配，可以用GLM5改进
3. **复杂度分析**: 基于规则，可以用GLM5改进
4. **结果验证**: 基础验证，需要添加更多规则

---

## 📅 更新日志

### v1.0.0 (2026-03-04)
- ✅ 初始版本
- ✅ 需求提取功能
- ✅ 任务分解功能
- ✅ 代码生成功能（模拟）
- ✅ 代码执行功能（模拟）
- ✅ 结果验证功能

---

**下一步**:
1. 集成真实的GLM5 API调用
2. 实现真实的代码执行环境
3. 添加更多验证规则
4. 优化prompt生成
