/**
 * Nanobot Agent Dashboard - 前端交互逻辑
 * 
 * 功能：
 * - WebSocket实时连接
 * - 数据加载和更新
 * - 图表渲染
 * - 实时通知
 * - 错误处理
 */

// ==================== 全局变量 ====================

// WebSocket连接
let socket = null;

// 图表实例
let historyChart = null;
let agentChart = null;

// 数据缓存
let currentTasks = [];
let currentStats = {};

// 配置
const CONFIG = {
    refreshInterval: 5000,  // 数据刷新间隔（毫秒）
    chartColors: {
        primary: '#667eea',
        secondary: '#764ba2',
        success: '#28a745',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#17a2b8',
        gray: '#a0aec0'
    }
};

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Dashboard] 初始化...');
    
    // 初始化WebSocket
    initWebSocket();
    
    // 初始化图表
    initCharts();
    
    // 加载初始数据
    loadData();
    
    // 启动定时刷新
    setInterval(loadData, CONFIG.refreshInterval);
});

// ==================== WebSocket ====================

function initWebSocket() {
    console.log('[Dashboard] 连接WebSocket...');
    
    socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10
    });
    
    // 连接成功
    socket.on('connect', function() {
        console.log('[Dashboard] WebSocket已连接');
        updateConnectionStatus(true);
        showNotification('已连接到Dashboard', 'success');
    });
    
    // 连接断开
    socket.on('disconnect', function() {
        console.log('[Dashboard] WebSocket断开');
        updateConnectionStatus(false);
        showNotification('连接断开，正在重连...', 'warning');
    });
    
    // 连接错误
    socket.on('connect_error', function(error) {
        console.error('[Dashboard] WebSocket连接错误:', error);
        updateConnectionStatus(false);
    });
    
    // 接收统计更新
    socket.on('stats_update', function(stats) {
        console.log('[Dashboard] 收到统计更新');
        updateStats(stats);
    });
    
    // 接收任务更新
    socket.on('task_update', function(data) {
        console.log('[Dashboard] 收到任务更新:', data.task_id);
        updateTaskInList(data);
    });
    
    // 接收任务列表更新
    socket.on('tasks_update', function(data) {
        console.log('[Dashboard] 收到任务列表更新');
        updateTaskList(data.tasks);
    });
    
    // 接收错误警告
    socket.on('error_alert', function(error) {
        console.error('[Dashboard] 收到错误:', error);
        showErrorAlert(error);
        showNotification('任务执行出错', 'danger');
    });
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById('connection-dot');
    const text = document.getElementById('connection-text');
    
    if (connected) {
        dot.classList.add('connected');
        text.textContent = '已连接';
    } else {
        dot.classList.remove('connected');
        text.textContent = '未连接';
    }
}

// ==================== 数据加载 ====================

async function loadData() {
    console.log('[Dashboard] 加载数据...');
    
    try {
        // 并行加载数据
        const [statsRes, tasksRes, errorsRes, historyRes] = await Promise.all([
            fetch('/api/stats').then(r => r.json()),
            fetch('/api/tasks').then(r => r.json()),
            fetch('/api/errors?limit=5').then(r => r.json()),
            fetch('/api/history?days=7').then(r => r.json())
        ]);
        
        // 更新统计
        if (statsRes.success) {
            updateStats(statsRes.stats);
        }
        
        // 更新任务列表
        if (tasksRes.success) {
            updateTaskList(tasksRes.tasks);
        }
        
        // 更新错误列表
        if (errorsRes.success) {
            updateErrorList(errorsRes.errors);
        }
        
        // 更新历史图表
        if (historyRes.success) {
            updateHistoryChart(historyRes.history);
        }
        
        // 更新最后更新时间
        updateLastUpdateTime();
        
    } catch (error) {
        console.error('[Dashboard] 加载数据失败:', error);
        showNotification('数据加载失败', 'danger');
    }
}

// ==================== 数据更新 ====================

