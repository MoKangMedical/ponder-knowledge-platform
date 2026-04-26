"""版本控制模块 - Ponder Knowledge Platform"""

import uuid
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Version:
    """版本记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    entity_type: str = ""
    data: Dict = field(default_factory=dict)
    hash: str = ""
    message: str = ""
    author: str = ""
    parent_version: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "entity_id": self.entity_id,
            "entity_type": self.entity_type, "data": self.data,
            "hash": self.hash, "message": self.message,
            "author": self.author, "parent_version": self.parent_version,
            "created_at": self.created_at
        }


class VersionControl:
    """版本控制系统"""

    def __init__(self):
        self.versions: Dict[str, Version] = {}
        self.entity_history: Dict[str, List[str]] = {}  # entity_id -> [version_ids]
        self.branches: Dict[str, str] = {"main": ""}  # branch -> latest_version_id
        self.tags: Dict[str, str] = {}  # tag -> version_id

    def _compute_hash(self, data: Dict) -> str:
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def commit(self, entity_id: str, entity_type: str, data: Dict,
               message: str = "", author: str = "",
               branch: str = "main") -> Version:
        """提交新版本"""
        parent = self.branches.get(branch, "")
        version = Version(
            entity_id=entity_id, entity_type=entity_type,
            data=data, hash=self._compute_hash(data),
            message=message, author=author,
            parent_version=parent if parent else None
        )
        self.versions[version.id] = version
        if entity_id not in self.entity_history:
            self.entity_history[entity_id] = []
        self.entity_history[entity_id].append(version.id)
        self.branches[branch] = version.id
        return version

    def get_version(self, version_id: str) -> Optional[Version]:
        return self.versions.get(version_id)

    def get_history(self, entity_id: str, limit: int = -1) -> List[Version]:
        """获取实体历史"""
        version_ids = self.entity_history.get(entity_id, [])
        versions = [self.versions[vid] for vid in version_ids if vid in self.versions]
        if limit > 0:
            versions = versions[-limit:]
        versions.reverse()
        return versions

    def get_latest(self, entity_id: str, branch: str = "main") -> Optional[Version]:
        """获取最新版本"""
        version_ids = self.entity_history.get(entity_id, [])
        if not version_ids:
            return None
        return self.versions.get(version_ids[-1])

    def diff(self, version_id1: str, version_id2: str) -> Dict:
        """比较两个版本"""
        v1 = self.versions.get(version_id1)
        v2 = self.versions.get(version_id2)
        if not v1 or not v2:
            return {"error": "Version not found"}
        changes = {}
        all_keys = set(list(v1.data.keys()) + list(v2.data.keys()))
        for key in all_keys:
            val1 = v1.data.get(key)
            val2 = v2.data.get(key)
            if val1 != val2:
                changes[key] = {"old": val1, "new": val2}
        return changes

    def revert(self, version_id: str, branch: str = "main") -> Optional[Version]:
        """回滚到指定版本"""
        version = self.versions.get(version_id)
        if not version:
            return None
        return self.commit(
            entity_id=version.entity_id,
            entity_type=version.entity_type,
            data=version.data,
            message=f"Revert to {version_id}",
            branch=branch
        )

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        if branch_name in self.branches:
            return False
        self.branches[branch_name] = self.branches.get(from_branch, "")
        return True

    def create_tag(self, tag_name: str, version_id: str) -> bool:
        if version_id not in self.versions:
            return False
        self.tags[tag_name] = version_id
        return True

    def get_tagged_version(self, tag_name: str) -> Optional[Version]:
        vid = self.tags.get(tag_name)
        return self.versions.get(vid) if vid else None

    def get_statistics(self) -> Dict:
        return {
            "total_versions": len(self.versions),
            "total_entities": len(self.entity_history),
            "branches": len(self.branches),
            "tags": len(self.tags),
        }

    def export_history(self, entity_id: str) -> str:
        history = self.get_history(entity_id)
        return json.dumps([v.to_dict() for v in history], indent=2, ensure_ascii=False)
