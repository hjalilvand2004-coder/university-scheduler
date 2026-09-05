# app/services/optimization_service.py

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
from datetime import datetime

# وارد کردن توابع مورد نیاز از فایل مرجع اسلات‌های زمانی
from app.services.schedule.slot_times import get_slots, time_to_minutes, normalize_term

logger = logging.getLogger(__name__)


class ChangeSuggestion:
    """کلاس کمکی برای ذخیره پیشنهادات جابه‌جایی"""

    def __init__(self, action: str, reason: str, expected_improvement: float):
        self.action = action
        self.reason = reason
        self.expected_improvement = expected_improvement


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

    def suggest_improvements(self, schedule_id: int) -> List[ChangeSuggestion]:
        """
        پیشنهاد جابه‌جایی‌های هوشمند برای بهبود برنامه

        Args:
            schedule_id: شناسه برنامه زمان‌بندی شده

        Returns:
            لیستی از پیشنهادات جابه‌جایی
        """
        # دریافت برنامه فعلی از دیتابیس
        current_schedule = self._get_schedule(schedule_id)

        if not current_schedule:
            logger.warning(f"برنامه با شناسه {schedule_id} یافت نشد")
            return []

        # تحلیل نقاط ضعف برنامه فعلی
        weak_points = self._analyze_weak_points(current_schedule)

        suggestions = []
        for point in weak_points:
            # استفاده از OR-Tools برای یافتن جابه‌جایی بهینه
            improvement = self._find_improvement(current_schedule, point)
            if improvement:
                suggestions.append(ChangeSuggestion(
                    action=improvement.get('action', ''),
                    reason=improvement.get('reason', ''),
                    expected_improvement=improvement.get('score_improvement', 0.0)
                ))

        return suggestions

    def _get_schedule(self, schedule_id: int) -> List[Dict]:
        """
        دریافت برنامه از دیتابیس بر اساس شناسه

        Args:
            schedule_id: شناسه برنامه

        Returns:
            لیست کلاس‌های برنامه
        """
        try:
            from app.models.schedule import Schedule
            schedule = self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if schedule and schedule.data:
                return schedule.data
            return []
        except Exception as e:
            logger.error(f"خطا در دریافت برنامه با شناسه {schedule_id}: {e}")
            return []

    def _analyze_weak_points(self, schedule: List[Dict]) -> List[Dict]:
        """
        تحلیل نقاط ضعف برنامه فعلی

        Args:
            schedule: لیست کلاس‌های زمان‌بندی‌شده

        Returns:
            لیستی از نقاط ضعف شناسایی شده
        """
        weak_points = []

        if not schedule:
            return weak_points

        # تحلیل توزیع کلاس‌ها در روزهای هفته
        day_distribution = defaultdict(int)
        for item in schedule:
            day = item.get('day')
            if day is not None:
                day_distribution[day] += 1

        # بررسی عدم تعادل در توزیع روزها
        if day_distribution:
            avg_classes = sum(day_distribution.values()) / len(day_distribution)
            for day, count in day_distribution.items():
                if count > avg_classes * 1.5:  # روز با بار زیاد
                    weak_points.append({
                        'type': 'unbalanced_days',
                        'day': day,
                        'count': count,
                        'severity': 'high'
                    })
                elif count < avg_classes * 0.5:  # روز با بار کم
                    weak_points.append({
                        'type': 'unbalanced_days',
                        'day': day,
                        'count': count,
                        'severity': 'low'
                    })

        # تحلیل فاصله‌های زمانی بین کلاس‌های هر استاد
        instructor_gaps = defaultdict(list)
        for item in schedule:
            instructor = item.get('instructor_code')
            if instructor:
                start_time = time_to_minutes(item.get('start', '00:00'))
                instructor_gaps[instructor].append({
                    'day': item.get('day'),
                    'start': start_time,
                    'end': time_to_minutes(item.get('end', '00:00')),
                    'course': item.get('course_name', '')
                })

        # بررسی فاصله‌های طولانی بین کلاس‌های یک استاد
        for instructor, classes in instructor_gaps.items():
            if len(classes) >= 2:
                # مرتب‌سازی بر اساس روز و زمان
                classes.sort(key=lambda x: (x['day'] or 0, x['start']))

                for i in range(len(classes) - 1):
                    if classes[i]['day'] == classes[i + 1]['day']:
                        gap = classes[i + 1]['start'] - classes[i]['end']
                        if gap > 120:  # فاصله بیشتر از 2 ساعت
                            weak_points.append({
                                'type': 'large_gap',
                                'instructor': instructor,
                                'gap_minutes': gap,
                                'course1': classes[i]['course'],
                                'course2': classes[i + 1]['course'],
                                'severity': 'medium'
                            })

        # تحلیل استفاده از اتاق‌ها
        room_usage = defaultdict(int)
        for item in schedule:
            room = item.get('room')
            if room:
                room_usage[room] += 1

        # بررسی اتاق‌های با استفاده کم یا زیاد
        if room_usage:
            avg_usage = sum(room_usage.values()) / len(room_usage)
            for room, count in room_usage.items():
                if count > avg_usage * 1.5:  # اتاق با استفاده زیاد
                    weak_points.append({
                        'type': 'overused_room',
                        'room': room,
                        'count': count,
                        'severity': 'medium'
                    })
                elif count < avg_usage * 0.5 and count > 0:  # اتاق با استفاده کم
                    weak_points.append({
                        'type': 'underused_room',
                        'room': room,
                        'count': count,
                        'severity': 'low'
                    })

        return weak_points

    def _find_improvement(self, schedule: List[Dict], weak_point: Dict) -> Optional[Dict]:
        """
        یافتن جابه‌جایی بهینه برای بهبود نقطه ضعف مشخص

        Args:
            schedule: لیست کلاس‌های زمان‌بندی‌شده
            weak_point: نقطه ضعف شناسایی شده

        Returns:
            دیکشنری شامل اطلاعات جابه‌جایی پیشنهادی
        """
        improvement = None

        try:
            # استفاده از OR-Tools برای یافتن جابه‌جایی بهینه
            from app.optimization.cp_sat_solver import find_improvement
            improvement = find_improvement(schedule, weak_point)
        except (ImportError, AttributeError):
            logger.warning("تابع find_improvement در دسترس نیست، از منطق ساده استفاده می‌شود.")
            improvement = self._heuristic_find_improvement(schedule, weak_point)

        return improvement

    def _heuristic_find_improvement(self, schedule: List[Dict], weak_point: Dict) -> Optional[Dict]:
        """
        یافتن جابه‌جایی با استفاده از منطق اکتشافی ساده

        Args:
            schedule: لیست کلاس‌های زمان‌بندی‌شده
            weak_point: نقطه ضعف شناسایی شده

        Returns:
            دیکشنری شامل اطلاعات جابه‌جایی پیشنهادی
        """
        improvement = None

        weak_type = weak_point.get('type')

        if weak_type == 'unbalanced_days':
            # پیشنهاد جابه‌جایی کلاس‌ها از روزهای شلوغ به روزهای خلوت
            day = weak_point.get('day')
            if day is not None:
                # یافتن کلاس‌هایی که در این روز برگزار می‌شوند
                day_classes = [item for item in schedule if item.get('day') == day]
                if day_classes:
                    # پیشنهاد جابه‌جایی یک کلاس به روز دیگر
                    improvement = {
                        'action': f"انتقال یک کلاس از روز {day} به روز دیگر",
                        'reason': f"روز {day} دارای {weak_point.get('count')} کلاس است که بیشتر از میانگین است",
                        'score_improvement': 5.0
                    }

        elif weak_type == 'large_gap':
            # پیشنهاد فشرده‌سازی کلاس‌های استاد
            instructor = weak_point.get('instructor')
            gap_minutes = weak_point.get('gap_minutes', 0)
            if instructor and gap_minutes > 120:
                improvement = {
                    'action': f"فشرده‌سازی کلاس‌های استاد {instructor}",
                    'reason': f"فاصله {gap_minutes} دقیقه‌ای بین کلاس‌های {weak_point.get('course1')} و {weak_point.get('course2')}",
                    'score_improvement': min(gap_minutes / 10, 10.0)
                }

        elif weak_type == 'overused_room':
            # پیشنهاد انتقال به اتاق کمتر استفاده شده
            room = weak_point.get('room')
            if room:
                improvement = {
                    'action': f"انتقال برخی کلاس‌ها از اتاق {room} به اتاق دیگر",
                    'reason': f"اتاق {room} دارای {weak_point.get('count')} کلاس است که بیشتر از میانگین است",
                    'score_improvement': 3.0
                }

        elif weak_type == 'underused_room':
            # پیشنهاد استفاده بهتر از اتاق
            room = weak_point.get('room')
            if room:
                improvement = {
                    'action': f"استفاده بهتر از اتاق {room}",
                    'reason': f"اتاق {room} تنها دارای {weak_point.get('count')} کلاس است",
                    'score_improvement': 2.0
                }

        return improvement

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