"""本体管理模块 - Ponder Knowledge Platform"""

import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OntologyClass:
    """本体类定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parent_classes: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "description": self.description,
            "parent_classes": self.parent_classes,
            "properties": self.properties,
            "created_at": self.created_at, "updated_at": self.updated_at
        }


@dataclass
class OntologyRelation:
    """本体关系定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain: str = ""
    range_type: str = ""
    inverse_of: Optional[str] = None
    transitive: bool = False
    symmetric: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "domain": self.domain, "range": self.range_type,
            "inverse_of": self.inverse_of,
            "transitive": self.transitive, "symmetric": self.symmetric
        }


class OntologyManager:
    """本体管理器"""

    def __init__(self):
        self.classes: Dict[str, OntologyClass] = {}
        self.relations: Dict[str, OntologyRelation] = {}
        self.prefixes: Dict[str, str] = {
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }

    def create_class(self, name: str, description: str = "",
                     parent_classes: Optional[List[str]] = None,
                     properties: Optional[Dict] = None) -> OntologyClass:
        """创建本体类"""
        cls = OntologyClass(
            name=name, description=description,
            parent_classes=parent_classes or [],
            properties=properties or {}
        )
        self.classes[cls.id] = cls
        return cls

    def get_class(self, class_id: str) -> Optional[OntologyClass]:
        return self.classes.get(class_id)

    def update_class(self, class_id: str, **kwargs) -> Optional[OntologyClass]:
        cls = self.classes.get(class_id)
        if not cls:
            return None
        for key, value in kwargs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
        cls.updated_at = datetime.now().isoformat()
        return cls

    def delete_class(self, class_id: str) -> bool:
        return self.classes.pop(class_id, None) is not None

    def create_relation(self, name: str, domain: str, range_type: str,
                        inverse_of: Optional[str] = None,
                        transitive: bool = False,
                        symmetric: bool = False) -> OntologyRelation:
        """创建本体关系"""
        rel = OntologyRelation(
            name=name, domain=domain, range_type=range_type,
            inverse_of=inverse_of, transitive=transitive, symmetric=symmetric
        )
        self.relations[rel.id] = rel
        return rel

    def get_subclasses(self, class_id: str) -> List[OntologyClass]:
        """获取子类列表"""
        return [c for c in self.classes.values() if class_id in c.parent_classes]

    def get_class_hierarchy(self, class_id: str, depth: int = -1) -> Dict:
        """获取类层次结构"""
        cls = self.classes.get(class_id)
        if not cls:
            return {}
        result = cls.to_dict()
        if depth != 0:
            result["children"] = [
                self.get_class_hierarchy(c.id, depth - 1 if depth > 0 else -1)
                for c in self.get_subclasses(class_id)
            ]
        return result

    def validate_ontology(self) -> List[str]:
        """验证本体一致性"""
        errors = []
        for cls in self.classes.values():
            for parent_id in cls.parent_classes:
                if parent_id not in self.classes:
                    errors.append(f"Class '{cls.name}' references non-existent parent '{parent_id}'")
        for rel in self.relations.values():
            if rel.domain and not any(c.name == rel.domain for c in self.classes.values()):
                errors.append(f"Relation '{rel.name}' domain '{rel.domain}' not found")
        return errors

    def export_to_json(self) -> str:
        data = {
            "prefixes": self.prefixes,
            "classes": {k: v.to_dict() for k, v in self.classes.items()},
            "relations": {k: v.to_dict() for k, v in self.relations.items()},
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def import_from_json(self, json_str: str) -> None:
        data = json.loads(json_str)
        self.prefixes.update(data.get("prefixes", {}))
        for k, v in data.get("classes", {}).items():
            cls = OntologyClass(**{f: v[f] for f in ["id", "name", "description", "parent_classes", "properties", "created_at", "updated_at"] if f in v})
            self.classes[k] = cls
        for k, v in data.get("relations", {}).items():
            rel = OntologyRelation(**{f: v[f] for f in ["id", "name", "domain", "inverse_of", "transitive", "symmetric"] if f in v})
            if "range" in v:
                rel.range_type = v["range"]
            self.relations[k] = rel

    def search_classes(self, query: str) -> List[OntologyClass]:
        query_lower = query.lower()
        return [c for c in self.classes.values()
                if query_lower in c.name.lower() or query_lower in c.description.lower()]

    def add_prefix(self, prefix: str, uri: str) -> None:
        self.prefixes[prefix] = uri

    def get_statistics(self) -> Dict:
        return {
            "total_classes": len(self.classes),
            "total_relations": len(self.relations),
            "root_classes": len([c for c in self.classes.values() if not c.parent_classes]),
        }
