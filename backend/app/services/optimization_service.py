# app/services/optimization_service.py

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict

# وارد کردن توابع مورد نیاز از فایل مرجع اسلات‌های زمانی
from app.services.schedule.slot_times import get_slots, time_to_minutes, normalize_term

logger = logging.getLogger(__name__)


class OptimizationService:
    """
    سرویس بهینه‌سازی برنامه
    بهبود کیفیت برنامه با استفاده از معیارهای:
    - کاهش زمان‌های نامطلوب استاد
    - کاهش کلاس‌های خیلی زود/دیر
    - کاهش فاصله‌های غیرمنطقی در برنامه استاد
    - کاهش فاصله بین کلاس‌های یک گروه
    - استفاده بهتر از اتاق‌ها
    - ایجاد تعادل بین روزهای هفته
    """

    def __init__(self, db: Session):
        self.db = db

    def process(self, schedule: List[Dict], term: Optional[str] = None) -> List[Dict]:
        """
        ورودی: برنامه با اتاق‌های تخصیص یافته
        خروجی: برنامه بهینه‌سازی‌شده

        Args:
            schedule: لیست کلاس‌های زمان‌بندی‌شده
            term: ترم جاری (اختیاری) - اگر داده نشود، از داده‌ها استخراج می‌شود.
        """
        if not schedule:
            return []

        # استخراج ترم از داده‌ها اگر ارسال نشده باشد
        if term is None:
            # اولویت با term_key (که توسط data_preparer اضافه شده)
            term = schedule[0].get("term_key") or schedule[0].get("term", "")
            try:
                term = normalize_term(term)
            except ValueError:
                logger.warning(f"ترم نامعتبر '{term}' - استفاده از پیش‌فرض 'mehr'")
                term = "mehr"

        # در صورت وجود OR-Tools
        try:
            from app.optimization.cp_sat_solver import optimize_schedule
            return optimize_schedule(schedule, term=term)
        except (ImportError, AttributeError):
            logger.warning("تابع optimize_schedule در دسترس نیست، از هیوریستیک ساده استفاده می‌شود.")
            return self._heuristic_optimize(schedule, term)

    def _heuristic_optimize(self, schedule: List[Dict], term: str) -> List[Dict]:
        """
        بهینه‌سازی اکتشافی ساده با استفاده از اسلات‌های استاندارد:

        1. گروه‌بندی کلاس‌های هر استاد بر اساس روز.
        2. برای هر روز، اسلات‌های مجاز (بر اساس ترم و واحد) را دریافت می‌کند.
        3. کلاس‌ها را به اسلات‌های بهینه‌تر (نزدیک‌تر به ترجیحات استاد و فشرده‌تر) جابه‌جا می‌کند.
        4. در صورت امکان، کلاس‌های یک استاد را در روزهای کمتر فشرده می‌کند.

        Args:
            schedule: لیست کلاس‌های زمان‌بندی‌شده
            term: ترم جاری (استاندارد شده)

        Returns:
            لیست برنامه‌ی بهینه‌سازی‌شده
        """
        if len(schedule) < 2:
            return [item.copy() for item in schedule]

        # کپی از داده
        optimized = [item.copy() for item in schedule]

        # گروه‌بندی بر اساس استاد و روز
        by_instructor_day = defaultdict(lambda: defaultdict(list))
        for item in optimized:
            inst = item.get("instructor_code")
            if inst:
                day = item.get("day")
                if day is not None:
                    by_instructor_day[inst][day].append(item)

        # برای هر استاد، به‌ینه‌سازی روزهای او
        for inst, day_groups in by_instructor_day.items():
            logger.info(f"بهینه‌سازی استاد {inst}...")
            for day, courses in day_groups.items():
                if len(courses) < 2:
                    continue

                # دریافت اسلات‌های مجاز برای این روز بر اساس ترم و واحد
                # (برای سادگی، از اولین درس برای تشخیص واحد استفاده می‌کنیم)
                units = courses[0].get("units", 2)
                try:
                    slots_data = get_slots(term=term, units=units)
                    valid_slots = [(item['start'], item['end']) for item in slots_data.get('slots', [])]
                except Exception as e:
                    logger.error(f"خطا در دریافت اسلات‌ها برای ترم {term} و واحد {units}: {e}")
                    continue

                if not valid_slots:
                    continue

                # مرتب‌سازی کلاس‌های این روز بر اساس زمان شروع
                courses.sort(key=lambda c: time_to_minutes(c.get("start", "00:00")))

                # اسلات‌های موجود را به‌روز می‌کنیم
                # (در این نسخه ساده، فقط کلاس‌ها را به اولین اسلات ممکن منتقل می‌کنیم
                # تا فشردگی ایجاد شود - می‌توان بهبود داد)
                for idx, course in enumerate(courses):
                    # اگر اسلات فعلی در لیست اسلات‌های مجاز نباشد، به اسلات مجاز تغییر می‌دهیم
                    current_start = course.get("start")
                    current_end = course.get("end")
                    if (current_start, current_end) not in valid_slots:
                        # سعی می‌کنیم اسلات بعدی (در صورت وجود) را اختصاص دهیم
                        # (در اینجا به سادگی به اولین اسلات مجاز منتقل می‌کنیم)
                        # می‌توان منطق پیچیده‌تری برای انتخاب بهترین اسلات نوشت
                        if idx < len(valid_slots):
                            new_start, new_end = valid_slots[idx]
                            course["start"] = new_start
                            course["end"] = new_end
                            logger.info(
                                f"   تغییر اسلات درس {course.get('course_name')} گروه {course.get('group_number')} "
                                f"از {current_start}-{current_end} به {new_start}-{new_end}"
                            )

        logger.info("بهینه‌سازی اکتشافی با استفاده از اسلات‌های استاندارد انجام شد.")
        return optimized