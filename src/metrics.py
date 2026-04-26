"""指标统计模块 - Ponder Knowledge Platform"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class Metric:
    """指标"""
    name: str = ""
    value: float = 0
    metric_type: str = "gauge"  # gauge, counter, histogram
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "value": self.value,
            "type": self.metric_type, "labels": self.labels,
            "timestamp": self.timestamp
        }


@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    timestamp: float = 0
    value: float = 0


class MetricsCollector:
    """指标收集器"""

    def __init__(self, retention_seconds: int = 3600):
        self.retention_seconds = retention_seconds
        self._metrics: Dict[str, Metric] = {}
        self._time_series: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def set_gauge(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None) -> Metric:
        """设置仪表盘指标"""
        metric = Metric(name=name, value=value, metric_type="gauge",
                        labels=labels or {})
        with self._lock:
            self._metrics[name] = metric
            self._time_series[name].append(
                TimeSeriesPoint(timestamp=time.time(), value=value)
            )
        return metric

    def increment_counter(self, name: str, value: float = 1,
                          labels: Optional[Dict[str, str]] = None) -> float:
        """递增计数器"""
        with self._lock:
            self._counters[name] += value
            current = self._counters[name]
            self._metrics[name] = Metric(
                name=name, value=current,
                metric_type="counter", labels=labels or {}
            )
            self._time_series[name].append(
                TimeSeriesPoint(timestamp=time.time(), value=current)
            )
        return current

    def record_histogram(self, name: str, value: float,
                         labels: Optional[Dict[str, str]] = None) -> Dict:
        """记录直方图"""
        with self._lock:
            self._histograms[name].append(value)
            values = self._histograms[name]
            stats = self._compute_histogram_stats(values)
            self._metrics[name] = Metric(
                name=name, value=stats.get("mean", 0),
                metric_type="histogram", labels=labels or {}
            )
        return stats

    def _compute_histogram_stats(self, values: List[float]) -> Dict:
        if not values:
            return {}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "sum": sum(values),
            "mean": sum(values) / n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "p50": sorted_vals[n // 2],
            "p90": sorted_vals[int(n * 0.9)],
            "p99": sorted_vals[int(n * 0.99)] if n >= 100 else sorted_vals[-1],
        }

    def get_metric(self, name: str) -> Optional[Metric]:
        return self._metrics.get(name)

    def get_time_series(self, name: str,
                        start: Optional[float] = None,
                        end: Optional[float] = None) -> List[Dict]:
        """获取时间序列"""
        points = self._time_series.get(name, [])
        if start:
            points = [p for p in points if p.timestamp >= start]
        if end:
            points = [p for p in points if p.timestamp <= end]
        return [{"timestamp": p.timestamp, "value": p.value} for p in points]

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0)

    def get_histogram_stats(self, name: str) -> Dict:
        values = self._histograms.get(name, [])
        return self._compute_histogram_stats(values)

    def cleanup(self) -> int:
        """清理过期数据"""
        cutoff = time.time() - self.retention_seconds
        cleaned = 0
        with self._lock:
            for name in list(self._time_series.keys()):
                before = len(self._time_series[name])
                self._time_series[name] = [
                    p for p in self._time_series[name]
                    if p.timestamp >= cutoff
                ]
                cleaned += before - len(self._time_series[name])
        return cleaned

    def get_all_metrics(self) -> List[Dict]:
        return [m.to_dict() for m in self._metrics.values()]

    def get_statistics(self) -> Dict:
        return {
            "total_metrics": len(self._metrics),
            "total_time_series_points": sum(len(v) for v in self._time_series.values()),
            "counters": dict(self._counters),
            "histograms": {
                name: self._compute_histogram_stats(values)
                for name, values in self._histograms.items()
            }
        }

    def reset(self) -> None:
        with self._lock:
            self._metrics.clear()
            self._time_series.clear()
            self._counters.clear()
            self._histograms.clear()

    def export_prometheus(self) -> str:
        """导出Prometheus格式"""
        lines = []
        for metric in self._metrics.values():
            labels_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
            label_part = f'{{{labels_str}}}' if labels_str else ""
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")
            lines.append(f"{metric.name}{label_part} {metric.value}")
        return "\n".join(lines)


# 全局指标收集器
metrics = MetricsCollector()
