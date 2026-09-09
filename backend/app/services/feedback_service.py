import logging
import yaml
import os
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np

from app.models.feedback import UserFeedback
from app.models.weight_history import WeightHistory

logger = logging.getLogger(__name__)


class FeedbackService:
    """سرویس تحلیل رضایت کاربران و تنظیم تدریجی وزن‌ها"""

    def __init__(self, db: Session):
        self.db = db
        self.config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'scoring.yaml'
        )
        self.weights = self._load_weights()

    def _load_weights(self) -> Dict:
        """بارگذاری وزن‌ها از فایل scoring.yaml"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('weights', {})
        except Exception as e:
            logger.error(f"خطا در بارگذاری scoring.yaml: {e}")
            return {
                "hard_constraints": 1000,
                "soft_constraints": {
                    "preferred_time": 10,
                    "minimize_gaps": 7,
                    "balance_workload": 6
                }
            }

    def _save_weights(self, new_weights: Dict) -> bool:
        """ذخیره وزن‌های جدید در فایل scoring.yaml"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            config['weights'] = new_weights
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره وزن‌ها: {e}")
            return False

    def collect_feedback(self, feedback_data: Dict) -> Dict:
        """ثبت بازخورد کاربر در دیتابیس"""
        try:
            feedback = UserFeedback(
                schedule_version_id=feedback_data.get('schedule_version_id'),
                ratings=feedback_data.get('ratings', {}),
                comment=feedback_data.get('comment', ''),
                submitted_at=feedback_data.get('submitted_at') or datetime.utcnow()
            )
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)

            logger.info(f"✅ بازخورد جدید ثبت شد: ID={feedback.id}")
            return {"feedback_id": feedback.id}
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ خطا در ثبت بازخورد: {e}")
            raise

    def get_feedback_statistics(self) -> Dict:
        """محاسبه آمار کلی بازخوردها"""
        feedbacks = self.db.query(UserFeedback).all()
        if not feedbacks:
            return {
                "total_feedback": 0,
                "avg_overall": 0,
                "avg_instructor": 0,
                "avg_time": 0,
                "avg_room": 0,
                "avg_comment_length": 0
            }

        total = len(feedbacks)
        ratings = [f.ratings for f in feedbacks]
        avg_overall = np.mean([r.get('overall', 0) for r in ratings])
        avg_instructor = np.mean([r.get('instructor', 0) for r in ratings])
        avg_time = np.mean([r.get('time', 0) for r in ratings])
        avg_room = np.mean([r.get('room', 0) for r in ratings])
        avg_comment_len = np.mean([len(f.comment or '') for f in feedbacks])

        return {
            "total_feedback": total,
            "avg_overall": round(avg_overall, 2),
            "avg_instructor": round(avg_instructor, 2),
            "avg_time": round(avg_time, 2),
            "avg_room": round(avg_room, 2),
            "avg_comment_length": round(avg_comment_len, 2)
        }

    def analyze_feedback(self) -> Dict:
        """تحلیل بازخوردها و محاسبه وزن‌های جدید بر اساس همبستگی"""
        feedbacks = self.db.query(UserFeedback).all()
        if len(feedbacks) < 10:
            return {
                "correlations": {},
                "new_weights": self.weights,
                "adjustment_reason": "تعداد بازخوردها کمتر از ۱۰ است، تنظیم انجام نشد.",
                "message": "نیاز به بازخورد بیشتر برای تنظیم دقیق وزن‌ها"
            }

        ratings_list = [f.ratings for f in feedbacks]
        overall_scores = [r.get('overall', 3) for r in ratings_list]

        categories = ['instructor', 'time', 'room']
        correlations = {}

        for cat in categories:
            scores = [r.get(cat, 3) for r in ratings_list]
            if len(scores) == len(overall_scores) and len(scores) > 1:
                corr = np.corrcoef(scores, overall_scores)[0, 1]
                if not np.isnan(corr):
                    correlations[cat] = corr

        new_weights = self.weights.copy()
        soft_weights = new_weights.get('soft_constraints', {})

        adjustment_made = False
        for cat, corr in correlations.items():
            if cat == 'instructor' and 'preferred_instructor' in soft_weights:
                old = soft_weights['preferred_instructor']
                new = max(1, int(old * (1 + 0.2 * corr)))
                soft_weights['preferred_instructor'] = new
                adjustment_made = True
            elif cat == 'time' and 'preferred_time' in soft_weights:
                old = soft_weights['preferred_time']
                new = max(1, int(old * (1 + 0.2 * corr)))
                soft_weights['preferred_time'] = new
                adjustment_made = True
            elif cat == 'room' and 'preferred_room' in soft_weights:
                old = soft_weights['preferred_room']
                new = max(1, int(old * (1 + 0.2 * corr)))
                soft_weights['preferred_room'] = new
                adjustment_made = True

        new_weights['soft_constraints'] = soft_weights

        if adjustment_made:
            self._save_weights(new_weights)
            self._save_weight_history(new_weights, correlations)
            self.weights = new_weights

        return {
            "correlations": correlations,
            "new_weights": new_weights,
            "adjustment_reason": "تنظیم بر اساس همبستگی بین امتیازات و رضایت کلی",
            "message": "وزن‌ها به‌روزرسانی شدند." if adjustment_made else "تغییری در وزن‌ها اعمال نشد."
        }

    def _save_weight_history(self, new_weights: Dict, correlations: Dict):
        """ذخیره تاریخچه تغییرات وزن‌ها"""
        try:
            history = WeightHistory(
                new_weights=new_weights,
                correlations=correlations,
                timestamp=datetime.utcnow(),
                reason="تنظیم خودکار بر اساس بازخورد"
            )
            self.db.add(history)
            self.db.commit()
        except Exception as e:
            logger.warning(f"ذخیره تاریخچه وزن‌ها با خطا مواجه شد: {e}")

    def get_weight_adjustment_history(self) -> List[Dict]:
        """دریافت تاریخچه تغییرات وزن‌ها"""
        try:
            history = self.db.query(WeightHistory).order_by(
                WeightHistory.timestamp.desc()
            ).limit(20).all()

            return [{
                "timestamp": h.timestamp.isoformat(),
                "new_weights": h.new_weights,
                "correlations": h.correlations,
                "reason": h.reason,
                "impact": h.impact or 0
            } for h in history]
        except Exception as e:
            logger.warning(f"خطا در دریافت تاریخچه وزن‌ها: {e}")
            return []