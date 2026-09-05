# backend/app/services/intelligent_recommendation_service.py
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.course import Course, OfferedCourse
from app.models.instructor import Instructor
from app.models.room import Room
from app.models.schedule import ScheduledClass
import yaml
import os

logger = logging.getLogger(__name__)

class IntelligentRecommendationService:
    """
    سرویس پیشنهاد هوشمند اتاق و استاد بر اساس محدودیت‌ها، ترجیحات و داده‌های تاریخی.
    """

    def __init__(self, db: Session):
        self.db = db
        self.scoring_config = self._load_scoring_config()
        self.constraints_config = self._load_constraints_config()

    def _load_scoring_config(self) -> Dict:
        """بارگذاری فایل scoring.yaml"""
        # مسیر فایل نسبت به محل اجرا (backend/app/services)
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scoring.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"خطا در بارگذاری scoring.yaml: {e}")
            return {}

    def _load_constraints_config(self) -> Dict:
        """بارگذاری فایل constraints.yaml"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'constraints.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"خطا در بارگذاری constraints.yaml: {e}")
            return {}

    def recommend_room(self, course_id: int, term_id: Optional[int] = None,
                       constraints: Optional[Dict] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        پیشنهاد اتاق‌های مناسب برای یک درس مشخص.

        :param course_id: شناسه درس (OfferedCourse یا UniqueCourse)
        :param term_id: شناسه ترم (اختیاری)
        :param constraints: محدودیت‌های اضافی (اختیاری)
        :param limit: تعداد پیشنهادات برگشتی
        :return: لیست اتاق‌های پیشنهادی با امتیاز
        """
        # دریافت اطلاعات درس
        course = self.db.query(OfferedCourse).filter(OfferedCourse.id == course_id).first()
        if not course:
            course = self.db.query(Course).filter(Course.id == course_id).first()
            if not course:
                raise ValueError("درس مورد نظر یافت نشد")

        # تعداد دانشجویان مورد انتظار
        expected_enrollment = getattr(course, 'expected_enrollment', None)
        if not expected_enrollment:
            if hasattr(course, 'predicted_demand') and course.predicted_demand:
                expected_enrollment = int(course.predicted_demand)
            else:
                expected_enrollment = 30  # مقدار پیش‌فرض

        rooms = self.db.query(Room).all()
        scored_rooms = []

        for room in rooms:
            score = self._score_room(room, course, expected_enrollment, constraints)
            if score is not None:
                scored_rooms.append({
                    'room': room,
                    'score': score,
                    'details': self._get_room_details(room)
                })

        scored_rooms.sort(key=lambda x: x['score'], reverse=True)
        return scored_rooms[:limit]

    def _score_room(self, room: Room, course: Any, expected_enrollment: int,
                    constraints: Optional[Dict] = None) -> Optional[float]:
        """امتیازدهی به یک اتاق برای یک درس خاص."""
        score = 0.0
        weights = self.scoring_config.get('weights', {})
        soft_weights = weights.get('soft_constraints', {})

        # 1. ظرفیت (محدودیت سخت)
        if room.capacity < expected_enrollment:
            if constraints and constraints.get('strict_capacity', False):
                return None
            score -= 100  # جریمه سنگین

        # 2. امکانات (در صورت وجود)
        facilities = getattr(room, 'facilities', {}) or {}
        course_needs = getattr(course, 'required_facilities', {}) or {}
        if course_needs:
            match_count = sum(1 for k, v in course_needs.items() if facilities.get(k) == v)
            facility_score = (match_count / len(course_needs)) * soft_weights.get('facility_match', 5)
            score += facility_score

        # 3. نسبت ظرفیت بهینه
        ratio = room.capacity / expected_enrollment
        if 1.2 <= ratio <= 2.0:
            score += soft_weights.get('optimal_capacity', 3)
        elif 1.0 <= ratio < 1.2:
            score += soft_weights.get('good_capacity', 2)
        elif ratio > 2.0:
            score -= soft_weights.get('waste_capacity_penalty', 2)

        # 4. موقعیت ساختمان (در صورت وجود)
        if hasattr(room, 'building') and hasattr(course, 'preferred_building'):
            if room.building == course.preferred_building:
                score += soft_weights.get('preferred_building', 2)

        # 5. امتیاز رضایت قبلی
        if hasattr(room, 'avg_rating') and room.avg_rating:
            score += (room.avg_rating / 5) * soft_weights.get('previous_satisfaction', 2)

        return score

    def _get_room_details(self, room: Room) -> Dict:
        """استخراج جزئیات اتاق برای نمایش"""
        return {
            'id': room.id,
            'name': room.name,
            'capacity': room.capacity,
            'building': getattr(room, 'building', None),
            'floor': getattr(room, 'floor', None),
            'facilities': getattr(room, 'facilities', {}),
        }

    def recommend_instructor(self, course_id: int, term_id: Optional[int] = None,
                             constraints: Optional[Dict] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        پیشنهاد اساتید مناسب برای یک درس مشخص.
        """
        course = self.db.query(OfferedCourse).filter(OfferedCourse.id == course_id).first()
        if not course:
            course = self.db.query(Course).filter(Course.id == course_id).first()
            if not course:
                raise ValueError("درس مورد نظر یافت نشد")

        instructors = self.db.query(Instructor).all()
        scored_instructors = []

        for instructor in instructors:
            score = self._score_instructor(instructor, course, constraints)
            if score is not None:
                scored_instructors.append({
                    'instructor': instructor,
                    'score': score,
                    'details': self._get_instructor_details(instructor)
                })

        scored_instructors.sort(key=lambda x: x['score'], reverse=True)
        return scored_instructors[:limit]

    def _score_instructor(self, instructor: Instructor, course: Any,
                          constraints: Optional[Dict] = None) -> Optional[float]:
        """امتیازدهی به یک استاد برای یک درس خاص."""
        score = 0.0
        weights = self.scoring_config.get('weights', {})
        soft_weights = weights.get('soft_constraints', {})

        # 1. تخصص (محدودیت سخت)
        if getattr(instructor, 'department', None) and getattr(course, 'department', None):
            if instructor.department != course.department:
                if constraints and constraints.get('strict_department', True):
                    return None
                score -= 50

        # 2. بار کاری
        current_workload = self._get_instructor_workload(instructor.id, term_id=None)
        max_workload = getattr(instructor, 'max_hours_per_week', 20)
        if current_workload >= max_workload:
            if constraints and constraints.get('strict_workload', True):
                return None
            score -= 100

        # 3. رتبه علمی
        rank = getattr(instructor, 'rank', '')
        rank_score_map = {'professor': 10, 'associate': 8, 'assistant': 6, 'lecturer': 4}
        score += rank_score_map.get(rank.lower(), 0) * 0.5

        # 4. رضایت قبلی
        if hasattr(instructor, 'avg_rating') and instructor.avg_rating:
            score += (instructor.avg_rating / 5) * soft_weights.get('previous_satisfaction', 2)

        # 5. سابقه تدریس این درس
        if hasattr(course, 'id'):
            prev_count = self.db.query(ScheduledClass).filter(
                ScheduledClass.instructor_id == instructor.id,
                ScheduledClass.offered_course_id == course.id
            ).count()
            if prev_count > 0:
                score += soft_weights.get('previous_teaching_experience', 3)

        return score

    def _get_instructor_workload(self, instructor_id: int, term_id: Optional[int] = None) -> int:
        """محاسبه بار کاری استاد (تعداد واحدهای تدریس در ترم مشخص)"""
        total_hours = 0
        try:
            query = self.db.query(ScheduledClass).filter(
                ScheduledClass.instructor_id == instructor_id
            )
            if term_id:
                query = query.filter(ScheduledClass.term_id == term_id)
            for cls in query.all():
                total_hours += getattr(cls, 'hours', 3)
        except Exception as e:
            logger.warning(f"خطا در محاسبه بار کاری: {e}")
        return total_hours

    def _get_instructor_details(self, instructor: Instructor) -> Dict:
        """استخراج جزئیات استاد برای نمایش"""
        return {
            'id': instructor.id,
            'name': getattr(instructor, 'name', ''),
            'department': getattr(instructor, 'department', None),
            'rank': getattr(instructor, 'rank', None),
            'avg_rating': getattr(instructor, 'avg_rating', None),
            'max_hours_per_week': getattr(instructor, 'max_hours_per_week', 20),
        }