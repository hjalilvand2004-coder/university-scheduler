import pytest
from app.services.schedule.time_scheduler import TimeScheduler
from tests.test_helpers import is_time_slot_within_preference

class TestTimeScheduler:

    def test_time_scheduler_no_overlap(self, assigned_courses, instructors_data, time_prefs):
        scheduler = TimeScheduler()
        # امضای assign_full_schedule: (self, courses, instructor_data, time_prefs)
        result = scheduler.assign_full_schedule(
            courses=assigned_courses,
            instructor_data=instructors_data,
            time_prefs=time_prefs
        )
        scheduled = result.get("scheduled", []) if isinstance(result, dict) else result
        assert scheduled is not None

        groups = {}
        for course in scheduled:
            key = (course["instructor_code"], course.get("day"))
            groups.setdefault(key, []).append(course)

        for (inst_code, day), items in groups.items():
            sorted_items = sorted(items, key=lambda x: (x["start"], x["end"]))
            for i in range(len(sorted_items)-1):
                a = sorted_items[i]
                b = sorted_items[i+1]
                assert a["end"] <= b["start"], f"تداخل برای استاد {inst_code} در روز {day}"

    def test_time_preference_match(self, assigned_courses, instructors_data, time_prefs):
        scheduler = TimeScheduler()
        result = scheduler.assign_full_schedule(
            courses=assigned_courses,
            instructor_data=instructors_data,
            time_prefs=time_prefs
        )
        scheduled = result.get("scheduled", []) if isinstance(result, dict) else result
        assert scheduled is not None

        mismatches = []
        for course in scheduled:
            inst = course["instructor_code"]
            day = course.get("day")
            start = course["start"]
            end = course["end"]
            prefs = [p for p in time_prefs if p["instructor_code"] == inst and p["day"] == day]
            if prefs:
                match = any(is_time_slot_within_preference(start, end, p["start_time"], p["end_time"], tolerance=60)
                            for p in prefs)
                if not match:
                    mismatches.append(course)

        max_ratio = 0.3
        ratio = len(mismatches) / len(scheduled) if scheduled else 0
        assert ratio <= max_ratio, f"{len(mismatches)} کلاس خارج از بازه مطلوب"

    def test_fallback_mechanism(self, assigned_courses, instructors_data, time_prefs):
        scheduler = TimeScheduler()
        result = scheduler.assign_full_schedule(
            courses=assigned_courses,
            instructor_data=instructors_data,
            time_prefs=time_prefs
        )
        scheduled = result.get("scheduled", []) if isinstance(result, dict) else result
        assert len(scheduled) == len(assigned_courses)

        for course in scheduled:
            assert course.get("day") is not None
            assert course.get("start") is not None
            assert course.get("end") is not None

    def test_max_units_respected_in_time_scheduling(self, assigned_courses, instructors_data, time_prefs):
        scheduler = TimeScheduler()
        result = scheduler.assign_full_schedule(
            courses=assigned_courses,
            instructor_data=instructors_data,
            time_prefs=time_prefs
        )
        scheduled = result.get("scheduled", []) if isinstance(result, dict) else result
        max_units = {inst["code"]: inst.get("max_teaching_units", 999) for inst in instructors_data}
        used_units = {}
        for course in scheduled:
            inst = course["instructor_code"]
            units = course.get("units", 0)
            used_units[inst] = used_units.get(inst, 0) + units

        for inst_code, used in used_units.items():
            assert used <= max_units.get(inst_code, 999), f"استاد {inst_code} از سقف واحد عبور کرده است."