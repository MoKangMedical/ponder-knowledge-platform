"""关系抽取模块 - Ponder Knowledge Platform"""

import re
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractedRelation:
    """抽取的关系"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject: str = ""
    predicate: str = ""
    obj: str = ""
    confidence: float = 0.0
    source_text: str = ""
    evidence: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "subject": self.subject,
            "predicate": self.predicate, "object": self.obj,
            "confidence": self.confidence, "source_text": self.source_text,
            "evidence": self.evidence, "created_at": self.created_at
        }


class RelationExtractor:
    """关系抽取器"""

    # 预定义关系模式
    RELATION_PATTERNS = {
        "is_a": [
            r"(.+?)\s+(?:是|属于|is a|is an)\s+(.+)",
            r"(.+?)\s+(?:的一种|的类型|的一种类型)\s*(.+)",
        ],
        "part_of": [
            r"(.+?)\s+(?:是.*?的一部分|包含|part of)\s*(.+)",
            r"(.+?)\s+(?:的组成部分)\s*(.+)",
        ],
        "causes": [
            r"(.+?)\s+(?:导致|引起|造成|causes|leads to)\s+(.+)",
        ],
        "treats": [
            r"(.+?)\s+(?:治疗|用于治疗|treats|cures)\s+(.+)",
        ],
        "has_property": [
            r"(.+?)\s+(?:具有|拥有|has|possesses)\s+(.+)",
        ],
        "related_to": [
            r"(.+?)\s+(?:与.*?相关|关联|related to)\s+(.+)",
        ],
    }

    def __init__(self):
        self.relations: List[ExtractedRelation] = []
        self.custom_patterns: Dict[str, List[str]] = {}

    def extract_from_text(self, text: str) -> List[ExtractedRelation]:
        """从文本中抽取关系"""
        results = []
        all_patterns = {**self.RELATION_PATTERNS, **self.custom_patterns}

        for predicate, patterns in all_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    subject = match.group(1).strip()
                    obj = match.group(2).strip()
                    if subject and obj:
                        rel = ExtractedRelation(
                            subject=subject, predicate=predicate,
                            obj=obj, confidence=0.7,
                            source_text=text[:200],
                            evidence=match.group(0)
                        )
                        results.append(rel)
                        self.relations.append(rel)

        return results

    def extract_from_triples(self, triples: List[Tuple[str, str, str]],
                              confidence: float = 1.0) -> List[ExtractedRelation]:
        """从三元组列表抽取关系"""
        results = []
        for subj, pred, obj in triples:
            rel = ExtractedRelation(
                subject=subj, predicate=pred, obj=obj,
                confidence=confidence
            )
            results.append(rel)
            self.relations.append(rel)
        return results

    def extract_from_structured_data(self, data: Dict) -> List[ExtractedRelation]:
        """从结构化数据抽取关系"""
        results = []
        entities = data.get("entities", [])
        for entity in entities:
            entity_name = entity.get("name", "")
            for key, value in entity.items():
                if key not in ("id", "name", "type") and value:
                    if isinstance(value, list):
                        for v in value:
                            rel = ExtractedRelation(
                                subject=entity_name, predicate=key,
                                obj=str(v), confidence=0.9
                            )
                            results.append(rel)
                            self.relations.append(rel)
                    elif isinstance(value, str):
                        rel = ExtractedRelation(
                            subject=entity_name, predicate=key,
                            obj=value, confidence=0.9
                        )
                        results.append(rel)
                        self.relations.append(rel)
        return results

    def add_custom_pattern(self, predicate: str, pattern: str) -> None:
        """添加自定义关系模式"""
        if predicate not in self.custom_patterns:
            self.custom_patterns[predicate] = []
        self.custom_patterns[predicate].append(pattern)

    def filter_by_confidence(self, min_confidence: float) -> List[ExtractedRelation]:
        """按置信度过滤"""
        return [r for r in self.relations if r.confidence >= min_confidence]

    def get_relations_by_entity(self, entity: str) -> List[ExtractedRelation]:
        """获取实体相关的关系"""
        entity_lower = entity.lower()
        return [r for r in self.relations
                if entity_lower in r.subject.lower() or entity_lower in r.obj.lower()]

    def deduplicate(self) -> List[ExtractedRelation]:
        """去重"""
        seen = set()
        unique = []
        for rel in self.relations:
            key = (rel.subject.lower(), rel.predicate, rel.obj.lower())
            if key not in seen:
                seen.add(key)
                unique.append(rel)
        self.relations = unique
        return unique

    def get_statistics(self) -> Dict:
        predicate_counts = {}
        for rel in self.relations:
            predicate_counts[rel.predicate] = predicate_counts.get(rel.predicate, 0) + 1
        return {
            "total_relations": len(self.relations),
            "by_predicate": predicate_counts,
            "avg_confidence": sum(r.confidence for r in self.relations) / max(len(self.relations), 1),
        }

    def export_to_json(self) -> str:
        import json
        return json.dumps([r.to_dict() for r in self.relations], indent=2, ensure_ascii=False)
