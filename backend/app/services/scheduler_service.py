from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import logging
import traceback
from collections import defaultdict

from app.models import (
    OfferedCourse,
    Instructor as InstructorModel,
    Room as RoomModel,
    ScheduledClass,
    TimePreference,
    TeachingPreference,
    ScheduleHistory
)
from app.models.term_course import TermCourse
from app.optimization.cp_sat_solver import solve_schedule
from app.services.course_selector import CourseSelector
from app.services.demand_service import predict_demand
from app.services.explanation_service import explain_scheduled_class
from app.services.scoring_service import Semester
from app.schemas.course import Course, Instructor, Room, TimeSlot, CourseType

logger = logging.getLogger(__name__)


def _serialize_course_info(course_info: Dict[str, Any], keep_score: bool = True) -> Dict[str, Any]:
    result = {}
    for key, value in course_info.items():
        if key == "offered_course":
            if value:
                result["offered_course_id"] = value.id
                result["offered_course_code"] = value.unique_code
                result["offered_course_title"] = value.offered_title
            else:
                result["offered_course_id"] = None
        elif key == "instructors" and isinstance(value, list):
            result[key] = [{"name": inst.get("name")} if isinstance(inst, dict) else {"name": str(inst)} for inst in
                           value]
        elif key == "score" and not keep_score:
            continue
        elif key == "reasons" and not keep_score:
            continue
        else:
            result[key] = value
    return result


