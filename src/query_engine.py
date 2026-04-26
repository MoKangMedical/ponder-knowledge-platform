"""
查询引擎 (Query Engine)
基于知识图谱的多模式查询：自然语言问答、图遍历、路径搜索、聚合统计
"""

import json
import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

# ============================================================
# 数据模型
# ============================================================

@dataclass
class QueryResult:
    """查询结果"""
    query: str
    query_type: str        # nlq | neighbor | path | aggregate | subgraph
    answer: str = ""
    results: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "answer": self.answer,
            "results": self.results,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


# ============================================================
# 查询引擎
# ============================================================

class QueryEngine:
    """知识图谱查询引擎"""

    def __init__(self, kg_data: Optional[Dict] = None, kg_path: Optional[str] = None):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self._name_index: Dict[str, List[str]] = defaultdict(list)  # name -> [node_ids]
        self._type_index: Dict[str, List[str]] = defaultdict(list)  # type -> [node_ids]

        if kg_path:
            self.load_kg(kg_path)
        elif kg_data:
            self._build_index(kg_data)

        logger.info(f"QueryEngine 初始化完成: {len(self.nodes)} 节点, {len(self.edges)} 边")

    # ----------------------------------------------------------
    # 加载与索引
    # ----------------------------------------------------------

    def load_kg(self, path: str) -> None:
        """加载知识图谱文件"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 兼容两种格式
        if "nodes" in data and isinstance(data["nodes"], dict):
            self._build_index(data)
        elif "entities" in data:
            # sample-kg.json 格式
            kg = {"nodes": {}, "edges": []}
            for ent in data["entities"]:
                nid = ent["id"]
                kg["nodes"][nid] = {
                    "id": nid,
                    "label": ent.get("type", "Unknown"),
                    "name": ent.get("name", ""),
                    "properties": {k: v for k, v in ent.items() if k not in ("id", "type", "name")},
                }
            for rel in data.get("relations", []):
                kg["edges"].append({
                    "source_id": rel["source"],
                    "target_id": rel["target"],
                    "relation_type": rel["type"],
                    "properties": {k: v for k, v in rel.items() if k not in ("source", "target", "type")},
                })
            self._build_index(kg)
        else:
            logger.warning("未知的图谱格式")

    def _build_index(self, kg_data: Dict) -> None:
        """构建内部索引"""
        self.nodes = kg_data.get("nodes", {})
        self.edges = kg_data.get("edges", [])

        for nid, node in self.nodes.items():
            name = node.get("name", "")
            label = node.get("label", "")
            self._name_index[name.lower()].append(nid)
            self._type_index[label.lower()].append(nid)

    # ----------------------------------------------------------
    # 实体识别（简易）
    # ----------------------------------------------------------

    def _match_entities(self, text: str) -> List[Tuple[str, str]]:
        """从文本中匹配实体，返回 [(node_id, name), ...]"""
        text_lower = text.lower()
        matches = []
        for name, ids in self._name_index.items():
            if name in text_lower:
                for nid in ids:
                    matches.append((nid, self.nodes[nid].get("name", name)))
        # 按名称长度降序，优先匹配长名称
        matches.sort(key=lambda x: len(x[1]), reverse=True)
        # 去重
        seen: Set[str] = set()
        unique = []
        for nid, name in matches:
            if nid not in seen:
                seen.add(nid)
                unique.append((nid, name))
        return unique

    # ----------------------------------------------------------
    # 邻居查询
    # ----------------------------------------------------------

    def query_neighbors(self, entity_name: str, relation: Optional[str] = None) -> QueryResult:
        """查询实体的邻居"""
        matches = self._match_entities(entity_name)
        if not matches:
            return QueryResult(
                query=entity_name,
                query_type="neighbor",
                answer=f"未找到实体：{entity_name}",
                confidence=0.0,
            )

        results = []
        reasoning = []
        for nid, name in matches:
            reasoning.append(f"匹配实体: {name} ({nid})")
            for e in self.edges:
                if relation and e["relation_type"] != relation:
                    continue
                neighbor_id = None
                direction = ""
                if e["source_id"] == nid:
                    neighbor_id = e["target_id"]
                    direction = "out"
                elif e["target_id"] == nid:
                    neighbor_id = e["source_id"]
                    direction = "in"

                if neighbor_id and neighbor_id in self.nodes:
                    nn = self.nodes[neighbor_id]
                    results.append({
                        "entity": name,
                        "neighbor": nn.get("name", ""),
                        "neighbor_type": nn.get("label", ""),
                        "relation": e["relation_type"],
                        "direction": direction,
                        "properties": e.get("properties", {}),
                    })
                    reasoning.append(
                        f"  {name} -[{e['relation_type']}]-> {nn.get('name', '')}"
                    )

        answer_lines = []
        for r in results:
            arrow = "→" if r["direction"] == "out" else "←"
            answer_lines.append(
                f"{r['entity']} {arrow} [{r['relation']}] {arrow} {r['neighbor']}（{r['neighbor_type']}）"
            )

        return QueryResult(
            query=entity_name,
            query_type="neighbor",
            answer="\n".join(answer_lines) if answer_lines else f"{entity_name} 无相关邻居",
            results=results,
            confidence=0.9 if results else 0.3,
            reasoning=reasoning,
        )

    # ----------------------------------------------------------
    # 路径搜索
    # ----------------------------------------------------------

    def query_path(self, source_name: str, target_name: str, max_depth: int = 4) -> QueryResult:
        """BFS 搜索两实体间路径"""
        src_matches = self._match_entities(source_name)
        tgt_matches = self._match_entities(target_name)

        if not src_matches:
            return QueryResult(query=f"{source_name} -> {target_name}", query_type="path",
                               answer=f"未找到源实体: {source_name}")
        if not tgt_matches:
            return QueryResult(query=f"{source_name} -> {target_name}", query_type="path",
                               answer=f"未找到目标实体: {target_name}")

        src_ids = {nid for nid, _ in src_matches}
        tgt_ids = {nid for nid, _ in tgt_matches}

        # BFS
        from collections import deque
        queue: deque = deque()
        visited: Dict[str, Optional[str]] = {}  # node_id -> parent_id

        for sid in src_ids:
            queue.append(sid)
            visited[sid] = None

        found_target: Optional[str] = None
        while queue and found_target is None:
            current = queue.popleft()
            depth = 0
            p = current
            while visited.get(p) is not None:
                depth += 1
                p = visited[p]
            if depth >= max_depth:
                continue

            for e in self.edges:
                neighbor = None
                if e["source_id"] == current:
                    neighbor = e["target_id"]
                elif e["target_id"] == current:
                    neighbor = e["source_id"]

                if neighbor and neighbor not in visited:
                    visited[neighbor] = current
                    if neighbor in tgt_ids:
                        found_target = neighbor
                        break
                    queue.append(neighbor)

        if found_target is None:
            return QueryResult(
                query=f"{source_name} -> {target_name}",
                query_type="path",
                answer=f"未找到 {source_name} 到 {target_name} 的路径",
            )

        # 回溯路径
        path_nodes = []
        cur = found_target
        while cur is not None:
            path_nodes.append(cur)
            cur = visited.get(cur)
        path_nodes.reverse()

        path_desc = []
        for nid in path_nodes:
            n = self.nodes.get(nid, {})
            path_desc.append(n.get("name", nid))

        return QueryResult(
            query=f"{source_name} -> {target_name}",
            query_type="path",
            answer=" → ".join(path_desc),
            results=[{"path": path_nodes, "node_names": path_desc}],
            confidence=0.85,
            reasoning=[f"BFS 路径搜索 (max_depth={max_depth})"],
        )

    # ----------------------------------------------------------
    # 聚合查询
    # ----------------------------------------------------------

    def query_aggregate(self, entity_type: Optional[str] = None) -> QueryResult:
        """统计指定类型的实体及关系"""
        type_key = (entity_type or "").lower()
        if type_key and type_key in self._type_index:
            nids = self._type_index[type_key]
        elif entity_type:
            return QueryResult(
                query=f"聚合: {entity_type}", query_type="aggregate",
                answer=f"未找到类型: {entity_type}",
            )
        else:
            nids = list(self.nodes.keys())

        type_counts: Dict[str, int] = defaultdict(int)
        rel_counts: Dict[str, int] = defaultdict(int)
        for nid in nids:
            node = self.nodes[nid]
            type_counts[node.get("label", "Unknown")] += 1
            for e in self.edges:
                if e["source_id"] == nid or e["target_id"] == nid:
                    rel_counts[e["relation_type"]] += 1

        lines = [f"实体总数: {len(nids)}"]
        for t, c in sorted(type_counts.items()):
            lines.append(f"  {t}: {c}")
        lines.append("关系统计:")
        for r, c in sorted(rel_counts.items()):
            lines.append(f"  {r}: {c}")

        return QueryResult(
            query=f"聚合: {entity_type or '全部'}",
            query_type="aggregate",
            answer="\n".join(lines),
            results=[{"type_counts": dict(type_counts), "relation_counts": dict(rel_counts)}],
            confidence=1.0,
        )

    # ----------------------------------------------------------
    # 自然语言查询（规则式）
    # ----------------------------------------------------------

    NLQ_PATTERNS = [
        # "XX 的症状" / "XX有哪些症状"
        (r"(.+?)的(?:症状|表现|临床表现)", "neighbor", "HAS_SYMPTOM"),
        (r"(.+?)(?:有哪些|有什么)(?:症状|表现)", "neighbor", "HAS_SYMPTOM"),
        # "XX 的治疗" / "XX怎么治"
        (r"(.+?)的(?:治疗|疗法|用药|药物)", "neighbor", "TREATED_BY"),
        (r"(.+?)(?:怎么治|如何治疗)", "neighbor", "TREATED_BY"),
        # "XX 的检查"
        (r"(.+?)的(?:检查|诊断|检测)", "neighbor", "DIAGNOSED_BY"),
        # "XX 和 YY 的关系"
        (r"(.+?)和(.+?)(?:的)?(?:关系|关联|联系)", "path", None),
        # "XX 影响什么部位"
        (r"(.+?)(?:影响|累及)(?:什么|哪些)(?:部位|器官)", "neighbor", "AFFECTS"),
    ]

    def query_nlq(self, question: str) -> QueryResult:
        """自然语言查询入口"""
        question = question.strip()

        # 统计类问题
        if any(kw in question for kw in ["统计", "有多少", "总共", "总览"]):
            entity_type = None
            for label in ["疾病", "症状", "药物", "检查", "治疗"]:
                if label in question:
                    # 反向映射中文 -> 英文
                    cn_map = {"疾病": "Disease", "症状": "Symptom", "药物": "Drug",
                              "检查": "Examination", "治疗": "Treatment"}
                    entity_type = cn_map.get(label)
                    break
            return self.query_aggregate(entity_type)

        # 模式匹配
        for pattern, qtype, relation in self.NLQ_PATTERNS:
            m = re.search(pattern, question)
            if m:
                if qtype == "neighbor":
                    return self.query_neighbors(m.group(1).strip(), relation=relation)
                elif qtype == "path":
                    return self.query_path(m.group(1).strip(), m.group(2).strip())

        # 回退：尝试匹配实体名并返回邻居
        entities = self._match_entities(question)
        if entities:
            return self.query_neighbors(entities[0][1])

        return QueryResult(
            query=question,
            query_type="nlq",
            answer=f"暂不支持此类查询，请尝试询问疾病的症状、治疗、检查等。",
            confidence=0.1,
        )

    # ----------------------------------------------------------
    # 统一查询入口
    # ----------------------------------------------------------

    def query(self, query_str: str, query_type: str = "auto") -> QueryResult:
        """统一查询入口"""
        if query_type == "nlq" or query_type == "auto":
            return self.query_nlq(query_str)
        elif query_type == "neighbor":
            return self.query_neighbors(query_str)
        elif query_type == "aggregate":
            return self.query_aggregate(query_str)
        else:
            return self.query_nlq(query_str)


# ============================================================
# CLI 入口
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="知识图谱查询引擎")
    parser.add_argument("--kg", default="data/sample-kg.json", help="图谱文件")
    parser.add_argument("--query", "-q", default="2型糖尿病的症状", help="查询内容")
    args = parser.parse_args()

    engine = QueryEngine(kg_path=args.kg)
    result = engine.query(args.query)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
