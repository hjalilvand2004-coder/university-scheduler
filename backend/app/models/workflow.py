from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, Enum
from app.core.database import Base
from datetime import datetime
import enum


class WorkflowStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ===== وضعیت‌های جدید برای فرایندهای چهارگانه =====
class ProcessStatus(str, enum.Enum):
    PENDING = "pending"
    BASKET_READY = "basket_ready"
    SCHEDULED = "scheduled"
    ROOMS_ALLOCATED = "rooms_allocated"
    OPTIMIZED = "optimized"
    ERROR = "error"


class ScheduleWorkflow(Base):
    __tablename__ = "schedule_workflows"

    id = Column(Integer, primary_key=True, index=True)
    semester = Column(String(20), nullable=False)  # mehr / bahman
    levels = Column(JSON, nullable=False)  # لیست مقاطع
    year = Column(String(20), nullable=False, default="1403")

    # ===== داده‌های هر گام (برای فرایند گام‌به‌گام قدیمی) =====
    # گام ۱: یکپارچه‌سازی دروس ترمیک بر اساس ترم فرد/زوج
    step1_data = Column(JSON)  # {"semester": "...", "levels": [...], "year": "...", "integrated_courses": [...]}

    # گام ۲: اضافه کردن دروس گلوگاهی و پیش‌نیازهای缺失
    # هر رکورد شامل: level, term, course_name, unique_code, units, course_type,
    # from_termic (bool), from_prerequisite (bool), from_student_demand (bool),
    # from_manager (bool), is_bottleneck (bool), weight (int)
    step2_data = Column(JSON)

    # گام ۳: تخمین تعداد گروه‌ها بر اساس فراوانی در ترم‌های مهر
    # اضافه شدن: frequency_in_mehr (int), avg_capacity (float), suggested_groups (int)
    step3_data = Column(JSON)

    # گام ۴: چیدمان روزانه دروس با رعایت عدم تداخل هم‌ترم
    # اضافه شدن: day (int), start (str), end (str)
    step4_data = Column(JSON)

    # گام ۵: تخصیص استاد و نهایی‌سازی
    # اضافه شدن: instructor_code (str), instructor_name (str)
    step5_data = Column(JSON)

    # ===== وضعیت گام‌های فرایند گام‌به‌گام =====
    step1_done = Column(Boolean, default=False)
    step2_done = Column(Boolean, default=False)
    step3_done = Column(Boolean, default=False)
    step4_done = Column(Boolean, default=False)
    step5_done = Column(Boolean, default=False)

    # ===== داده‌های فرایندهای چهارگانه جدید =====
    # فرایند ۱: شناسایی سبد دروس
    basket_data = Column(JSON)  # لیست دروس با ستون‌های: level, course_name, unique_code, required_classes, ...

    # فرایند ۲: زمان‌بندی استاد و درس (بدون اتاق)
    schedule_no_room_data = Column(JSON)  # لیست کلاس‌ها با استاد، روز و ساعت

    # فرایند ۳: تخصیص اتاق
    rooms_allocated_data = Column(JSON)  # لیست کلاس‌ها با اتاق اختصاص‌یافته

    # فرایند ۴: بهینه‌سازی برنامه
    optimized_data = Column(JSON)  # لیست کلاس‌های بهینه‌سازی‌شده

    # ===== وضعیت تکمیل فرایندهای چهارگانه =====
    basket_done = Column(Boolean, default=False)
    schedule_no_room_done = Column(Boolean, default=False)
    rooms_allocated_done = Column(Boolean, default=False)
    optimized_done = Column(Boolean, default=False)

    # ===== وضعیت کلی فرایند (برای فرایند گام‌به‌گام) =====
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.IN_PROGRESS)
    current_step = Column(Integer, default=0)  # 0-based: 0 = step1, 1 = step2, ...

    # ===== وضعیت کلی برای فرایندهای چهارگانه =====
    process_status = Column(Enum(ProcessStatus), default=ProcessStatus.PENDING)

    # ===== زمان‌ها =====
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ScheduleWorkflow(id={self.id}, semester={self.semester}, status={self.status})>"

    def to_dict(self):
        """تبدیل شیء به دیکشنری برای پاسخ‌های API"""
        return {
            "id": self.id,
            "semester": self.semester,
            "levels": self.levels,
            "year": self.year,
            # داده‌های گام‌های قدیمی
            "step1_data": self.step1_data,
            "step2_data": self.step2_data,
            "step3_data": self.step3_data,
            "step4_data": self.step4_data,
            "step5_data": self.step5_data,
            "step1_done": self.step1_done,
            "step2_done": self.step2_done,
            "step3_done": self.step3_done,
            "step4_done": self.step4_done,
            "step5_done": self.step5_done,
            # داده‌های فرایندهای چهارگانه جدید
            "basket_data": self.basket_data,
            "schedule_no_room_data": self.schedule_no_room_data,
            "rooms_allocated_data": self.rooms_allocated_data,
            "optimized_data": self.optimized_data,
            "basket_done": self.basket_done,
            "schedule_no_room_done": self.schedule_no_room_done,
            "rooms_allocated_done": self.rooms_allocated_done,
            "optimized_done": self.optimized_done,
            # وضعیت‌ها
            "status": self.status.value if self.status else None,
            "current_step": self.current_step,
            "process_status": self.process_status.value if self.process_status else None,
            # زمان‌ها
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }