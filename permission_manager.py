"""
权限管理器 - 管理用户权限和访问控制

功能：
1. 角色定义
2. 权限检查
3. 访问控制
4. 权限审计
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime


class Role(Enum):
    """角色枚举"""

    ADMIN = "admin"
    OWNER = "owner"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


@dataclass
class Permission:
    """权限"""

    resource: str  # 资源类型：project, task, code, settings
    action: str  # 操作：create, read, update, delete, review, assign
    conditions: Dict = None  # 条件


class PermissionManager:
    """权限管理器"""

    def __init__(self):
        # 角色权限映射
        self.role_permissions = {
            Role.ADMIN: {
                # 管理员：所有权限
                "all": ["*"]
            },
            Role.OWNER: {
                # 所有者：项目级所有权限
                "project": ["create", "read", "update", "delete"],
                "task": ["create", "read", "update", "delete", "assign"],
                "code": ["create", "read", "update", "delete", "review"],
                "settings": ["read", "update"],
                "members": ["invite", "remove", "update_role"],
            },
            Role.DEVELOPER: {
                # 开发者：代码和任务权限
                "project": ["read"],
                "task": ["create", "read", "update"],
                "code": ["create", "read", "update"],
                "settings": ["read"],
            },
            Role.REVIEWER: {
                # 审核者：代码审查权限
                "project": ["read"],
                "task": ["read"],
                "code": ["read", "review"],
                "settings": [],
            },
            Role.VIEWER: {
                # 查看者：只读权限
                "project": ["read"],
                "task": ["read"],
                "code": ["read"],
                "settings": [],
            },
        }

        # 特殊权限规则
        self.special_rules = {
            # 任务只能被分配者或管理员修改
            "task_update": lambda user_id, resource: (
                resource.get("assigned_to") == user_id or self.has_role(user_id, Role.ADMIN)
            ),
            # 代码只能被创建者或审核者删除
            "code_delete": lambda user_id, resource: (
                resource.get("created_by") == user_id or self.has_role(user_id, Role.ADMIN)
            ),
        }

    def check_permission(
        self, user_id: str, resource: str, action: str, resource_data: Dict = None, user_role: Role = None
    ) -> bool:
        """
        检查权限

        Args:
            user_id: 用户ID
            resource: 资源类型（project, task, code, settings）
            action: 操作（create, read, update, delete, review, assign）
            resource_data: 资源数据（用于特殊规则检查）
            user_role: 用户角色

        Returns:
            是否有权限
        """
        # 1. 获取用户角色
        if user_role is None:
            user_role = self.get_user_role(user_id)

        # 2. 获取角色权限
        role_perms = self.role_permissions.get(user_role, {})

        # 3. 检查通配符权限（管理员）
        if "*" in role_perms.get("all", []):
            return True

        # 4. 检查资源权限
        allowed_actions = role_perms.get(resource, [])

        if action not in allowed_actions:
            return False

        # 5. 检查特殊规则
        rule_key = f"{resource}_{action}"
        if rule_key in self.special_rules:
            if resource_data is None:
                resource_data = {}

            return self.special_rules[rule_key](user_id, resource_data)

        return True

    def has_role(self, user_id: str, role: Role) -> bool:
        """检查用户是否有指定角色（简化版）"""
        # 实际实现应该查询数据库
        return False

    def get_user_role(self, user_id: str) -> Role:
        """获取用户角色（简化版）"""
        # 实际实现应该查询数据库
        return Role.DEVELOPER

    def grant_permission(self, user_id: str, resource: str, actions: List[str], conditions: Dict = None):
        """授予自定义权限"""
        # 实际实现应该保存到数据库
        pass

    def revoke_permission(self, user_id: str, resource: str, actions: List[str]):
        """撤销权限"""
        # 实际实现应该从数据库删除
        pass

    def get_user_permissions(self, user_id: str) -> Dict:
        """获取用户所有权限"""
        role = self.get_user_role(user_id)

        return self.role_permissions.get(role, {})

    def audit_permission_change(self, user_id: str, action: str, resource: str, granted_by: str, timestamp: datetime = None):
        """审计权限变更"""
        audit_log = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "granted_by": granted_by,
            "timestamp": (timestamp or datetime.now()).isoformat(),
        }

        # 实际实现应该保存到审计日志
        print(f"Permission audit: {audit_log}")

        return audit_log


# 权限装饰器
def require_permission(resource: str, action: str):
    """权限检查装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从参数中获取user_id
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            if not user_id:
                raise PermissionError("User ID required")

            # 检查权限
            pm = PermissionManager()

            if not pm.check_permission(user_id, resource, action):
                raise PermissionError(f"User {user_id} does not have permission to {action} {resource}")

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 使用示例
if __name__ == "__main__":
    pm = PermissionManager()

    # 检查权限
    user_id = "user_123"

    # 开发者创建任务
    has_perm = pm.check_permission(user_id=user_id, resource="task", action="create", user_role=Role.DEVELOPER)
    print(f"Developer can create task: {has_perm}")

    # 查看者删除任务
    has_perm = pm.check_permission(user_id=user_id, resource="task", action="delete", user_role=Role.VIEWER)
    print(f"Viewer can delete task: {has_perm}")

    # 审核者审查代码
    has_perm = pm.check_permission(user_id=user_id, resource="code", action="review", user_role=Role.REVIEWER)
    print(f"Reviewer can review code: {has_perm}")

    # 获取用户权限
    permissions = pm.get_user_permissions(user_id)
    print(f"User permissions: {permissions}")
