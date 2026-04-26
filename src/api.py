"""
FastAPI 服务 (API)
知识图谱平台 RESTful API
"""

import json
import logging
from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph_builder import GraphBuilder, KnowledgeGraph
from query_engine import QueryEngine

logger = logging.getLogger(__name__)

# ============================================================
# App 初始化
# ============================================================

app = FastAPI(
    title="Ponder Knowledge — 医学知识图谱平台",
    description="基于知识图谱的医学知识查询与管理 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
_builder: Optional[GraphBuilder] = None
_engine: Optional[QueryEngine] = None

DATA_DIR = Path(__file__).parent.parent / "data"
ONTOLOGY_PATH = DATA_DIR / "medical-ontology.json"
SAMPLE_KG_PATH = DATA_DIR / "sample-kg.json"
KG_BUILT_PATH = DATA_DIR / "kg-built.json"


def _ensure_initialized() -> None:
    """延迟初始化"""
    global _builder, _engine
    if _builder is not None:
        return

    _builder = GraphBuilder()
    if ONTOLOGY_PATH.exists():
        _builder.load_ontology(str(ONTOLOGY_PATH))

    kg_source = str(KG_BUILT_PATH) if KG_BUILT_PATH.exists() else str(SAMPLE_KG_PATH)
    if Path(kg_source).exists():
        _builder.load_sample_kg(kg_source) if kg_source == str(SAMPLE_KG_PATH) else _builder.load(kg_source)

    _engine = QueryEngine(kg_data=_builder.kg.to_dict())
    logger.info("API 引擎初始化完成")


# ============================================================
# 请求 / 响应模型
# ============================================================

class QueryRequest(BaseModel):
    query: str = Field(..., description="查询内容")
    query_type: str = Field("auto", description="查询类型: auto|nlq|neighbor|aggregate")


class EntityRequest(BaseModel):
    name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型: Disease|Symptom|Drug|...")
    properties: dict = Field(default_factory=dict, description="属性")


class RelationRequest(BaseModel):
    source_id: str = Field(..., description="源节点 ID")
    target_id: str = Field(..., description="目标节点 ID")
    relation_type: str = Field(..., description="关系类型")
    properties: dict = Field(default_factory=dict, description="属性")


# ============================================================
# API 路由
# ============================================================

@app.get("/", tags=["General"])
def root():
    return {
        "service": "Ponder Knowledge API",
        "version": "1.0.0",
        "endpoints": ["/query", "/graph/stats", "/graph/neighbors", "/graph/path",
                       "/entities", "/relations", "/ontology"],
    }


@app.get("/health", tags=["General"])
def health():
    _ensure_initialized()
    stats = _builder.kg.stats()
    return {"status": "ok", "nodes": stats["total_nodes"], "edges": stats["total_edges"]}


# ---------- 查询 ----------

@app.post("/query", tags=["Query"])
def query_kg(req: QueryRequest):
    """知识图谱查询（支持自然语言、邻居、聚合）"""
    _ensure_initialized()
    result = _engine.query(req.query, req.query_type)
    return result.to_dict()


@app.get("/query/nlq", tags=["Query"])
def query_nlq(q: str = Query(..., description="自然语言问题")):
    """自然语言查询"""
    _ensure_initialized()
    result = _engine.query_nlq(q)
    return result.to_dict()


# ---------- 图谱浏览 ----------

@app.get("/graph/stats", tags=["Graph"])
def graph_stats():
    """图谱统计"""
    _ensure_initialized()
    return _builder.kg.stats()


@app.get("/graph/neighbors", tags=["Graph"])
def graph_neighbors(entity: str = Query(..., description="实体名称"),
                    relation: Optional[str] = Query(None, description="关系类型过滤")):
    """邻居查询"""
    _ensure_initialized()
    matches = _engine._match_entities(entity)
    if not matches:
        raise HTTPException(404, f"未找到实体: {entity}")

    nid = matches[0][0]
    results = _builder.get_neighbors(nid, relation_type=relation)
    return {"entity": entity, "node_id": nid, "neighbors": results}


@app.get("/graph/path", tags=["Graph"])
def graph_path(source: str = Query(...), target: str = Query(...)):
    """路径查询"""
    _ensure_initialized()
    result = _engine.query_path(source, target)
    return result.to_dict()


@app.get("/graph/subgraph", tags=["Graph"])
def graph_subgraph(entity: str = Query(...), depth: int = Query(2, ge=1, le=5)):
    """子图查询"""
    _ensure_initialized()
    matches = _engine._match_entities(entity)
    if not matches:
        raise HTTPException(404, f"未找到实体: {entity}")
    sub = _builder.get_subgraph(matches[0][0], depth=depth)
    return sub


# ---------- 实体管理 ----------

@app.get("/entities", tags=["Entities"])
def list_entities(entity_type: Optional[str] = Query(None)):
    """列出实体"""
    _ensure_initialized()
    nodes = _builder.kg.nodes
    if entity_type:
        nodes = {nid: n for nid, n in nodes.items() if n.label == entity_type}
    return {"count": len(nodes), "entities": [n.to_dict() for n in nodes.values()]}


@app.post("/entities", tags=["Entities"])
def add_entity(req: EntityRequest):
    """添加实体"""
    _ensure_initialized()
    from graph_builder import GraphBuilder as GB
    node_id = GB._make_id(req.entity_type, req.name)
    node = _builder.add_node(node_id, req.entity_type, req.name, req.properties)
    return {"status": "ok", "node": node.to_dict()}


# ---------- 关系管理 ----------

@app.post("/relations", tags=["Relations"])
def add_relation(req: RelationRequest):
    """添加关系"""
    _ensure_initialized()
    edge = _builder.add_edge(req.source_id, req.target_id, req.relation_type, req.properties)
    if not edge:
        raise HTTPException(400, "添加关系失败（节点不存在）")
    return {"status": "ok", "edge": edge.to_dict()}


# ---------- 本体 ----------

@app.get("/ontology", tags=["Ontology"])
def get_ontology():
    """获取医学本体定义"""
    _ensure_initialized()
    return _builder.ontology


# ============================================================
# CLI 入口
# ============================================================

def main():
    import uvicorn
    _ensure_initialized()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
