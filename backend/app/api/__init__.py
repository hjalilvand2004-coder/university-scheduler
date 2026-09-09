from fastapi import APIRouter
from app.api.routes_proposals import router as proposals_router
from app.api.routes_votes import router as votes_router
from app.api.routes_ratings import router as ratings_router
from app.api.routes_vote_polls import router as vote_polls_router
from app.api.routes_schedule import router as schedule_router
from app.api.routes_courses import router as courses_router
from app.api.routes_professors_rooms import router as professors_rooms_router
from app.api.routes_schedule_history import router as schedule_history_router
from app.api.routes_term_courses import router as term_courses_router
from app.api.routes_teaching_preferences import router as teaching_preferences_router
from app.api.routes_time_preferences import router as time_preferences_router
from app.api.routes_workflow import router as workflow_router
from app.api.routes_baskets import router as baskets_router
from app.api.routes_room_allocation import router as room_allocation_router
from app.api.routes_optimization import router as optimization_router
from app.api.routes_feedback import router as feedback_router
from app.api import test_report
from app.services.schedule.slot_times import router as slot_times_router  # ← اضافه شد
from app.api.routes_charts import router as charts_router  # ← اضافه شد

router = APIRouter()
router.include_router(proposals_router)
router.include_router(votes_router)
router.include_router(ratings_router)
router.include_router(vote_polls_router)
router.include_router(schedule_router)
router.include_router(courses_router)
router.include_router(professors_rooms_router)
router.include_router(schedule_history_router)
router.include_router(term_courses_router)
router.include_router(teaching_preferences_router)
router.include_router(time_preferences_router)
router.include_router(workflow_router)
router.include_router(baskets_router)
router.include_router(room_allocation_router)
router.include_router(optimization_router)
router.include_router(feedback_router)
router.include_router(test_report.router)
router.include_router(slot_times_router)  # ← اضافه شد
router.include_router(charts_router)  # ← اضافه شد