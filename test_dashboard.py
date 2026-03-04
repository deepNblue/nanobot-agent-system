#!/usr/bin/env python3
"""
Dashboard测试脚本
测试Dashboard的基本功能
"""

import sys
import time
import json
import requests
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from dashboard import start_dashboard, get_dashboard


def test_dashboard_startup():
    """测试Dashboard启动"""
    print("\n" + "="*60)
    print("测试1: Dashboard启动")
    print("="*60)
    
    try:
        # 启动Dashboard
        dashboard = start_dashboard(port=5001)  # 使用5001端口避免冲突
        
        if dashboard:
            print("✅ Dashboard启动成功")
            
            # 等待启动
            time.sleep(2)
            
            return True
        else:
            print("❌ Dashboard启动失败")
            return False
    except Exception as e:
        print(f"❌ Dashboard启动异常: {e}")
        return False


def test_api_endpoints():
    """测试API端点"""
    print("\n" + "="*60)
    print("测试2: API端点")
    print("="*60)
    
    base_url = "http://localhost:5001"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查: {data['status']}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
    
    # 测试统计接口
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data.get("stats", {})
                print(f"✅ 统计接口: 总任务数 {stats.get('total', 0)}")
            else:
                print(f"❌ 统计接口返回失败")
        else:
            print(f"❌ 统计接口失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 统计接口异常: {e}")
    
    # 测试任务列表
    try:
        response = requests.get(f"{base_url}/api/tasks", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                tasks = data.get("tasks", [])
                print(f"✅ 任务列表: {len(tasks)} 个任务")
            else:
                print(f"❌ 任务列表返回失败")
        else:
            print(f"❌ 任务列表失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 任务列表异常: {e}")
    
    # 测试错误日志
    try:
        response = requests.get(f"{base_url}/api/errors?limit=5", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                errors = data.get("errors", [])
                print(f"✅ 错误日志: {len(errors)} 条记录")
            else:
                print(f"❌ 错误日志返回失败")
        else:
            print(f"❌ 错误日志失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 错误日志异常: {e}")
    
    # 测试历史数据
    try:
        response = requests.get(f"{base_url}/api/history?days=7", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                history = data.get("history", {})
                dates = history.get("dates", [])
                print(f"✅ 历史数据: {len(dates)} 天")
            else:
                print(f"❌ 历史数据返回失败")
        else:
            print(f"❌ 历史数据失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 历史数据异常: {e}")
    
    return True


def test_dashboard_broadcast():
    """测试Dashboard广播功能"""
    print("\n" + "="*60)
    print("测试3: Dashboard广播")
    print("="*60)
    
    dashboard = get_dashboard()
    
    if not dashboard:
        print("❌ Dashboard实例不存在")
        return False
    
    try:
        # 测试任务更新广播
        dashboard.broadcast_task_update("test-task-123", {
            "status": "running",
            "progress": 50,
            "description": "测试任务"
        })
        print("✅ 任务更新广播成功")
        
        # 测试错误广播
        dashboard.broadcast_error({
            "message": "测试错误消息",
            "task_id": "test-task-123"
        })
        print("✅ 错误广播成功")
        
        # 测试统计更新广播
        dashboard.broadcast_stats_update()
        print("✅ 统计更新广播成功")
        
        return True
    except Exception as e:
        print(f"❌ 广播测试异常: {e}")
        return False


def test_dashboard_stats():
    """测试统计数据计算"""
    print("\n" + "="*60)
    print("测试4: 统计数据计算")
    print("="*60)
    
    dashboard = get_dashboard()
    
    if not dashboard:
        print("❌ Dashboard实例不存在")
        return False
    
    try:
        # 计算统计数据
        stats = dashboard.calculate_stats()
        
        print(f"总任务数: {stats.get('total', 0)}")
        print(f"运行中: {stats.get('running', 0)}")
        print(f"已完成: {stats.get('completed', 0)}")
        print(f"失败: {stats.get('failed', 0)}")
        print(f"等待中: {stats.get('pending', 0)}")
        
        if stats.get('performance'):
            perf = stats['performance']
            print(f"平均执行时间: {perf.get('avg_execution_time', 0):.1f} 分钟")
            print(f"成功率: {perf.get('success_rate', 0):.1f}%")
            print(f"代码质量: {perf.get('avg_code_quality', 0):.0f}/100")
        
        if stats.get('today'):
            today = stats['today']
            print(f"今日创建: {today.get('tasks_created', 0)}")
            print(f"今日完成: {today.get('tasks_completed', 0)}")
            print(f"今日错误: {today.get('errors', 0)}")
        
        print("✅ 统计数据计算成功")
        return True
    except Exception as e:
        print(f"❌ 统计数据计算异常: {e}")
        return False


def test_dashboard_history():
    """测试历史数据计算"""
    print("\n" + "="*60)
    print("测试5: 历史数据计算")
    print("="*60)
    
    dashboard = get_dashboard()
    
    if not dashboard:
        print("❌ Dashboard实例不存在")
        return False
    
    try:
        # 计算历史数据
        history = dashboard.calculate_history(days=7)
        
        print(f"日期数量: {len(history.get('dates', []))}")
        print(f"创建任务数据点: {len(history.get('tasks_created', []))}")
        print(f"完成任务数据点: {len(history.get('tasks_completed', []))}")
        print(f"失败任务数据点: {len(history.get('tasks_failed', []))}")
        print(f"成功率数据点: {len(history.get('success_rates', []))}")
        
        print("✅ 历史数据计算成功")
        return True
    except Exception as e:
        print(f"❌ 历史数据计算异常: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Dashboard功能测试")
    print("="*60)
    
    results = []
    
    # 测试1: 启动
    results.append(("Dashboard启动", test_dashboard_startup()))
    
    # 测试2: API端点
    results.append(("API端点", test_api_endpoints()))
    
    # 测试3: 广播功能
    results.append(("Dashboard广播", test_dashboard_broadcast()))
    
    # 测试4: 统计数据
    results.append(("统计数据计算", test_dashboard_stats()))
    
    # 测试5: 历史数据
    results.append(("历史数据计算", test_dashboard_history()))
    
    # 打印测试结果
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    # 统计
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 测试通过")
    print("="*60)
    
    # 保持Dashboard运行
    print("\nDashboard将继续运行在 http://localhost:5001")
    print("按 Ctrl+C 退出...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n退出测试...")


if __name__ == '__main__':
    # 检查依赖
    try:
        import flask
        import flask_socketio
        import flask_cors
        print("✅ 所有依赖已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("\n请安装依赖:")
        print("pip install flask flask-socketio flask-cors requests")
        sys.exit(1)
    
    main()
