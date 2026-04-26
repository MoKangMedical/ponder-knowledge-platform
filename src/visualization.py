"""可视化模块 - Ponder Knowledge Platform"""

import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VisualNode:
    """可视化节点"""
    id: str = ""
    label: str = ""
    group: str = ""
    size: int = 10
    color: str = "#4A90D9"
    properties: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "label": self.label,
            "group": self.group, "size": self.size,
            "color": self.color, **self.properties
        }


@dataclass
class VisualEdge:
    """可视化边"""
    source: str = ""
    target: str = ""
    label: str = ""
    weight: float = 1.0
    color: str = "#999"

    def to_dict(self) -> Dict:
        return {
            "source": self.source, "target": self.target,
            "label": self.label, "weight": self.weight,
            "color": self.color
        }


class Visualizer:
    """知识图谱可视化器"""

    # 类型颜色映射
    TYPE_COLORS = {
        "person": "#E74C3C",
        "organization": "#3498DB",
        "location": "#2ECC71",
        "concept": "#F39C12",
        "event": "#9B59B6",
        "default": "#95A5A6"
    }

    def __init__(self):
        self.layouts = ["force", "circular", "hierarchical", "radial"]

    def create_graph_data(self, entities: List[Dict],
                          relations: List[Dict]) -> Dict:
        """创建图数据"""
        nodes = []
        for entity in entities:
            entity_type = entity.get("type", entity.get("entity_type", "default"))
            nodes.append(VisualNode(
                id=entity.get("id", str(uuid.uuid4())),
                label=entity.get("name", ""),
                group=entity_type,
                size=max(10, len(entity.get("name", "")) * 2),
                color=self.TYPE_COLORS.get(entity_type, self.TYPE_COLORS["default"]),
                properties={k: v for k, v in entity.items()
                           if k not in ("id", "name", "type", "entity_type")}
            ).to_dict())

        edges = []
        for rel in relations:
            edges.append(VisualEdge(
                source=rel.get("subject", ""),
                target=rel.get("object", ""),
                label=rel.get("predicate", ""),
                weight=rel.get("confidence", 1.0)
            ).to_dict())

        return {"nodes": nodes, "edges": edges}

    def generate_d3_config(self, graph_data: Dict,
                           width: int = 800, height: int = 600,
                           layout: str = "force") -> Dict:
        """生成D3.js配置"""
        return {
            "type": "d3",
            "width": width, "height": height,
            "layout": layout,
            "data": graph_data,
            "options": {
                "nodeRadius": 8,
                "linkDistance": 100,
                "charge": -300,
                "showLabels": True,
                "showEdgeLabels": True,
                "zoom": True
            }
        }

    def generate_cytoscape_config(self, graph_data: Dict) -> Dict:
        """生成Cytoscape配置"""
        elements = []
        for node in graph_data.get("nodes", []):
            elements.append({
                "group": "nodes",
                "data": node
            })
        for edge in graph_data.get("edges", []):
            elements.append({
                "group": "edges",
                "data": {
                    "source": edge["source"],
                    "target": edge["target"],
                    "label": edge.get("label", "")
                }
            })
        return {
            "type": "cytoscape",
            "elements": elements,
            "style": [
                {"selector": "node", "style": {"label": "data(label)"}},
                {"selector": "edge", "style": {"label": "data(label)"}}
            ],
            "layout": {"name": "cose"}
        }

    def generate_html(self, graph_data: Dict, title: str = "Knowledge Graph") -> str:
        """生成HTML可视化页面"""
        nodes_json = json.dumps(graph_data.get("nodes", []))
        edges_json = json.dumps(graph_data.get("edges", []))
        return f"""<!DOCTYPE html>
<html><head><title>{title}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; }}
svg {{ width: 100%; height: 100vh; }}
.node {{ cursor: pointer; }}
.link {{ stroke: #999; stroke-opacity: 0.6; }}
.node-label {{ font-size: 12px; pointer-events: none; }}
</style></head><body>
<h2 style="position:absolute;top:10px;left:10px;">{title}</h2>
<svg id="graph"></svg>
<script>
const nodes = {nodes_json};
const edges = {edges_json};
const svg = d3.select("#graph");
const width = window.innerWidth, height = window.innerHeight;
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(edges).id(d => d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width/2, height/2));
const link = svg.selectAll(".link").data(edges).enter().append("line").attr("class","link");
const node = svg.selectAll(".node").data(nodes).enter().append("circle").attr("class","node").attr("r", d => d.size || 10).attr("fill", d => d.color || "#4A90D9");
const label = svg.selectAll(".node-label").data(nodes).enter().append("text").attr("class","node-label").text(d => d.label);
simulation.on("tick", () => {{ link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y); node.attr("cx",d=>d.x).attr("cy",d=>d.y); label.attr("x",d=>d.x).attr("y",d=>d.y-15); }});
</script></body></html>"""

    def generate_statistics_chart_data(self, entities: List[Dict],
                                       relations: List[Dict]) -> Dict:
        """生成统计图表数据"""
        type_counts = {}
        for e in entities:
            t = e.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        pred_counts = {}
        for r in relations:
            p = r.get("predicate", "unknown")
            pred_counts[p] = pred_counts.get(p, 0) + 1

        return {
            "entity_types": {
                "labels": list(type_counts.keys()),
                "values": list(type_counts.values())
            },
            "relation_types": {
                "labels": list(pred_counts.keys()),
                "values": list(pred_counts.values())
            },
            "summary": {
                "total_entities": len(entities),
                "total_relations": len(relations),
                "entity_types_count": len(type_counts),
                "relation_types_count": len(pred_counts)
            }
        }
