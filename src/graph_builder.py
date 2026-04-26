"""
知识图谱构建模块 (Graph Builder)
从抽取结果和结构化数据构建、合并、持久化知识图谱
"""

import json
import logging
import hashlib
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 数据模型
# ============================================================

@dataclass
class KGNode:
    """知识图谱节点"""
    id: str
    label: str           # 实体类型: Disease, Symptom, Drug, etc.
    name: str
    properties: Dict = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KGEdge:
    """知识图谱边"""
    source_id: str
    target_id: str
    relation_type: str   # HAS_SYMPTOM, TREATED_BY, etc.
    properties: Dict = field(default_factory=list)
    weight: float = 1.0
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KnowledgeGraph:
    """知识图谱"""
    name: str = "medical-kg"
    version: str = "1.0.0"
    nodes: Dict[str, KGNode] = field(default_factory=dict)
    edges: List[KGEdge] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
        }

    def stats(self) -> Dict:
        """统计信息"""
        label_counts: Dict[str, int] = {}
        for n in self.nodes.values():
            label_counts[n.label] = label_counts.get(n.label, 0) + 1
        rel_counts: Dict[str, int] = {}
        for e in self.edges:
            rel_counts[e.relation_type] = rel_counts.get(e.relation_type, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": label_counts,
            "relation_types": rel_counts,
        }


# ============================================================
# 图谱构建器
# ============================================================

