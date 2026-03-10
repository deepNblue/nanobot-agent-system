"""
Agent集群系统配置文件
使用nanobot配置文件中的GLM-5
"""

# GLM-5配置（从nanobot config.json读取）
GLM5_CONFIG = {
    "model": "zhipu/glm-5",
    "provider": "zhipu",
    "api_key": "268cd5516f1547d2a6705ee616ec311a.IIjRJs4bJzrZTpET",
    "api_base": "https://open.bigmodel.cn/api/coding/paas/v4",
    "max_tokens": 8192,
    "temperature": 0.1
}

# OpenCode CLI配置（仍然使用OpenCode的模型）
OPENCODE_CONFIG = {
    "models": {
        "free": "minimax-m2.5-free",
        "fast": "mimo-v2-flash-free",
        "premium": "zai/glm-5"
    },
    "default_model": "free"
}

# 任务类型配置
TASK_TYPES = {
    "development": {
        "name": "开发",
        "agent_mode": "build",
        "description": "代码生成和开发 - 适合实现新功能、创建文件"
    },
    "planning": {
        "name": "规划",
        "agent_mode": "plan",
        "description": "项目规划和架构设计 - 适合系统设计、技术选型"
    },
    "exploration": {
        "name": "探索",
        "agent_mode": "explore",
        "description": "代码探索和理解 - 适合查看代码、理解逻辑"
    },
    "debugging": {
        "name": "调试",
        "agent_mode": "debug",
        "description": "Bug调试和修复 - 适合定位问题、修复错误"
    },
    "testing": {
        "name": "测试",
        "agent_mode": "test",
        "description": "测试用例生成 - 适合编写测试、验证功能"
    },
    "review": {
        "name": "审查",
        "agent_mode": "review",
        "description": "代码审查和优化 - 适合代码优化、质量检查"
    }
}

# Agent模式配置
AGENT_MODES = {
    "build": {
        "name": "代码生成",
        "slash_command": "/opencode-gen",
        "description": "生成新代码、实现功能"
    },
    "plan": {
        "name": "项目规划",
        "slash_command": "/opencode-plan",
        "description": "系统设计、架构制定"
    },
    "explore": {
        "name": "代码探索",
        "slash_command": "/opencode-explore",
        "description": "查看代码、理解逻辑"
    },
    "debug": {
        "name": "调试修复",
        "slash_command": "/opencode-debug",
        "description": "定位问题、修复Bug"
    },
    "test": {
        "name": "测试生成",
        "slash_command": "/opencode-test",
        "description": "编写测试、验证功能"
    },
    "review": {
        "name": "代码审查",
        "slash_command": "/opencode-review",
        "description": "代码优化、质量检查"
    }
}

# 复杂度阈值
COMPLEXITY_THRESHOLDS = {
    "high": {
        "keywords": ["架构", "重构", "系统设计", "完整", "复杂"],
        "estimated_time_multiplier": 3.0
    },
    "medium": {
        "keywords": ["优化", "改进", "扩展", "集成"],
        "estimated_time_multiplier": 2.0
    },
    "low": {
        "keywords": ["简单", "实现", "修复", "添加"],
        "estimated_time_multiplier": 1.0
    }
}
