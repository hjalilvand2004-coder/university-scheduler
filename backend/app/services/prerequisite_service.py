from app.schemas.course import Course


def check_course_prerequisites(
    course: Course,
    passed_course_ids: set[int],
) -> dict:
    missing = [
        prerequisite_id
        for prerequisite_id in course.prerequisites
        if prerequisite_id not in passed_course_ids
    ]

    return {
        "valid": len(missing) == 0,
        "missing_prerequisites": missing,
    }


def check_course_corequisites(
    course: Course,
    selected_course_ids: set[int],
) -> dict:
    missing = [
        corequisite_id
        for corequisite_id in course.corequisites
        if corequisite_id not in selected_course_ids
    ]

    return {
        "valid": len(missing) == 0,
        "missing_corequisites": missing,
    }