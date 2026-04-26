"""批处理模块 - Ponder Knowledge Platform"""

import uuid
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchTask:
    """批处理任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Optional[Callable] = None
    args: tuple = ()
    kwargs: Dict = field(default_factory=dict)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "status": self.status, "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class BatchJob:
    """批处理作业"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    tasks: List[BatchTask] = field(default_factory=list)
    status: str = "pending"
    total: int = 0
    completed: int = 0
    failed: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name,
            "status": self.status, "total": self.total,
            "completed": self.completed, "failed": self.failed,
            "progress": round(self.completed / max(self.total, 1) * 100, 1),
            "created_at": self.created_at
        }


class BatchProcessor:
    """批处理器"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.jobs: Dict[str, BatchJob] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()

    def create_job(self, name: str) -> BatchJob:
        job = BatchJob(name=name)
        self.jobs[job.id] = job
        return job

    def add_task(self, job_id: str, func: Callable,
                 args: tuple = (), kwargs: Optional[Dict] = None,
                 name: str = "") -> Optional[BatchTask]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        task = BatchTask(name=name or func.__name__, func=func,
                         args=args, kwargs=kwargs or {})
        job.tasks.append(task)
        job.total = len(job.tasks)
        return task

    def _execute_task(self, task: BatchTask) -> None:
        task.status = "running"
        task.started_at = datetime.now().isoformat()
        try:
            if task.func:
                task.result = task.func(*task.args, **task.kwargs)
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        task.completed_at = datetime.now().isoformat()

    def run_job(self, job_id: str) -> Optional[BatchJob]:
        """运行批处理作业"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        job.status = "running"

        futures: List[Future] = []
        for task in job.tasks:
            future = self._executor.submit(self._execute_task, task)
            futures.append(future)

        def on_complete():
            for future in futures:
                future.result()
            with self._lock:
                job.completed = len([t for t in job.tasks if t.status == "completed"])
                job.failed = len([t for t in job.tasks if t.status == "failed"])
                job.status = "completed" if job.failed == 0 else "completed_with_errors"

        thread = threading.Thread(target=on_complete)
        thread.start()
        return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        return self.jobs.get(job_id)

    def get_job_progress(self, job_id: str) -> Dict:
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        completed = len([t for t in job.tasks if t.status in ("completed", "failed")])
        return {
            "job_id": job_id, "total": job.total,
            "completed": completed, "failed": job.failed,
            "progress": round(completed / max(job.total, 1) * 100, 1),
            "status": job.status
        }

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job:
            return False
        for task in job.tasks:
            if task.status == "pending":
                task.status = "cancelled"
        job.status = "cancelled"
        return True

    def run_parallel(self, items: List[Any], func: Callable,
                     max_workers: Optional[int] = None) -> List[Any]:
        """并行执行"""
        workers = max_workers or self.max_workers
        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(func, item) for item in items]
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({"error": str(e)})
        return results

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    def get_statistics(self) -> Dict:
        return {
            "total_jobs": len(self.jobs),
            "max_workers": self.max_workers,
            "jobs": [j.to_dict() for j in self.jobs.values()]
        }
