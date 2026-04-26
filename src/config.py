"""配置管理模块 - Ponder Knowledge Platform"""

import os
import json
import yaml
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConfigSection:
    """配置段"""
    name: str = ""
    values: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def to_dict(self) -> Dict:
        return dict(self.values)


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG = {
        "app": {
            "name": "Ponder Knowledge Platform",
            "version": "1.0.0",
            "debug": False,
            "host": "0.0.0.0",
            "port": 8000
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "ponder_knowledge",
            "pool_size": 10
        },
        "cache": {
            "enabled": True,
            "max_size": 10000,
            "default_ttl": 3600
        },
        "auth": {
            "token_expiry": 3600,
            "max_login_attempts": 5,
            "require_email_verification": False
        },
        "logging": {
            "level": "info",
            "max_entries": 10000,
            "file": "logs/ponder.log"
        },
        "knowledge_graph": {
            "max_entities": 1000000,
            "max_relations": 5000000,
            "auto_merge": True,
            "conflict_resolution": "highest_confidence"
        },
        "export": {
            "max_export_size": 100000,
            "allowed_formats": ["json", "csv", "turtle", "markdown"]
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        self._config: Dict[str, Any] = {}
        self._config_path = config_path
        self._load_defaults()
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)

    def _load_defaults(self):
        """加载默认配置"""
        self._config = json.loads(json.dumps(self.DEFAULT_CONFIG))

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号分隔）"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_section(self, section: str) -> ConfigSection:
        """获取配置段"""
        values = self._config.get(section, {})
        return ConfigSection(name=section, values=values)

    def load_from_file(self, path: str) -> None:
        """从文件加载配置"""
        path_obj = Path(path)
        with open(path_obj, 'r', encoding='utf-8') as f:
            if path_obj.suffix in ('.yaml', '.yml'):
                file_config = yaml.safe_load(f) or {}
            else:
                file_config = json.load(f)
        self._merge_config(self._config, file_config)

    def _merge_config(self, base: Dict, override: Dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def save_to_file(self, path: Optional[str] = None) -> None:
        """保存配置到文件"""
        save_path = path or self._config_path
        if not save_path:
            return
        path_obj = Path(save_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path_obj, 'w', encoding='utf-8') as f:
            if path_obj.suffix in ('.yaml', '.yml'):
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

    def load_from_env(self, prefix: str = "PONDER_") -> Dict[str, str]:
        """从环境变量加载配置"""
        loaded = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("__", ".")
                self.set(config_key, value)
                loaded[config_key] = value
        return loaded

    def get_all(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._config))

    def reset(self) -> None:
        self._load_defaults()

    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        port = self.get("app.port")
        if port and (not isinstance(port, int) or port < 1 or port > 65535):
            errors.append(f"Invalid port: {port}")
        pool_size = self.get("database.pool_size")
        if pool_size and (not isinstance(pool_size, int) or pool_size < 1):
            errors.append(f"Invalid pool_size: {pool_size}")
        cache_size = self.get("cache.max_size")
        if cache_size and (not isinstance(cache_size, int) or cache_size < 1):
            errors.append(f"Invalid cache max_size: {cache_size}")
        return errors

    def get_statistics(self) -> Dict:
        def count_keys(d):
            count = 0
            for v in d.values():
                if isinstance(v, dict):
                    count += count_keys(v)
                else:
                    count += 1
            return count
        return {
            "total_keys": count_keys(self._config),
            "sections": list(self._config.keys()),
            "config_path": self._config_path
        }


# 全局配置实例
config = ConfigManager()
