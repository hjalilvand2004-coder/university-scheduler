import pytest
import json
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.schedule.orchestrator import ScheduleOrchestrator
from app.services.schedule.instructor_assigner import InstructorAssigner

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def sample_basket():
    with open(FIXTURES_DIR / "sample_basket.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session")
def sample_preferences():
    with open(FIXTURES_DIR / "sample_preferences.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def instructors_data(sample_preferences):
    return sample_preferences["instructors"]

@pytest.fixture
def teaching_prefs(sample_preferences):
    return sample_preferences["teaching_preferences"]

@pytest.fixture
def time_prefs(sample_preferences):
    return sample_preferences["time_preferences"]

@pytest.fixture
def mock_db():
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    return Session()

@pytest.fixture
def orchestrator(mock_db, instructors_data, teaching_prefs, time_prefs):
    with patch("app.services.schedule.orchestrator.InstructorLoader") as MockLoader:
        mock_loader = MockLoader.return_value
        # load() باید یک دیکشنری برگرداند
        mock_loader.load.return_value = {
            "instructors": instructors_data,
            "teaching_preferences": teaching_prefs,
            "time_preferences": time_prefs
        }
        # همچنین متدهای جداگانه را تنظیم می‌کنیم
        mock_loader.load_instructors.return_value = instructors_data
        mock_loader.load_teaching_preferences.return_value = teaching_prefs
        mock_loader.load_time_preferences.return_value = time_prefs

        orch = ScheduleOrchestrator(db=mock_db)
        return orch

@pytest.fixture
def assigned_courses(sample_basket, instructors_data, teaching_prefs):
    """دروس با استاد تخصیص‌یافته (برای تست زمان‌بندی)"""
    assigner = InstructorAssigner()
    # امضای متد: assign_instructors(courses, teaching_prefs, instructor_data)
    result = assigner.assign_instructors(
        courses=sample_basket,
        teaching_prefs=teaching_prefs,
        instructor_data=instructors_data
    )
    if isinstance(result, dict) and "assigned" in result:
        return result["assigned"]
    return result