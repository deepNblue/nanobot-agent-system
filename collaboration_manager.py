"""
协作管理器 - 支持多人协作

功能：
1. 项目协作管理
2. 任务分配
3. 进度同步
4. 实时协作
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
import sqlite3


@dataclass
class User:
    """用户"""
    id: str
    name: str
    email: str
    role: str = "developer"
    projects: Set[str] = field(default_factory=set)


@dataclass
class Project:
    """项目"""
    id: str
    name: str
    description: str
    owner: str
    members: Dict[str, str] = field(default_factory=dict)  # user_id -> role
    created_at: datetime = field(default_factory=datetime.now)


class CollaborationManager:
    """协作管理器"""
    
    def __init__(self, db_path: str = "./data/collaboration.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.setup_database()
        
        # 内存缓存
        self.active_users: Dict[str, User] = {}
        self.projects: Dict[str, Project] = {}
    
    def setup_database(self):
        """设置数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'developer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 项目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner) REFERENCES users(id)
            )
        """)
        
        # 项目成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_members (
                project_id TEXT,
                user_id TEXT,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, user_id),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                assigned_to TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (assigned_to) REFERENCES users(id)
            )
        """)
        
        # 任务历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT,
                old_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ============ 用户管理 ============
    
    async def create_user(self, user_data: Dict) -> User:
        """创建用户"""
        user = User(
            id=user_data.get("id", f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            name=user_data["name"],
            email=user_data["email"],
            role=user_data.get("role", "developer")
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (id, name, email, role)
            VALUES (?, ?, ?, ?)
        """, (user.id, user.name, user.email, user.role))
        
        conn.commit()
        conn.close()
        
        self.active_users[user.id] = user
        
        return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        if user_id in self.active_users:
            return self.active_users[user_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return User(id=row[0], name=row[1], email=row[2], role=row[3])
        
        return None
    
    # ============ 项目管理 ============
    
    async def create_project(self, project_data: Dict) -> Project:
        """创建项目"""
        project = Project(
            id=project_data.get("id", f"proj_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            name=project_data["name"],
            description=project_data.get("description", ""),
            owner=project_data["owner"]
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入项目
        cursor.execute("""
            INSERT INTO projects (id, name, description, owner)
            VALUES (?, ?, ?, ?)
        """, (project.id, project.name, project.description, project.owner))
        
        # 添加所有者为项目成员
        cursor.execute("""
            INSERT INTO project_members (project_id, user_id, role)
            VALUES (?, ?, 'owner')
        """, (project.id, project.owner))
        
        conn.commit()
        conn.close()
        
        self.projects[project.id] = project
        
        return project
    
    async def join_project(self, user_id: str, project_id: str, role: str = "member"):
        """加入项目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO project_members (project_id, user_id, role)
                VALUES (?, ?, ?)
            """, (project_id, user_id, role))
            
            conn.commit()
            
            # 更新缓存
            if project_id in self.projects:
                self.projects[project_id].members[user_id] = role
            
            return True
        except sqlite3.IntegrityError:
            # 已经是成员
            return False
        finally:
            conn.close()
    
    async def get_project_members(self, project_id: str) -> Dict[str, str]:
        """获取项目成员"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, role
            FROM project_members
            WHERE project_id = ?
        """, (project_id,))
        
        members = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return members
    
    # ============ 任务管理 ============
    
    async def create_task(self, task_data: Dict) -> Dict:
        """创建任务"""
        task_id = task_data.get("id", f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tasks (id, project_id, title, description, priority)
            VALUES (?, ?, ?, ?, ?)
        """, (
            task_id,
            task_data["project_id"],
            task_data["title"],
            task_data.get("description", ""),
            task_data.get("priority", "medium")
        ))
        
        conn.commit()
        conn.close()
        
        return await self.get_task(task_id)
    
    async def assign_task(self, task_id: str, user_id: str) -> bool:
        """分配任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取旧值
        cursor.execute("SELECT assigned_to FROM tasks WHERE id = ?", (task_id,))
        old_value = cursor.fetchone()[0]
        
        # 更新任务
        cursor.execute("""
            UPDATE tasks
            SET assigned_to = ?, updated_at = ?
            WHERE id = ?
        """, (user_id, datetime.now().isoformat(), task_id))
        
        # 记录历史
        cursor.execute("""
            INSERT INTO task_history (task_id, action, user_id, old_value, new_value)
            VALUES (?, 'assigned', ?, ?, ?)
        """, (task_id, user_id, old_value, user_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    async def update_task_status(self, task_id: str, status: str, user_id: str = None) -> bool:
        """更新任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取旧值
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        old_status = cursor.fetchone()[0]
        
        # 更新任务
        cursor.execute("""
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, datetime.now().isoformat(), task_id))
        
        # 记录历史
        cursor.execute("""
            INSERT INTO task_history (task_id, action, user_id, old_value, new_value)
            VALUES (?, 'status_change', ?, ?, ?)
        """, (task_id, user_id, old_status, status))
        
        conn.commit()
        conn.close()
        
        return True
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, project_id, title, description, assigned_to, status, priority, created_at, updated_at
            FROM tasks
            WHERE id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "project_id": row[1],
                "title": row[2],
                "description": row[3],
                "assigned_to": row[4],
                "status": row[5],
                "priority": row[6],
                "created_at": row[7],
                "updated_at": row[8]
            }
        
        return None
    
    async def get_project_tasks(self, project_id: str, status: str = None) -> List[Dict]:
        """获取项目任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT id, project_id, title, description, assigned_to, status, priority, created_at, updated_at
                FROM tasks
                WHERE project_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (project_id, status))
        else:
            cursor.execute("""
                SELECT id, project_id, title, description, assigned_to, status, priority, created_at, updated_at
                FROM tasks
                WHERE project_id = ?
                ORDER BY created_at DESC
            """, (project_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append({
                "id": row[0],
                "project_id": row[1],
                "title": row[2],
                "description": row[3],
                "assigned_to": row[4],
                "status": row[5],
                "priority": row[6],
                "created_at": row[7],
                "updated_at": row[8]
            })
        
        return tasks
    
    # ============ 统计和报告 ============
    
    async def get_project_stats(self, project_id: str) -> Dict:
        """获取项目统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 任务统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM tasks
            WHERE project_id = ?
        """, (project_id,))
        
        task_stats = cursor.fetchone()
        
        # 成员统计
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM project_members
            WHERE project_id = ?
        """, (project_id,))
        
        member_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "tasks": {
                "total": task_stats[0],
                "completed": task_stats[1],
                "in_progress": task_stats[2],
                "pending": task_stats[3]
            },
            "members": member_count,
            "completion_rate": (task_stats[1] / task_stats[0] * 100) if task_stats[0] > 0 else 0
        }


# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def main():
        manager = CollaborationManager()
        
        # 创建用户
        user1 = await manager.create_user({
            "name": "Alice",
            "email": "alice@example.com",
            "role": "developer"
        })
        
        user2 = await manager.create_user({
            "name": "Bob",
            "email": "bob@example.com",
            "role": "developer"
        })
        
        print(f"Created users: {user1.name}, {user2.name}")
        
        # 创建项目
        project = await manager.create_project({
            "name": "AI Agent System",
            "description": "Building an AI-powered development system",
            "owner": user1.id
        })
        
        print(f"Created project: {project.name}")
        
        # 加入项目
        await manager.join_project(user2.id, project.id, "developer")
        
        # 创建任务
        task = await manager.create_task({
            "project_id": project.id,
            "title": "Implement collaboration features",
            "description": "Add multi-user collaboration support",
            "priority": "high"
        })
        
        print(f"Created task: {task['title']}")
        
        # 分配任务
        await manager.assign_task(task["id"], user2.id)
        
        # 更新状态
        await manager.update_task_status(task["id"], "in_progress", user2.id)
        
        # 获取统计
        stats = await manager.get_project_stats(project.id)
        print(f"Project stats: {stats}")
    
    asyncio.run(main())
