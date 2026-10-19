# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os
import traceback
from pathlib import Path
from sqlalchemy import inspect, text
from app.core.database import engine

from app.api import router as api_router


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
from app.services.schedule.slot_times import router as slot_times_router
from app.api import test_report
from app.api.routes_feedback import router as feedback_router

# ===== ایمپورت جدید: روتر مرکزی برای ویژگی‌های جدید =====
from app.api import router as api_router  # این شامل proposals, votes, ratings است

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== تابع برای اضافه کردن ستون‌های گم‌شده به دیتابیس =====
def ensure_missing_columns():
    """
    بررسی و اضافه کردن ستون‌های مورد نیاز به جداول موجود (برای SQLite)
    """
    required_columns = {
        "unique_courses": ["historical_demand", "avg_rating"],
        "offered_courses": ["preferred_instructors", "preferred_time_slots", "enrollment_count", "demand_prediction"],
    }

    with engine.connect() as conn:
        for table, columns in required_columns.items():
            # دریافت لیست ستون‌های موجود
            inspector = inspect(engine)
            existing_columns = [col['name'] for col in inspector.get_columns(table)]

            for col in columns:
                if col not in existing_columns:
                    # اضافه کردن ستون به جدول
                    try:
                        # نوع داده‌ها بر اساس نیاز: برای TEXT و FLOAT
                        if col in ["historical_demand", "avg_rating", "enrollment_count", "demand_prediction"]:
                            col_type = "FLOAT"
                        else:
                            col_type = "TEXT"

                        alter_sql = f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"
                        conn.execute(text(alter_sql))
                        conn.commit()
                        logger.info(f"✅ ستون '{col}' به جدول '{table}' اضافه شد.")
                    except Exception as e:
                        logger.error(f"❌ خطا در اضافه کردن ستون '{col}' به جدول '{table}': {e}")
                else:
                    logger.info(f"ℹ️ ستون '{col}' در جدول '{table}' وجود دارد.")


# ===== استفاده از lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 راه‌اندازی سامانه هوشمند برنامه‌ریزی درسی...")
    try:
        # مقداردهی اولیه دیتابیس (ایجاد جداول در صورت عدم وجود)
        init_db()
        logger.info("✅ دیتابیس با موفقیت مقداردهی شد.")

        # اضافه کردن ستون‌های گم‌شده (برای رفع خطای no such column)
        ensure_missing_columns()
        logger.info("✅ ساختار دیتابیس به‌روزرسانی شد.")

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

# ===== ثبت روترهای موجود =====
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
app.include_router(slot_times_router)
app.include_router(feedback_router)


# ===== ثبت روتر جدید برای ویژگی‌های پیشنهاد درس، نظرسنجی و امتیازدهی =====
# این روتر شامل مسیرهای /proposals, /votes, /ratings با پیشوند /api می‌باشد
app.include_router(api_router, prefix="/api")

# ===== اندپوینت ریشه =====
@app.get("/")
def root():
    # در حالت Portable، اگر رابط کاربری ساخته‌شده موجود باشد، آن را سرو کن
    if _FRONTEND_DIST:
        return FileResponse(_FRONTEND_DIST / "index.html")
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


# =====================================================================
# حالت Portable: سرو کردن رابط کاربری ساخته‌شده (frontend/dist)
# اگر پوشه dist وجود داشته باشد، فایل‌های استاتیک + SPA fallback فعال می‌شود
# و کل برنامه روی یک سرور (http://localhost:8000) قابل استفاده است.
# =====================================================================
def _find_frontend_dist() -> Path | None:
    """جستجوی پوشه dist رابط کاربری در مسیرهای معمول"""
    candidates = []
    env_dir = os.getenv("FRONTEND_DIST_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    base = Path(__file__).resolve().parent.parent.parent  # backend/
    candidates += [
        base / "frontend" / "dist",          # حالت توسعه از مخزن
        base / "frontend_dist",              # حالت Portable (کنار کد)
        Path.cwd() / "frontend" / "dist",    # اجرا از ریشه پروژه
        Path.cwd() / "frontend_dist",        # اجرا از کنار فایل exe
        Path.cwd() / "_internal" / "frontend_dist",  # حالت PyInstaller
        Path(getattr(sys, "_MEIPASS", "/nonexistent")) / "frontend_dist",  # PyInstaller onefile
    ]
    for c in candidates:
        try:
            if (c / "index.html").exists():
                return c
        except Exception:
            continue
    return None


import sys

_FRONTEND_DIST = _find_frontend_dist()

if _FRONTEND_DIST:
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        """سرو فایل‌های استاتیک یا بازگشت به index.html برای مسیرهای SPA"""
        # مسیرهای API هرگز نباید به index.html هدایت شوند
        if full_path == "api" or full_path.startswith("api/"):
            # بازسازی رفتار استاندارد FastAPI برای اسلش انتهایی
            # (مثلاً /api/baskets -> /api/baskets/)
            if not full_path.endswith("/"):
                return RedirectResponse(url=request.url.path + "/", status_code=307)
            raise HTTPException(status_code=404, detail="Not Found")
        if full_path:
            file_path = (_FRONTEND_DIST / full_path).resolve()
            # جلوگیری از path traversal
            if str(file_path).startswith(str(_FRONTEND_DIST.resolve())) and file_path.is_file():
                return FileResponse(file_path)
        return FileResponse(_FRONTEND_DIST / "index.html")

    logger.info(f"🌐 رابط کاربری وب از مسیر {_FRONTEND_DIST} سرو می‌شود (حالت تک‌سروری)")