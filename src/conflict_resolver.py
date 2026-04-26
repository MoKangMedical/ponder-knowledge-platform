"""冲突解决模块 - Ponder Knowledge Platform"""

import uuid
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ConflictType(Enum):
    VALUE_CONFLICT = "value_conflict"
    TYPE_CONFLICT = "type_conflict"
    MISSING_PROPERTY = "missing_property"
    TEMPORAL_CONFLICT = "temporal_conflict"
    LOGICAL_CONFLICT = "logical_conflict"


class ResolutionStrategy(Enum):
    MOST_RECENT = "most_recent"
    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_SOURCES = "most_sources"
    MANUAL = "manual"
    CUSTOM = "custom"


@dataclass
class Conflict:
    """知识冲突"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: str = ""
    subject: str = ""
    predicate: str = ""
    values: List[Dict] = field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "conflict_type": self.conflict_type,
            "subject": self.subject, "predicate": self.predicate,
            "values": self.values, "resolved": self.resolved,
            "resolution": self.resolution, "created_at": self.created_at
        }


@dataclass
class ResolutionRule:
    """解决规则"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    conflict_type: str = ""
    strategy: str = ""
    priority: int = 0
    custom_func: Optional[Callable] = None


class ConflictResolver:
    """冲突解决器"""

    def __init__(self):
        self.conflicts: Dict[str, Conflict] = {}
        self.rules: List[ResolutionRule] = []
        self._setup_default_rules()

    def _setup_default_rules(self):
        self.rules.extend([
            ResolutionRule(name="highest_confidence", strategy="highest_confidence", priority=10),
            ResolutionRule(name="most_sources", strategy="most_sources", priority=5),
        ])

    def register_conflict(self, subject: str, predicate: str,
                          values: List[Dict],
                          conflict_type: str = "value_conflict") -> Conflict:
        """注册冲突"""
        conflict = Conflict(
            conflict_type=conflict_type,
            subject=subject, predicate=predicate,
            values=values
        )
        self.conflicts[conflict.id] = conflict
        return conflict

    def add_rule(self, name: str, strategy: str,
                 conflict_type: str = "", priority: int = 0,
                 custom_func: Optional[Callable] = None) -> ResolutionRule:
        rule = ResolutionRule(
            name=name, strategy=strategy,
            conflict_type=conflict_type, priority=priority,
            custom_func=custom_func
        )
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        return rule

    def resolve_by_confidence(self, conflict: Conflict) -> Optional[str]:
        """按置信度解决"""
        if not conflict.values:
            return None
        best = max(conflict.values, key=lambda v: v.get("confidence", 0))
        conflict.resolved = True
        conflict.resolution = best.get("value", "")
        return conflict.resolution

    def resolve_by_source_count(self, conflict: Conflict) -> Optional[str]:
        """按来源数量解决"""
        if not conflict.values:
            return None
        value_counts: Dict[str, int] = {}
        for v in conflict.values:
            val = v.get("value", "")
            value_counts[val] = value_counts.get(val, 0) + 1
        best = max(value_counts, key=value_counts.get)
        conflict.resolved = True
        conflict.resolution = best
        return best

    def resolve_by_recency(self, conflict: Conflict) -> Optional[str]:
        """按时间解决"""
        if not conflict.values:
            return None
        best = max(conflict.values, key=lambda v: v.get("timestamp", ""))
        conflict.resolved = True
        conflict.resolution = best.get("value", "")
        return conflict.resolution

    def resolve_conflict(self, conflict_id: str,
                         strategy: Optional[str] = None) -> Optional[str]:
        """解决指定冲突"""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return None

        if strategy:
            if strategy == "highest_confidence":
                return self.resolve_by_confidence(conflict)
            elif strategy == "most_sources":
                return self.resolve_by_source_count(conflict)
            elif strategy == "most_recent":
                return self.resolve_by_recency(conflict)

        # 使用规则自动解决
        applicable = [r for r in self.rules
                      if not r.conflict_type or r.conflict_type == conflict.conflict_type]
        for rule in applicable:
            if rule.custom_func:
                result = rule.custom_func(conflict)
                if result:
                    conflict.resolved = True
                    conflict.resolution = result
                    return result
            elif rule.strategy == "highest_confidence":
                return self.resolve_by_confidence(conflict)
            elif rule.strategy == "most_sources":
                return self.resolve_by_source_count(conflict)
        return None

    def resolve_all(self) -> Dict[str, Optional[str]]:
        """解决所有冲突"""
        results = {}
        for cid, conflict in self.conflicts.items():
            if not conflict.resolved:
                results[cid] = self.resolve_conflict(cid)
        return results

    def get_unresolved(self) -> List[Conflict]:
        return [c for c in self.conflicts.values() if not c.resolved]

    def get_resolved(self) -> List[Conflict]:
        return [c for c in self.conflicts.values() if c.resolved]

    def get_statistics(self) -> Dict:
        total = len(self.conflicts)
        resolved = len(self.get_resolved())
        return {
            "total_conflicts": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "resolution_rate": resolved / max(total, 1),
            "by_type": self._count_by_type()
        }

    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for c in self.conflicts.values():
            counts[c.conflict_type] = counts.get(c.conflict_type, 0) + 1
        return counts

    def export_to_json(self) -> str:
        import json
        return json.dumps(
            {k: v.to_dict() for k, v in self.conflicts.items()},
            indent=2, ensure_ascii=False
        )
