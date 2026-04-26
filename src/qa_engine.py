"""
知识问答引擎 (QA Engine)
基于知识图谱的医疗知识问答系统
"""

import json
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

@dataclass
class QAAnswer:
    """问答结果"""
    question: str
    answer: str
    confidence: float
    evidence: List[Dict] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)
    reasoning_path: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "entities_mentioned": self.entities_mentioned,
            "reasoning_path": self.reasoning_path,
        }

    def __str__(self) -> str:
        return f"Q: {self.question}\nA: {self.answer}\n(置信度: {self.confidence:.2f})"


# ============================================================
# 知识库
# ============================================================

class KnowledgeBase:
    """知识图谱加载与查询"""

    def __init__(self, kg_path: Optional[str] = None):
        self.entities: Dict[str, Dict] = {}
        self.relations: List[Dict] = []
        self.name_index: Dict[str, str] = {}  # name -> id
        self.type_index: Dict[str, List[str]] = {}  # type -> [ids]

        if kg_path:
            self.load(kg_path)

    def load(self, path: str):
        """加载知识图谱数据"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entity in data.get('entities', []):
            eid = entity['id']
            self.entities[eid] = entity
            self.name_index[entity['name']] = eid
            etype = entity.get('type', 'Unknown')
            self.type_index.setdefault(etype, []).append(eid)

        self.relations = data.get('relations', [])
        logger.info(f"知识库加载完成: {len(self.entities)} 实体, {len(self.relations)} 关系")

    def find_entity(self, name: str) -> Optional[Dict]:
        """按名称查找实体"""
        eid = self.name_index.get(name)
        return self.entities.get(eid) if eid else None

    def find_entity_by_id(self, eid: str) -> Optional[Dict]:
        """按ID查找实体"""
        return self.entities.get(eid)

    def get_related(self, entity_id: str, relation_type: Optional[str] = None) -> List[Dict]:
        """获取实体的关联实体"""
        results = []
        for rel in self.relations:
            if rel['source'] == entity_id:
                if relation_type is None or rel['type'] == relation_type:
                    target = self.entities.get(rel['target'])
                    if target:
                        results.append({'entity': target, 'relation': rel, 'direction': 'outgoing'})
            elif rel['target'] == entity_id:
                if relation_type is None or rel['type'] == relation_type:
                    source = self.entities.get(rel['source'])
                    if source:
                        results.append({'entity': source, 'relation': rel, 'direction': 'incoming'})
        return results

    def get_symptoms(self, disease_name: str) -> List[Dict]:
        entity = self.find_entity(disease_name)
        if not entity:
            return []
        return [r['entity'] for r in self.get_related(entity['id'], 'HAS_SYMPTOM') if r['direction'] == 'outgoing']

    def get_treatments(self, disease_name: str) -> List[Dict]:
        entity = self.find_entity(disease_name)
        if not entity:
            return []
        return [r['entity'] for r in self.get_related(entity['id'], 'TREATED_BY') if r['direction'] == 'outgoing']

    def get_diagnosis(self, disease_name: str) -> List[Dict]:
        entity = self.find_entity(disease_name)
        if not entity:
            return []
        return [r['entity'] for r in self.get_related(entity['id'], 'DIAGNOSED_BY') if r['direction'] == 'outgoing']

    def get_comorbidities(self, disease_name: str) -> List[Dict]:
        entity = self.find_entity(disease_name)
        if not entity:
            return []
        return [r['entity'] for r in self.get_related(entity['id'], 'COMORBID_WITH') if r['direction'] == 'outgoing']

    def search_by_type(self, entity_type: str) -> List[Dict]:
        ids = self.type_index.get(entity_type, [])
        return [self.entities[eid] for eid in ids]


# ============================================================
# 意图识别
# ============================================================

class IntentClassifier:
    """问题意图分类"""

    INTENT_PATTERNS = {
        "query_symptoms": [
            r"(.+?)的(症状|表现|临床表现)",
            r"(.+?)有什么(症状|表现)",
            r"得了(.+?)会怎样",
        ],
        "query_treatment": [
            r"(.+?)怎么(治疗|治|用药)",
            r"(.+?)用什么药",
            r"如何治疗(.+)",
            r"(.+?)的治疗方案",
        ],
        "query_diagnosis": [
            r"(.+?)怎么(诊断|检查|确诊)",
            r"如何(诊断|检查)(.+)",
            r"(.+?)需要做什么检查",
        ],
        "query_comorbidity": [
            r"(.+?)容易(合并|并发|伴发)什么",
            r"(.+?)和(.+?)有什么关系",
        ],
        "query_drug_info": [
            r"(.+?)的(作用|机制|适应症)",
            r"(.+?)是什么药",
        ],
        "query_disease_info": [
            r"什么是(.+)",
            r"(.+?)是什么病",
            r"介绍一下(.+)",
        ],
    }

    def classify(self, question: str) -> Tuple[str, List[str]]:
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, question)
                if match:
                    entities = [g for g in match.groups() if g and len(g) > 1]
                    return intent, entities
        return "unknown", []


# ============================================================
# 答案生成
# ============================================================

class AnswerGenerator:
    """基于知识图谱的答案生成"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def generate(self, question: str, intent: str, entity_names: List[str]) -> QAAnswer:
        generators = {
            "query_symptoms": self._answer_symptoms,
            "query_treatment": self._answer_treatment,
            "query_diagnosis": self._answer_diagnosis,
            "query_comorbidity": self._answer_comorbidity,
            "query_drug_info": self._answer_drug_info,
            "query_disease_info": self._answer_disease_info,
        }
        generator = generators.get(intent, self._answer_general)
        return generator(question, entity_names)

    def _answer_symptoms(self, question: str, entities: List[str]) -> QAAnswer:
        if not entities:
            return QAAnswer(question=question, answer="请指定疾病名称", confidence=0.1)
        disease = entities[0]
        symptoms = self.kb.get_symptoms(disease)
        if symptoms:
            answer = f"{disease}的常见症状包括：{'、'.join(s['name'] for s in symptoms)}。"
            evidence = [{"type": "知识图谱", "entity": s['name'], "relation": "HAS_SYMPTOM"} for s in symptoms]
        else:
            answer = f"暂未找到{disease}的相关症状信息。"
            evidence = []
        return QAAnswer(question=question, answer=answer, confidence=0.85 if symptoms else 0.3,
                        evidence=evidence, entities_mentioned=entities,
                        reasoning_path=[f"查询 {disease} 的 HAS_SYMPTOM 关系"])

    def _answer_treatment(self, question: str, entities: List[str]) -> QAAnswer:
        if not entities:
            return QAAnswer(question=question, answer="请指定疾病名称", confidence=0.1)
        disease = entities[0]
        drugs = self.kb.get_treatments(disease)
        if drugs:
            drug_info = []
            for d in drugs:
                info = d['name']
                if d.get('drug_class'):
                    info += f"（{d['drug_class']}）"
                drug_info.append(info)
            answer = f"{disease}的治疗药物包括：{'、'.join(drug_info)}。"
            evidence = [{"type": "知识图谱", "entity": d['name'], "relation": "TREATED_BY"} for d in drugs]
        else:
            answer = f"暂未找到{disease}的治疗方案信息。"
            evidence = []
        return QAAnswer(question=question, answer=answer, confidence=0.85 if drugs else 0.3,
                        evidence=evidence, entities_mentioned=entities,
                        reasoning_path=[f"查询 {disease} 的 TREATED_BY 关系"])

    def _answer_diagnosis(self, question: str, entities: List[str]) -> QAAnswer:
        if not entities:
            return QAAnswer(question=question, answer="请指定疾病名称", confidence=0.1)
        disease = entities[0]
        exams = self.kb.get_diagnosis(disease)
        if exams:
            answer = f"{disease}的诊断检查包括：{'、'.join(e['name'] for e in exams)}。"
            evidence = [{"type": "知识图谱", "entity": e['name'], "relation": "DIAGNOSED_BY"} for e in exams]
        else:
            answer = f"暂未找到{disease}的诊断检查信息。"
            evidence = []
        return QAAnswer(question=question, answer=answer, confidence=0.85 if exams else 0.3,
                        evidence=evidence, entities_mentioned=entities,
                        reasoning_path=[f"查询 {disease} 的 DIAGNOSED_BY 关系"])

    def _answer_comorbidity(self, question: str, entities: List[str]) -> QAAnswer:
        if not entities:
            return QAAnswer(question=question, answer="请指定疾病名称", confidence=0.1)
        disease = entities[0]
        comorbid = self.kb.get_comorbidities(disease)
        if comorbid:
            answer = f"{disease}常见的合并症包括：{'、'.join(c['name'] for c in comorbid)}。"
            evidence = [{"type": "知识图谱", "entity": c['name'], "relation": "COMORBID_WITH"} for c in comorbid]
        else:
            answer = f"暂未找到{disease}的合并症信息。"
            evidence = []
        return QAAnswer(question=question, answer=answer, confidence=0.8 if comorbid else 0.3,
                        evidence=evidence, entities_mentioned=entities,
                        reasoning_path=[f"查询 {disease} 的 COMORBID_WITH 关系"])

    def _answer_drug_info(self, question: str, entities: List[str]) -> QAAnswer:
        if not entities:
            return QAAnswer(question=question, answer="请指定药物名称", confidence=0.1)
        drug_name = entities[0]
        drug = self.kb.find_entity(drug_name)
        if drug and drug.get('type') == 'Drug':
            parts = [f"{drug['name']}"]
            if drug.get('generic_name'):
                parts.append(f"通用名：{drug['generic_name']}")
            if drug.get('drug_class'):
                parts.append(f"分类：{drug['drug_class']}")
            if drug.get('mechanism'):
                parts.append(f"作用机制：{drug['mechanism']}")
            return QAAnswer(question=question, answer="。".join(parts) + "。", confidence=0.9,
                            evidence=[{"type": "知识图谱", "entity": drug_name, "relation": "属性"}],
                            entities_mentioned=entities)
        return QAAnswer(question=question, answer=f"暂未找到{drug_name}的详细信息。", confidence=0.3)

    def _answer_disease_info(self, question: str, entities: List[str]) -> QAAnswer:
        if not entities:
            return QAAnswer(question=question, answer="请指定疾病名称", confidence=0.1)
        disease_name = entities[0]
        disease = self.kb.find_entity(disease_name)
        if disease and disease.get('type') == 'Disease':
            symptoms = self.kb.get_symptoms(disease_name)
            drugs = self.kb.get_treatments(disease_name)
            exams = self.kb.get_diagnosis(disease_name)
            parts = [f"**{disease_name}**"]
            if disease.get('description'):
                parts.append(disease['description'])
            if symptoms:
                parts.append(f"常见症状：{'、'.join(s['name'] for s in symptoms)}")
            if drugs:
                parts.append(f"治疗药物：{'、'.join(d['name'] for d in drugs)}")
            if exams:
                parts.append(f"诊断检查：{'、'.join(e['name'] for e in exams)}")
            return QAAnswer(question=question, answer="\n".join(parts), confidence=0.9,
                            entities_mentioned=entities, reasoning_path=["综合查询疾病属性及关联实体"])
        return QAAnswer(question=question, answer=f"暂未找到{disease_name}的信息。", confidence=0.3)

    def _answer_general(self, question: str, entities: List[str]) -> QAAnswer:
        found = [e for name in entities if (e := self.kb.find_entity(name))]
        if found:
            info_parts = []
            for e in found[:3]:
                desc = e.get('description', '')
                info_parts.append(f"{e['name']}（{e.get('type', '')}）：{desc}" if desc else e['name'])
            return QAAnswer(question=question, answer="\n".join(info_parts), confidence=0.6,
                            entities_mentioned=entities)
        return QAAnswer(question=question, answer="抱歉，暂未找到相关信息。请尝试更具体的问题。",
                        confidence=0.2, entities_mentioned=entities)


