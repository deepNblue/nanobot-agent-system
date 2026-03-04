"""
协作功能测试

测试协作管理器的各项功能
"""

import pytest
import asyncio
from collaboration_manager import CollaborationManager
from permission_manager import PermissionManager, Role
from realtime_collaboration import RealtimeCollaboration, Operation, Cursor


import tempfile


import os


from pathlib import Path


class TestCollaboration:
    """协作功能测试"""

    @pytest.fixture
    def collaboration_manager(self, tmp_path):
        """协作管理器"""
        manager = CollaborationManager(db_path=str(tmp_path / "collab.db"))
        yield manager

    @pytest.fixture
    def permission_manager(self):
        """权限管理器"""
        return PermissionManager()

    @pytest.fixture
    def realtime_collaboration(self):
        """实时协作"""
        return RealtimeCollaboration()

    @pytest.mark.asyncio
    async def test_create_project(self, collaboration_manager):
        """测试创建项目"""
        project_data = {"name": "Test Project", "description": "A test project", "owner": "user_1"}

        project = await collaboration_manager.create_project(project_data)

        assert project.id is not None
        assert project.name == "Test Project"

    @pytest.mark.asyncio
    async def test_join_project(self, collaboration_manager):
        """测试加入项目"""
        # 创建用户
        user1 = await collaboration_manager.create_user({"name": "Alice", "email": "alice@example.com"})

        user2 = await collaboration_manager.create_user({"name": "Bob", "email": "bob@example.com"})

        # 创建项目
        project = await collaboration_manager.create_project(
            {"name": "Test Project", "description": "Test", "owner": user1.id}
        )

        # 加入项目
        joined = await collaboration_manager.join_project(user2.id, project.id)

        assert joined

    @pytest.mark.asyncio
    async def test_task_management(self, collaboration_manager):
        """测试任务管理"""
        # 创建任务
        task_data = {
            "project_id": (await collaboration_manager.create_project({"name": "Test Project", "owner": "user_1"}))["id"],
            "title": "Implement feature X",
            "description": "Test task",
            "priority": "high",
        }

        task = await collaboration_manager.create_task(task_data)

        assert task["id"] is not None
        assert task["title"] == "Implement feature X"

        # 分配任务
        assigned = await collaboration_manager.assign_task(task["id"], "user_2")

        assert assigned

        # 更新状态
        await collaboration_manager.update_task_status(task["id"], "in_progress", "user_2")

        # 获取统计
        stats = await collaboration_manager.get_project_stats(task["project_id"])

        assert stats["tasks"]["total"] == 1
        assert stats["completion_rate"] > 0

    @pytest.mark.asyncio
    async def test_permission_check(self, permission_manager):
        """测试权限检查"""
        # 检查开发者权限
        has_create = permission_manager.check_permission(
            user_id="user_1", resource="task", action="create", user_role=Role.DEVELOPER
        )

        assert has_create

        # 检查查看者权限
        has_delete = permission_manager.check_permission(
            user_id="user_1", resource="task", action="delete", user_role=Role.VIEWER
        )

        assert not has_delete

        # 检查审核者权限
        has_review = permission_manager.check_permission(
            user_id="user_1", resource="code", action="review", user_role=Role.REVIEWER
        )

        assert has_review

    @pytest.mark.asyncio
    async def test_realtime_collaboration(self, realtime_collaboration):
        """测试实时协作"""
        # 创建文档
        await realtime_collaboration.create_document("doc_1", "Hello World")

        content = await realtime_collaboration.get_document("doc_1")

        assert content == "Hello World"

        # 应用操作
        operation = Operation(
            id="op_1", user_id="user_1", document_id="doc_1", type="insert", position=6, content=" Beautiful"
        )

        success = await realtime_collaboration.apply_operation(operation)

        assert success

        # 更新光标
        cursor = Cursor(user_id="user_1", document_id="doc_1", line=1, column=5)

        await realtime_collaboration.update_cursor(cursor)

        # 检查光标
        cursors = realtime_collaboration.cursors
        assert "doc_1" in cursors
        assert cursors["doc_1"].line == 1
