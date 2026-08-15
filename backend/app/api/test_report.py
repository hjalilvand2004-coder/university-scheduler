# app/api/test_report.py
import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/test-report", tags=["test-report"])


class TestResult(BaseModel):
    nodeid: str
    outcome: str
    duration: float
    call: Optional[dict] = None


class TestReportResponse(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    results: List[TestResult]
    coverage: Optional[dict] = None


def load_test_report():
    """بارگذاری فایل report.json تولید شده توسط pytest-json-report"""
    report_path = "report.json"  # مسیر فایل گزارش
    if not os.path.exists(report_path):
        return None

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def load_coverage_report():
    """بارگذاری فایل coverage.xml و استخراج اطلاعات پوشش کد"""
    # می‌توانید از کتابخانه‌های parsing XML استفاده کنید
    # یا اطلاعات را از coverage.json بخوانید
    pass


@router.get("/", response_model=TestReportResponse)
async def get_test_report():
    report = load_test_report()
    if not report:
        raise HTTPException(status_code=404, detail="گزارش تست یافت نشد")

    # استخراج آمار
    total = len(report.get("tests", []))
    passed = sum(1 for t in report["tests"] if t["outcome"] == "passed")
    failed = sum(1 for t in report["tests"] if t["outcome"] == "failed")
    skipped = sum(1 for t in report["tests"] if t["outcome"] == "skipped")
    errors = sum(1 for t in report["tests"] if t["outcome"] == "error")
    duration = report.get("duration", 0)

    return TestReportResponse(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        duration=duration,
        results=report["tests"]
    )