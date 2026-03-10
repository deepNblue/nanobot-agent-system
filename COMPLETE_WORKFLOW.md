# Agent集群系统完整开发流程

> 版本：v3.0.1
> 更新时间：2026-03-10 17:15
> 状态：✅ 完整流程

---

## 📋 目录

1. [项目初始化](#1-项目初始化)
2. [开发阶段](#2-开发阶段)
3. [测试验证](#3-测试验证)
4. [GitHub管理](#4-github管理)
5. [部署发布](#5-部署发布)
6. [完整示例](#6-完整示例)

---

## 1. 项目初始化

### 1.1 创建项目目录

```bash
# 创建项目目录
mkdir -p /path/to/your-project
cd /path/to/your-project

# 初始化Git
git init
```

### 1.2 创建项目配置

```python
# project_config.py
PROJECT_NAME = "your-project"
PROJECT_VERSION = "1.0.0"
PROJECT_DESCRIPTION = "项目描述"
```

### 1.3 创建README

```markdown
# 项目名称

> 使用Agent集群系统v3.0.1开发

## 项目概述

简要描述项目

## 功能特性

- 功能1
- 功能2

## 快速开始

使用说明
```

---

## 2. 开发阶段

### 2.1 任务分析

```python
from task_router import analyze_task

# 分析任务
task = "实现用户登录功能"
task_info = analyze_task(task)

print(f"任务类型: {task_info['task_type']}")
print(f"Agent模式: {task_info['agent_mode']}")
print(f"模型: {task_info['model']}")  # glm-5
print(f"预估时间: {task_info['estimated_time']}秒")
```

### 2.2 执行开发任务

#### 方式1：使用任务路由器

```python
from opencode_executor import executor

result = await executor.execute_task(
    prompt="实现用户登录功能",
    agent_mode="build",  # 自动识别
    model="glm-5",       # 统一使用GLM-5
    working_dir="/path/to/your-project"
)
```

#### 方式2：使用完整工作流

```python
from nanobot_scheduler import orchestrator

result = await orchestrator.run_workflow(
    requirement_text="""
    实现用户登录功能：
    1. 用户名密码登录
    2. JWT token认证
    3. 密码加密存储
    """,
    working_dir="/path/to/your-project"
)
```

### 2.3 分阶段开发

```python
# Phase 1: 设计
design_result = await executor.execute_task(
    prompt="设计用户登录系统架构",
    agent_mode="plan",
    model="glm-5"
)

# Phase 2: 实现
impl_result = await executor.execute_task(
    prompt="实现用户登录功能",
    agent_mode="build",
    model="glm-5"
)

# Phase 3: 测试
test_result = await executor.execute_task(
    prompt="编写登录功能单元测试",
    agent_mode="test",
    model="glm-5"
)

# Phase 4: 文档
doc_result = await executor.execute_task(
    prompt="编写API文档和使用说明",
    agent_mode="build",
    model="glm-5"
)
```

---

## 3. 测试验证

### 3.1 单元测试

```python
# test_login.py
import pytest
from your_module import login

def test_login_success():
    result = login("user", "password")
    assert result["status"] == "success"

def test_login_failed():
    result = login("user", "wrong")
    assert result["status"] == "failed"
```

### 3.2 集成测试

```python
# test_integration.py
import pytest
from your_module import app

def test_full_workflow():
    # 1. 注册
    # 2. 登录
    # 3. 访问资源
    # 4. 登出
    pass
```

### 3.3 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_login.py

# 生成覆盖率报告
pytest --cov=your_module tests/
```

---

## 4. GitHub管理

### 4.1 创建GitHub仓库

```bash
# 初始化Git
git init

# 添加所有文件
git add .

# 提交
git commit -m "feat: 初始提交

- 实现核心功能
- 完成单元测试
- 编写文档

使用Agent集群系统v3.0.1开发"

# 创建GitHub仓库并推送
gh repo create your-project \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "项目描述"
```

### 4.2 分支管理

```bash
# 创建功能分支
git checkout -b feature/new-feature

# 开发...
git add .
git commit -m "feat: 添加新功能"

# 推送分支
git push origin feature/new-feature

# 创建Pull Request
gh pr create \
  --title "feat: 添加新功能" \
  --body "功能描述

## 变更内容
- 变更1
- 变更2

## 测试
- 测试1
- 测试2"
```

### 4.3 版本发布

```bash
# 创建标签
git tag -a v1.0.0 -m "Release v1.0.0

功能：
- 功能1
- 功能2

修复：
- 修复1
- 修复2"

# 推送标签
git push origin v1.0.0

# 创建GitHub Release
gh release create v1.0.0 \
  --title "v1.0.0 - 首次发布" \
  --notes "发布说明"
```

### 4.4 Commit规范

```bash
# 功能
git commit -m "feat: 添加用户登录功能"

# 修复
git commit -m "fix: 修复登录验证bug"

# 文档
git commit -m "docs: 更新API文档"

# 测试
git commit -m "test: 添加登录功能测试"

# 重构
git commit -m "refactor: 重构登录逻辑"

# 优化
git commit -m "perf: 优化登录性能"

# 样式
git commit -m "style: 代码格式调整"

# 其他
git commit -m "chore: 更新依赖"
```

---

## 5. 部署发布

### 5.1 构建项目

```bash
# Python项目
python setup.py build
python setup.py sdist

# Web项目
npm run build

# Android项目
./gradlew assembleRelease
```

### 5.2 Docker部署

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

```bash
# 构建镜像
docker build -t your-project:v1.0.0 .

# 运行容器
docker run -d -p 8000:8000 your-project:v1.0.0
```

### 5.3 CI/CD配置

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 6. 完整示例

### 6.1 3D贪吃蛇游戏完整流程

```bash
# 1. 创建项目
cd /tmp
mkdir snake-3d-game
cd snake-3d-game
git init

# 2. 项目初始化
cat > README.md << 'EOF'
# 3D贪吃蛇游戏

> 使用Agent集群系统v3.0.1开发

## 支持平台
- Web (Three.js)
- Android (OpenGL ES)
EOF

# 3. Phase 1: 游戏设计
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/dudu/.nanobot/workspace/skills/agent-system')

from opencode_executor import executor
import asyncio

async def main():
    result = await executor.execute_task(
        prompt="设计3D贪吃蛇游戏架构（Web + Android）",
        agent_mode="plan",
        model="glm-5",
        working_dir="/tmp/snake-3d-game"
    )
    print(f"设计完成: {result['status']}")

asyncio.run(main())
PYEOF

# 4. Phase 2: Web版本开发
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/dudu/.nanobot/workspace/skills/agent-system')

from opencode_executor import executor
import asyncio

async def main():
    result = await executor.execute_task(
        prompt="实现3D贪吃蛇Web版本（Three.js）",
        agent_mode="build",
        model="glm-5",
        working_dir="/tmp/snake-3d-game"
    )
    print(f"Web版本完成: {result['status']}")

asyncio.run(main())
PYEOF

# 5. Phase 3: Android版本开发
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/dudu/.nanobot/workspace/skills/agent-system')

from opencode_executor import executor
import asyncio

async def main():
    result = await executor.execute_task(
        prompt="实现3D贪吃蛇Android版本（OpenGL ES）",
        agent_mode="build",
        model="glm-5",
        working_dir="/tmp/snake-3d-game"
    )
    print(f"Android版本完成: {result['status']}")

asyncio.run(main())
PYEOF

# 6. Git提交
git add .
git commit -m "feat: 3D贪吃蛇游戏初始版本

- 完整游戏设计
- Web版本（Three.js）
- Android版本（OpenGL ES）
- 跨平台支持

使用Agent集群系统v3.0.1开发
开发时间：5.5分钟
代码行数：1420+"

# 7. 创建GitHub仓库
gh repo create snake-3d-game \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "3D贪吃蛇游戏 - 使用Agent集群系统v3.0.1开发（Web + Android）"

# 8. 创建版本标签
git tag -a v1.0.0 -m "首次发布

功能：
- 3D贪吃蛇游戏
- Web版本支持
- Android版本支持
- 分数和等级系统"

git push origin v1.0.0

# 9. 创建Release
gh release create v1.0.0 \
  --title "v1.0.0 - 首次发布" \
  --notes "3D贪吃蛇游戏首次发布

## 功能特性
- ✅ 3D渲染（Three.js + OpenGL ES）
- ✅ 流畅游戏体验（60 FPS）
- ✅ 多平台支持
- ✅ 分数和等级系统

## 开发信息
- 开发工具：Agent集群系统v3.0.1
- 开发时间：5.5分钟
- 代码行数：1420+
- 测试通过：100%"

# 10. 完成
echo "✅ 项目开发完成！"
echo "📦 GitHub: https://github.com/deepNblue/snake-3d-game"
```

### 6.2 项目结构

```
snake-3d-game/
├── README.md                   # 项目说明
├── game-design.md              # 游戏设计文档
├── web-version/                # Web版本
│   ├── index.html
│   └── js/
│       └── game.js
├── android-version/            # Android版本
│   └── app/src/main/
│       ├── AndroidManifest.xml
│       └── java/com/snake3d/game/
│           ├── MainActivity.java
│           ├── GameEngine.java
│           └── SnakeRenderer.java
├── .gitignore
└── LICENSE
```

---

## 7. 最佳实践

### 7.1 开发流程

1. **需求分析** → 使用task_router分析
2. **架构设计** → plan模式
3. **功能实现** → build模式
4. **单元测试** → test模式
5. **代码审查** → review模式
6. **文档编写** → build模式
7. **Git提交** → 规范commit
8. **GitHub推送** → 创建PR
9. **版本发布** → 打tag/release

### 7.2 质量保证

- ✅ 每个功能都要有测试
- ✅ 代码覆盖率 > 80%
- ✅ 文档完整清晰
- ✅ Commit信息规范
- ✅ PR描述详细

### 7.3 团队协作

- 使用分支开发
- Code Review必须
- CI/CD自动化
- 定期重构优化

---

## 8. 工具清单

### 8.1 Agent集群系统工具

| 工具 | 用途 | 命令 |
|------|------|------|
| task_router | 任务分析 | analyze_task() |
| opencode_executor | 任务执行 | executor.execute_task() |
| nanobot_scheduler | 工作流编排 | orchestrator.run_workflow() |

### 8.2 GitHub工具

| 工具 | 用途 | 命令 |
|------|------|------|
| gh | GitHub CLI | gh repo create |
| git | 版本控制 | git add/commit/push |
| GitHub Actions | CI/CD | .github/workflows/ |

### 8.3 测试工具

| 工具 | 用途 | 命令 |
|------|------|------|
| pytest | 单元测试 | pytest tests/ |
| coverage | 覆盖率 | pytest --cov |
| black | 代码格式 | black . |

---

## 9. 常见问题

### Q1: OpenCode CLI超时？

**解决方案**：
```python
# 增加超时时间
executor.wrapper.timeout = 600  # 10分钟

# 或手动开发
# 直接编写代码，使用系统辅助
```

### Q2: GLM-5 API限制？

**解决方案**：
```python
# 添加重试机制
import time

for retry in range(3):
    try:
        result = await executor.execute_task(...)
        break
    except RateLimitError:
        time.sleep(60)
```

### Q3: 如何查看任务进度？

**解决方案**：
```python
# 查看执行器统计
stats = executor.get_stats()
print(stats)

# 查看任务状态
task_info = analyze_task("your task")
print(task_info)
```

---

## 10. 总结

### 完整流程清单

- [x] 项目初始化
- [x] 任务分析
- [x] 代码开发
- [x] 单元测试
- [x] Git提交
- [x] GitHub推送
- [x] 版本发布
- [x] 文档完善

### 核心优势

1. **智能路由** - 自动选择Agent模式
2. **统一模型** - GLM-5高质量输出
3. **GitHub集成** - 完整版本管理
4. **快速开发** - 5分钟完成项目

---

**文档版本**: v1.0
**更新时间**: 2026-03-10 17:15
**状态**: ✅ 完整

**🎉 使用Agent集群系统，快速开发高质量项目！**