def generate_schedule_from_db(
        db: Session,
        semester: str,
        levels: Optional[List[str]] = None,
        year: str = "1403",
        max_groups_per_course: int = 1,  # ← کاهش به ۱ (قبلاً ۲ بود)
        demand_threshold: int = 15,  # ← افزایش آستانه
        number_of_scenarios: int = 3,
        max_courses: int = 60  # ← کاهش به ۶۰ (قبلاً ۱۲۰ بود)
) -> Dict[str, Any]:
    try:
        logger.info(f"شروع تولید برنامه - نیمسال: {semester}, مقاطع: {levels}, max_courses: {max_courses}")

        semester_enum = Semester.MEHR if semester == "mehr" else Semester.BAHMAN

        selector = CourseSelector(db)
        selected_courses, rejected_courses = selector.select_courses(
            semester=semester_enum,
            levels=levels,
            demand_threshold=demand_threshold,
            max_courses=max_courses
        )

        logger.info(f"تعداد دروس انتخاب‌شده: {len(selected_courses)}, ردشده: {len(rejected_courses)}")

        if not selected_courses:
            return {
                "status": "no_courses",
                "message": "هیچ درسی برای این نیمسال و مقاطع انتخابی یافت نشد",
                "classes": [],
                "rejected_courses": [],
                "selected_courses": [],
                "ranked_courses": []
            }

        # ===== ساخت ranked_courses =====
        ranked_courses = sorted(
            [{
                "course_code": sc.get("unique_course_code") or sc.get("code", ""),
                "course_name": sc.get("course_name") or sc.get("title", ""),
                "score": sc.get("score", 0),
                "reasons": sc.get("reasons", []),
                "course_id": sc.get("term_course_id") or sc.get("id", 0)
            } for sc in selected_courses if sc.get("score") is not None],
            key=lambda x: x["score"],
            reverse=True
        )

        # ===== 2. تبدیل داده‌ها به اشیاء Pydantic =====
        logger.info("تبدیل داده‌ها به اشیاء Pydantic...")
        courses = []
        course_id_by_unique_code = {}
        all_course_ids = []
        course_unique_codes = []

        for idx, sc in enumerate(selected_courses):
            try:
                offered = sc.get("offered_course")
                course_type_str = "theory"
                if offered and offered.course_type:
                    course_type_str = offered.course_type
                elif sc.get("course_type"):
                    course_type_str = sc["course_type"]

                level = sc.get("level", "نامشخص")
                term = sc.get("term", "نامشخص")
                cohort = f"{level}-{term}"

                try:
                    course_type_enum = CourseType(course_type_str.lower())
                except (ValueError, AttributeError):
                    course_type_enum = CourseType.THEORY
                    logger.warning(
                        f"نوع درس نامعتبر '{course_type_str}' برای درس {sc.get('course_name', '')} - استفاده از THEORY")

                avg_capacity = sc.get("avg_capacity", 0) or 0
                historical_count = sc.get("historical_count", 0) or 0
                historical_demand = avg_capacity or (historical_count * 10)

                course_id = sc["term_course_id"] if not offered else offered.id
                unique_code = offered.unique_code if offered else sc.get("unique_course_code", "")

                # استخراج تعداد واحد از dictionary (اگر موجود باشد)
                units = sc.get("units", 2)  # پیش‌فرض ۲ واحد

                course_obj = Course(
                    id=course_id,
                    code=unique_code,
                    title=offered.offered_title if offered else sc["course_name"],
                    chart_term=sc.get("approximate_term", 1),
                    course_type=course_type_enum,
                    cohorts=[cohort] if cohort else [],
                    prerequisites=[],
                    corequisites=[],
                    active=True,
                    graduation_critical=sc.get("is_bottleneck", False),
                    bottleneck=sc.get("is_bottleneck", False),
                    historical_demand=historical_demand,
                    direct_requests=0,
                    chart_required=True,
                    preferred_days=[],
                    preferred_slots=[],
                    units=units,  # ← اضافه کردن units به مدل Course
                )
                courses.append(course_obj)
                if unique_code:
                    course_id_by_unique_code[unique_code] = course_id
                    course_unique_codes.append(unique_code)
                all_course_ids.append(course_id)
            except Exception as e:
                logger.error(f"خطا در تبدیل درس {idx}: {sc.get('course_name', 'نامشخص')} - {e}")
                logger.error(traceback.format_exc())
                raise

        logger.info(f"تعداد دروس تبدیل‌شده: {len(courses)}")

        # ===== 2.2 استخراج اساتید واجد شرایط از سوابق =====
        history_instructors = defaultdict(set)
        if course_unique_codes:
            history_records = db.query(ScheduleHistory).filter(
                ScheduleHistory.ref_unique_course_code.in_(course_unique_codes)
            ).all()
            for record in history_records:
                if record.ref_unique_course_code and record.instructor_code:
                    history_instructors[record.ref_unique_course_code].add(record.instructor_code)

        # ===== 2.3 ساخت لیست اساتید =====
        logger.info("دریافت اساتید از دیتابیس...")
        instructors_db = db.query(InstructorModel).all()

        instructor_code_to_id = {inst.code: inst.id for inst in instructors_db}
        instructor_courses = defaultdict(set)

        # از TeachingPreference
        teaching_prefs = db.query(TeachingPreference).all()
        for tp in teaching_prefs:
            if tp.unique_course_code and tp.instructor_code:
                course_id = course_id_by_unique_code.get(tp.unique_course_code)
                instructor_id = instructor_code_to_id.get(tp.instructor_code)
                if course_id and instructor_id:
                    instructor_courses[instructor_id].add(course_id)

        # از ScheduleHistory
        for unique_code, instructor_codes in history_instructors.items():
            course_id = course_id_by_unique_code.get(unique_code)
            if not course_id:
                continue
            for instructor_code in instructor_codes:
                instructor_id = instructor_code_to_id.get(instructor_code)
                if instructor_id:
                    instructor_courses[instructor_id].add(course_id)

        # ساخت اساتید واقعی
        instructors = []
        for inst in instructors_db:
            if inst.id not in instructor_courses:
                continue
            qualified_course_ids = list(instructor_courses[inst.id])

            time_prefs = db.query(TimePreference).filter(
                TimePreference.instructor_code == inst.code
            ).all()
            preferred_days = []
            preferred_slots = []
            for tp in time_prefs:
                day_map = {"شنبه": 0, "یکشنبه": 1, "دوشنبه": 2, "سه‌شنبه": 3, "چهارشنبه": 4, "پنجشنبه": 5}
                if tp.day in day_map:
                    preferred_days.append(day_map[tp.day])
                time_to_slot = {"08:00": 1, "10:00": 2, "13:00": 3, "15:00": 4}
                if tp.start_time in time_to_slot:
                    preferred_slots.append(time_to_slot[tp.start_time])

            instructor_obj = Instructor(
                id=inst.id,
                name=inst.name,
                qualified_course_ids=qualified_course_ids,
                preferred_days=preferred_days,
                preferred_slots=preferred_slots,
            )
            instructors.append(instructor_obj)

        # ===== 2.4 استاد مجازی برای دروس بدون استاد =====
        courses_without_instructor = set(all_course_ids)
        for instructor in instructors:
            for cid in instructor.qualified_course_ids:
                courses_without_instructor.discard(cid)

        if courses_without_instructor:
            logger.info(f"تعداد دروس بدون استاد: {len(courses_without_instructor)}")
            virtual_instructor = Instructor(
                id=0,
                name="بدون استاد",
                qualified_course_ids=list(courses_without_instructor),
                preferred_days=[],
                preferred_slots=[],
            )
            instructors.append(virtual_instructor)
            logger.info("استاد مجازی با id=0 برای دروس بدون استاد اضافه شد.")

        logger.info(f"تعداد اساتید نهایی: {len(instructors)} (شامل استاد مجازی)")

        # ===== 2.5 اتاق‌ها =====
        logger.info("دریافت اتاق‌ها از دیتابیس...")
        rooms_db = db.query(RoomModel).all()
        rooms = []
        for room in rooms_db:
            try:
                room_types_list = []
                if room.room_types:
                    for rt in room.room_types:
                        try:
                            room_types_list.append(CourseType(rt.lower()))
                        except ValueError:
                            pass
                if not room_types_list:
                    room_types_list = [CourseType.THEORY, CourseType.PRACTICAL, CourseType.LAB]

                room_obj = Room(
                    id=room.id,
                    name=room.name,
                    capacity=room.capacity,
                    room_types=room_types_list,
                )
                rooms.append(room_obj)
            except Exception as e:
                logger.error(f"خطا در تبدیل اتاق {room.name}: {e}")
                raise

        logger.info(f"تعداد اتاق‌ها: {len(rooms)}")

        # ===== 2.6 زمان‌ها (بر اساس فرمول جدید) =====
        logger.info("ایجاد زمان‌ها بر اساس واحد درس...")
        slots = []
        slot_id = 1
        days = [0, 1, 2, 3, 4, 5]  # شنبه تا پنجشنبه

        # شیفت‌های استاندارد برای دروس ۲ واحدی
        two_unit_slots = [
            ("07:30", "09:15"),
            ("09:16", "11:00"),
            ("11:01", "12:45"),
            ("13:00", "14:45"),
            ("14:46", "16:30"),
            ("16:31", "18:15"),
            ("18:16", "20:00"),
        ]

        # شیفت‌های استاندارد برای دروس ۳ واحدی
        three_unit_slots = [
            ("07:30", "10:10"),
            ("10:11", "12:50"),
            ("13:00", "15:30"),
            ("15:31", "18:00"),
            ("18:01", "20:30"),
        ]

        # برای هر روز، تمام شیفت‌ها را اضافه می‌کنیم
        for day in days:
            # ابتدا شیفت‌های ۲ واحدی
            for start, end in two_unit_slots:
                slot_obj = TimeSlot(
                    id=slot_id,
                    day=day,
                    start=start,
                    end=end,
                    slot_type="2_unit"  # اضافه کردن نوع شیفت
                )
                slots.append(slot_obj)
                slot_id += 1

            # سپس شیفت‌های ۳ واحدی
            for start, end in three_unit_slots:
                slot_obj = TimeSlot(
                    id=slot_id,
                    day=day,
                    start=start,
                    end=end,
                    slot_type="3_unit"  # اضافه کردن نوع شیفت
                )
                slots.append(slot_obj)
                slot_id += 1

        logger.info(
            f"تعداد زمان‌ها: {len(slots)} (شامل {len(two_unit_slots) * len(days)} شیفت ۲ واحدی و {len(three_unit_slots) * len(days)} شیفت ۳ واحدی)")

        # ===== 3. اجرای حل‌کننده =====
        logger.info("اجرای حل‌کننده OR-Tools...")
        try:
            solution = solve_schedule(
                courses=courses,
                instructors=instructors,
                rooms=rooms,
                slots=slots,
                max_groups_per_course=max_groups_per_course,
            )
            logger.info(f"وضعیت حل: {solution.get('status')}")
            logger.info(f"تعداد کلاس‌های تولیدشده: {len(solution.get('classes', []))}")
            unschedulable = solution.get('unschedulable_courses', [])
            if unschedulable:
                logger.warning(f"دروس غیرقابل زمان‌بندی: {len(unschedulable)}")
                for uc in unschedulable:
                    logger.warning(f"  {uc.get('course_title')} - {uc.get('reason')}")
                    if 'predicted_students' in uc:
                        logger.warning(f"    دانشجویان پیش‌بینی‌شده: {uc['predicted_students']}")
                    if 'number_of_groups' in uc:
                        logger.warning(f"    تعداد گروه‌های لازم: {uc['number_of_groups']}")
        except Exception as e:
            logger.error(f"خطا در اجرای حل‌کننده: {e}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"خطا در اجرای حل‌کننده: {str(e)}",
                "classes": [],
                "rejected_courses": [],
                "selected_courses": [],
                "ranked_courses": [],
                "explanations": [f"خطا: {str(e)}"],
                "alternative_scenarios": [],
                "quality_metrics": {}
            }

        # ===== 4. ذخیره‌سازی =====
        logger.info("ذخیره‌سازی برنامه در دیتابیس...")
        saved_classes = []
        try:
            for idx, item in enumerate(solution.get("classes", [])):
                try:
                    course_id = None
                    for sc in selected_courses:
                        offered = sc.get("offered_course")
                        if offered and offered.id == item.get("course_id"):
                            course_id = offered.id
                            break
                        elif sc["term_course_id"] == item.get("course_id"):
                            course_id = sc["term_course_id"]
                            break

                    cohort_list = item.get("cohorts", [])
                    if not cohort_list:
                        level = "نامشخص"
                        term = "نامشخص"
                        for sc in selected_courses:
                            if sc["term_course_id"] == item.get("course_id") or (
                                    sc.get("offered_course") and sc["offered_course"].id == item.get("course_id")
                            ):
                                level = sc.get("level", "نامشخص")
                                term = sc.get("term", "نامشخص")
                                break
                        cohort_list = [f"{level}-{term}"] if level and term else []

                    # ===== محاسبه زمان پایان بر اساس واحد درس =====
                    units = 2  # پیش‌فرض
                    # پیدا کردن واحد درس از selected_courses
                    for sc in selected_courses:
                        if sc["term_course_id"] == item.get("course_id") or (
                                sc.get("offered_course") and sc["offered_course"].id == item.get("course_id")
                        ):
                            units = sc.get("units", 2)
                            break

                    start_time = item.get("start", "")
                    end_time = item.get("end", "")

                    # اگر زمان پایان موجود نباشد، بر اساس واحد محاسبه می‌کنیم
                    if not end_time and start_time:
                        from datetime import datetime, timedelta
                        try:
                            start_dt = datetime.strptime(start_time, "%H:%M")
                            if units == 2:
                                duration = timedelta(minutes=105)  # 1:45
                            else:
                                # برای ۳ واحدی: اگر قبل از ۱۳ باشد ۱۶۰ دقیقه، وگرنه ۱۵۰ دقیقه
                                if start_dt < datetime.strptime("13:00", "%H:%M"):
                                    duration = timedelta(minutes=160)  # 2:40
                                else:
                                    duration = timedelta(minutes=150)  # 2:30
                            end_dt = start_dt + duration
                            end_time = end_dt.strftime("%H:%M")
                        except:
                            end_time = item.get("end", "")

                    scheduled_class = ScheduledClass(
                        course_id=course_id or 0,
                        course_code=item.get("course_code", ""),
                        course_title=item.get("course_title", ""),
                        group_number=item.get("group_number", 1),
                        instructor_id=item.get("instructor_id"),
                        instructor_name=item.get("instructor_name", ""),
                        room_id=item.get("room_id"),
                        room_name=item.get("room_name", ""),
                        room_capacity=item.get("room_capacity", 0),
                        slot_id=item.get("slot_id", 0),
                        day=item.get("day", 0),
                        start_time=start_time,
                        end_time=end_time,
                        predicted_students=item.get("predicted_students", 0),
                        students_per_group=item.get("students_per_group", 0),
                        course_type=item.get("course_type", "theory"),
                        cohorts=json.dumps(cohort_list),
                        semester=semester,
                        year=year,
                        term_code=f"{year}_{semester}",
                        score=solution.get("objective_value", 0),
                        explanation=json.dumps(item.get("explanation", [])),
                        scenario_id=1
                    )
                    db.add(scheduled_class)
                    saved_classes.append(scheduled_class)
                except Exception as e:
                    logger.error(f"خطا در ذخیره کلاس {idx}: {e}")
                    logger.error(traceback.format_exc())
                    raise

            db.commit()
            logger.info(f"تعداد کلاس‌های ذخیره‌شده: {len(saved_classes)}")
        except Exception as e:
            logger.error(f"خطا در ذخیره‌سازی دیتابیس: {e}")
            logger.error(traceback.format_exc())
            db.rollback()
            return {
                "status": "error",
                "message": f"خطا در ذخیره‌سازی: {str(e)}",
                "classes": [],
                "rejected_courses": [],
                "selected_courses": [],
                "ranked_courses": [],
                "explanations": [f"خطا: {str(e)}"],
                "alternative_scenarios": [],
                "quality_metrics": {}
            }

        # ===== 5. سناریوهای جایگزین =====
        logger.info("تولید سناریوهای جایگزین...")
        alternative_scenarios = []
        try:
            if solution.get('status') != 'infeasible':
                alternative_scenarios = generate_alternative_scenarios(
                    db=db,
                    courses=courses,
                    instructors=instructors,
                    rooms=rooms,
                    slots=slots,
                    selected_courses=selected_courses,
                    semester=semester,
                    year=year,
                    max_groups_per_course=max_groups_per_course
                )
            else:
                logger.info("به دلیل infeasible بودن برنامه اصلی، سناریوهای جایگزین تولید نشدند.")
        except Exception as e:
            logger.warning(f"خطا در تولید سناریوهای جایگزین (غیر بحرانی): {e}")

        # ===== 6. خروجی =====
        term_info = {}
        for sc in selected_courses:
            level = sc.get("level", "نامشخص")
            term = sc.get("term", "نامشخص")
            key = f"{level} - {term}"
            term_info[key] = term_info.get(key, 0) + 1
        term_summary = ", ".join([f"{k}: {v} درس" for k, v in term_info.items()])

        serializable_selected = [_serialize_course_info(sc, keep_score=True) for sc in selected_courses]
        serializable_rejected = [_serialize_course_info(rc, keep_score=True) for rc in rejected_courses]

        unschedulable_courses = solution.get('unschedulable_courses', [])

        extra_message = ""
        if solution.get('status') == 'infeasible':
            extra_message = "برنامه قابل تولید نیست. دلایل احتمالی: کمبود استاد واجد شرایط، عدم تطابق نوع کلاس، ظرفیت ناکافی، یا تداخل زمانی. لطفاً لاگ‌های 'دروس غیرقابل زمان‌بندی' را بررسی کنید."

        logger.info("خروجی نهایی آماده شد")
        return {
            "status": solution.get("status", "infeasible"),
            "objective_value": solution.get("objective_value"),
            "classes": [
                {
                    "id": sc.id,
                    "course_code": sc.course_code,
                    "course_title": sc.course_title,
                    "group_number": sc.group_number,
                    "instructor_name": sc.instructor_name,
                    "room_name": sc.room_name,
                    "day": sc.day,
                    "start_time": sc.start_time,
                    "end_time": sc.end_time,
                    "predicted_students": sc.predicted_students,
                    "explanation": json.loads(sc.explanation) if sc.explanation else []
                }
                for sc in saved_classes
            ],
            "hard_constraints_satisfied": solution.get("status") != "infeasible",
            "conflicts": [],
            "explanations": [
                f"برنامه برای نیمسال {semester} و مقاطع {'همه' if levels is None else ', '.join(levels)} تولید شده است",
                f"تعداد کل دروس انتخاب‌شده: {len(selected_courses)}",
                f"توزیع دروس: {term_summary}",
                "محدودیت‌های سخت (تداخل استاد، کلاس، گروه) رعایت شده است",
                f"{len(saved_classes)} کلاس برنامه‌ریزی شده است",
                extra_message
            ],
            "rejected_courses": serializable_rejected,
            "selected_courses": serializable_selected,
            "ranked_courses": ranked_courses,
            "alternative_scenarios": alternative_scenarios,
            "quality_metrics": {
                "total_classes": len(saved_classes),
                "total_groups": sum(1 for sc in saved_classes),
                "instructors_used": len(set(sc.instructor_id for sc in saved_classes if sc.instructor_id)),
                "rooms_used": len(set(sc.room_id for sc in saved_classes if sc.room_id)),
            },
            "unschedulable_courses": unschedulable_courses
        }
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در generate_schedule_from_db: {e}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"خطای غیرمنتظره: {str(e)}",
            "classes": [],
            "rejected_courses": [],
            "selected_courses": [],
            "ranked_courses": [],
            "explanations": [f"خطا: {str(e)}"],
            "alternative_scenarios": [],
            "quality_metrics": {},
            "unschedulable_courses": []
        }


