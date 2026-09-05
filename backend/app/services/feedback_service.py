# app/services/feedback_service.py
class FeedbackAnalysisService:
    def __init__(self, scoring_config_path="scoring.yaml"):
        self.config = self._load_config(scoring_config_path)
        self.weights = self.config['weights']

    def collect_feedback(self, schedule_version_id: int, user_id: int, ratings: dict):
        """جمع‌آوری بازخورد کاربران (امتیاز به زمان، استاد، اتاق، ...)"""
        feedback = UserFeedback(
            schedule_version_id=schedule_version_id,
            user_id=user_id,
            ratings=ratings,
            timestamp=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()

    def adjust_weights(self):
        """تنظیم تدریجی وزن‌ها بر اساس بازخورد کاربران"""
        all_feedback = self._get_recent_feedback()

        # محاسبه همبستگی بین هر وزن و رضایت کاربران
        correlations = {}
        for weight_name, current_weight in self.weights.items():
            correlation = self._calculate_correlation(weight_name, all_feedback)
            correlations[weight_name] = correlation

        # تنظیم وزن‌ها: افزایش وزن‌هایی که همبستگی مثبت دارند
        for name, corr in correlations.items():
            if corr > 0.3:  # همبستگی قابل قبول
                self.weights[name] = min(self.weights[name] * 1.1, 20)  # افزایش حداکثر ۲۰
            elif corr < -0.3:  # همبستگی منفی
                self.weights[name] = max(self.weights[name] * 0.9, 1)  # کاهش حداقل ۱

        # ذخیره تنظیمات جدید
        self._save_config(self.weights)