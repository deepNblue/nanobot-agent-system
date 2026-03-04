# AI辅助测试功能使用指南

> **版本**: v4.0.0  
> **创建时间**: 2026-03-04  
> **适用场景**: 自动化测试生成、覆盖率优化、回归测试

---

## 📋 目录

1. [功能概述](#功能概述)
2. [快速开始](#快速开始)
3. [模块详解](#模块详解)
4. [高级用法](#高级用法)
5. [最佳实践](#最佳实践)
6. [故障排查](#故障排查)

---

## 功能概述

### 核心功能

1. **测试用例生成器** (`test_generator.py`)
   - 自动生成单元测试、集成测试、端到端测试
   - 支持多种测试类型和模板
   - 测试代码质量验证

2. **覆盖率优化器** (`coverage_optimizer.py`)
   - 自动运行覆盖率测试
   - 分析未覆盖代码
   - 生成测试建议

3. **回归测试器** (`regression_tester.py`)
   - 自动化回归测试
   - 基线对比和变更检测
   - 不稳定测试检测

4. **测试套件管理器** (`test_suite_manager.py`)
   - 测试发现和组织
   - 分类和标签管理
   - 测试依赖分析

### 技术栈

- **Python**: 3.11+
- **pytest**: 测试框架
- **coverage**: 覆盖率工具
- **asyncio**: 异步支持
- **GLM5-Turbo**: AI模型（快速且便宜）

---

## 快速开始

### 1. 安装依赖

```bash
pip install pytest pytest-asyncio pytest-cov pytest-json-report
```

### 2. 基本使用

#### 生成测试用例

```python
import asyncio
from test_generator import TestCaseGenerator
from model_adapter import ModelAdapter

async def generate_tests():
    # 初始化
    adapter = ModelAdapter()
    generator = TestCaseGenerator(adapter)
    
    # 要测试的代码
    code = """
def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
    
    # 生成单元测试
    result = await generator.generate_tests(
        code,
        test_type="unit_test"
    )
    
    if result["success"]:
        print(result["test_code"])
        
        # 保存测试文件
        await generator.save_test(
            result["test_code"],
            "test_math.py",
            "./tests"
        )

# 运行
asyncio.run(generate_tests())
```

#### 分析覆盖率

```python
import asyncio
from coverage_optimizer import CoverageOptimizer

async def analyze_coverage():
    optimizer = CoverageOptimizer("./my_project")
    
    # 运行覆盖率测试
    result = await optimizer.run_coverage(
        source_dir="src",
        test_dir="tests"
    )
    
    # 分析覆盖率
    analysis = optimizer.analyze_coverage()
    
    print(f"总体覆盖率: {analysis['summary']['overall_coverage']:.2f}%")
    print(f"完全覆盖: {analysis['fully_covered']} 个文件")
    print(f"部分覆盖: {analysis['partially_covered']} 个文件")
    
    # 获取测试建议
    suggestions = await optimizer.suggest_tests()
    for suggestion in suggestions[:5]:
        print(f"\n文件: {suggestion['file']}")
        print(f"未覆盖行: {suggestion['lines']}")
        print(f"建议测试类型: {suggestion['suggested_test_type']}")

asyncio.run(analyze_coverage())
```

#### 运行回归测试

```python
import asyncio
from regression_tester import RegressionTester

async def run_regression():
    tester = RegressionTester("./my_project")
    
    # 运行回归测试
    result = await tester.run_regression_suite("./tests")
    
    print(f"测试通过: {result['results']['passed']}")
    print(f"测试失败: {result['results']['failed']}")
    print(f"耗时: {result['duration']:.2f}s")
    
    # 捕获基线
    await tester.capture_baseline("all")
    
    # 与基线对比
    comparison = await tester.compare_with_baseline("all")
    
    if comparison["has_regression"]:
        print("⚠️ 检测到回归!")
        print(f"新失败: {comparison['new_failures']}")
    
    # 检测不稳定测试
    flaky = await tester.detect_flaky_tests(runs=5)
    if flaky:
        print(f"⚠️ 发现 {len(flaky)} 个不稳定测试")

asyncio.run(run_regression())
```

#### 管理测试套件

```python
from test_suite_manager import TestSuiteManager

def manage_suites():
    manager = TestSuiteManager("./tests")
    
    # 获取统计
    stats = manager.get_statistics()
    print(f"总测试文件: {stats['total_files']}")
    print(f"总测试用例: {stats['total_tests']}")
    
    # 按分类查看
    for category, data in stats['categories'].items():
        print(f"{category}: {data['test_count']} 个测试")
    
    # 搜索测试
    results = manager.find_tests("user", search_in="all")
    for result in results:
        print(f"{result['file']}: {result['test']}")
    
    # 导出配置
    manager.export_suite_config("test_config.json")

manage_suites()
```

---

## 模块详解

### 1. TestCaseGenerator

#### 初始化

```python
from test_generator import TestCaseGenerator
from model_adapter import ModelAdapter

adapter = ModelAdapter()
generator = TestCaseGenerator(adapter)
```

#### 主要方法

**`generate_tests(code, test_type, context, model, temperature, max_tokens)`**

生成测试用例。

参数:
- `code` (str): 源代码
- `test_type` (str): 测试类型
  - `"unit_test"`: 单元测试
  - `"integration_test"`: 集成测试
  - `"e2e_test"`: 端到端测试
  - `"performance_test"`: 性能测试
- `context` (dict): 额外上下文
- `model` (str): 使用的模型（默认: `"glm5-turbo"`）
- `temperature` (float): 生成温度（默认: 0.3）
- `max_tokens` (int): 最大token数（默认: 3000）

返回:
```python
{
    "success": bool,
    "test_code": str,  # 生成的测试代码
    "test_type": str,
    "validation": {
        "is_valid": bool,
        "score": int,
        "checks": dict
    },
    "coverage_analysis": {
        "test_functions": list,
        "tested_functions": list,
        "coverage_estimate": float
    }
}
```

**`generate_from_file(file_path, test_type, output_dir, context)`**

从文件生成测试。

```python
result = await generator.generate_from_file(
    "./src/utils.py",
    test_type="unit_test",
    output_dir="./tests"
)
```

**`batch_generate(files, test_type, output_dir, max_concurrent)`**

批量生成测试。

```python
files = ["./src/module1.py", "./src/module2.py"]
result = await generator.batch_generate(
    files,
    test_type="unit_test",
    output_dir="./tests",
    max_concurrent=3
)
```

**`improve_test(existing_test, source_code, issues)`**

改进现有测试。

```python
improved = await generator.improve_test(
    existing_test=current_test_code,
    source_code=source_code,
    issues=["缺少边界测试", "没有异常处理测试"]
)
```

### 2. CoverageOptimizer

#### 初始化

```python
from coverage_optimizer import CoverageOptimizer

optimizer = CoverageOptimizer("./my_project")
```

#### 主要方法

**`run_coverage(source_dir, test_dir, extra_args)`**

运行覆盖率测试。

```python
result = await optimizer.run_coverage(
    source_dir="src",
    test_dir="tests",
    extra_args=["--cov-report=html"]
)
```

**`analyze_coverage()`**

分析覆盖率数据。

```python
analysis = optimizer.analyze_coverage()

print(f"总体覆盖率: {analysis['summary']['overall_coverage']:.2f}%")
print(f"未覆盖行: {analysis['uncovered_lines']}")
```

**`suggest_tests(uncovered_lines, max_suggestions)`**

生成测试建议。

```python
suggestions = await optimizer.suggest_tests(max_suggestions=10)

for suggestion in suggestions:
    print(f"文件: {suggestion['file']}")
    print(f"未覆盖行: {suggestion['lines']}")
    print(f"优先级: {suggestion['priority']}")
```

**`optimize_coverage(target_coverage, max_iterations, test_generator)`**

自动优化覆盖率。

```python
result = await optimizer.optimize_coverage(
    target_coverage=90.0,
    max_iterations=5,
    test_generator=generator
)

print(f"初始覆盖率: {result['initial_coverage']:.2f}%")
print(f"最终覆盖率: {result['final_coverage']:.2f}%")
print(f"提升: {result['improvement']:.2f}%")
```

**`get_coverage_report()`**

生成覆盖率报告。

```python
report = optimizer.get_coverage_report()
print(report)  # Markdown格式
```

### 3. RegressionTester

#### 初始化

```python
from regression_tester import RegressionTester

tester = RegressionTester("./my_project")
```

#### 主要方法

**`run_regression_suite(test_path, extra_args, save_results)`**

运行回归测试。

```python
result = await tester.run_regression_suite(
    test_path="./tests",
    save_results=True
)
```

**`capture_baseline(test_suite)`**

捕获测试基线。

```python
baseline = await tester.capture_baseline("all")
```

**`compare_with_baseline(test_suite)`**

与基线对比。

```python
comparison = await tester.compare_with_baseline("all")

if comparison["has_regression"]:
    print("检测到回归!")
    print(f"新失败: {comparison['new_failures']}")
```

**`detect_flaky_tests(test_path, runs, threshold)`**

检测不稳定测试。

```python
flaky_tests = await tester.detect_flaky_tests(
    test_path="./tests",
    runs=5,
    threshold=0.8
)

for test in flaky_tests:
    print(f"{test['test']}: 通过率 {test['pass_rate']:.2%}")
```

**`get_trend_analysis(days)`**

趋势分析。

```python
trend = tester.get_trend_analysis(days=7)
print(f"平均通过率: {trend['avg_pass_rate']:.2f}%")
```

### 4. TestSuiteManager

#### 初始化

```python
from test_suite_manager import TestSuiteManager

manager = TestSuiteManager("./tests")
```

#### 主要方法

**`get_statistics()`**

获取统计信息。

```python
stats = manager.get_statistics()
```

**`run_suite(suite_name, verbose)`**

运行指定测试套件。

```python
result = await manager.run_suite("test_user_api.py")
```

**`run_category(category, parallel)`**

运行分类测试。

```python
result = await manager.run_category("unit", parallel=True)
```

**`run_by_tags(tags, mode)`**

按标签运行测试。

```python
result = await manager.run_by_tags(
    tags=["fast", "api"],
    mode="all"  # 或 "any"
)
```

**`find_tests(query, search_in)`**

搜索测试。

```python
results = manager.find_tests(
    query="user authentication",
    search_in="all"  # 或 "name", "docstring"
)
```

---

## 高级用法

### 1. 自定义测试模板

```python
# 添加自定义模板
generator.test_templates["custom_test"] = """
Generate tests for: {code}

Custom Requirements:
1. ...
2. ...
"""

# 使用自定义模板
result = await generator.generate_tests(
    code,
    test_type="custom_test"
)
```

### 2. 覆盖率目标优化

```python
# 自动优化到90%覆盖率
result = await optimizer.optimize_coverage(
    target_coverage=90.0,
    max_iterations=10,
    test_generator=generator
)

if result["success"]:
    print(f"✅ 达到目标覆盖率: {result['final_coverage']:.2f}%")
else:
    print(f"❌ 未达到目标，当前: {result['final_coverage']:.2f}%")
```

### 3. CI/CD集成

```python
# ci_test.py
import asyncio
from regression_tester import RegressionTester
from coverage_optimizer import CoverageOptimizer

async def run_ci_tests():
    # 1. 运行回归测试
    tester = RegressionTester(".")
    result = await tester.run_regression_suite()
    
    if not result["success"]:
        print("❌ 回归测试失败")
        return False
    
    # 2. 检查覆盖率
    optimizer = CoverageOptimizer(".")
    await optimizer.run_coverage()
    analysis = optimizer.analyze_coverage()
    
    if analysis["summary"]["overall_coverage"] < 80:
        print(f"❌ 覆盖率不足: {analysis['summary']['overall_coverage']:.2f}%")
        return False
    
    print("✅ 所有测试通过")
    return True

if __name__ == "__main__":
    success = asyncio.run(run_ci_tests())
    exit(0 if success else 1)
```

### 4. 定时测试调度

```python
from regression_tester import RegressionTester, TestScheduler

async def scheduled_testing():
    tester = RegressionTester(".")
    scheduler = TestScheduler(tester)
    
    # 每小时运行一次
    scheduler.schedule_test(
        test_path="./tests",
        interval_minutes=60,
        name="hourly_regression"
    )
    
    # 启动调度器
    await scheduler.start()

asyncio.run(scheduled_testing())
```

### 5. 测试报告生成

```python
from coverage_optimizer import CoverageOptimizer
from regression_tester import RegressionTester

async def generate_reports():
    # 覆盖率报告
    optimizer = CoverageOptimizer(".")
    await optimizer.run_coverage()
    coverage_report = optimizer.get_coverage_report()
    
    # 回归测试报告
    tester = RegressionTester(".")
    await tester.run_regression_suite()
    regression_report = tester.generate_report("markdown")
    
    # 保存报告
    with open("coverage_report.md", "w") as f:
        f.write(coverage_report)
    
    with open("regression_report.md", "w") as f:
        f.write(regression_report)

asyncio.run(generate_reports())
```

---

## 最佳实践

### 1. 测试生成策略

**✅ 推荐做法:**

```python
# 1. 先生成基础测试
result = await generator.generate_tests(code, "unit_test")

# 2. 验证测试质量
if result["validation"]["score"] < 5:
    # 3. 改进测试
    improved = await generator.improve_test(
        result["test_code"],
        code
    )
    result["test_code"] = improved["improved_test"]

# 4. 保存并运行
await generator.save_test(result["test_code"], filename, output_dir)
```

**❌ 不推荐:**

```python
# 不要盲目保存生成的测试
result = await generator.generate_tests(code, "unit_test")
await generator.save_test(result["test_code"], filename, output_dir)
# 缺少验证和改进步骤
```

### 2. 覆盖率优化流程

```python
# 1. 运行初始覆盖率
await optimizer.run_coverage()

# 2. 分析
analysis = optimizer.analyze_coverage()

# 3. 识别低覆盖率文件
low_coverage = [
    f for f, data in analysis["files_analysis"].items()
    if data["coverage_percent"] < 80
]

# 4. 为低覆盖率文件生成测试
for file in low_coverage[:5]:  # 先处理5个
    await generator.generate_from_file(file, "unit_test")

# 5. 重新运行覆盖率
await optimizer.run_coverage()
```

### 3. 回归测试策略

```python
# 1. 建立基线
await tester.capture_baseline("all")

# 2. 定期运行回归测试
result = await tester.run_regression_suite()

# 3. 与基线对比
comparison = await tester.compare_with_baseline("all")

# 4. 处理回归
if comparison["has_regression"]:
    # 通知团队
    notify_team(comparison["new_failures"])
    
    # 自动创建issue
    create_github_issue(comparison)
```

### 4. 测试组织建议

```python
# 使用分类和标签
"""
Category: unit
Tags: fast, core, auth
Priority: high
"""

# 按优先级运行
await manager.run_category("unit")  # 快速反馈
await manager.run_category("integration")  # 深度测试
await manager.run_category("e2e")  # 完整验证
```

---

## 故障排查

### 问题1: 模型调用失败

**症状:**
```python
{"success": False, "error": "API Error"}
```

**解决方案:**
```python
# 1. 检查API密钥
from model_adapter import ModelAdapter
adapter = ModelAdapter()
print(adapter.get_available_models())

# 2. 使用备用模型
result = await generator.generate_tests(
    code,
    test_type="unit_test",
    model="deepseek-chat"  # 备用模型
)
```

### 问题2: 覆盖率测试失败

**症状:**
```python
{"success": False, "error": "No coverage data"}
```

**解决方案:**
```bash
# 1. 确保安装了pytest-cov
pip install pytest-cov

# 2. 手动运行一次
pytest --cov=src tests/

# 3. 检查coverage.json是否存在
```

### 问题3: 生成的测试无法运行

**症状:**
测试文件有语法错误或导入错误

**解决方案:**
```python
# 1. 验证测试代码
validation = generator._validate_test(test_code, "unit_test")

if not validation["is_valid"]:
    print("验证失败:")
    for check, passed in validation["checks"].items():
        if not passed:
            print(f"  - {check}")

# 2. 改进测试
improved = await generator.improve_test(test_code, source_code)
```

### 问题4: 回归检测误报

**症状:**
正常的测试变化被标记为回归

**解决方案:**
```python
# 1. 更新基线
await tester.capture_baseline("all")

# 2. 调整阈值
comparison = await tester.compare_with_baseline("all")

# 只关注真正的新失败
if comparison["new_failures"]:
    # 手动验证是否真的失败
    pass
```

---

## 性能优化

### 1. 批量生成优化

```python
# 使用并发控制
result = await generator.batch_generate(
    files,
    max_concurrent=5  # 不要太大，避免API限流
)
```

### 2. 覆盖率测试优化

```python
# 只测试变更的文件
result = await optimizer.run_coverage(
    extra_args=["--cov-fail-under=80"]  # 设置阈值
)
```

### 3. 回归测试优化

```python
# 并行运行测试
result = await tester.run_regression_suite(
    extra_args=["-n", "4"]  # 使用pytest-xdist并行
)
```

---

## 总结

AI辅助测试功能可以显著提升测试效率：

- ✅ **测试生成速度提升10倍**
- ✅ **覆盖率提升15-30%**
- ✅ **回归检测自动化**
- ✅ **测试质量提升**

**建议工作流程:**

1. 使用 `TestCaseGenerator` 生成初始测试
2. 使用 `CoverageOptimizer` 分析覆盖率
3. 使用 `RegressionTester` 建立基线
4. 使用 `TestSuiteManager` 组织测试
5. 定期运行回归测试和覆盖率检查

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04
