"""认证授权模块 - Ponder Knowledge Platform"""

import uuid
import hashlib
import time
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"


@dataclass
class User:
    """用户"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    email: str = ""
    password_hash: str = ""
    roles: List[str] = field(default_factory=lambda: ["viewer"])
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "username": self.username,
            "email": self.email, "roles": self.roles,
            "is_active": self.is_active, "created_at": self.created_at,
            "last_login": self.last_login
        }


@dataclass
class Role:
    """角色"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    permissions: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "permissions": self.permissions,
            "description": self.description
        }


@dataclass
class Token:
    """访问令牌"""
    token: str = ""
    user_id: str = ""
    expires_at: float = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class AuthManager:
    """认证授权管理器"""

    def __init__(self, token_expiry: int = 3600):
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.tokens: Dict[str, Token] = {}
        self.token_expiry = token_expiry
        self._setup_default_roles()

    def _setup_default_roles(self):
        self.roles["admin"] = Role(name="admin", permissions=["read", "write", "delete", "admin", "export"],
                                    description="Full access")
        self.roles["editor"] = Role(name="editor", permissions=["read", "write", "export"],
                                     description="Read and write access")
        self.roles["viewer"] = Role(name="viewer", permissions=["read"],
                                     description="Read-only access")

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username: str, password: str,
                    email: str = "", roles: Optional[List[str]] = None) -> User:
        """创建用户"""
        user = User(
            username=username, email=email,
            password_hash=self._hash_password(password),
            roles=roles or ["viewer"]
        )
        self.users[user.id] = user
        return user

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """认证并返回token"""
        password_hash = self._hash_password(password)
        user = None
        for u in self.users.values():
            if u.username == username and u.password_hash == password_hash and u.is_active:
                user = u
                break
        if not user:
            return None
        token_str = secrets.token_hex(32)
        token = Token(
            token=token_str, user_id=user.id,
            expires_at=time.time() + self.token_expiry
        )
        self.tokens[token_str] = token
        user.last_login = datetime.now().isoformat()
        return token_str

    def verify_token(self, token_str: str) -> Optional[User]:
        """验证token"""
        token = self.tokens.get(token_str)
        if not token or token.is_expired():
            if token:
                del self.tokens[token_str]
            return None
        return self.users.get(token.user_id)

    def check_permission(self, token_str: str, permission: str) -> bool:
        """检查权限"""
        user = self.verify_token(token_str)
        if not user:
            return False
        for role_name in user.roles:
            role = self.roles.get(role_name)
            if role and permission in role.permissions:
                return True
        return False

    def create_role(self, name: str, permissions: List[str],
                    description: str = "") -> Role:
        role = Role(name=name, permissions=permissions, description=description)
        self.roles[name] = role
        return role

    def assign_role(self, user_id: str, role_name: str) -> bool:
        user = self.users.get(user_id)
        if not user or role_name not in self.roles:
            return False
        if role_name not in user.roles:
            user.roles.append(role_name)
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        if role_name in user.roles:
            user.roles.remove(role_name)
        return True

    def deactivate_user(self, user_id: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        user.is_active = False
        return True

    def logout(self, token_str: str) -> bool:
        return self.tokens.pop(token_str, None) is not None

    def cleanup_expired_tokens(self) -> int:
        expired = [k for k, v in self.tokens.items() if v.is_expired()]
        for k in expired:
            del self.tokens[k]
        return len(expired)

    def get_user_permissions(self, user_id: str) -> List[str]:
        user = self.users.get(user_id)
        if not user:
            return []
        perms = set()
        for role_name in user.roles:
            role = self.roles.get(role_name)
            if role:
                perms.update(role.permissions)
        return list(perms)

    def get_statistics(self) -> Dict:
        return {
            "total_users": len(self.users),
            "active_users": len([u for u in self.users.values() if u.is_active]),
            "total_roles": len(self.roles),
            "active_tokens": len(self.tokens),
        }
