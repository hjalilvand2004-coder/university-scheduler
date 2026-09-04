# app/services/schedule/step_logger.py

from datetime import datetime
from typing import List, Dict, Any, Optional

class StepLogger:
    """
    ثبت گام‌های فرایند زمان‌بندی برای گزارش‌گیری و عیب‌یابی.
    """

    def __init__(self) -> None:
        self.steps: List[Dict[str, Any]] = []
        self.current_step: int = 0

    def start_step(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        شروع یک گام جدید.

        Args:
            name: نام گام
            description: توضیح اختیاری

        Returns:
            دیکشنری اطلاعات گام ایجادشده
        """
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

    def complete_step(self, details: Dict[str, Any], status: str = "success") -> None:
        """
        پایان موفقیت‌آمیز یک گام.

        Args:
            details: اطلاعات تکمیلی
            status: وضعیت نهایی (پیش‌فرض success)
        """
        if self.steps:
            self.steps[-1]["status"] = status
            self.steps[-1]["details"] = details
            self.steps[-1]["timestamp_end"] = datetime.now().isoformat()

    def fail_step(self, error_message: str) -> None:
        """
        ثبت شکست یک گام.

        Args:
            error_message: پیام خطا
        """
        if self.steps:
            self.steps[-1]["status"] = "failed"
            self.steps[-1]["details"]["error"] = error_message
            self.steps[-1]["timestamp_end"] = datetime.now().isoformat()

    def get_result(self) -> List[Dict[str, Any]]:
        """
        بازگرداندن لیست تمام گام‌های ثبت‌شده.

        Returns:
            لیست دیکشنری‌های گام‌ها
        """
        return self.steps

    def reset(self) -> None:
        """پاک کردن تمام گام‌های ثبت‌شده (برای استفاده مجدد)."""
        self.steps = []
        self.current_step = 0