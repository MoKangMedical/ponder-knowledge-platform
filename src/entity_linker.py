"""实体链接模块 - Ponder Knowledge Platform"""

import re
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class Entity:
    """实体定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    aliases: List[str] = field(default_factory=list)
    entity_type: str = ""
    description: str = ""
    properties: Dict = field(default_factory=dict)
    external_ids: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "aliases": self.aliases, "entity_type": self.entity_type,
            "description": self.description, "properties": self.properties,
            "external_ids": self.external_ids
        }


@dataclass
class EntityMention:
    """实体提及"""
    text: str
    start: int
    end: int
    entity_id: Optional[str] = None
    confidence: float = 0.0


class EntityLinker:
    """实体链接器"""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.alias_index: Dict[str, List[str]] = defaultdict(list)  # alias -> entity_ids
        self.type_index: Dict[str, List[str]] = defaultdict(list)

    def register_entity(self, name: str, entity_type: str = "",
                        aliases: Optional[List[str]] = None,
                        description: str = "",
                        properties: Optional[Dict] = None,
                        external_ids: Optional[Dict] = None) -> Entity:
        """注册实体"""
        entity = Entity(
            name=name, entity_type=entity_type,
            aliases=aliases or [], description=description,
            properties=properties or {}, external_ids=external_ids or {}
        )
        self.entities[entity.id] = entity
        # 构建索引
        self.alias_index[name.lower()].append(entity.id)
        for alias in entity.aliases:
            self.alias_index[alias.lower()].append(entity.id)
        if entity_type:
            self.type_index[entity_type].append(entity.id)
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def search_by_name(self, name: str, fuzzy: bool = False) -> List[Entity]:
        """按名称搜索实体"""
        name_lower = name.lower()
        if not fuzzy:
            ids = self.alias_index.get(name_lower, [])
            return [self.entities[eid] for eid in ids if eid in self.entities]
        # 模糊匹配
        results = []
        for alias, ids in self.alias_index.items():
            if name_lower in alias or alias in name_lower:
                for eid in ids:
                    if eid in self.entities:
                        results.append(self.entities[eid])
        return results

    def search_by_type(self, entity_type: str) -> List[Entity]:
        ids = self.type_index.get(entity_type, [])
        return [self.entities[eid] for eid in ids if eid in self.entities]

    def find_mentions(self, text: str) -> List[EntityMention]:
        """在文本中查找实体提及"""
        mentions = []
        sorted_aliases = sorted(self.alias_index.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            pattern = re.compile(re.escape(alias), re.IGNORECASE)
            for match in pattern.finditer(text):
                entity_ids = self.alias_index[alias]
                if entity_ids:
                    mention = EntityMention(
                        text=match.group(), start=match.start(),
                        end=match.end(), entity_id=entity_ids[0],
                        confidence=0.9
                    )
                    mentions.append(mention)
        # 去除重叠
        mentions.sort(key=lambda m: (m.start, -(m.end - m.start)))
        filtered = []
        last_end = -1
        for m in mentions:
            if m.start >= last_end:
                filtered.append(m)
                last_end = m.end
        return filtered

    def link_entities(self, text: str) -> List[Dict]:
        """链接文本中的实体"""
        mentions = self.find_mentions(text)
        results = []
        for mention in mentions:
            entity = self.entities.get(mention.entity_id)
            if entity:
                results.append({
                    "mention": mention.text,
                    "start": mention.start,
                    "end": mention.end,
                    "entity": entity.to_dict(),
                    "confidence": mention.confidence
                })
        return results

    def resolve_entity(self, name: str, context: Optional[str] = None,
                       entity_type: Optional[str] = None) -> Optional[Entity]:
        """消歧并解析实体"""
        candidates = self.search_by_name(name, fuzzy=True)
        if not candidates:
            return None
        if entity_type:
            typed = [c for c in candidates if c.entity_type == entity_type]
            if typed:
                candidates = typed
        if context:
            context_lower = context.lower()
            scored = []
            for c in candidates:
                score = 0
                if c.name.lower() in context_lower:
                    score += 2
                for alias in c.aliases:
                    if alias.lower() in context_lower:
                        score += 1
                scored.append((c, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]
        return candidates[0]

    def merge_entities(self, entity_id1: str, entity_id2: str) -> Optional[Entity]:
        """合并两个实体"""
        e1 = self.entities.get(entity_id1)
        e2 = self.entities.get(entity_id2)
        if not e1 or not e2:
            return None
        e1.aliases = list(set(e1.aliases + e2.aliases + [e2.name]))
        e1.properties.update(e2.properties)
        e1.external_ids.update(e2.external_ids)
        del self.entities[entity_id2]
        return e1

    def get_statistics(self) -> Dict:
        type_counts = {}
        for entity in self.entities.values():
            type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1
        return {
            "total_entities": len(self.entities),
            "total_aliases": len(self.alias_index),
            "by_type": type_counts,
        }

    def export_to_json(self) -> str:
        import json
        return json.dumps(
            {k: v.to_dict() for k, v in self.entities.items()},
            indent=2, ensure_ascii=False
        )
