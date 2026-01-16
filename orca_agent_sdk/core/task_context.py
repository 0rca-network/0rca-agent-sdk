from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import time

class TaskStatus(Enum):
    RECEIVED = "received"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaskContext:
    task_id: str
    sub_task_id: Optional[str] = None
    max_budget: float = 0.0
    status: TaskStatus = TaskStatus.RECEIVED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    def update_status(self, new_status: TaskStatus):
        self.status = new_status
