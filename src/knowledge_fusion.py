"""知识融合模块 - Ponder Knowledge Platform"""

import uuid
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class KnowledgeSource:
    """知识源"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    url: str = ""
    reliability: float = 1.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name, "url": self.url,
                "reliability": self.reliability, "last_updated": self.last_updated}


@dataclass
class FusionResult:
    """融合结果"""
    triples: List[Tuple[str, str, str]] = field(default_factory=list)
    conflicts: List[Dict] = field(default_factory=list)
    merged_entities: List[Dict] = field(default_factory=list)
    statistics: Dict = field(default_factory=dict)


class KnowledgeFusion:
    """知识融合引擎"""

    def __init__(self):
        self.sources: Dict[str, KnowledgeSource] = {}
        self.knowledge_bases: Dict[str, List[Dict]] = {}  # source_id -> triples
        self.entity_mappings: Dict[str, Dict[str, str]] = {}  # source -> {local_id -> global_id}

    def add_source(self, name: str, url: str = "", reliability: float = 1.0) -> KnowledgeSource:
        """添加知识源"""
        source = KnowledgeSource(name=name, url=url, reliability=reliability)
        self.sources[source.id] = source
        self.knowledge_bases[source.id] = []
        return source

    def load_knowledge(self, source_id: str, triples: List[Dict]) -> int:
        """加载知识三元组"""
        if source_id not in self.knowledge_bases:
            self.knowledge_bases[source_id] = []
        self.knowledge_bases[source_id].extend(triples)
        return len(triples)

    def entity_alignment(self, method: str = "name_match") -> Dict[str, str]:
        """实体对齐"""
        all_entities: Dict[str, Set[str]] = defaultdict(set)  # normalized_name -> set of entity_ids

        for source_id, triples in self.knowledge_bases.items():
            for triple in triples:
                subj = triple.get("subject", "")
                obj = triple.get("object", "")
                if subj:
                    all_entities[subj.lower().strip()].add(subj)
                if obj:
                    all_entities[obj.lower().strip()].add(obj)

        # 生成映射
        mappings = {}
        for norm_name, entity_set in all_entities.items():
            if len(entity_set) > 1:
                representative = min(entity_set, key=len)
                for eid in entity_set:
                    if eid != representative:
                        mappings[eid] = representative

        return mappings

    def merge_triples(self, entity_mappings: Optional[Dict[str, str]] = None) -> List[Dict]:
        """合并三元组"""
        if entity_mappings is None:
            entity_mappings = self.entity_alignment()

        merged = []
        seen_triples: Set[Tuple[str, str, str]] = set()

        for source_id, triples in self.knowledge_bases.items():
            source = self.sources.get(source_id)
            for triple in triples:
                subj = entity_mappings.get(triple.get("subject", ""), triple.get("subject", ""))
                obj = entity_mappings.get(triple.get("object", ""), triple.get("object", ""))
                pred = triple.get("predicate", "")
                key = (subj.lower(), pred.lower(), obj.lower())
                if key not in seen_triples:
                    seen_triples.add(key)
                    merged.append({
                        "subject": subj, "predicate": pred, "object": obj,
                        "source": source.name if source else source_id,
                        "confidence": triple.get("confidence", 0.8) * (source.reliability if source else 1.0)
                    })
        return merged

    def detect_conflicts(self) -> List[Dict]:
        """检测知识冲突"""
        triple_sources: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
        conflicts = []

        for source_id, triples in self.knowledge_bases.items():
            for triple in triples:
                key = (triple.get("subject", "").lower(),
                       triple.get("predicate", "").lower(),
                       triple.get("object", "").lower())
                triple_sources[key].append(source_id)

        # 检测同一主语-谓语不同宾语的冲突
        subj_pred: Dict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)
        for source_id, triples in self.knowledge_bases.items():
            for triple in triples:
                sp = (triple.get("subject", "").lower(), triple.get("predicate", "").lower())
                subj_pred[sp].append((triple.get("object", ""), source_id))

        for (subj, pred), obj_sources in subj_pred.items():
            objects = set(o for o, _ in obj_sources)
            if len(objects) > 1:
                conflicts.append({
                    "subject": subj, "predicate": pred,
                    "conflicting_values": [{"object": o, "source": s} for o, s in obj_sources]
                })

        return conflicts

    def fuse(self) -> FusionResult:
        """执行完整融合流程"""
        mappings = self.entity_alignment()
        merged = self.merge_triples(mappings)
        conflicts = self.detect_conflicts()
        return FusionResult(
            triples=[(t["subject"], t["predicate"], t["object"]) for t in merged],
            conflicts=conflicts,
            merged_entities=[{"from": k, "to": v} for k, v in mappings.items()],
            statistics={
                "sources": len(self.sources),
                "total_triples": sum(len(t) for t in self.knowledge_bases.values()),
                "merged_triples": len(merged),
                "conflicts": len(conflicts),
                "entity_mappings": len(mappings)
            }
        )

    def get_statistics(self) -> Dict:
        return {
            "sources": len(self.sources),
            "total_triples": sum(len(v) for v in self.knowledge_bases.values()),
            "by_source": {sid: len(triples) for sid, triples in self.knowledge_bases.items()}
        }