function updateStats(stats) {
    currentStats = stats;
    
    // 更新数字（带动画）
    updateNumber('running-count', stats.running || 0);
    updateNumber('completed-count', stats.completed || 0);
    updateNumber('failed-count', stats.failed || 0);
    updateNumber('pending-count', stats.pending || 0);
    updateNumber('total-count', stats.total || 0);
    
    // 性能指标
    if (stats.performance) {
        const avgTime = stats.performance.avg_execution_time || 0;
        document.getElementById('avg-time').textContent = avgTime.toFixed(1) + ' 分钟';
        
        const successRate = stats.performance.success_rate || 0;
        document.getElementById('success-rate').textContent = successRate.toFixed(1) + '%';
        
        const avgQuality = stats.performance.avg_code_quality || 0;
        document.getElementById('avg-quality').textContent = avgQuality.toFixed(0) + '/100';
        
        const avgRetry = stats.performance.avg_retry_count || 0;
        document.getElementById('avg-retry').textContent = avgRetry.toFixed(1);
    }
    
    // 今日统计
    if (stats.today) {
        updateNumber('today-completed', stats.today.tasks_completed || 0);
    }
    
    // Agent分布
    if (stats.agents) {
        updateAgentChart(stats.agents);
    }
}

function updateNumber(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const oldValue = parseInt(element.textContent) || 0;
    
    if (oldValue !== value) {
        element.textContent = value;
        element.classList.add('number-update');
        
        setTimeout(() => {
            element.classList.remove('number-update');
        }, 500);
    }
}