# ============================================================
# 问答引擎
# ============================================================

class QAEngine:
    """医疗知识问答引擎"""

    def __init__(self, kg_path: Optional[str] = None):
        self.kb = KnowledgeBase(kg_path)
        self.classifier = IntentClassifier()
        self.generator = AnswerGenerator(self.kb)

    def ask(self, question: str) -> QAAnswer:
        """回答问题"""
        logger.info(f"收到问题: {question}")
        intent, entities = self.classifier.classify(question)
        logger.info(f"意图: {intent}, 实体: {entities}")

        # 如果未识别到实体，尝试从问题中模糊匹配
        if not entities:
            for name in self.kb.name_index:
                if name in question:
                    entities.append(name)

        answer = self.generator.generate(question, intent, entities)
        logger.info(f"答案置信度: {answer.confidence:.2f}")
        return answer

    def batch_ask(self, questions: List[str]) -> List[QAAnswer]:
        """批量问答"""
        return [self.ask(q) for q in questions]


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="医疗知识问答引擎")
    parser.add_argument("--kg", help="知识图谱 JSON 文件路径", default="data/sample-kg.json")
    parser.add_argument("--question", "-q", help="要问的问题")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式问答模式")
    args = parser.parse_args()

    kg_path = args.kg
    if not Path(kg_path).exists():
        print(f"知识图谱文件不存在: {kg_path}")
        print("请确保 data/sample-kg.json 文件存在")
        exit(1)

    engine = QAEngine(kg_path)

    if args.question:
        answer = engine.ask(args.question)
        print(answer)
    elif args.interactive:
        print("医疗知识问答系统（输入 'quit' 退出）")
        print("-" * 50)
        while True:
            question = input("\n请输入问题: ").strip()
            if question.lower() in ('quit', 'exit', 'q'):
                break
            if not question:
                continue
            answer = engine.ask(question)
            print(f"\n{answer.answer}")
            print(f"[置信度: {answer.confidence:.2f}]")
    else:
        # 演示模式
        demo_questions = [
            "2型糖尿病有什么症状？",
            "如何治疗2型糖尿病？",
            "2型糖尿病需要做什么检查？",
            "恩格列净是什么药？",
            "什么是糖尿病肾病？",
        ]
        print("=" * 60)
        print("医疗知识问答系统 — 演示")
        print("=" * 60)
        for q in demo_questions:
            answer = engine.ask(q)
            print(f"\nQ: {answer.question}")
            print(f"A: {answer.answer}")
            print(f"[置信度: {answer.confidence:.2f}]")
