"""数据验证模块 - Ponder Knowledge Platform"""

import re
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """验证结果"""
    level: str = "info"
    field: str = ""
    message: str = ""
    value: Any = None

    def to_dict(self) -> Dict:
        return {"level": self.level, "field": self.field, "message": self.message}


@dataclass
class ValidationReport:
    """验证报告"""
    valid: bool = True
    results: List[ValidationResult] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_error(self, field: str, message: str, value: Any = None):
        self.results.append(ValidationResult(level="error", field=field, message=message, value=value))
        self.valid = False

    def add_warning(self, field: str, message: str, value: Any = None):
        self.results.append(ValidationResult(level="warning", field=field, message=message, value=value))

    def add_info(self, field: str, message: str):
        self.results.append(ValidationResult(level="info", field=field, message=message))

    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "error_count": len([r for r in self.results if r.level == "error"]),
            "warning_count": len([r for r in self.results if r.level == "warning"]),
            "results": [r.to_dict() for r in self.results],
            "checked_at": self.checked_at
        }


class Validator:
    """数据验证器"""

    def __init__(self):
        self.custom_rules: Dict[str, List[Callable]] = {}

    def validate_entity(self, entity: Dict) -> ValidationReport:
        """验证实体"""
        report = ValidationReport()
        if not entity.get("name"):
            report.add_error("name", "Entity name is required")
        if not entity.get("id"):
            report.add_warning("id", "Entity ID is missing, will auto-generate")
        name = entity.get("name", "")
        if len(name) > 500:
            report.add_warning("name", f"Name is very long ({len(name)} chars)")
        if entity.get("type") and not isinstance(entity["type"], str):
            report.add_error("type", "Entity type must be a string")
        return report

    def validate_triple(self, triple: Dict) -> ValidationReport:
        """验证三元组"""
        report = ValidationReport()
        for field_name in ["subject", "predicate", "object"]:
            if not triple.get(field_name):
                report.add_error(field_name, f"Triple {field_name} is required")
        if triple.get("confidence") is not None:
            conf = triple["confidence"]
            if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
                report.add_error("confidence", "Confidence must be between 0 and 1")
        return report

    def validate_ontology_class(self, cls: Dict) -> ValidationReport:
        """验证本体类"""
        report = ValidationReport()
        if not cls.get("name"):
            report.add_error("name", "Class name is required")
        if cls.get("parent_classes"):
            if not isinstance(cls["parent_classes"], list):
                report.add_error("parent_classes", "Must be a list")
        return report

    def validate_relation(self, relation: Dict) -> ValidationReport:
        """验证关系"""
        report = ValidationReport()
        if not relation.get("name"):
            report.add_error("name", "Relation name is required")
        if not relation.get("domain"):
            report.add_warning("domain", "Domain is recommended")
        if not relation.get("range"):
            report.add_warning("range", "Range is recommended")
        return report

    def validate_batch(self, items: List[Dict],
                       validator_func: Callable) -> Dict:
        """批量验证"""
        results = []
        valid_count = 0
        invalid_count = 0
        for item in items:
            report = validator_func(item)
            results.append(report.to_dict())
            if report.valid:
                valid_count += 1
            else:
                invalid_count += 1
        return {
            "total": len(items),
            "valid": valid_count,
            "invalid": invalid_count,
            "results": results
        }

    def add_custom_rule(self, entity_type: str, rule: Callable) -> None:
        if entity_type not in self.custom_rules:
            self.custom_rules[entity_type] = []
        self.custom_rules[entity_type].append(rule)

    def validate_with_custom_rules(self, entity: Dict) -> ValidationReport:
        """使用自定义规则验证"""
        report = self.validate_entity(entity)
        entity_type = entity.get("type", "")
        for rule in self.custom_rules.get(entity_type, []):
            try:
                result = rule(entity)
                if isinstance(result, ValidationResult):
                    report.results.append(result)
                    if result.level == "error":
                        report.valid = False
            except Exception as e:
                report.add_warning("custom_rule", f"Rule execution failed: {e}")
        return report

    def validate_schema(self, data: Dict, schema: Dict) -> ValidationReport:
        """根据schema验证数据"""
        report = ValidationReport()
        required_fields = schema.get("required", [])
        field_types = schema.get("types", {})
        for field_name in required_fields:
            if field_name not in data:
                report.add_error(field_name, f"Required field '{field_name}' is missing")
        for field_name, expected_type in field_types.items():
            if field_name in data:
                value = data[field_name]
                if expected_type == "string" and not isinstance(value, str):
                    report.add_error(field_name, f"Expected string, got {type(value).__name__}")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    report.add_error(field_name, f"Expected number, got {type(value).__name__}")
                elif expected_type == "list" and not isinstance(value, list):
                    report.add_error(field_name, f"Expected list, got {type(value).__name__}")
                elif expected_type == "dict" and not isinstance(value, dict):
                    report.add_error(field_name, f"Expected dict, got {type(value).__name__}")
        return report
