# app/services/validation_service.py
class ValidationService:
    def __init__(self, db_session):
        self.db = db_session

    def validate_all(self, schedule_data: dict) -> ValidationResult:
        """اجرای تمام اعتبارسنجی‌ها بر اساس constraints.yaml"""
        errors = []
        warnings = []

        # بارگذاری قوانین از فایل constraints.yaml
        constraints = self._load_constraints()

        for constraint in constraints['hard_constraints']:
            validator = getattr(self, f"_validate_{constraint}")
            result = validator(schedule_data)
            if not result.is_valid:
                errors.append(result.error)

        for constraint in constraints['soft_constraints']:
            validator = getattr(self, f"_check_{constraint}")
            result = validator(schedule_data)
            if not result.is_met:
                warnings.append(result.message)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=self._calculate_score(schedule_data)
        )