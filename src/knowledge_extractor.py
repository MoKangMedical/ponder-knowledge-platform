"""
知识抽取模块 (Knowledge Extractor)
从非结构化医疗文本中提取实体和关系，构建知识图谱
"""

import json
import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Entity:
    """医疗实体"""
    id: str
    name: str
    entity_type: str  # Disease, Symptom, Drug, Examination, BodyPart, Treatment
    attributes: Dict = field(default_factory=dict)
    source_text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Relation:
    """实体关系"""
    source_id: str
    target_id: str
    relation_type: str  # HAS_SYMPTOM, TREATED_BY, DIAGNOSED_BY, etc.
    attributes: Dict = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExtractionResult:
    """抽取结果"""
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    source_text: str = ""

    def to_dict(self) -> Dict:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "entity_count": len(self.entities),
            "relation_count": len(self.relations),
        }


# ============================================================
# 医学词典（内置基础词典，实际项目应连接外部术语库）
# ============================================================

MEDICAL_TERMS = {
    "Disease": [
        "2型糖尿病", "1型糖尿病", "糖尿病", "高血压", "冠心病", "心肌梗死",
        "脑卒中", "脑梗死", "脑出血", "肺炎", "肺癌", "肝癌", "胃癌",
        "慢性肾病", "糖尿病肾病", "糖尿病视网膜病变", "甲状腺功能亢进",
        "甲状腺功能减退", "痛风", "类风湿关节炎", "系统性红斑狼疮",
        "哮喘", "慢性阻塞性肺疾病", "肺结核", "贫血", "白血病",
    ],
    "Symptom": [
        "发热", "咳嗽", "头痛", "头晕", "胸痛", "腹痛", "恶心", "呕吐",
        "腹泻", "便秘", "乏力", "消瘦", "水肿", "多饮", "多尿", "多食",
        "体重下降", "蛋白尿", "血尿", "黄疸", "皮疹", "瘙痒", "失眠",
        "心悸", "气促", "呼吸困难", "吞咽困难", "关节疼痛",
    ],
    "Drug": [
        "二甲双胍", "格列美脲", "格列齐特", "阿卡波糖", "恩格列净",
        "达格列净", "利拉鲁肽", "司美格鲁肽", "胰岛素", "缬沙坦",
        "氨氯地平", "阿托伐他汀", "氯吡格雷", "阿司匹林", "奥美拉唑",
        "头孢克肟", "阿莫西林", "左氧氟沙星", "布洛芬", "对乙酰氨基酚",
    ],
    "Examination": [
        "空腹血糖", "餐后血糖", "糖化血红蛋白", "血常规", "尿常规",
        "肝功能", "肾功能", "血脂", "心电图", "胸部CT", "腹部B超",
        "甲状腺功能", "肿瘤标志物", "尿微量白蛋白", "眼底检查",
        "头颅MRI", "冠脉造影", "胃镜", "肠镜", "骨密度",
    ],
}

# 实体类型别名映射
ENTITY_ALIASES = {
    "糖尿病": "Disease", "血糖": "Examination", "降糖药": "Drug",
    "降压药": "Drug", "抗生素": "Drug", "检查": "Examination",
}

# 关系触发词
RELATION_PATTERNS = {
    "HAS_SYMPTOM": ["表现为", "症状包括", "出现", "伴有", "并发", "常见症状"],
    "TREATED_BY": ["使用", "服用", "治疗药物", "用药", "给予", "处方"],
    "DIAGNOSED_BY": ["检查", "检测", "化验", "诊断依据", "确诊需要"],
    "COMORBID_WITH": ["合并", "伴发", "同时患有", "并发"],
    "CONTRAINDICATED_FOR": ["禁用于", "禁忌", "不宜使用", "慎用"],
}


# ============================================================
# 命名实体识别 (NER)
# ============================================================

class MedicalNER:
    """基于词典+规则的医学NER（生产环境应替换为训练好的模型）"""

    def __init__(self, custom_terms: Optional[Dict] = None):
        self.terms = MEDICAL_TERMS.copy()
        if custom_terms:
            for etype, words in custom_terms.items():
                self.terms.setdefault(etype, []).extend(words)
        # 构建索引
        self._term_to_type: Dict[str, str] = {}
        for etype, words in self.terms.items():
            for w in words:
                self._term_to_type[w] = etype

    def recognize(self, text: str) -> List[Entity]:
        """从文本中识别医疗实体"""
        entities = []
        seen = set()
        # 按长度降序匹配，优先长词
        sorted_terms = sorted(self._term_to_type.keys(), key=len, reverse=True)
        for term in sorted_terms:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx == -1:
                    break
                end = idx + len(term)
                if term not in seen:
                    seen.add(term)
                    entity = Entity(
                        id=f"E_{len(entities):04d}",
                        name=term,
                        entity_type=self._term_to_type[term],
                        source_text=text[max(0, idx-20):end+20],
                        confidence=0.85,
                    )
                    entities.append(entity)
                start = end
        return entities


# ============================================================
# 关系抽取
# ============================================================

