"""导出功能模块 - Ponder Knowledge Platform"""

import json
import csv
import io
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExportFormat(Enum):
    JSON = "json"
    CSV = "csv"
    RDF_TURTLE = "turtle"
    RDF_XML = "xml"
    MARKDOWN = "markdown"
    GRAPHML = "graphml"


@dataclass
class ExportResult:
    """导出结果"""
    format: str = ""
    content: str = ""
    filename: str = ""
    size: int = 0
    record_count: int = 0
    exported_at: str = field(default_factory=lambda: datetime.now().isoformat())


class Exporter:
    """知识导出器"""

    def __init__(self):
        self.exports: List[ExportResult] = []

    def export_json(self, data: Any, pretty: bool = True) -> ExportResult:
        """导出为JSON"""
        content = json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)
        result = ExportResult(
            format="json", content=content,
            filename=f"export_{uuid.uuid4().hex[:8]}.json",
            size=len(content.encode()),
            record_count=len(data) if isinstance(data, (list, dict)) else 1
        )
        self.exports.append(result)
        return result

    def export_csv(self, records: List[Dict], columns: Optional[List[str]] = None) -> ExportResult:
        """导出为CSV"""
        if not records:
            return ExportResult(format="csv", content="", record_count=0)
        if columns is None:
            columns = list(records[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)
        content = output.getvalue()
        result = ExportResult(
            format="csv", content=content,
            filename=f"export_{uuid.uuid4().hex[:8]}.csv",
            size=len(content.encode()),
            record_count=len(records)
        )
        self.exports.append(result)
        return result

    def export_rdf_turtle(self, triples: List[Dict],
                          prefixes: Optional[Dict[str, str]] = None) -> ExportResult:
        """导出为RDF Turtle"""
        lines = []
        if prefixes:
            for prefix, uri in prefixes.items():
                lines.append(f"@prefix {prefix}: <{uri}> .")
            lines.append("")

        for triple in triples:
            subj = triple.get("subject", "")
            pred = triple.get("predicate", "")
            obj = triple.get("object", "")
            obj_str = f'"{obj}"' if not obj.startswith("http") else f"<{obj}>"
            lines.append(f"<{subj}> <{pred}> {obj_str} .")

        content = "\n".join(lines)
        result = ExportResult(
            format="turtle", content=content,
            filename=f"export_{uuid.uuid4().hex[:8]}.ttl",
            size=len(content.encode()),
            record_count=len(triples)
        )
        self.exports.append(result)
        return result

    def export_markdown(self, title: str, sections: List[Dict]) -> ExportResult:
        """导出为Markdown"""
        lines = [f"# {title}\n"]
        for section in sections:
            heading = section.get("heading", "")
            level = section.get("level", 2)
            lines.append(f"{'#' * level} {heading}\n")
            content = section.get("content", "")
            if isinstance(content, list):
                for item in content:
                    lines.append(f"- {item}")
            else:
                lines.append(str(content))
            lines.append("")

        content = "\n".join(lines)
        result = ExportResult(
            format="markdown", content=content,
            filename=f"export_{uuid.uuid4().hex[:8]}.md",
            size=len(content.encode()),
            record_count=len(sections)
        )
        self.exports.append(result)
        return result

    def export_graphml(self, nodes: List[Dict], edges: List[Dict]) -> ExportResult:
        """导出为GraphML"""
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <graph id="G" edgedefault="directed">'
        ]
        for node in nodes:
            nid = node.get("id", "")
            label = node.get("label", nid)
            xml_lines.append(f'    <node id="{nid}"><data key="label">{label}</data></node>')
        for i, edge in enumerate(edges):
            source = edge.get("source", "")
            target = edge.get("target", "")
            label = edge.get("label", "")
            xml_lines.append(f'    <edge id="e{i}" source="{source}" target="{target}"><data key="label">{label}</data></edge>')
        xml_lines.append("  </graph>")
        xml_lines.append("</graphml>")

        content = "\n".join(xml_lines)
        result = ExportResult(
            format="graphml", content=content,
            filename=f"export_{uuid.uuid4().hex[:8]}.graphml",
            size=len(content.encode()),
            record_count=len(nodes) + len(edges)
        )
        self.exports.append(result)
        return result

    def export_knowledge_graph(self, entities: List[Dict],
                               relations: List[Dict],
                               fmt: str = "json") -> ExportResult:
        """导出知识图谱"""
        if fmt == "json":
            data = {"entities": entities, "relations": relations}
            return self.export_json(data)
        elif fmt == "graphml":
            nodes = [{"id": e.get("id", ""), "label": e.get("name", "")} for e in entities]
            edges = [{"source": r.get("subject", ""), "target": r.get("object", ""),
                       "label": r.get("predicate", "")} for r in relations]
            return self.export_graphml(nodes, edges)
        elif fmt == "turtle":
            return self.export_rdf_turtle(relations)
        return ExportResult(format=fmt, content="")

    def get_export_history(self) -> List[Dict]:
        return [{
            "format": e.format, "filename": e.filename,
            "size": e.size, "record_count": e.record_count,
            "exported_at": e.exported_at
        } for e in self.exports]

    def get_statistics(self) -> Dict:
        return {
            "total_exports": len(self.exports),
            "by_format": self._count_by_format(),
            "total_size": sum(e.size for e in self.exports)
        }

    def _count_by_format(self) -> Dict[str, int]:
        counts = {}
        for e in self.exports:
            counts[e.format] = counts.get(e.format, 0) + 1
        return counts
