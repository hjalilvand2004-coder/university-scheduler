# app/api/test_report.py
import json
import os
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test-report", tags=["test-report"])


class TestResult(BaseModel):
    nodeid: str
    outcome: str
    duration: Optional[float] = None
    call: Optional[dict] = None


class TestReportResponse(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    results: List[TestResult]


def run_tests():
    """اجرای تست‌ها و تولید فایل report.json"""
    try:
        # مسیر فعلی را به پوشه backend تنظیم کنید
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.chdir(backend_dir)

        # اجرای pytest با تولید گزارش JSON
        result = subprocess.run(
            ["pytest", "tests/", "--json-report", "--json-report-file=report.json"],
            capture_output=True,
            timeout=120,  # حداکثر ۲ دقیقه
            text=True
        )

        if result.returncode != 0:
            logger.error(f"خطا در اجرای تست‌ها: {result.stderr}")
            return False

        logger.info("✅ تست‌ها با موفقیت اجرا شدند.")
        return True

    except subprocess.TimeoutExpired:
        logger.error("❌ زمان اجرای تست‌ها به پایان رسید.")
        return False
    except Exception as e:
        logger.error(f"❌ خطا در اجرای تست‌ها: {e}")
        return False


def find_report_file():
    """پیدا کردن فایل report.json در مسیرهای مختلف"""
    possible_paths = [
        "report.json",
        "../report.json",
        "backend/report.json",
        os.path.join(os.path.dirname(__file__), "../../report.json"),
        os.path.join(os.path.dirname(__file__), "../report.json"),
        os.path.join(os.path.dirname(__file__), "report.json"),
    ]

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    possible_paths.append(os.path.join(base_dir, "report.json"))
    possible_paths.append(os.path.join(base_dir, "backend", "report.json"))

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


@router.get("/", response_model=TestReportResponse)
async def get_test_report():
    """دریافت گزارش تست - در صورت عدم وجود، تست‌ها را اجرا می‌کند"""
    # ۱. ابتدا بررسی کن که گزارش وجود دارد یا نه
    report_path = find_report_file()

    # ۲. اگر گزارش وجود نداشت، تست‌ها را اجرا کن
    if not report_path:
        logger.info("📊 گزارشی یافت نشد. در حال اجرای تست‌ها...")
        success = run_tests()
        if not success:
            raise HTTPException(
                status_code=500,
                detail="خطا در اجرای تست‌ها. لطفاً به لاگ‌ها مراجعه کنید."
            )
        # دوباره مسیر را پیدا کن
        report_path = find_report_file()
        if not report_path:
            raise HTTPException(
                status_code=404,
                detail="گزارش تست پس از اجرا ایجاد نشد. لطفاً به‌صورت دستی تست‌ها را اجرا کنید."
            )

    # ۳. خواندن فایل گزارش
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"خطا در خواندن گزارش: {str(e)}")

    # ۴. پردازش نتایج
    tests = data.get("tests", [])
    total = len(tests)
    passed = 0
    failed = 0
    skipped = 0
    errors = 0

    processed_tests = []
    for test in tests:
        outcome = test.get("outcome", "unknown")
        if outcome == "passed":
            passed += 1
        elif outcome == "failed":
            failed += 1
        elif outcome == "skipped":
            skipped += 1
        elif outcome == "error":
            errors += 1

        duration = test.get("duration")
        if duration is None:
            call = test.get("call")
            if call and isinstance(call, dict):
                duration = call.get("duration")
        if duration is None:
            duration = 0.0

        processed_tests.append({
            "nodeid": test.get("nodeid", ""),
            "outcome": outcome,
            "duration": duration,
            "call": test.get("call"),
        })

    total_duration = data.get("duration", 0.0)

    return TestReportResponse(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        duration=total_duration,
        results=processed_tests
    )