# app/services/schedule/step_logger.py

from datetime import datetime
from typing import List, Dict

class StepLogger:
    def __init__(self):
        self.steps = []
        self.current_step = 0

    def start_step(self, name: str, description: str = ""):
        self.current_step += 1
        step = {
            "step": self.current_step,
            "name": name,
            "description": description,
            "status": "running",
            "details": {},
            "timestamp": datetime.now().isoformat()
        }
        self.steps.append(step)
        return step

    def complete_step(self, details: dict, status: str = "success"):
        if self.steps:
            self.steps[-1]["status"] = status
            self.steps[-1]["details"] = details
            self.steps[-1]["timestamp_end"] = datetime.now().isoformat()

    def fail_step(self, error_message: str):
        if self.steps:
            self.steps[-1]["status"] = "failed"
            self.steps[-1]["details"]["error"] = error_message

    def get_result(self):
        return self.steps