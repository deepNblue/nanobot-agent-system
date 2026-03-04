"""
Nanobot AI Agent系统 - Dashboard可视化监控（Phase 3）
实时监控Agent任务执行、统计数据、性能指标

功能：
- 实时任务状态监控
- WebSocket实时更新
- 统计数据展示
- 性能指标分析
- 错误日志追踪
- 响应式Web界面

技术栈：
- Flask (Web框架)
- Flask-SocketIO (WebSocket)
- Bootstrap 5 (UI)
- Chart.js (图表)
"""

import os
import json
import glob
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# 配置日志
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Dashboard:
    """Dashboard管理器"""

    def __init__(self, port: int = 5000, tasks_dir: Optional[str] = None):
        """
        初始化Dashboard

        Args:
            port: 监听端口
            tasks_dir: 任务目录路径
        """
        self.app = Flask(
            __name__,
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static"),
        )
        self.app.config["SECRET_KEY"] = "nanobot-dashboard-secret-key"

        # 启用CORS
        CORS(self.app)

        # 初始化SocketIO（使用threading模式以兼容性更好）
        self.socketio = SocketIO(
            self.app, cors_allowed_origins="*", async_mode="threading", logger=False, engineio_logger=False
        )

        self.port = port
        self.tasks_dir = tasks_dir or str(Path.home() / ".nanobot" / "workspace" / "skills" / "agent-system" / ".worktrees")

        # 数据存储
        self.active_tasks = {}
        self.stats_cache = {}
        self.error_log = []
        self.max_error_log = 100  # 最多保留100条错误日志

        # 缓存配置
        self.cache_timeout = 5  # 缓存5秒
        self.last_cache_update = 0
        self.cached_stats = None

        # 设置路由和事件
        self.setup_routes()
        self.setup_socket_events()

        # 启动后台任务
        self.start_background_tasks()

        logger.info(f"[Dashboard] 初始化完成，任务目录: {self.tasks_dir}")

    def setup_routes(self):
        """设置HTTP路由"""

        @self.app.route("/")
        def index():
            """主页"""
            return render_template("dashboard.html")

        @self.app.route("/api/tasks")
        def get_tasks():
            """获取任务列表"""
            try:
                tasks = self.get_all_tasks()
                return jsonify({"success": True, "tasks": tasks, "count": len(tasks)})
            except Exception as e:
                logger.error(f"[Dashboard] 获取任务列表失败: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/stats")
        def get_stats():
            """获取统计数据"""
            try:
                stats = self.calculate_stats()
                return jsonify({"success": True, "stats": stats})
            except Exception as e:
                logger.error(f"[Dashboard] 获取统计数据失败: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/task/<task_id>")
        def get_task(task_id):
            """获取任务详情"""
            try:
                task = self.load_task(task_id)
                if "error" in task:
                    return jsonify({"success": False, "error": task["error"]}), 404

                return jsonify({"success": True, "task": task})
            except Exception as e:
                logger.error(f"[Dashboard] 获取任务详情失败: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/errors")
        def get_errors():
            """获取错误日志"""
            try:
                limit = request.args.get("limit", 10, type=int)
                limit = min(limit, 100)  # 最多100条
                errors = self.error_log[-limit:]

                return jsonify({"success": True, "errors": errors, "count": len(errors), "total": len(self.error_log)})
            except Exception as e:
                logger.error(f"[Dashboard] 获取错误日志失败: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/health")
        def health_check():
            """健康检查"""
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": time.time() - self.start_time if hasattr(self, "start_time") else 0,
                }
            )

        @self.app.route("/api/performance")
        def get_performance():
            """获取性能指标"""
            try:
                performance = self.calculate_performance_metrics()
                return jsonify({"success": True, "performance": performance})
            except Exception as e:
                logger.error(f"[Dashboard] 获取性能指标失败: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/history")
        def get_history():
            """获取历史数据（用于图表）"""
            try:
                days = request.args.get("days", 7, type=int)
                days = min(days, 30)  # 最多30天

                history = self.calculate_history(days)
                return jsonify({"success": True, "history": history})
            except Exception as e:
                logger.error(f"[Dashboard] 获取历史数据失败: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

    def setup_socket_events(self):
        """设置WebSocket事件"""

        @self.socketio.on("connect")
        def handle_connect():
            """客户端连接"""
            client_id = request.sid
            logger.info(f"[Dashboard] 客户端连接: {client_id}")

            emit("connected", {"message": "Connected to Dashboard", "timestamp": datetime.now().isoformat()})

            # 发送当前状态
            try:
                stats = self.calculate_stats()
                emit("stats_update", stats)

                tasks = self.get_all_tasks()
                emit("tasks_update", {"tasks": tasks})
            except Exception as e:
                logger.error(f"[Dashboard] 发送初始数据失败: {e}")

        @self.socketio.on("disconnect")
        def handle_disconnect():
            """客户端断开"""
            client_id = request.sid
            logger.info(f"[Dashboard] 客户端断开: {client_id}")

        @self.socketio.on("request_update")
        def handle_update_request(data):
            """处理更新请求"""
            task_id = data.get("task_id")

            if task_id:
                task = self.load_task(task_id)
                emit("task_update", task)
            else:
                # 发送所有任务更新
                tasks = self.get_all_tasks()
                emit("tasks_update", {"tasks": tasks})

        @self.socketio.on("request_stats")
        def handle_stats_request():
            """处理统计请求"""
            stats = self.calculate_stats()
            emit("stats_update", stats)

        @self.socketio.on("subscribe_task")
        def handle_subscribe_task(data):
            """订阅特定任务的更新"""
            task_id = data.get("task_id")
            if task_id:
                # 将客户端添加到任务订阅列表
                # 这里可以扩展为按任务分组的房间
                emit("subscribed", {"task_id": task_id})

    def broadcast_task_update(self, task_id: str, update: Dict):
        """
        广播任务更新

        Args:
            task_id: 任务ID
            update: 更新内容
        """
        try:
            message = {"task_id": task_id, "timestamp": datetime.now().isoformat(), **update}

            self.socketio.emit("task_update", message)
            logger.debug(f"[Dashboard] 广播任务更新: {task_id}")
        except Exception as e:
            logger.error(f"[Dashboard] 广播任务更新失败: {e}")

    def broadcast_error(self, error: Dict):
        """
        广播错误

        Args:
            error: 错误信息
        """
        try:
            error["timestamp"] = error.get("timestamp", datetime.now().isoformat())

            # 添加到错误日志
            self.error_log.append(error)

            # 限制日志大小
            if len(self.error_log) > self.max_error_log:
                self.error_log = self.error_log[-self.max_error_log :]

            # 广播错误
            self.socketio.emit("error_alert", error)
            logger.warning(f"[Dashboard] 广播错误: {error.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"[Dashboard] 广播错误失败: {e}")

    def broadcast_stats_update(self):
        """广播统计更新"""
        try:
            stats = self.calculate_stats()
            self.socketio.emit("stats_update", stats)
        except Exception as e:
            logger.error(f"[Dashboard] 广播统计更新失败: {e}")

    def get_all_tasks(self) -> List[Dict]:
        """
        获取所有任务

        Returns:
            任务列表
        """
        tasks = []

        if not os.path.exists(self.tasks_dir):
            logger.warning(f"[Dashboard] 任务目录不存在: {self.tasks_dir}")
            return tasks

        # 从worktrees目录加载任务
        for task_file in glob.glob(f"{self.tasks_dir}/*/task.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task = json.load(f)
                    tasks.append(task)
            except Exception as e:
                logger.error(f"[Dashboard] 加载任务文件失败 {task_file}: {e}")

        # 也从agent_tasks目录加载
        agent_tasks_dir = str(Path.home() / ".nanobot" / "workspace" / "agent_tasks")
        if os.path.exists(agent_tasks_dir):
            for task_file in glob.glob(f"{agent_tasks_dir}/*.json"):
                try:
                    with open(task_file, "r", encoding="utf-8") as f:
                        task = json.load(f)
                        # 避免重复
                        if not any(t.get("id") == task.get("id") for t in tasks):
                            tasks.append(task)
                except Exception as e:
                    logger.error(f"[Dashboard] 加载任务文件失败 {task_file}: {e}")

        # 按创建时间排序（最新的在前）
        tasks.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

        return tasks

    def load_task(self, task_id: str) -> Dict:
        """
        加载单个任务

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        # 尝试从worktrees加载
        task_file = os.path.join(self.tasks_dir, task_id, "task.json")

        if not os.path.exists(task_file):
            # 尝试从agent_tasks加载
            task_file = str(Path.home() / ".nanobot" / "workspace" / "agent_tasks" / f"{task_id}.json")

        if os.path.exists(task_file):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[Dashboard] 加载任务失败 {task_file}: {e}")
                return {"error": f"加载失败: {e}"}

        return {"error": "Task not found"}

    def calculate_stats(self) -> Dict:
        """
        计算统计数据（带缓存）

        Returns:
            统计数据
        """
        # 检查缓存
        current_time = time.time()
        if self.cached_stats and current_time - self.last_cache_update < self.cache_timeout:
            return self.cached_stats

        tasks = self.get_all_tasks()

        # 基础统计
        stats = {
            "total": len(tasks),
            "running": sum(1 for t in tasks if t.get("status") == "running"),
            "completed": sum(1 for t in tasks if t.get("status") == "completed"),
            "failed": sum(1 for t in tasks if t.get("status") == "failed"),
            "pending": sum(1 for t in tasks if t.get("status") == "pending"),
            "merged": sum(1 for t in tasks if t.get("status") == "merged"),
            "timestamp": datetime.now().isoformat(),
        }

        # 性能指标
        stats["performance"] = {
            "avg_execution_time": self._calculate_avg_time(tasks),
            "success_rate": self._calculate_success_rate(tasks),
            "avg_code_quality": self._calculate_avg_quality(tasks),
            "avg_retry_count": self._calculate_avg_retry(tasks),
        }

        # 今日统计
        stats["today"] = {
            "tasks_created": self._count_today(tasks, "createdAt"),
            "tasks_completed": self._count_today(tasks, "completedAt"),
            "errors": self._count_today_errors(),
        }

        # Agent类型分布
        stats["agents"] = self._calculate_agent_distribution(tasks)

        # 优先级分布
        stats["priorities"] = self._calculate_priority_distribution(tasks)

        # 更新缓存
        self.cached_stats = stats
        self.last_cache_update = current_time

        return stats

    def calculate_performance_metrics(self) -> Dict:
        """
        计算性能指标

        Returns:
            性能指标
        """
        tasks = self.get_all_tasks()

        # 按日期分组的统计
        daily_stats = {}

        for task in tasks:
            created_at = task.get("createdAt")
            if created_at:
                try:
                    date = datetime.fromisoformat(created_at).date()
                    date_str = date.isoformat()

                    if date_str not in daily_stats:
                        daily_stats[date_str] = {"total": 0, "completed": 0, "failed": 0, "avg_time": []}

                    daily_stats[date_str]["total"] += 1

                    if task.get("status") == "completed":
                        daily_stats[date_str]["completed"] += 1

                    if task.get("status") == "failed":
                        daily_stats[date_str]["failed"] += 1

                    if task.get("execution_time"):
                        daily_stats[date_str]["avg_time"].append(task["execution_time"])
                except Exception as e:
                    logger.error(f"[Dashboard] 处理任务日期失败: {e}")

        # 计算每日平均时间
        for date_str, stats in daily_stats.items():
            if stats["avg_time"]:
                stats["avg_time"] = sum(stats["avg_time"]) / len(stats["avg_time"])
            else:
                stats["avg_time"] = 0

        return {
            "daily_stats": daily_stats,
            "overall": {
                "total_tasks": len(tasks),
                "success_rate": self._calculate_success_rate(tasks),
                "avg_execution_time": self._calculate_avg_time(tasks),
            },
        }

    def calculate_history(self, days: int = 7) -> Dict:
        """
        计算历史数据

        Args:
            days: 天数

        Returns:
            历史数据
        """
        tasks = self.get_all_tasks()

        # 初始化历史数据
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        history = {"dates": [], "tasks_created": [], "tasks_completed": [], "tasks_failed": [], "success_rates": []}

        # 按日期统计
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.isoformat()

            history["dates"].append(date_str)

            # 统计当天创建的任务
            created = sum(1 for t in tasks if self._is_date(t.get("createdAt"), date))
            history["tasks_created"].append(created)

            # 统计当天完成的任务
            completed = sum(1 for t in tasks if self._is_date(t.get("completedAt"), date))
            history["tasks_completed"].append(completed)

            # 统计当天失败的任务
            failed = sum(1 for t in tasks if self._is_date(t.get("completedAt"), date) and t.get("status") == "failed")
            history["tasks_failed"].append(failed)

            # 计算成功率
            total = completed + failed
            success_rate = (completed / total * 100) if total > 0 else 0
            history["success_rates"].append(round(success_rate, 1))

        return history

    def _calculate_avg_time(self, tasks: List[Dict]) -> float:
        """计算平均执行时间（分钟）"""
        completed = [t for t in tasks if t.get("execution_time")]
        if not completed:
            return 0.0

        avg_seconds = sum(t["execution_time"] for t in completed) / len(completed)
        return round(avg_seconds / 60, 1)  # 转换为分钟

    def _calculate_success_rate(self, tasks: List[Dict]) -> float:
        """计算成功率（百分比）"""
        finished = [t for t in tasks if t.get("status") in ["completed", "failed", "merged"]]
        if not finished:
            return 0.0

        success = sum(1 for t in finished if t["status"] in ["completed", "merged"])
        return round((success / len(finished)) * 100, 1)

    def _calculate_avg_quality(self, tasks: List[Dict]) -> float:
        """计算平均代码质量"""
        reviewed = [t for t in tasks if t.get("code_review", {}).get("score")]
        if not reviewed:
            return 0.0

        return round(sum(t["code_review"]["score"] for t in reviewed) / len(reviewed), 1)

    def _calculate_avg_retry(self, tasks: List[Dict]) -> float:
        """计算平均重试次数"""
        with_retry = [t for t in tasks if t.get("ci_retry_count")]
        if not with_retry:
            return 0.0

        return round(sum(t["ci_retry_count"] for t in with_retry) / len(with_retry), 1)

    def _count_today(self, tasks: List[Dict], field: str) -> int:
        """统计今天的任务"""
        count = 0
        today = datetime.now().date()

        for task in tasks:
            timestamp = task.get(field)
            if timestamp and self._is_today(timestamp):
                count += 1

        return count

    def _count_today_errors(self) -> int:
        """统计今天的错误数"""
        count = 0
        today = datetime.now().date()

        for error in self.error_log:
            timestamp = error.get("timestamp")
            if timestamp:
                try:
                    error_date = datetime.fromisoformat(timestamp).date()
                    if error_date == today:
                        count += 1
                except Exception as e:
                    pass

        return count

    def _is_today(self, timestamp: str) -> bool:
        """判断是否是今天"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.date() == datetime.now().date()
        except Exception as e:
            return False

    def _is_date(self, timestamp: str, date) -> bool:
        """判断是否是特定日期"""
        if not timestamp:
            return False

        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.date() == date
        except Exception as e:
            return False

    def _calculate_agent_distribution(self, tasks: List[Dict]) -> Dict:
        """计算Agent类型分布"""
        distribution = {}

        for task in tasks:
            agent = task.get("agent", "unknown")
            distribution[agent] = distribution.get(agent, 0) + 1

        return distribution

    def _calculate_priority_distribution(self, tasks: List[Dict]) -> Dict:
        """计算优先级分布"""
        distribution = {}

        for task in tasks:
            priority = task.get("priority", "medium")
            distribution[priority] = distribution.get(priority, 0) + 1

        return distribution

    def start_background_tasks(self):
        """启动后台任务"""

        def stats_updater():
            """定期更新统计数据"""
            while True:
                try:
                    time.sleep(10)  # 每10秒更新一次
                    self.broadcast_stats_update()
                except Exception as e:
                    logger.error(f"[Dashboard] 后台统计更新失败: {e}")

        # 启动后台线程
        thread = threading.Thread(target=stats_updater, daemon=True)
        thread.start()

        logger.info("[Dashboard] 后台任务已启动")

    def run(self):
        """启动Dashboard"""
        self.start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"[Dashboard] 启动中...")
        logger.info(f"[Dashboard] 监听端口: {self.port}")
        logger.info(f"[Dashboard] 访问地址: http://0.0.0.0:{self.port}")
        logger.info(f"[Dashboard] 本地访问: http://localhost:{self.port}")
        logger.info("=" * 60)

        try:
            self.socketio.run(self.app, host="0.0.0.0", port=self.port, debug=False, allow_unsafe_werkzeug=True)
        except Exception as e:
            logger.error(f"[Dashboard] 启动失败: {e}")
            raise


# 全局实例
dashboard = None
dashboard_thread = None


def start_dashboard(port: int = 5000, tasks_dir: Optional[str] = None):
    """
    启动Dashboard（在后台线程中运行）

    Args:
        port: 监听端口
        tasks_dir: 任务目录路径

    Returns:
        Dashboard实例
    """
    global dashboard, dashboard_thread

    if dashboard:
        logger.warning("[Dashboard] Dashboard已在运行")
        return dashboard

    try:
        # 创建Dashboard实例
        dashboard = Dashboard(port=port, tasks_dir=tasks_dir)

        # 在后台线程中启动
        dashboard_thread = threading.Thread(target=dashboard.run, daemon=True)
        dashboard_thread.start()

        # 等待启动
        time.sleep(1)

        logger.info("[Dashboard] Dashboard已启动")
        return dashboard

    except Exception as e:
        logger.error(f"[Dashboard] 启动失败: {e}")
        return None


def get_dashboard() -> Optional[Dashboard]:
    """
    获取Dashboard实例

    Returns:
        Dashboard实例或None
    """
    return dashboard


def stop_dashboard():
    """停止Dashboard"""
    global dashboard, dashboard_thread

    if dashboard:
        logger.info("[Dashboard] 停止Dashboard...")
        # SocketIO没有直接的停止方法，依赖daemon线程自动退出
        dashboard = None
        dashboard_thread = None


# 直接运行时的入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Nanobot Agent Dashboard")
    parser.add_argument("--port", type=int, default=5000, help="Dashboard端口")
    parser.add_argument("--tasks-dir", type=str, help="任务目录路径")

    args = parser.parse_args()

    # 创建并运行Dashboard
    dashboard = Dashboard(port=args.port, tasks_dir=args.tasks_dir)
    dashboard.run()
