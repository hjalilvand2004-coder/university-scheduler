import pytest
from tests.test_helpers import (
    check_no_overlap,
    check_teaching_preference_match,
    check_time_preference_match,
    check_max_units_respected,
    compute_quality_score
)

class TestScheduleQuality:

    def test_orchestrator_runs_without_error(self, orchestrator, sample_basket):
        result = orchestrator.process(basket=sample_basket)
        assert result is not None
        assert "assigned" in result or "unassigned" in result

    def test_no_overlap_constraint(self, orchestrator, sample_basket):
        result = orchestrator.process(basket=sample_basket)
        assigned = result.get("assigned", [])
        ok, conflicts = check_no_overlap(assigned)
        assert ok, f"تداخل‌های یافت‌شده: {conflicts}"

    def test_teaching_preference_match(self, orchestrator, sample_basket, teaching_prefs):
        result = orchestrator.process(basket=sample_basket)
        assigned = result.get("assigned", [])
        ok, mismatches = check_teaching_preference_match(assigned, teaching_prefs)
        max_mismatch_ratio = 0.2
        mismatch_ratio = len(mismatches) / len(assigned) if assigned else 0
        assert mismatch_ratio <= max_mismatch_ratio

    def test_time_preference_match(self, orchestrator, sample_basket, time_prefs):
        result = orchestrator.process(basket=sample_basket)
        assigned = result.get("assigned", [])
        ok, mismatches = check_time_preference_match(assigned, time_prefs)
        max_mismatch_ratio = 0.3
        mismatch_ratio = len(mismatches) / len(assigned) if assigned else 0
        assert mismatch_ratio <= max_mismatch_ratio

    def test_max_units_respected(self, orchestrator, sample_basket, instructors_data):
        result = orchestrator.process(basket=sample_basket)
        assigned = result.get("assigned", [])
        ok, violations = check_max_units_respected(assigned, instructors_data)
        assert ok, f"اساتید زیر از سقف واحد عبور کرده‌اند: {violations}"

    def test_quality_score_threshold(self, orchestrator, sample_basket, teaching_prefs, time_prefs, instructors_data):
        result = orchestrator.process(basket=sample_basket)
        assigned = result.get("assigned", [])
        quality = compute_quality_score(assigned, teaching_prefs, time_prefs, instructors_data)
        assert quality >= 70, f"امتیاز کیفیت {quality}% کمتر از حد مجاز است."

    def test_unassigned_courses_reasons(self, orchestrator, sample_basket):
        result = orchestrator.process(basket=sample_basket)
        unassigned = result.get("unassigned", [])
        for course in unassigned:
            assert "reason" in course
            assert course["reason"] != ""

    def test_balanced_distribution(self, orchestrator, sample_basket):
        result = orchestrator.process(basket=sample_basket)
        assigned = result.get("assigned", [])
        instructor_52 = [c for c in assigned if c.get('instructor_code') == '52']
        if instructor_52:
            days = set(c.get('day') for c in instructor_52 if c.get('day') is not None)
            assert len(days) >= 2, "توزیع روزها برای استاد ۵۲ متوازن نیست"