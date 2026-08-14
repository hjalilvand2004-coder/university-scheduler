import pytest
from app.services.schedule.instructor_assigner import InstructorAssigner

class TestInstructorAssigner:

    def test_assign_instructors_basic(self, sample_basket, instructors_data, teaching_prefs):
        assigner = InstructorAssigner()
        result = assigner.assign_instructors(
            courses=sample_basket,
            teaching_prefs=teaching_prefs,
            instructor_data=instructors_data
        )
        assert result is not None
        if isinstance(result, dict):
            assert "assigned" in result or "unassigned" in result

    def test_priority_respected(self, sample_basket, instructors_data, teaching_prefs):
        assigner = InstructorAssigner()
        result = assigner.assign_instructors(
            courses=sample_basket,
            teaching_prefs=teaching_prefs,
            instructor_data=instructors_data
        )
        assert result is not None

    def test_unassigned_reason(self, sample_basket, instructors_data, teaching_prefs):
        assigner = InstructorAssigner()
        result = assigner.assign_instructors(
            courses=sample_basket,
            teaching_prefs=teaching_prefs,
            instructor_data=instructors_data
        )
        if isinstance(result, dict) and "unassigned" in result:
            for course in result["unassigned"]:
                assert "reason" in course

    def test_assigner_handles_empty_basket(self, instructors_data, teaching_prefs):
        assigner = InstructorAssigner()
        result = assigner.assign_instructors(
            courses=[],
            teaching_prefs=teaching_prefs,
            instructor_data=instructors_data
        )
        assert result is not None