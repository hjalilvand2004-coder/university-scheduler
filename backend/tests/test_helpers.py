# tests/test_helpers.py

def time_to_minutes(time_str):
    """تبدیل زمان رشته‌ای به دقیقه"""
    if not time_str:
        return 0
    parts = time_str.split(':')
    if len(parts) != 2:
        return 0
    return int(parts[0]) * 60 + int(parts[1])

def is_time_slot_within_preference(slot_start, slot_end, pref_start, pref_end, tolerance=60):
    """
    بررسی تطابق یک اسلات زمانی با بازه مطلوب با تساهل (دقیقه)
    """
    # نرمال‌سازی بازه ۱۲-۱۶ به ۱۳-۱۷ (مشابه بک‌اند)
    if pref_start == "12:00" and pref_end == "16:00":
        pref_start = "13:00"
        pref_end = "17:00"

    slot_s = time_to_minutes(slot_start)
    slot_e = time_to_minutes(slot_end)
    pref_s = time_to_minutes(pref_start)
    pref_e = time_to_minutes(pref_end)
    expanded_start = pref_s - tolerance
    expanded_end = pref_e + tolerance
    return slot_s >= expanded_start and slot_e <= expanded_end

# سایر توابع کمکی (همانند قبل)
def check_no_overlap(scheduled_classes):
    from collections import defaultdict
    groups = defaultdict(list)
    for cls in scheduled_classes:
        key = (cls.get('instructor_code'), cls.get('day'))
        groups[key].append(cls)
    conflicts = []
    for (inst, day), items in groups.items():
        sorted_items = sorted(items, key=lambda x: (x['start'], x['end']))
        for i in range(len(sorted_items)-1):
            a = sorted_items[i]
            b = sorted_items[i+1]
            if a['end'] > b['start']:
                conflicts.append((inst, day, a, b))
    return len(conflicts) == 0, conflicts

def check_teaching_preference_match(classes, teaching_prefs):
    pref_map = {}
    for p in teaching_prefs:
        pref_map.setdefault(p['unique_course_code'], []).append(p['instructor_code'])
    mismatches = []
    for cls in classes:
        course_code = cls.get('unique_code')
        instructor = cls.get('instructor_code')
        if course_code in pref_map and instructor not in pref_map[course_code]:
            mismatches.append(cls)
    return len(mismatches) == 0, mismatches

def check_time_preference_match(classes, time_prefs):
    mismatches = []
    for cls in classes:
        inst = cls.get('instructor_code')
        day = cls.get('day')
        start = cls.get('start')
        end = cls.get('end')
        prefs = [p for p in time_prefs if p['instructor_code'] == inst and p['day'] == day]
        if prefs:
            match = any(is_time_slot_within_preference(start, end, p['start_time'], p['end_time'], tolerance=60)
                        for p in prefs)
            if not match:
                mismatches.append(cls)
    return len(mismatches) == 0, mismatches

def check_max_units_respected(classes, instructors):
    max_units = {inst['code']: inst.get('max_teaching_units', 999) for inst in instructors}
    used_units = {}
    for cls in classes:
        inst = cls.get('instructor_code')
        units = cls.get('units', 0)
        used_units[inst] = used_units.get(inst, 0) + units
    violations = []
    for inst, used in used_units.items():
        if used > max_units.get(inst, 999):
            violations.append((inst, used, max_units.get(inst)))
    return len(violations) == 0, violations

def compute_quality_score(classes, teaching_prefs, time_prefs, instructors):
    total = len(classes)
    if total == 0:
        return 0.0
    teach_ok, _ = check_teaching_preference_match(classes, teaching_prefs)
    time_ok, _ = check_time_preference_match(classes, time_prefs)
    units_ok, _ = check_max_units_respected(classes, instructors)
    no_overlap, _ = check_no_overlap(classes)
    quality = ( (1.0 if teach_ok else 0.0) * 0.3 +
                (1.0 if time_ok else 0.0) * 0.4 +
                (1.0 if units_ok else 0.0) * 0.2 +
                (1.0 if no_overlap else 0.0) * 0.1 ) * 100
    return round(quality, 2)