function updateTaskList(tasks) {
    currentTasks = tasks;
    const container = document.getElementById('task-list');
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state fade-in">
                <i class="fas fa-inbox"></i>
                <p>暂无任务</p>
            </div>
        `;
        return;
    }
    
    // 限制显示数量
    const displayTasks = tasks.slice(0, 20);
    
    container.innerHTML = displayTasks.map(task => createTaskCard(task)).join('');
}

function updateTaskInList(updatedTask) {
    // 查找并更新任务
    const index = currentTasks.findIndex(t => t.id === updatedTask.task_id);
    
    if (index !== -1) {
        currentTasks[index] = { ...currentTasks[index], ...updatedTask };
    } else {
        // 新任务，添加到开头
        currentTasks.unshift(updatedTask);
    }
    
    // 重新渲染任务列表
    updateTaskList(currentTasks);
}

function createTaskCard(task) {
    const statusClass = task.status || 'pending';
    const statusBadge = getStatusBadge(task.status);
    const progressBar = task.status === 'running' ? `
        <div class="progress mt-2">
            <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                 style="width: ${task.progress || 0}%"></div>
        </div>
    ` : '';
    
    const description = task.description || task.id || '未知任务';
    const agent = task.agent || 'unknown';
    const createdAt = formatTime(task.createdAt || task.startedAt);
    
    return `
        <div class="task-card ${statusClass} fade-in">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="task-description">${escapeHtml(description)}</div>
                    <div class="task-meta">
                        <span class="me-3">
                            <i class="fas fa-robot"></i> ${agent}
                        </span>
                        <span class="me-3">
                            <i class="fas fa-clock"></i> ${createdAt}
                        </span>
                        ${task.branch ? `
                            <span class="me-3">
                                <i class="fas fa-code-branch"></i> ${task.branch}
                            </span>
                        ` : ''}
                        ${task.execution_time ? `
                            <span>
                                <i class="fas fa-stopwatch"></i> ${(task.execution_time / 60).toFixed(1)} 分钟
                            </span>
                        ` : ''}
                    </div>
                    ${progressBar}
                </div>
                <div class="ms-3">
                    ${statusBadge}
                </div>
            </div>
        </div>
    `;
}

function getStatusBadge(status) {
    const statusConfig = {
        'running': { class: 'bg-primary', text: '运行中', icon: 'spinner fa-spin' },
        'completed': { class: 'bg-success', text: '已完成', icon: 'check-circle' },
        'failed': { class: 'bg-danger', text: '失败', icon: 'times-circle' },
        'pending': { class: 'bg-secondary', text: '等待中', icon: 'clock' },
        'merged': { class: 'bg-info', text: '已合并', icon: 'code-merge' }
    };
    
    const config = statusConfig[status] || statusConfig['pending'];
    
    return `
        <span class="badge ${config.class}">
            <i class="fas fa-${config.icon}"></i> ${config.text}
        </span>
    `;
}

function updateErrorList(errors) {
    const container = document.getElementById('error-list');
    
    if (!errors || errors.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-check-circle text-success"></i>
                <p>暂无错误</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = errors.map(error => `
        <div class="error-alert fade-in">
            <small class="text-muted d-block mb-1">
                <i class="fas fa-clock"></i> ${formatTime(error.timestamp)}
            </small>
            <p>${escapeHtml(error.message || error.error || '未知错误')}</p>
        </div>
    `).join('');
}

function showErrorAlert(error) {
    const container = document.getElementById('error-list');
    
    // 移除空状态提示
    const emptyState = container.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }
    
    // 添加新错误到开头
    const alertHtml = `
        <div class="error-alert fade-in">
            <small class="text-muted d-block mb-1">
                <i class="fas fa-clock"></i> ${formatTime(error.timestamp)}
            </small>
            <p>${escapeHtml(error.message || error.error || '未知错误')}</p>
        </div>
    `;
    
    container.insertAdjacentHTML('afterbegin', alertHtml);
    
    // 限制显示数量
    const alerts = container.querySelectorAll('.error-alert');
    if (alerts.length > 5) {
        alerts[alerts.length - 1].remove();
    }
}

// ==================== 图表 ====================

function initCharts() {
    // 历史趋势图
    const historyCtx = document.getElementById('historyChart');
    if (historyCtx) {
        historyChart = new Chart(historyCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '创建任务',
                        data: [],
                        borderColor: CONFIG.chartColors.primary,
                        backgroundColor: hexToRgba(CONFIG.chartColors.primary, 0.1),
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: '完成任务',
                        data: [],
                        borderColor: CONFIG.chartColors.success,
                        backgroundColor: hexToRgba(CONFIG.chartColors.success, 0.1),
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
    
    // Agent分布图
    const agentCtx = document.getElementById('agentChart');
    if (agentCtx) {
        agentChart = new Chart(agentCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        CONFIG.chartColors.primary,
                        CONFIG.chartColors.success,
                        CONFIG.chartColors.warning,
                        CONFIG.chartColors.info,
                        CONFIG.chartColors.danger,
                        CONFIG.chartColors.secondary,
                        CONFIG.chartColors.gray
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

function updateHistoryChart(history) {
    if (!historyChart || !history) return;
    
    historyChart.data.labels = history.dates.map(date => formatDate(date));
    historyChart.data.datasets[0].data = history.tasks_created;
    historyChart.data.datasets[1].data = history.tasks_completed;
    historyChart.update('none');  // 不使用动画
}

function updateAgentChart(agents) {
    if (!agentChart || !agents) return;
    
    const labels = Object.keys(agents);
    const data = Object.values(agents);
    
    agentChart.data.labels = labels;
    agentChart.data.datasets[0].data = data;
    agentChart.update('none');
}

// ==================== 辅助函数 ====================

function formatTime(timestamp) {
    if (!timestamp) return '未知时间';
    
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        // 小于1分钟
        if (diff < 60000) {
            return '刚刚';
        }
        
        // 小于1小时
        if (diff < 3600000) {
            return Math.floor(diff / 60000) + ' 分钟前';
        }
        
        // 小于24小时
        if (diff < 86400000) {
            return Math.floor(diff / 3600000) + ' 小时前';
        }
        
        // 否则显示日期时间
        return date.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return timestamp;
    }
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            month: '2-digit',
            day: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

function updateLastUpdateTime() {
    const element = document.getElementById('last-update-time');
    if (element) {
        element.textContent = new Date().toLocaleTimeString('zh-CN');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function showNotification(message, type = 'info') {
    // 简单的控制台通知（可以扩展为Toast通知）
    const timestamp = new Date().toLocaleTimeString('zh-CN');
    const prefix = {
        'success': '✅',
        'danger': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    console.log(`[${timestamp}] ${prefix[type] || 'ℹ️'} ${message}`);
}

// ==================== 事件处理 ====================

// 页面可见性变化时重新连接
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible' && socket && !socket.connected) {
        console.log('[Dashboard] 页面可见，尝试重新连接...');
        socket.connect();
    }
});

// 窗口关闭前清理
window.addEventListener('beforeunload', function() {
    if (socket) {
        socket.disconnect();
    }
});

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    // Ctrl+R 或 F5: 刷新数据
    if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
        e.preventDefault();
        loadData();
    }
});