def generate_alternative_scenarios(
        db: Session,
        courses: List[Course],
        instructors: List[Instructor],
        rooms: List[Room],
        slots: List[TimeSlot],
        selected_courses: List[Dict],
        semester: str,
        year: str,
        max_groups_per_course: int = 1
) -> List[Dict]:
    scenarios = []
    modes = [
        {"name": "متعادل", "description": "تعادل بین همه عوامل", "objective_mode": "balanced"},
        {"name": "رضایت استاد", "description": "اولویت با ترجیحات زمانی و درسی اساتید",
         "objective_mode": "teacher_preferences"},
        {"name": "فشردگی برنامه دانشجویان", "description": "کاهش پراکندگی کلاس‌های دانشجویان",
         "objective_mode": "compact_schedule"},
        {"name": "اولویت دروس گلوگاهی", "description": "اولویت با دروس مهم و گلوگاهی",
         "objective_mode": "graduation_priority"}
    ]

    for mode in modes:
        try:
            solution = solve_schedule(
                courses=courses,
                instructors=instructors,
                rooms=rooms,
                slots=slots,
                max_groups_per_course=max_groups_per_course,
                objective_mode=mode["objective_mode"]
            )
            scenarios.append({
                "name": mode["name"],
                "description": mode["description"],
                "objective_mode": mode["objective_mode"],
                "status": solution.get("status"),
                "objective_value": solution.get("objective_value"),
                "classes_count": len(solution.get("classes", [])),
            })
        except Exception as e:
            logger.error(f"خطا در تولید سناریو {mode['name']}: {e}")
            scenarios.append({
                "name": mode["name"],
                "description": mode["description"],
                "objective_mode": mode["objective_mode"],
                "status": "error",
                "error": str(e)
            })

    return scenarios