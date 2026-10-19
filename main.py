# -*- coding: utf-8 -*-
"""
=====================================================================
 سامانه هوشمند برنامه‌ریزی درسی — اجرای حالت توسعه (Development)
=====================================================================
 استفاده:
     python main.py            →  سرور بک‌اند روی پورت 8000

 نکته: در حالت توسعه معمول دو ترمینال لازم است:
     ترمینال ۱:  python main.py                      (بک‌اند)
     ترمینال ۲:  cd frontend && npm run dev          (فرانت‌اند روی 5173)

 اگر پوشه frontend/dist موجود باشد، همین اسکریپت به‌تنهایی
 کل برنامه (بک‌اند + رابط کاربری) را روی یک پورت سرو می‌کند.
 برای ساخت نسخه قابل حمل ویندوز، فایل .github/workflows/build-portable.yml
 و پوشه portable/ را ببینید.
=====================================================================
"""
import os
import sys
import webbrowser
import threading

import uvicorn


def main() -> None:
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)

    # دیتابیس پیش‌فرض پروژه
    os.environ.setdefault("DATABASE_URL", "sqlite:///./university_scheduler.db")

    dist = os.path.join(os.path.dirname(backend_dir), "frontend", "dist")
    if os.path.isdir(os.path.join(dist, "assets")):
        os.environ["FRONTEND_DIST_DIR"] = dist
        url = "http://127.0.0.1:8000"
        hint = "رابط کاربری: http://127.0.0.1:8000  (frontend/dist یافت شد)"
    else:
        url = "http://127.0.0.1:5173"
        hint = (
            "frontend/dist یافت نشد؛ فقط API فعال است.\n"
            "  برای رابط کاربری: cd frontend && npm install && npm run dev\n"
            "  سپس: http://127.0.0.1:5173"
        )

    print("=" * 60)
    print("  Intelligent University Scheduler — Development Server")
    print("=" * 60)
    print(f"  {hint}")
    print(f"  مستندات API: http://127.0.0.1:8000/docs")
    print("=" * 60)

    threading.Timer(2.0, lambda: webbrowser.open(url)).start()

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
