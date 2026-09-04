# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback

from app.api.routes_schedule import router as schedule_router
from app.api.routes_courses import router as courses_router
from app.api.routes_charts import router as charts_router
from app.api.routes_professors_rooms import router as professors_rooms_router
from app.core.db_init import init_db
from app.api.routes_schedule_history import router as schedule_history_router
from app.api.routes_term_courses import router as term_courses_router
from app.api.routes_teaching_preferences import router as teaching_preferences_router
from app.api.routes_time_preferences import router as time_preferences_router
from app.api.routes_workflow import router as workflow_router
from app.api.routes_baskets import router as baskets_router
from app.api.routes_room_allocation import router as room_allocation_router
from app.api.routes_optimization import router as optimization_router

# ===== اضافه کردن روتر اسلات‌های زمانی =====
from app.services.schedule.slot_times import router as slot_times_router

from app.api import test_report

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== استفاده از lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 راه‌اندازی سامانه هوشمند برنامه‌ریزی درسی...")
    try:
        init_db()
        logger.info("✅ دیتابیس با موفقیت مقداردهی شد.")
    except Exception as e:
        logger.error(f"❌ خطا در مقداردهی دیتابیس: {e}")
        logger.error(traceback.format_exc())
    yield
    logger.info("🛑 سامانه در حال خاموش‌شدن...")


app = FastAPI(
    title="Intelligent University Scheduler",
    version="2.0.0",
    description="سامانه هوشمند برنامه‌ریزی درسی دانشگاهی با قابلیت گام‌به‌گام و مدیریت فرایند",
    lifespan=lifespan
)

# ===== CORS - تنظیمات کامل =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ===== ثبت روترها =====
app.include_router(courses_router, tags=["Courses"])
app.include_router(charts_router, tags=["Charts"])
app.include_router(professors_rooms_router, tags=["Professors & Rooms"])
app.include_router(term_courses_router, tags=["Term Courses"])
app.include_router(schedule_history_router, tags=["Schedule History"])
app.include_router(teaching_preferences_router, tags=["Teaching Preferences"])
app.include_router(time_preferences_router, tags=["Time Preferences"])
app.include_router(schedule_router, tags=["Schedule"])
app.include_router(workflow_router, tags=["Workflow"])
app.include_router(baskets_router, prefix="/api", tags=["Baskets"])
app.include_router(optimization_router, prefix="/api")
app.include_router(room_allocation_router)
app.include_router(test_report.router)

# ===== اضافه کردن روتر اسلات‌های زمانی =====
app.include_router(slot_times_router)

# ===== اندپوینت ریشه =====
@app.get("/")
def root():
    return {
        "service": "Intelligent University Scheduler",
        "version": app.version,
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
        }
    }

# ===== اندپوینت سلامت =====
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ===== مدیریت خطاهای عمومی =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ خطای سرور: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": "خطای داخلی سرور رخ داده است.",
            "error": str(exc)
        }
    )