# app/services/schedule/orchestrator.py
# هماهنگ‌کننده اصلی مراحل (ارکستراسیون) با لاگ‌های مقایسه‌ای و کنترل نهایی

import logging
from collections import defaultdict
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.schedule.step_logger import StepLogger
from app.services.schedule.data_preparer import DataPreparer
from app.services.schedule.instructor_loader import InstructorLoader
from app.services.schedule.course_scorer import CourseScorer
from app.services.schedule.instructor_assigner import InstructorAssigner
from app.services.schedule.time_scheduler import TimeScheduler
from app.services.schedule.internship_assigner import InternshipAssigner
from app.services.schedule.report_generator import ReportGenerator
from app.utils.helpers import is_internship_or_project, get_day_name

logger = logging.getLogger(__name__)


class ScheduleOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.logger = StepLogger()
        self.data_preparer = DataPreparer()
        self.instructor_loader = InstructorLoader(db)
        self.course_scorer = CourseScorer()
        self.instructor_assigner = InstructorAssigner()
        self.time_scheduler = TimeScheduler()
        self.internship_assigner = InternshipAssigner()
        self.report_generator = ReportGenerator()

    def process(self, basket: List[Dict]) -> Dict[str, Any]:
        if not basket:
            logger.warning("سبد دروس خالی است")
            return {"assigned": [], "unassigned": [], "all": [], "steps": self.logger.get_result()}

        total_input = len(basket)
        logger.info("=" * 80)
        logger.info("🚀 شروع فرایند زمان‌بندی استاد و درس")
        logger.info(f"📊 تعداد کلاس‌های سبد: {total_input}")
        logger.info("=" * 80)

        # ============================================================
        # مرحله ۱: آماده‌سازی داده‌ها
        # ============================================================
        self.logger.start_step("آماده‌سازی داده‌ها", "نرمال‌سازی کدها و استخراج شماره ترم")
        try:
            prepared_courses = self.data_preparer.prepare(basket)
            self.logger.complete_step({
                "total_courses": len(prepared_courses),
                "sample_codes": [c.get("unique_code") for c in prepared_courses[:3]]
            })
            logger.info(f"📝 مرحله ۱: آماده‌سازی داده‌ها - {len(prepared_courses)} درس آماده شد")
            if len(prepared_courses) != total_input:
                logger.warning(
                    f"⚠️ تعداد دروس بعد از آماده‌سازی ({len(prepared_courses)}) با ورودی ({total_input}) متفاوت است!"
                )
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        # ============================================================
        # مرحله ۲: بارگذاری اطلاعات اساتید (استفاده از متد load())
        # ============================================================
        self.logger.start_step("بارگذاری اطلاعات اساتید", "دریافت از دیتابیس")
        try:
            # بارگذاری با متد load() که یک tuple یا dict برمی‌گرداند
            loaded = self.instructor_loader.load()

            # پردازش خروجی load()
            if isinstance(loaded, tuple) and len(loaded) == 3:
                instructor_data, teaching_prefs, time_prefs = loaded
            elif isinstance(loaded, dict):
                instructor_data = loaded.get("instructors", []) or loaded.get("instructor_data", [])
                teaching_prefs = loaded.get("teaching_prefs", {}) or loaded.get("teaching_preferences", {})
                time_prefs = loaded.get("time_prefs", {}) or loaded.get("time_preferences", {})
            else:
                # اگر هیچکدام نبود، مقادیر پیش‌فرض
                logger.warning("⚠️ خروجی load() غیرمنتظره است. استفاده از مقادیر پیش‌فرض.")
                instructor_data = []
                teaching_prefs = {}
                time_prefs = {}

            # ساخت دیکشنری نام اساتید برای لاگ (از هر دو فرمت پشتیبانی می‌کند)
            instructor_names = {}
            if isinstance(instructor_data, list):
                for inst in instructor_data:
                    code = inst.get("code")
                    if code:
                        instructor_names[code] = inst.get("name", code)
            elif isinstance(instructor_data, dict):
                instructor_names = instructor_data.get("names", {})
                if not instructor_names and "codes" in instructor_data:
                    for code in instructor_data.get("codes", []):
                        instructor_names[code] = instructor_data.get("names", {}).get(code, code)

            # ساخت نمونه‌هایی از teaching_prefs و time_prefs برای لاگ
            sample_teaching = []
            if isinstance(teaching_prefs, dict):
                for idx, (course_code, inst_list) in enumerate(list(teaching_prefs.items())[:5]):
                    instructors_info = []
                    for inst_code in inst_list[:3]:
                        name = instructor_names.get(inst_code, inst_code)
                        instructors_info.append({"code": inst_code, "name": name})
                    sample_teaching.append({
                        "course_code": course_code,
                        "instructors": instructors_info
                    })
            elif isinstance(teaching_prefs, list):
                for pref in teaching_prefs[:5]:
                    inst_code = pref.get("instructor_code", "")
                    name = instructor_names.get(inst_code, inst_code)
                    sample_teaching.append({
                        "course_code": pref.get("unique_course_code", ""),
                        "instructors": [{"code": inst_code, "name": name}]
                    })

            sample_time = []
            if isinstance(time_prefs, dict):
                for inst_code, time_list in list(time_prefs.items())[:5]:
                    prefs = []
                    for item in time_list[:3]:
                        if isinstance(item, tuple) and len(item) >= 3:
                            day, start, end = item[0], item[1], item[2]
                            priority = item[3] if len(item) > 3 else None
                            prefs.append({
                                "day": get_day_name(day),
                                "start": start,
                                "end": end,
                                "priority": priority
                            })
                    sample_time.append({
                        "instructor_code": inst_code,
                        "instructor_name": instructor_names.get(inst_code, inst_code),
                        "preferences": prefs
                    })
            elif isinstance(time_prefs, list):
                for pref in time_prefs[:5]:
                    sample_time.append({
                        "instructor_code": pref.get("instructor_code", ""),
                        "instructor_name": instructor_names.get(pref.get("instructor_code", ""),
                                                                pref.get("instructor_code", "")),
                        "preferences": [{
                            "day": pref.get("day", ""),
                            "start": pref.get("start_time", ""),
                            "end": pref.get("end_time", ""),
                            "priority": pref.get("priority", None)
                        }]
                    })

            instructor_count = len(instructor_data) if isinstance(instructor_data, list) else len(
                instructor_data.get('codes', []))
            teaching_prefs_count = len(teaching_prefs) if isinstance(teaching_prefs, (dict, list)) else 0
            time_prefs_count = len(time_prefs) if isinstance(time_prefs, (dict, list)) else 0

            self.logger.complete_step({
                "instructors_count": instructor_count,
                "teaching_prefs_count": teaching_prefs_count,
                "time_prefs_count": time_prefs_count,
                "sample_teaching_prefs": sample_teaching,
                "sample_time_prefs": sample_time
            })
            logger.info(f"👨‍🏫 مرحله ۲: اطلاعات اساتید بارگذاری شد - {instructor_count} استاد")
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        # تفکیک دروس عادی و کارآموزی
        regular_courses = [c for c in prepared_courses if not is_internship_or_project(c)]
        internship_courses = [c for c in prepared_courses if is_internship_or_project(c)]
        logger.info(f"🔍 تفکیک دروس: {len(regular_courses)} درس عادی، {len(internship_courses)} درس کارآموزی/پروژه")

        # ============================================================
        # مرحله ۳: اولویت‌بندی دروس عادی
        # ============================================================
        self.logger.start_step("اولویت‌بندی دروس عادی", "محاسبه امتیاز بر اساس پیش‌نیاز، ترم جاری، تقاضا و واحد")
        try:
            scored_courses = self.course_scorer.score_and_sort(regular_courses)
            self.logger.complete_step({
                "total_courses": len(scored_courses),
                "sample_scores": [
                    {
                        "course_name": c.get("course_name"),
                        "group_number": c.get("group_number"),
                        "priority_score": c.get("priority_score"),
                        "score_components": c.get("score_components", {})
                    }
                    for c in scored_courses[:10]
                ]
            })
            logger.info(f"📊 مرحله ۳: اولویت‌بندی دروس عادی - {len(scored_courses)} درس امتیازدهی شد")
            if len(scored_courses) != len(regular_courses):
                logger.warning(
                    f"⚠️ تعداد دروس امتیازدهی‌شده ({len(scored_courses)}) با تعداد دروس عادی ({len(regular_courses)}) متفاوت است!"
                )
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        # ============================================================
        # مرحله ۴: تخصیص استاد به دروس عادی (با امضای جدید)
        # ============================================================
        self.logger.start_step("تخصیص استاد به دروس عادی", "بر اساس اولویت‌های تدریس و نوع همکاری (چرخشی)")
        try:
            # فراخوانی با پارامترهای نام‌دار و دریافت دیکشنری
            assign_result = self.instructor_assigner.assign_instructors(
                courses=scored_courses,
                teaching_prefs=teaching_prefs,
                instructor_data=instructor_data
            )
            assigned_regular_with_instructor = assign_result.get("assigned", [])
            unassigned_regular_no_instructor = assign_result.get("unassigned", [])
            # اطمینان از اینکه همه دروس در خروجی هستند (چک توسط assigner انجام شده)
            self.logger.complete_step({
                "assigned": len(assigned_regular_with_instructor),
                "unassigned": len(unassigned_regular_no_instructor),
                "assigned_instructor": assigned_regular_with_instructor[:50],
                "unassigned_instructor": unassigned_regular_no_instructor[:50]
            })
            total_after_step4 = len(assigned_regular_with_instructor) + len(unassigned_regular_no_instructor)
            logger.info(
                f"✅ مرحله ۴: تخصیص استاد به دروس عادی - {len(assigned_regular_with_instructor)} تخصیص یافت، "
                f"{len(unassigned_regular_no_instructor)} بدون استاد"
            )
            if total_after_step4 != len(scored_courses):
                logger.error(
                    f"⚠️ تعداد خروجی مرحله ۴ ({total_after_step4}) با تعداد ورودی ({len(scored_courses)}) متفاوت است! "
                    f"{len(scored_courses) - total_after_step4} درس گم شده‌اند."
                )
            else:
                logger.info(f"✅ مرحله ۴: همه {len(scored_courses)} درس عادی پردازش شدند.")
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        # ============================================================
        # مرحله ۵: زمان‌بندی کامل هر استاد (با امضای جدید)
        # ============================================================
        self.logger.start_step("زمان‌بندی کامل به ازای هر استاد",
                               "برای هر استاد، با افزایش تدریجی تساهل، دروس را به طور متوازن در روزهای ترجیحی تخصیص می‌دهد")
        try:
            # فراخوانی با پارامترهای نام‌دار و دریافت دیکشنری
            schedule_result = self.time_scheduler.assign_full_schedule(
                courses=assigned_regular_with_instructor,
                instructor_data=instructor_data,
                time_prefs=time_prefs
            )
            assigned_regular_complete = schedule_result.get("scheduled", [])
            unassigned_regular_no_time = schedule_result.get("unscheduled", [])
            self.logger.complete_step({
                "assigned": len(assigned_regular_complete),
                "unassigned": len(unassigned_regular_no_time),
                "assigned_time": assigned_regular_complete[:50],
                "unassigned_time": unassigned_regular_no_time[:50]
            })
            total_after_step5 = len(assigned_regular_complete) + len(unassigned_regular_no_time)
            logger.info(
                f"✅ مرحله ۵: زمان‌بندی کامل به ازای هر استاد - {len(assigned_regular_complete)} تخصیص یافت، "
                f"{len(unassigned_regular_no_time)} بدون زمان"
            )
            if total_after_step5 != len(assigned_regular_with_instructor):
                logger.error(
                    f"⚠️ تعداد خروجی مرحله ۵ ({total_after_step5}) با تعداد ورودی ({len(assigned_regular_with_instructor)}) متفاوت است! "
                    f"{len(assigned_regular_with_instructor) - total_after_step5} درس گم شده‌اند."
                )
            else:
                logger.info(f"✅ مرحله ۵: همه {len(assigned_regular_with_instructor)} درس زمان‌بندی شدند.")
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        # ============================================================
        # مرحله ۶: تخصیص استاد به کارآموزی/پروژه
        # ============================================================
        self.logger.start_step("تخصیص استاد به کارآموزی/پروژه", "بدون محدودیت زمان و واحد")
        try:
            assigned_internship, unassigned_internship = self.internship_assigner.assign_internships(
                internship_courses, teaching_prefs, instructor_data
            )
            self.logger.complete_step({
                "assigned": len(assigned_internship),
                "unassigned": len(unassigned_internship),
                "assigned_internship": assigned_internship[:50],
                "unassigned_internship": unassigned_internship[:50]
            })
            total_after_step6 = len(assigned_internship) + len(unassigned_internship)
            logger.info(
                f"✅ مرحله ۶: تخصیص استاد به کارآموزی/پروژه - {len(assigned_internship)} تخصیص یافت، "
                f"{len(unassigned_internship)} بدون استاد"
            )
            if total_after_step6 != len(internship_courses):
                logger.error(
                    f"⚠️ تعداد خروجی مرحله ۶ ({total_after_step6}) با تعداد ورودی ({len(internship_courses)}) متفاوت است! "
                    f"{len(internship_courses) - total_after_step6} درس گم شده‌اند."
                )
            else:
                logger.info(f"✅ مرحله ۶: همه {len(internship_courses)} درس کارآموزی پردازش شدند.")
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        # ============================================================
        # ترکیب نتایج و کنترل نهایی
        # ============================================================
        assigned = assigned_regular_complete + assigned_internship
        unassigned = unassigned_regular_no_instructor + unassigned_regular_no_time + unassigned_internship

        # ---- کنترل نهایی: اطمینان از حضور همه دروس ورودی ----
        processed_ids = {id(c) for c in assigned + unassigned}
        all_course_ids = {id(c) for c in prepared_courses}

        missing_courses = []
        for course in prepared_courses:
            if id(course) not in processed_ids:
                course["instructor_code"] = None
                course["instructor_name"] = None
                course["day"] = None
                course["start"] = None
                course["end"] = None
                course["final_score"] = 0
                course["manual_required"] = True
                course["unassigned_reason"] = "درس در طول فرایند زمان‌بندی گم شده است (احتمالاً unique_code نامعتبر)"
                unassigned.append(course)
                missing_courses.append(course)

        if missing_courses:
            logger.error(f"❌ {len(missing_courses)} درس در کنترل نهایی به unassigned اضافه شدند (گم‌شده بودند).")
            for course in missing_courses:
                logger.error(f"   درس '{course.get('course_name')}' (گروه {course.get('group_number')}) "
                             f"کد یکتا: {course.get('unique_code', 'ندارد')}")

        # ============================================================
        # مرحله ۷: گزارش نهایی
        # ============================================================
        self.logger.start_step("گزارش نهایی", "جمع‌بندی و پاک‌سازی")
        try:
            instructor_used_units = defaultdict(int)
            for item in assigned_regular_complete:
                if item.get("instructor_code"):
                    instructor_used_units[item["instructor_code"]] += item.get("units", 0)

            # ساخت mismatch_details
            mismatch_details = self.report_generator.build_mismatch_details(
                assigned, unassigned, teaching_prefs, time_prefs, instructor_data
            )

            # حذف فیلدهای اتاق
            for item in assigned:
                item.pop("room", None)
                item.pop("room_id", None)
                item.pop("room_name", None)
                item.pop("capacity", None)

            # تولید گزارش نهایی
            self.report_generator.generate_report(
                assigned, unassigned, instructor_data, dict(instructor_used_units),
                mismatch_details=mismatch_details, total_input_courses=len(basket)
            )

            logger.info("📋 زمان‌های نهایی تخصیص‌یافته (نمونه):")
            for item in assigned[:5]:
                logger.info(
                    f"   {item.get('course_name')} گروه {item.get('group_number')} → {item.get('day')} {item.get('start')}-{item.get('end')} (واحد: {item.get('units')})"
                )

            # لاگ نهایی از تعداد کل
            total_assigned = len(assigned)
            total_unassigned = len(unassigned)
            total_output = total_assigned + total_unassigned
            logger.info("=" * 80)
            logger.info(f"📊 گزارش نهایی:")
            logger.info(f"   تعداد ورودی: {len(basket)}")
            logger.info(f"   تعداد آماده‌شده: {len(prepared_courses)}")
            logger.info(f"   تخصیص‌یافته: {total_assigned}")
            logger.info(f"   تخصیص‌نیافته: {total_unassigned}")
            logger.info(f"   مجموع خروجی: {total_output}")
            if total_output != len(basket):
                logger.error(f"⚠️ تعداد خروجی ({total_output}) با تعداد ورودی ({len(basket)}) متفاوت است! "
                             f"{len(basket) - total_output} درس گم شده‌اند.")
            else:
                logger.info(f"✅ همه {len(basket)} درس در خروجی حضور دارند.")
            logger.info("=" * 80)

            self.logger.complete_step({
                "total_assigned": total_assigned,
                "total_unassigned": total_unassigned,
                "success_rate": f"{total_assigned / total_output * 100:.2f}%" if total_output > 0 else "0%",
                "mismatch_details": mismatch_details
            })
        except Exception as e:
            self.logger.fail_step(str(e))
            raise

        all_classes = assigned + unassigned
        return {
            "assigned": assigned,
            "unassigned": unassigned,
            "all": all_classes,
            "steps": self.logger.get_result()
        }