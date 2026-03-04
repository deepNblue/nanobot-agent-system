"""
节点服务器 - 接收和执行分布式任务

功能：
- HTTP API端点
- 任务接收和执行
- 节点状态报告
- 资源监控
- 检查点保存
"""

from flask import Flask, jsonify, request
import psutil
import asyncio
import threading
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import json
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局状态
tasks = {}
task_executor = None
node_config = {
    "node_id": os.getenv("NODE_ID", "node_1"),
    "port": int(os.getenv("NODE_PORT", 8000)),
    "max_concurrent_tasks": int(os.getenv("MAX_TASKS", 5)),
    "has_gpu": os.getenv("HAS_GPU", "false").lower() == "true",
    "gpu_memory": int(os.getenv("GPU_MEMORY", 0)),
    "available_env": os.getenv("AVAILABLE_ENV", "python3.11,nodejs,git").split(",")
}


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, max_concurrent_tasks: int = 5):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks = {}
        self.loop = None
        self.thread = None
    
    def start(self):
        """启动执行器"""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Task executor started")
    
    def _run_loop(self):
        """运行事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def execute_task(self, task_id: str, task: Dict):
        """执行任务"""
        if self.loop is None:
            logger.error("Event loop not initialized")
            return
        
        # 提交到事件循环
        asyncio.run_coroutine_threadsafe(
            self._execute_task_async(task_id, task),
            self.loop
        )
    
    async def _execute_task_async(self, task_id: str, task: Dict):
        """异步执行任务"""
        # 更新状态为运行中
        tasks[task_id]["status"] = "running"
        tasks[task_id]["started_at"] = datetime.now().isoformat()
        
        try:
            # 这里应该调用实际的Agent执行逻辑
            # 例如：await agent.execute(task)
            
            # 模拟执行
            await asyncio.sleep(30)
            
            # 完成
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["completed_at"] = datetime.now().isoformat()
            tasks[task_id]["result"] = {"message": "Task completed successfully"}
            
            logger.info(f"Task {task_id} completed")
        
        except Exception as e:
            # 失败
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)
            tasks[task_id]["failed_at"] = datetime.now().isoformat()
            
            logger.error(f"Task {task_id} failed: {e}")
        
        finally:
            # 从活跃任务中移除
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def get_active_task_count(self) -> int:
        """获取活跃任务数"""
        return len(self.active_tasks)


# API端点


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取节点状态"""
    try:
        # 获取系统资源信息
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 计算活跃任务数
        active_tasks = sum(
            1 for t in tasks.values()
            if t.get("status") == "running"
        )
        
        # GPU信息（如果有）
        gpu_info = {}
        if node_config["has_gpu"]:
            try:
                # 尝试获取GPU信息（需要pynvml库）
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                gpu_info = {
                    "gpu_usage": pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
                    "gpu_memory_used": pynvml.nvmlDeviceGetMemoryInfo(handle).used // (1024 ** 2),
                    "gpu_memory_total": pynvml.nvmlDeviceGetMemoryInfo(handle).total // (1024 ** 2)
                }
                pynvml.nvmlShutdown()
            except:
                gpu_info = {"error": "GPU info unavailable"}
        
        status = {
            "status": "healthy",
            "node_id": node_config["node_id"],
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "memory_available": memory.available // (1024 ** 3),  # GB
            "disk_usage": disk.percent,
            "disk_available_gb": disk.free // (1024 ** 3),
            "active_tasks": active_tasks,
            "max_concurrent_tasks": node_config["max_concurrent_tasks"],
            "network_latency": 0,
            "has_gpu": node_config["has_gpu"],
            "gpu_memory": node_config["gpu_memory"],
            "available_env": node_config["available_env"],
            "uptime": _get_uptime(),
            "timestamp": datetime.now().isoformat()
        }
        
        # 合并GPU信息
        status.update(gpu_info)
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route('/api/task', methods=['POST'])
def receive_task():
    """接收任务"""
    try:
        data = request.json
        task_id = data.get("task_id")
        task = data.get("task")
        
        if not task_id or not task:
            return jsonify({"error": "Missing task_id or task"}), 400
        
        # 检查并发限制
        active_count = task_executor.get_active_task_count()
        if active_count >= node_config["max_concurrent_tasks"]:
            return jsonify({
                "error": "Node at maximum capacity",
                "active_tasks": active_count,
                "max_tasks": node_config["max_concurrent_tasks"]
            }), 503
        
        # 保存任务
        tasks[task_id] = {
            **task,
            "id": task_id,
            "status": "pending",
            "received_at": datetime.now().isoformat()
        }
        
        # 异步执行任务
        task_executor.execute_task(task_id, task)
        
        logger.info(f"Received task {task_id}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "pending"
        })
    
    except Exception as e:
        logger.error(f"Error receiving task: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404
    
    task = tasks[task_id]
    
    # 构建响应
    response = {
        "task_id": task_id,
        "status": task.get("status"),
        "received_at": task.get("received_at"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "failed_at": task.get("failed_at"),
        "error": task.get("error"),
        "result": task.get("result")
    }
    
    # 包含检查点（如果有）
    if "checkpoint" in task:
        response["checkpoint"] = task["checkpoint"]
    
    return jsonify(response)


@app.route('/api/task/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """取消任务"""
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404
    
    task = tasks[task_id]
    status = task.get("status")
    
    # 检查是否可以取消
    if status == "completed":
        return jsonify({"error": "Task already completed"}), 400
    
    if status == "cancelled":
        return jsonify({"error": "Task already cancelled"}), 400
    
    # 更新状态
    tasks[task_id]["status"] = "cancelled"
    tasks[task_id]["cancelled_at"] = datetime.now().isoformat()
    
    # TODO: 实际取消正在运行的任务
    
    logger.info(f"Cancelled task {task_id}")
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "status": "cancelled"
    })


@app.route('/api/task/<task_id>/checkpoint', methods=['POST'])
def save_task_checkpoint(task_id):
    """保存任务检查点"""
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404
    
    try:
        checkpoint_data = request.json
        
        # 保存检查点
        tasks[task_id]["checkpoint"] = {
            "data": checkpoint_data,
            "saved_at": datetime.now().isoformat()
        }
        
        logger.info(f"Saved checkpoint for task {task_id}")
        
        return jsonify({"success": True})
    
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务"""
    # 分页参数
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    
    # 过滤参数
    status_filter = request.args.get("status")
    
    # 过滤任务
    filtered_tasks = list(tasks.values())
    
    if status_filter:
        filtered_tasks = [
            t for t in filtered_tasks
            if t.get("status") == status_filter
        ]
    
    # 排序（按接收时间倒序）
    filtered_tasks.sort(
        key=lambda t: t.get("received_at", ""),
        reverse=True
    )
    
    # 分页
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_tasks = filtered_tasks[start:end]
    
    return jsonify({
        "tasks": paginated_tasks,
        "total": len(filtered_tasks),
        "page": page,
        "per_page": per_page,
        "pages": (len(filtered_tasks) + per_page - 1) // per_page
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """获取详细指标"""
    try:
        # CPU指标
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        
        # 内存指标
        memory = psutil.virtual_memory()
        
        # 磁盘指标
        disk = psutil.disk_usage('/')
        
        # 网络指标
        net_io = psutil.net_io_counters()
        
        # 任务统计
        task_stats = {
            "total": len(tasks),
            "pending": sum(1 for t in tasks.values() if t.get("status") == "pending"),
            "running": sum(1 for t in tasks.values() if t.get("status") == "running"),
            "completed": sum(1 for t in tasks.values() if t.get("status") == "completed"),
            "failed": sum(1 for t in tasks.values() if t.get("status") == "failed"),
            "cancelled": sum(1 for t in tasks.values() if t.get("status") == "cancelled")
        }
        
        return jsonify({
            "cpu": {
                "percent_per_cpu": cpu_percent,
                "percent_avg": sum(cpu_percent) / len(cpu_percent)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            },
            "tasks": task_stats,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取节点配置"""
    return jsonify(node_config)


@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """关闭节点（需要授权）"""
    # TODO: 添加授权检查
    
    logger.info("Shutdown requested")
    
    # 优雅关闭
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    
    return jsonify({"message": "Shutting down"})


def _get_uptime() -> str:
    """获取运行时间"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}h {minutes}m {seconds}s"
    
    except:
        return "unknown"


def create_app(config: Dict = None) -> Flask:
    """
    创建Flask应用
    
    Args:
        config: 配置字典
    
    Returns:
        Flask应用实例
    """
    global node_config, task_executor
    
    if config:
        node_config.update(config)
    
    # 初始化任务执行器
    task_executor = TaskExecutor(
        max_concurrent_tasks=node_config["max_concurrent_tasks"]
    )
    task_executor.start()
    
    return app


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nanobot Node Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--node-id", default="node_1", help="Node ID")
    parser.add_argument("--max-tasks", type=int, default=5, help="Maximum concurrent tasks")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # 更新配置
    node_config["node_id"] = args.node_id
    node_config["port"] = args.port
    node_config["max_concurrent_tasks"] = args.max_tasks
    
    # 初始化任务执行器
    global task_executor
    task_executor = TaskExecutor(
        max_concurrent_tasks=node_config["max_concurrent_tasks"]
    )
    task_executor.start()
    
    logger.info(f"Starting node server on {args.host}:{args.port}")
    logger.info(f"Node ID: {args.node_id}")
    logger.info(f"Max concurrent tasks: {args.max_tasks}")
    
    # 启动Flask应用
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )


if __name__ == '__main__':
    main()
