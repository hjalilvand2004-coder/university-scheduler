from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from collections import defaultdict

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

    def process(self, schedule: List[Dict]) -> List[Dict]:
        """
        ورودی: برنامه با اتاق‌های تخصیص یافته
        خروجی: برنامه بهینه‌سازی‌شده
        """
        if not schedule:
            return []

        # در صورت وجود OR-Tools
        try:
            from app.optimization.cp_sat_solver import optimize_schedule
            return optimize_schedule(schedule)
        except (ImportError, AttributeError):
            logger.warning("تابع optimize_schedule در دسترس نیست، از هیوریستیک ساده استفاده می‌شود.")
            return self._heuristic_optimize(schedule)

    def _heuristic_optimize(self, schedule: List[Dict]) -> List[Dict]:
        """
        بهینه‌سازی اکتشافی ساده:
        - گروه‌بندی کلاس‌های یک استاد در روزهای کمتر (فشرده‌سازی)
        - در این نسخه، صرفاً کپی داده‌ها برمی‌گردد (قابل توسعه)
        """
        if len(schedule) < 2:
            return schedule

        # کپی از داده
        optimized = [item.copy() for item in schedule]

        # گروه‌بندی بر اساس استاد
        by_instructor = defaultdict(list)
        for item in optimized:
            inst = item.get("instructor_code")
            if inst:
                by_instructor[inst].append(item)

        # در اینجا می‌توان الگوریتم‌های بهبود را پیاده‌سازی کرد
        # فعلاً فقط لاگ می‌زنیم
        logger.info("بهینه‌سازی اکتشافی اعمال شد (فقط کپی داده).")
        return optimized