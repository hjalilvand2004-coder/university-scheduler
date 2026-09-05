# app/services/demand_service.py

import math
import logging
from typing import Optional, List, Dict, Any
from collections import defaultdict
import joblib
import os
import pandas as pd
import numpy as np

from app.schemas.course import Course

logger = logging.getLogger(__name__)


# ============================================================
# کلاس جدید: DemandPredictionService برای پیش‌بینی هوشمند
# ============================================================
class DemandPredictionService:
    """
    سرویس پیش‌بینی تقاضای درس بر اساس داده‌های ترم‌های گذشته
    با استفاده از Random Forest و سایر الگوریتم‌های یادگیری ماشین
    """

    def __init__(self, model_path: str = "models/demand_model.pkl"):
        """
        مقداردهی اولیه سرویس پیش‌بینی

        Args:
            model_path: مسیر فایل مدل ذخیره شده
        """
        self.model_path = model_path
        self.model = self._load_model(model_path) if os.path.exists(model_path) else None
        self.feature_columns = [
            'course_id', 'semester_code', 'instructor_id', 'day_of_week',
            'time_slot', 'course_level', 'credits', 'historical_trend'
        ]
        logger.info(f"سرویس پیش‌بینی تقاضا مقداردهی شد. مدل موجود: {self.model is not None}")

    def _load_model(self, model_path: str):
        """
        بارگذاری مدل از فایل

        Args:
            model_path: مسیر فایل مدل

        Returns:
            مدل بارگذاری شده یا None در صورت خطا
        """
        try:
            if os.path.exists(model_path):
                model = joblib.load(model_path)
                logger.info(f"مدل از {model_path} بارگذاری شد")
                return model
            return None
        except Exception as e:
            logger.error(f"خطا در بارگذاری مدل از {model_path}: {e}")
            return None

    def train_model(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        آموزش مدل بر اساس داده‌های ترم‌های گذشته

        Args:
            historical_data: لیست دیکشنری‌های شامل داده‌های تاریخی هر درس

        Returns:
            دیکشنری شامل نتایج آموزش
        """
        logger.info(f"شروع آموزش مدل با {len(historical_data)} رکورد")

        if not historical_data:
            return {
                "status": "failed",
                "message": "داده‌های تاریخی برای آموزش وجود ندارد"
            }

        try:
            # آماده‌سازی ویژگی‌ها و برچسب‌ها
            X, y = self._prepare_features(historical_data)

            if len(X) < 10:
                logger.warning(f"تعداد رکوردهای آموزشی ({len(X)}) کمتر از حداقل ۱۰ است")
                return {
                    "status": "failed",
                    "message": f"تعداد رکوردهای آموزشی ({len(X)}) کافی نیست",
                    "records_count": len(X)
                }

            # ایجاد و آموزش مدل Random Forest
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_absolute_error, r2_score

            # تقسیم داده‌ها به آموزش و تست
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # آموزش مدل
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_train, y_train)

            # ارزیابی مدل
            y_pred = self.model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            logger.info(f"آموزش مدل کامل شد. MAE: {mae:.2f}, R2: {r2:.3f}")

            # ذخیره مدل
            self._save_model()

            # محاسبه اهمیت ویژگی‌ها
            feature_importance = {}
            if hasattr(self.model, 'feature_importances_'):
                for idx, col in enumerate(self.feature_columns[:len(self.model.feature_importances_)]):
                    feature_importance[col] = float(self.model.feature_importances_[idx])

            return {
                "status": "success",
                "mae": mae,
                "r2_score": r2,
                "train_size": len(X_train),
                "test_size": len(X_test),
                "feature_importance": feature_importance,
                "message": "مدل با موفقیت آموزش و ذخیره شد"
            }

        except Exception as e:
            logger.error(f"خطا در آموزش مدل: {e}")
            return {
                "status": "failed",
                "message": f"خطا در آموزش مدل: {str(e)}"
            }

    def _prepare_features(self, historical_data: List[Dict[str, Any]]) -> tuple:
        """
        آماده‌سازی ویژگی‌ها و برچسب‌ها برای آموزش مدل

        Args:
            historical_data: لیست دیکشنری‌های شامل داده‌های تاریخی

        Returns:
            tuple (X, y): ماتریس ویژگی‌ها و بردار برچسب‌ها
        """
        X = []
        y = []

        for record in historical_data:
            features = self._extract_features_for_training(record)
            X.append(features)
            y.append(record.get('enrollment_count', 0))

        # تبدیل به numpy array
        X = np.array(X)
        y = np.array(y)

        # حذف رکوردهای با مقادیر NaN
        mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
        X = X[mask]
        y = y[mask]

        return X, y

    def _extract_features_for_training(self, record: Dict[str, Any]) -> List[float]:
        """
        استخراج ویژگی‌ها برای آموزش مدل

        Args:
            record: دیکشنری شامل داده‌های یک درس

        Returns:
            لیست ویژگی‌ها به صورت عددی
        """
        features = []

        # 1. شناسه درس (کد شده)
        features.append(float(record.get('course_id', 0)) % 100)

        # 2. کد ترم (کد شده)
        semester_codes = {'mehr': 0, 'bahman': 1, 'khordad': 2}
        features.append(semester_codes.get(record.get('semester', 'mehr'), 0))

        # 3. شناسه استاد (کد شده)
        features.append(float(record.get('instructor_id', 0)) % 50)

        # 4. روز هفته (0-6)
        features.append(float(record.get('day', 0)))

        # 5. زمان (کد شده: قبل از 10=0، 10-14=1، بعد از 14=2)
        time = record.get('time', '08:00')
        try:
            hour = int(time.split(':')[0])
            if hour < 10:
                time_code = 0
            elif hour < 14:
                time_code = 1
            else:
                time_code = 2
        except:
            time_code = 1
        features.append(float(time_code))

        # 6. سطح درس (کارشناسی=0، کارشناسی ارشد=1، دکتری=2)
        level_codes = {'undergraduate': 0, 'graduate': 1, 'phd': 2}
        features.append(level_codes.get(record.get('course_level', 'undergraduate'), 0))

        # 7. تعداد واحد (2-4)
        features.append(float(record.get('credits', 3)))

        # 8. روند تاریخی (تغییر نسبت به ترم قبل)
        features.append(float(record.get('historical_trend', 0)))

        return features

    def predict_demand(self, course_id: int, semester: str = "mehr") -> int:
        """
        پیش‌بینی تعداد دانشجویان برای یک درس در ترم مشخص

        Args:
            course_id: شناسه درس
            semester: کد ترم (mehr, bahman, khordad)

        Returns:
            تعداد دانشجویان پیش‌بینی شده
        """
        try:
            # اگر مدل موجود باشد، از مدل استفاده می‌کنیم
            if self.model is not None:
                features = self._extract_features(course_id, semester)
                features = np.array(features).reshape(1, -1)
                prediction = int(self.model.predict(features)[0])
                return max(1, prediction)

            # در غیر این صورت از روش ساده استفاده می‌کنیم
            logger.warning("مدل موجود نیست، از روش ساده پیش‌بینی استفاده می‌شود")
            return self._simple_predict(course_id)

        except Exception as e:
            logger.error(f"خطا در پیش‌بینی تقاضا برای درس {course_id}: {e}")
            return 30  # مقدار پیش‌فرض

    def _extract_features(self, course_id: int, semester: str) -> List[float]:
        """
        استخراج ویژگی‌ها برای پیش‌بینی یک درس خاص

        Args:
            course_id: شناسه درس
            semester: کد ترم

        Returns:
            لیست ویژگی‌ها به صورت عددی
        """
        # در اینجا باید اطلاعات درس از دیتابیس دریافت شود
        # برای سادگی، از مقادیر پیش‌فرض استفاده می‌کنیم
        semester_codes = {'mehr': 0, 'bahman': 1, 'khordad': 2}

        features = [
            float(course_id % 100),
            semester_codes.get(semester, 0),
            0.0,  # instructor_id (پیش‌فرض)
            2.0,  # day (پیش‌فرض: سه‌شنبه)
            1.0,  # time_code (پیش‌فرض)
            0.0,  # course_level (پیش‌فرض: کارشناسی)
            3.0,  # credits (پیش‌فرض)
            0.0   # historical_trend (پیش‌فرض)
        ]

        return features

    def _simple_predict(self, course_id: int) -> int:
        """
        پیش‌بینی ساده برای مواقعی که مدل در دسترس نیست

        Args:
            course_id: شناسه درس

        Returns:
            تعداد دانشجویان پیش‌بینی شده
        """
        # پیش‌بینی بر اساس شناسه درس
        base_demand = 30 + (course_id % 20)
        return max(1, min(base_demand, 100))

    def suggest_room(self, course_id: int, semester: str) -> Dict[str, Any]:
        """
        پیشنهاد اتاق مناسب بر اساس پیش‌بینی تقاضا

        Args:
            course_id: شناسه درس
            semester: کد ترم

        Returns:
            دیکشنری شامل پیشنهاد اتاق
        """
        predicted_enrollment = self.predict_demand(course_id, semester)

        # یافتن اتاق با ظرفیت مناسب (با کمی فاصله اطمینان)
        suitable_rooms = self._find_rooms_by_capacity(
            min_capacity=predicted_enrollment,
            max_capacity=int(predicted_enrollment * 1.3) + 10
        )

        # انتخاب بهترین اتاق با توجه به اولویت‌ها
        return self._select_best_room(suitable_rooms, course_id)

    def _find_rooms_by_capacity(self, min_capacity: int, max_capacity: int) -> List[Dict]:
        """
        یافتن اتاق‌های با ظرفیت مناسب

        Args:
            min_capacity: حداقل ظرفیت
            max_capacity: حداکثر ظرفیت

        Returns:
            لیست اتاق‌های مناسب
        """
        # در اینجا باید از دیتابیس اتاق‌ها را دریافت کرد
        # برای سادگی، لیست نمونه برمی‌گردانیم
        sample_rooms = [
            {"id": 1, "name": "سالن A", "capacity": 30, "type": "نظری"},
            {"id": 2, "name": "سالن B", "capacity": 40, "type": "نظری"},
            {"id": 3, "name": "سالن C", "capacity": 50, "type": "نظری"},
            {"id": 4, "name": "آزمایشگاه 1", "capacity": 25, "type": "عملی"},
            {"id": 5, "name": "آزمایشگاه 2", "capacity": 30, "type": "عملی"},
        ]

        suitable = []
        for room in sample_rooms:
            if min_capacity <= room["capacity"] <= max_capacity:
                suitable.append(room)

        return suitable

    def _select_best_room(self, rooms: List[Dict], course_id: int) -> Dict[str, Any]:
        """
        انتخاب بهترین اتاق از بین اتاق‌های مناسب

        Args:
            rooms: لیست اتاق‌های مناسب
            course_id: شناسه درس

        Returns:
            بهترین اتاق انتخاب شده
        """
        if not rooms:
            return {
                "status": "no_room_found",
                "message": "هیچ اتاق مناسبی یافت نشد",
                "suggested_room": None
            }

        # انتخاب اتاق با ظرفیت نزدیک‌تر به نیاز
        # (در اینجا ساده‌ترین انتخاب: اولین اتاق)
        best_room = rooms[0]

        # سعی می‌کنیم بهترین اتاق را بر اساس نزدیک‌ترین ظرفیت انتخاب کنیم
        predicted_enrollment = self.predict_demand(course_id, "mehr")
        for room in rooms:
            if abs(room["capacity"] - predicted_enrollment) < abs(best_room["capacity"] - predicted_enrollment):
                best_room = room

        return {
            "status": "success",
            "predicted_enrollment": predicted_enrollment,
            "suggested_room": best_room,
            "message": f"اتاق {best_room['name']} با ظرفیت {best_room['capacity']} پیشنهاد می‌شود"
        }

    def _save_model(self) -> bool:
        """
        ذخیره مدل در فایل

        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            if self.model is not None:
                # اطمینان از وجود دایرکتوری
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                joblib.dump(self.model, self.model_path)
                logger.info(f"مدل در {self.model_path} ذخیره شد")
                return True
            return False
        except Exception as e:
            logger.error(f"خطا در ذخیره مدل: {e}")
            return False

    def evaluate_model(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        ارزیابی مدل با داده‌های تست

        Args:
            test_data: لیست دیکشنری‌های شامل داده‌های تست

        Returns:
            دیکشنری شامل نتایج ارزیابی
        """
        if self.model is None:
            return {
                "status": "failed",
                "message": "مدل وجود ندارد"
            }

        try:
            X_test, y_test = self._prepare_features(test_data)

            if len(X_test) == 0:
                return {
                    "status": "failed",
                    "message": "داده‌های تست معتبر وجود ندارد"
                }

            y_pred = self.model.predict(X_test)

            from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error

            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            return {
                "status": "success",
                "mae": mae,
                "mse": mse,
                "r2_score": r2,
                "test_size": len(X_test),
                "message": "ارزیابی مدل با موفقیت انجام شد"
            }

        except Exception as e:
            logger.error(f"خطا در ارزیابی مدل: {e}")
            return {
                "status": "failed",
                "message": f"خطا در ارزیابی مدل: {str(e)}"
            }


# ============================================================
# توابع موجود (برای سازگاری با کد قبلی)
# ============================================================

def predict_demand(course: Course) -> int:
    """
    پیش‌بینی ساده تقاضای درس بر اساس داده‌های تاریخی و درخواست‌های مستقیم.

    فرمول:
        predicted_demand = (historical_demand * 0.7) + (direct_requests * 1.5)

    در نسخه اولیه از یک مدل خطی ساده استفاده می‌شود.
    در نسخه‌های بعدی می‌توان این تابع را با مدل یادگیری ماشین جایگزین کرد.

    Args:
        course: شیء Course شامل historical_demand و direct_requests

    Returns:
        تعداد دانشجویان پیش‌بینی‌شده (حداقل ۱)
    """
    # استفاده از سرویس پیش‌بینی در صورت موجود بودن
    try:
        prediction_service = DemandPredictionService()
        if prediction_service.model is not None:
            return prediction_service.predict_demand(course.id, "mehr")
    except Exception as e:
        logger.warning(f"خطا در استفاده از مدل پیش‌بینی: {e}")

    # روش ساده
    historical_part = getattr(course, 'historical_demand', 0) * 0.7
    direct_request_part = getattr(course, 'direct_requests', 0) * 1.5

    predicted_demand = historical_part + direct_request_part

    return max(1, round(predicted_demand))


def calculate_required_groups(
    predicted_students: int,
    room_capacity: int,
    max_groups: int = 3,
) -> int:
    """
    محاسبه تعداد گروه‌های لازم بر اساس تعداد دانشجویان پیش‌بینی‌شده و ظرفیت اتاق.

    فرمول:
        required_groups = ceil(predicted_students / room_capacity)

    Args:
        predicted_students: تعداد دانشجویان پیش‌بینی‌شده
        room_capacity: ظرفیت هر اتاق (تعداد صندلی)
        max_groups: حداکثر تعداد گروه مجاز (پیش‌فرض ۳)

    Returns:
        تعداد گروه‌های مورد نیاز (بین ۱ تا max_groups)

    مثال:
        >>> calculate_required_groups(60, 30)
        2
        >>> calculate_required_groups(100, 30, 4)
        4
    """
    if predicted_students <= 0:
        return 1

    if room_capacity <= 0:
        return max_groups

    required_groups = math.ceil(predicted_students / room_capacity)

    return min(max(1, required_groups), max_groups)


# ============================================================
# تابع جدید: پیش‌بینی تقاضای گروهی
# ============================================================

def predict_demand_batch(course_ids: List[int], semester: str = "mehr") -> Dict[int, int]:
    """
    پیش‌بینی تقاضا برای چند درس به صورت همزمان

    Args:
        course_ids: لیست شناسه‌های دروس
        semester: کد ترم

    Returns:
        دیکشنری با کلید شناسه درس و مقدار تعداد دانشجویان پیش‌بینی شده
    """
    try:
        prediction_service = DemandPredictionService()
        result = {}

        for course_id in course_ids:
            if prediction_service.model is not None:
                demand = prediction_service.predict_demand(course_id, semester)
            else:
                # استفاده از روش ساده
                demand = 30 + (course_id % 20)
            result[course_id] = max(1, min(demand, 100))

        return result

    except Exception as e:
        logger.error(f"خطا در پیش‌بینی گروهی: {e}")
        return {course_id: 30 for course_id in course_ids}