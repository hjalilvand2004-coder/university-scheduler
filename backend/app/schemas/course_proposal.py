from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime
import json


class CourseProposalCreate(BaseModel):
    term: str
    course_ids: List[int]
    description: Optional[str] = None


class CourseProposalResponse(BaseModel):
    id: int
    student_id: int
    term: str
    course_ids: List[int]
    description: Optional[str]
    status: str
    created_at: datetime

    # ===== پیکربندی برای تبدیل خودکار =====
    model_config = ConfigDict(from_attributes=True)

    @field_validator("course_ids", mode="before")
    @classmethod
    def parse_course_ids(cls, value):
        """تبدیل رشته JSON به لیست، در صورت لزوم"""
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        # در صورت عدم تطابق، یک لیست خالی برگردانید تا خطا ندهد
        return []