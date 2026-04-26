"""日志服务模块 - Ponder Knowledge Platform"""

import json
import uuid
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """日志条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: str = "info"
    message: str = ""
    module: str = ""
    function: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "level": self.level,
            "message": self.message, "module": self.module,
            "function": self.function, "details": self.details,
            "timestamp": self.timestamp
        }


class LoggingService:
    """日志服务"""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._entries: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._handlers: Dict[str, List[callable]] = {}
        self._logger = logging.getLogger("ponder_knowledge")

    def log(self, level: str, message: str, module: str = "",
            function: str = "", **details) -> LogEntry:
        """记录日志"""
        entry = LogEntry(
            level=level, message=message,
            module=module, function=function,
            details=details
        )
        with self._lock:
            self._entries.append(entry)
        # 触发处理器
        for handler in self._handlers.get(level, []):
            try:
                handler(entry)
            except Exception:
                pass
        for handler in self._handlers.get("*", []):
            try:
                handler(entry)
            except Exception:
                pass
        return entry

    def debug(self, message: str, **kwargs) -> LogEntry:
        return self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs) -> LogEntry:
        return self.log("info", message, **kwargs)

    def warning(self, message: str, **kwargs) -> LogEntry:
        return self.log("warning", message, **kwargs)

    def error(self, message: str, **kwargs) -> LogEntry:
        return self.log("error", message, **kwargs)

    def critical(self, message: str, **kwargs) -> LogEntry:
        return self.log("critical", message, **kwargs)

    def add_handler(self, level: str, handler: callable) -> None:
        if level not in self._handlers:
            self._handlers[level] = []
        self._handlers[level].append(handler)

    def get_logs(self, level: Optional[str] = None,
                 module: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0) -> List[LogEntry]:
        """获取日志"""
        entries = list(self._entries)
        if level:
            entries = [e for e in entries if e.level == level]
        if module:
            entries = [e for e in entries if e.module == module]
        entries.reverse()
        return entries[offset:offset + limit]

    def search_logs(self, query: str, limit: int = 50) -> List[LogEntry]:
        """搜索日志"""
        query_lower = query.lower()
        results = []
        for entry in reversed(self._entries):
            if query_lower in entry.message.lower() or query_lower in json.dumps(entry.details).lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        return results

    def get_logs_by_time_range(self, start: str, end: str) -> List[LogEntry]:
        """按时间范围获取日志"""
        return [e for e in self._entries if start <= e.timestamp <= end]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def get_statistics(self) -> Dict:
        entries = list(self._entries)
        level_counts = {}
        module_counts = {}
        for e in entries:
            level_counts[e.level] = level_counts.get(e.level, 0) + 1
            if e.module:
                module_counts[e.module] = module_counts.get(e.module, 0) + 1
        return {
            "total_entries": len(entries),
            "by_level": level_counts,
            "by_module": module_counts,
            "oldest": entries[0].timestamp if entries else None,
            "newest": entries[-1].timestamp if entries else None,
        }

    def export_logs(self, format: str = "json") -> str:
        entries = [e.to_dict() for e in self._entries]
        if format == "json":
            return json.dumps(entries, indent=2, ensure_ascii=False)
        elif format == "text":
            lines = []
            for e in entries:
                lines.append(f"[{e['timestamp']}] [{e['level'].upper()}] {e['module']}:{e['function']} - {e['message']}")
            return "\n".join(lines)
        return json.dumps(entries)

    def create_operation_logger(self, operation: str):
        """创建操作日志上下文管理器"""
        service = self
        class OperationLogger:
            def __enter__(self):
                service.info(f"Starting operation: {operation}")
                self.start_time = datetime.now()
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = (datetime.now() - self.start_time).total_seconds()
                if exc_type:
                    service.error(f"Operation failed: {operation}", error=str(exc_val), duration=duration)
                else:
                    service.info(f"Operation completed: {operation}", duration=duration)
                return False
        return OperationLogger()


# 全局日志服务实例
logging_service = LoggingService()
