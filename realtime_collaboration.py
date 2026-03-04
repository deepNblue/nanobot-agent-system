"""
实时协作 - 支持多人实时协作

功能：
1. 实时文档编辑
2. 光标位置同步
3. 在线状态
4. 操作历史
"""

import asyncio
import json
from typing import Dict, List, Set, Optional
from datetime import datetime
from dataclasses import dataclass, field
import weakref


@dataclass
class Cursor:
    """光标位置"""
    user_id: str
    document_id: str
    line: int
    column: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Operation:
    """操作记录"""
    id: str
    user_id: str
    document_id: str
    type: str  # insert, delete, replace
    position: int
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    applied: bool = False


class RealtimeCollaboration:
    """实时协作管理器"""
    
    def __init__(self):
        # 文档内容
        self.documents: Dict[str, str] = {}
        
        # 文档版本
        self.document_versions: Dict[str, int] = {}
        
        # 光标位置
        self.cursors: Dict[str, Cursor] = {}
        
        # 操作历史
        self.operations: Dict[str, List[Operation]] = {}
        
        # 在线用户
        self.online_users: Dict[str, Set[str]] = {}  # document_id -> user_ids
        
        # WebSocket连接（如果有）
        self.websocket_manager = None
    
    # ============ 文档管理 ============
    
    async def create_document(self, document_id: str, content: str = ""):
        """创建文档"""
        self.documents[document_id] = content
        self.document_versions[document_id] = 0
        self.operations[document_id] = []
        self.online_users[document_id] = set()
    
    async def get_document(self, document_id: str) -> Optional[str]:
        """获取文档内容"""
        return self.documents.get(document_id)
    
    async def delete_document(self, document_id: str):
        """删除文档"""
        self.documents.pop(document_id, None)
        self.document_versions.pop(document_id, None)
        self.operations.pop(document_id, None)
        self.online_users.pop(document_id, None)
    
    # ============ 实时编辑 ============
    
    async def apply_operation(self, operation: Operation) -> bool:
        """应用操作"""
        document_id = operation.document_id
        
        if document_id not in self.documents:
            return False
        
        # 1. 获取文档
        content = self.documents[document_id]
        
        # 2. 应用操作
        if operation.type == "insert":
            # 插入内容
            new_content = (
                content[:operation.position] +
                operation.content +
                content[operation.position:]
            )
        
        elif operation.type == "delete":
            # 删除内容
            end_pos = operation.position + len(operation.content)
            new_content = (
                content[:operation.position] +
                content[end_pos:]
            )
        
        elif operation.type == "replace":
            # 替换内容
            new_content = (
                content[:operation.position] +
                operation.content +
                content[operation.position + len(operation.content):]
            )
        
        else:
            return False
        
        # 3. 更新文档
        self.documents[document_id] = new_content
        self.document_versions[document_id] += 1
        
        # 4. 记录操作
        operation.applied = True
        self.operations[document_id].append(operation)
        
        # 5. 广播给其他用户
        await self.broadcast_operation(operation)
        
        return True
    
    async def broadcast_operation(self, operation: Operation):
        """广播操作给其他用户"""
        if self.websocket_manager:
            # 通过WebSocket广播
            message = {
                "type": "document_update",
                "document_id": operation.document_id,
                "operation": {
                    "id": operation.id,
                    "user_id": operation.user_id,
                    "type": operation.type,
                    "position": operation.position,
                    "content": operation.content,
                    "timestamp": operation.timestamp.isoformat()
                },
                "version": self.document_versions[operation.document_id]
            }
            
            await self.websocket_manager.broadcast(
                document_id=operation.document_id,
                message=message,
                exclude_user=operation.user_id
            )
    
    # ============ 光标同步 ============
    
    async def update_cursor(self, cursor: Cursor):
        """更新光标位置"""
        self.cursors[f"{cursor.document_id}:{cursor.user_id}"] = cursor
        
        # 广播给其他用户
        if self.websocket_manager:
            message = {
                "type": "cursor_update",
                "document_id": cursor.document_id,
                "user_id": cursor.user_id,
                "position": {
                    "line": cursor.line,
                    "column": cursor.column
                },
                "timestamp": cursor.timestamp.isoformat()
            }
            
            await self.websocket_manager.broadcast(
                document_id=cursor.document_id,
                message=message,
                exclude_user=cursor.user_id
            )
    
    async def get_cursors(self, document_id: str) -> List[Dict]:
        """获取文档的所有光标"""
        cursors = []
        
        for key, cursor in self.cursors.items():
            if cursor.document_id == document_id:
                cursors.append({
                    "user_id": cursor.user_id,
                    "line": cursor.line,
                    "column": cursor.column,
                    "timestamp": cursor.timestamp.isoformat()
                })
        
        return cursors
    
    # ============ 在线状态 ============
    
    async def user_join(self, user_id: str, document_id: str):
        """用户加入文档"""
        if document_id not in self.online_users:
            self.online_users[document_id] = set()
        
        self.online_users[document_id].add(user_id)
        
        # 广播加入通知
        if self.websocket_manager:
            message = {
                "type": "user_joined",
                "document_id": document_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket_manager.broadcast(
                document_id=document_id,
                message=message
            )
    
    async def user_leave(self, user_id: str, document_id: str):
        """用户离开文档"""
        if document_id in self.online_users:
            self.online_users[document_id].discard(user_id)
        
        # 移除光标
        cursor_key = f"{document_id}:{user_id}"
        self.cursors.pop(cursor_key, None)
        
        # 广播离开通知
        if self.websocket_manager:
            message = {
                "type": "user_left",
                "document_id": document_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket_manager.broadcast(
                document_id=document_id,
                message=message
            )
    
    async def get_online_users(self, document_id: str) -> List[str]:
        """获取文档的在线用户"""
        return list(self.online_users.get(document_id, set()))
    
    # ============ 操作历史 ============
    
    async def get_operations(
        self,
        document_id: str,
        since_version: int = None
    ) -> List[Dict]:
        """获取操作历史"""
        if document_id not in self.operations:
            return []
        
        operations = self.operations[document_id]
        
        if since_version is not None:
            # 只返回指定版本之后的操作
            operations = operations[since_version:]
        
        return [
            {
                "id": op.id,
                "user_id": op.user_id,
                "type": op.type,
                "position": op.position,
                "content": op.content,
                "timestamp": op.timestamp.isoformat()
            }
            for op in operations
        ]
    
    async def undo_last_operation(self, user_id: str, document_id: str) -> bool:
        """撤销最后一次操作"""
        if document_id not in self.operations:
            return False
        
        operations = self.operations[document_id]
        
        if not operations:
            return False
        
        # 找到用户最后一次操作
        last_op = None
        for op in reversed(operations):
            if op.user_id == user_id:
                last_op = op
                break
        
        if not last_op:
            return False
        
        # 创建反向操作
        if last_op.type == "insert":
            reverse_op = Operation(
                id=f"undo_{last_op.id}",
                user_id=user_id,
                document_id=document_id,
                type="delete",
                position=last_op.position,
                content=last_op.content
            )
        elif last_op.type == "delete":
            reverse_op = Operation(
                id=f"undo_{last_op.id}",
                user_id=user_id,
                document_id=document_id,
                type="insert",
                position=last_op.position,
                content=last_op.content
            )
        else:
            return False
        
        # 应用反向操作
        return await self.apply_operation(reverse_op)


# WebSocket管理器（简化版）
class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self):
        self.connections: Dict[str, Set] = {}  # document_id -> connections
    
    async def broadcast(
        self,
        document_id: str,
        message: Dict,
        exclude_user: str = None
    ):
        """广播消息"""
        # 实际实现应该通过WebSocket发送消息
        print(f"Broadcast to {document_id}: {message}")
    
    async def send_to_user(self, user_id: str, message: Dict):
        """发送消息给特定用户"""
        # 实际实现应该通过WebSocket发送消息
        print(f"Send to {user_id}: {message}")


# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def main():
        collab = RealtimeCollaboration()
        
        # 创建文档
        await collab.create_document("doc_1", "Hello World")
        
        # 用户加入
        await collab.user_join("user_1", "doc_1")
        await collab.user_join("user_2", "doc_1")
        
        # 更新光标
        cursor = Cursor(
            user_id="user_1",
            document_id="doc_1",
            line=1,
            column=5
        )
        await collab.update_cursor(cursor)
        
        # 应用操作
        operation = Operation(
            id="op_1",
            user_id="user_1",
            document_id="doc_1",
            type="insert",
            position=5,
            content=" Beautiful"
        )
        await collab.apply_operation(operation)
        
        # 获取文档
        content = await collab.get_document("doc_1")
        print(f"Document content: {content}")
        
        # 获取在线用户
        online = await collab.get_online_users("doc_1")
        print(f"Online users: {online}")
        
        # 获取光标
        cursors = await collab.get_cursors("doc_1")
        print(f"Cursors: {cursors}")
    
    asyncio.run(main())