class RelationExtractor:
    """基于规则的医疗关系抽取"""

    def extract(self, text: str, entities: List[Entity]) -> List[Relation]:
        """从文本和已识别实体中抽取关系"""
        relations = []
        entity_map = {e.name: e for e in entities}

        for rel_type, triggers in RELATION_PATTERNS.items():
            for trigger in triggers:
                pattern = rf'(\w+){re.escape(trigger)}(\w+)'
                for match in re.finditer(pattern, text):
                    src_name, tgt_name = match.group(1), match.group(2)
                    if src_name in entity_map and tgt_name in entity_map:
                        src = entity_map[src_name]
                        tgt = entity_map[tgt_name]
                        relation = Relation(
                            source_id=src.id,
                            target_id=tgt.id,
                            relation_type=rel_type,
                            confidence=0.75,
                        )
                        relations.append(relation)

        # 基于共现的关系推断（实体在同一句中共现）
        relations.extend(self._cooccurrence_relations(text, entities))

        return relations

    def _cooccurrence_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """基于共现的弱关系抽取"""
        relations = []
        sentences = re.split(r'[。；\n]', text)
        for sent in sentences:
            sent_entities = [e for e in entities if e.name in sent]
            for i, e1 in enumerate(sent_entities):
                for e2 in sent_entities[i+1:]:
                    rel_type = self._infer_relation_type(e1.entity_type, e2.entity_type)
                    if rel_type:
                        relations.append(Relation(
                            source_id=e1.id,
                            target_id=e2.id,
                            relation_type=rel_type,
                            confidence=0.5,
                        ))
        return relations

    @staticmethod
    def _infer_relation_type(src_type: str, tgt_type: str) -> Optional[str]:
        """根据实体类型推断可能的关系类型"""
        type_pair_map = {
            ("Disease", "Symptom"): "HAS_SYMPTOM",
            ("Disease", "Drug"): "TREATED_BY",
            ("Disease", "Examination"): "DIAGNOSED_BY",
            ("Disease", "Disease"): "COMORBID_WITH",
            ("Drug", "Disease"): "CONTRAINDICATED_FOR",
        }
        return type_pair_map.get((src_type, tgt_type))


# ============================================================
# 知识抽取引擎
# ============================================================

class KnowledgeExtractor:
    """知识抽取主引擎"""

    def __init__(self, ontology_path: Optional[str] = None):
        self.ner = MedicalNER()
        self.relation_extractor = RelationExtractor()
        self.ontology = None
        if ontology_path:
            self.load_ontology(ontology_path)

    def load_ontology(self, path: str):
        """加载医学本体"""
        with open(path, 'r', encoding='utf-8') as f:
            self.ontology = json.load(f)
        logger.info(f"已加载本体: {path}")

    def extract_from_text(self, text: str) -> ExtractionResult:
        """从文本中抽取知识"""
        logger.info(f"开始抽取，文本长度: {len(text)}")
        entities = self.ner.recognize(text)
        relations = self.relation_extractor.extract(text, entities)
        result = ExtractionResult(
            entities=entities,
            relations=relations,
            source_text=text,
        )
        logger.info(f"抽取完成: {len(entities)} 个实体, {len(relations)} 条关系")
        return result

    def extract_from_file(self, file_path: str) -> ExtractionResult:
        """从文件中抽取知识"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        text = path.read_text(encoding='utf-8')
        return self.extract_from_text(text)

    def import_to_neo4j(self, result: ExtractionResult, neo4j_uri: str, neo4j_auth: Tuple[str, str]):
        """将抽取结果导入 Neo4j（需安装 neo4j 驱动）"""
        try:
            from neo4j import GraphDatabase
        except ImportError:
            logger.error("请安装 neo4j 驱动: pip install neo4j")
            return

        driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
        with driver.session() as session:
            for entity in result.entities:
                session.run(
                    f"MERGE (n:{entity.entity_type} {{name: $name}}) "
                    f"SET n += $attrs",
                    name=entity.name,
                    attrs=entity.attributes,
                )
            for rel in result.relations:
                session.run(
                    f"MATCH (a) WHERE a.name = $src_name "
                    f"MATCH (b) WHERE b.name = $tgt_name "
                    f"MERGE (a)-[r:{rel.relation_type}]->(b) "
                    f"SET r += $attrs",
                    src_name=next(e.name for e in result.entities if e.id == rel.source_id),
                    tgt_name=next(e.name for e in result.entities if e.id == rel.target_id),
                    attrs=rel.attributes,
                )
        driver.close()
        logger.info("Neo4j 导入完成")

    def export_to_json(self, result: ExtractionResult, output_path: str):
        """导出抽取结果为 JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"结果已导出至: {output_path}")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="医疗知识抽取工具")
    parser.add_argument("--input", "-i", help="输入文本文件路径")
    parser.add_argument("--text", "-t", help="直接输入文本")
    parser.add_argument("--ontology", "-o", help="本体文件路径")
    parser.add_argument("--output", help="输出 JSON 文件路径")
    parser.add_argument("--import", dest="import_file", help="导入 sample-kg.json 到图数据库")
    args = parser.parse_args()

    extractor = KnowledgeExtractor(ontology_path=args.ontology)

    if args.import_file:
        with open(args.import_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"已加载 {len(data.get('entities', []))} 个实体, {len(data.get('relations', []))} 条关系")
        print("提示: 配置 Neo4j 连接后可导入图数据库")
    elif args.input:
        result = extractor.extract_from_file(args.input)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif args.text:
        result = extractor.extract_from_text(args.text)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        # 默认演示
        demo_text = "2型糖尿病患者常表现为多饮、多尿、多食和体重下降。" \
                    "治疗首选二甲双胍，可联合恩格列净。" \
                    "需定期检查空腹血糖和糖化血红蛋白。"
        result = extractor.extract_from_text(demo_text)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