class GraphBuilder:
    """知识图谱构建与管理"""

    def __init__(self, ontology_path: Optional[str] = None):
        self.kg = KnowledgeGraph(
            metadata={"created_at": datetime.now().isoformat()}
        )
        self.ontology: Dict = {}
        if ontology_path:
            self.load_ontology(ontology_path)
        logger.info("GraphBuilder 初始化完成")

    # ----------------------------------------------------------
    # 本体加载
    # ----------------------------------------------------------

    def load_ontology(self, path: str) -> Dict:
        """加载医学本体定义"""
        with open(path, "r", encoding="utf-8") as f:
            self.ontology = json.load(f)
        logger.info(f"本体加载完成: {len(self.ontology.get('entity_types', {}))} 实体类型, "
                     f"{len(self.ontology.get('relation_types', {}))} 关系类型")
        return self.ontology

    def validate_entity_type(self, entity_type: str) -> bool:
        """校验实体类型是否在本体中"""
        if not self.ontology:
            return True
        valid_types = set(self.ontology.get("entity_types", {}).keys())
        return entity_type in valid_types

    def validate_relation_type(self, relation_type: str) -> bool:
        """校验关系类型是否在本体中"""
        if not self.ontology:
            return True
        valid_types = set(self.ontology.get("relation_types", {}).keys())
        return relation_type in valid_types

    # ----------------------------------------------------------
    # 节点 / 边操作
    # ----------------------------------------------------------

    @staticmethod
    def _make_id(prefix: str, name: str) -> str:
        """生成确定性 ID"""
        h = hashlib.md5(f"{prefix}:{name}".encode()).hexdigest()[:8]
        return f"{prefix}_{h}"

    def add_node(self, node_id: str, label: str, name: str,
                 properties: Optional[Dict] = None, source: str = "") -> KGNode:
        """添加节点（自动去重合并）"""
        now = datetime.now().isoformat()
        if node_id in self.kg.nodes:
            existing = self.kg.nodes[node_id]
            if properties:
                existing.properties.update(properties)
            if source and source not in existing.sources:
                existing.sources.append(source)
            existing.updated_at = now
            logger.debug(f"合并节点: {node_id}")
            return existing

        node = KGNode(
            id=node_id,
            label=label,
            name=name,
            properties=properties or {},
            sources=[source] if source else [],
            created_at=now,
            updated_at=now,
        )
        self.kg.nodes[node_id] = node
        logger.debug(f"新增节点: {node_id} ({label}: {name})")
        return node

    def add_edge(self, source_id: str, target_id: str, relation_type: str,
                 properties: Optional[Dict] = None, weight: float = 1.0,
                 source: str = "") -> Optional[KGEdge]:
        """添加边（自动去重合并）"""
        if source_id not in self.kg.nodes:
            logger.warning(f"源节点不存在: {source_id}")
            return None
        if target_id not in self.kg.nodes:
            logger.warning(f"目标节点不存在: {target_id}")
            return None

        # 查找已有边
        for e in self.kg.edges:
            if e.source_id == source_id and e.target_id == target_id and e.relation_type == relation_type:
                if properties:
                    e.properties.update(properties)
                e.weight = max(e.weight, weight)
                if source and source not in e.sources:
                    e.sources.append(source)
                logger.debug(f"合并边: {source_id} -[{relation_type}]-> {target_id}")
                return e

        edge = KGEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            properties=properties or {},
            weight=weight,
            sources=[source] if source else [],
        )
        self.kg.edges.append(edge)
        logger.debug(f"新增边: {source_id} -[{relation_type}]-> {target_id}")
        return edge

    # ----------------------------------------------------------
    # 批量构建
    # ----------------------------------------------------------

    def load_sample_kg(self, path: str) -> KnowledgeGraph:
        """从 sample-kg.json 加载示例图谱"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for ent in data.get("entities", []):
            self.add_node(
                node_id=ent["id"],
                label=ent["type"],
                name=ent["name"],
                properties={k: v for k, v in ent.items() if k not in ("id", "type", "name")},
                source="sample-kg",
            )

        for rel in data.get("relations", []):
            self.add_edge(
                source_id=rel["source"],
                target_id=rel["target"],
                relation_type=rel["type"],
                properties={k: v for k, v in rel.items() if k not in ("source", "target", "type")},
                source="sample-kg",
            )

        stats = self.kg.stats()
        logger.info(f"示例图谱加载完成: {stats['total_nodes']} 节点, {stats['total_edges']} 边")
        return self.kg

    def ingest_extraction_result(self, entities: List[Dict], relations: List[Dict],
                                  source: str = "extraction") -> Tuple[int, int]:
        """导入知识抽取结果"""
        node_count = 0
        for ent in entities:
            eid = ent.get("id") or self._make_id(ent.get("entity_type", "Unknown"), ent.get("name", ""))
            self.add_node(
                node_id=eid,
                label=ent.get("entity_type", "Unknown"),
                name=ent.get("name", ""),
                properties=ent.get("attributes", {}),
                source=source,
            )
            node_count += 1

        edge_count = 0
        for rel in relations:
            e = self.add_edge(
                source_id=rel["source_id"],
                target_id=rel["target_id"],
                relation_type=rel.get("relation_type", "RELATED"),
                properties=rel.get("attributes", {}),
                weight=rel.get("confidence", 1.0),
                source=source,
            )
            if e:
                edge_count += 1

        logger.info(f"导入抽取结果: {node_count} 节点, {edge_count} 边")
        return node_count, edge_count

    # ----------------------------------------------------------
    # 图遍历
    # ----------------------------------------------------------

    def get_neighbors(self, node_id: str, relation_type: Optional[str] = None,
                      direction: str = "both") -> List[Dict]:
        """获取邻居节点"""
        if node_id not in self.kg.nodes:
            return []

        results = []
        for e in self.kg.edges:
            if relation_type and e.relation_type != relation_type:
                continue

            neighbor_id = None
            if direction in ("out", "both") and e.source_id == node_id:
                neighbor_id = e.target_id
            elif direction in ("in", "both") and e.target_id == node_id:
                neighbor_id = e.source_id

            if neighbor_id and neighbor_id in self.kg.nodes:
                neighbor = self.kg.nodes[neighbor_id]
                results.append({
                    "node": neighbor.to_dict(),
                    "relation": e.relation_type,
                    "direction": "out" if e.source_id == node_id else "in",
                    "edge_properties": e.properties,
                })

        return results

    def get_subgraph(self, center_id: str, depth: int = 2) -> Dict:
        """以某节点为中心获取子图"""
        visited: Set[str] = set()
        frontier = {center_id}
        sub_nodes: Dict[str, KGNode] = {}
        sub_edges: List[KGEdge] = []

        for _ in range(depth):
            next_frontier: Set[str] = set()
            for nid in frontier:
                if nid in visited:
                    continue
                visited.add(nid)
                if nid in self.kg.nodes:
                    sub_nodes[nid] = self.kg.nodes[nid]
                for e in self.kg.edges:
                    if e.source_id == nid and e.target_id not in visited:
                        sub_edges.append(e)
                        next_frontier.add(e.target_id)
                    elif e.target_id == nid and e.source_id not in visited:
                        sub_edges.append(e)
                        next_frontier.add(e.source_id)
            frontier = next_frontier

        return {
            "nodes": {nid: n.to_dict() for nid, n in sub_nodes.items()},
            "edges": [e.to_dict() for e in sub_edges],
        }

    # ----------------------------------------------------------
    # 持久化
    # ----------------------------------------------------------

    def save(self, path: str) -> None:
        """保存图谱到 JSON"""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.kg.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"图谱已保存: {path} ({self.kg.stats()['total_nodes']} 节点)")

    def load(self, path: str) -> KnowledgeGraph:
        """从 JSON 加载图谱"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.kg.name = data.get("name", "medical-kg")
        self.kg.version = data.get("version", "1.0.0")
        self.kg.metadata = data.get("metadata", {})

        for nid, ndata in data.get("nodes", {}).items():
            self.kg.nodes[nid] = KGNode(**ndata)

        for edata in data.get("edges", []):
            self.kg.edges.append(KGEdge(**edata))

        logger.info(f"图谱加载完成: {self.kg.stats()}")
        return self.kg


# ============================================================
# CLI 入口
# ============================================================

def main():
    """命令行演示"""
    import argparse
    parser = argparse.ArgumentParser(description="知识图谱构建工具")
    parser.add_argument("--ontology", default="data/medical-ontology.json", help="本体文件路径")
    parser.add_argument("--sample", default="data/sample-kg.json", help="示例图谱路径")
    parser.add_argument("--output", default="data/kg-built.json", help="输出路径")
    args = parser.parse_args()

    builder = GraphBuilder(ontology_path=args.ontology)
    builder.load_sample_kg(args.sample)
    builder.save(args.output)

    stats = builder.kg.stats()
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
