# -*- coding: utf-8 -*-
"""
=====================================================================
 اجراکننده نسخه قابل حمل (Portable) — سامانه هوشمند برنامه‌ریزی درسی
=====================================================================
 این اسکریپت نقطه ورود ساخت فایل اجرایی با PyInstaller است.
 - سرور FastAPI + رابط کاربری ساخته‌شده را در یک پروسه اجرا می‌کند
 - دیتابیس را در کنار فایل اجرایی نگه می‌دارد (قابل حمل روی فلش!)
 - مرورگر را به‌صورت خودکار باز می‌کند
 - اگر پورت اشغال باشد، پورت بعدی را امتحان می‌کند
=====================================================================
"""
import os
import sys
import time
import shutil
import socket
import threading
import webbrowser


def app_base() -> str:
    """پوشه‌ای که فایل اجرایی (exe) در آن قرار دارد — برای ذخیره دیتابیس"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_base() -> str:
    """پوشه منابع باندل‌شده (frontend_dist، دیتابیس اولیه و ...)"""
    if getattr(sys, "frozen", False):
        # onedir: sys._MEIPASS به پوشه _internal اشاره می‌کند
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port(preferred: int = 8000, tries: int = 12) -> int:
    """پورت دلخواه را امتحان می‌کند؛ اگر اشغال بود پورت‌های بعدی"""
    port = preferred
    for _ in range(tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port  # آزاد است
        port += 1
    return preferred


def prepare_database() -> None:
    """
    دیتابیس را در پوشه data کنار exe آماده می‌کند.
    اگر اولین اجراست، دیتابیس نمونه (با داده‌های واقعی دانشگاه) کپی می‌شود.
    """
    data_dir = os.path.join(app_base(), "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "university_scheduler.db")

    if not os.path.exists(db_path):
        seed = os.path.join(resource_base(), "university_scheduler.db")
        if os.path.exists(seed):
            shutil.copy2(seed, db_path)
            print(f"[i] دیتابیس نمونه در {db_path} قرار گرفت.")
        else:
            print("[!] دیتابیس نمونه یافت نشد؛ دیتابیس خالی ساخته می‌شود.")

    # مسیر دیتابیس را برای app/core/database.py ست می‌کنیم
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # مسیر رابط کاربری ساخته‌شده
    fe = os.path.join(resource_base(), "frontend_dist")
    if os.path.isdir(fe):
        os.environ["FRONTEND_DIST_DIR"] = fe

    # مسیر کار برنامه را کنار exe می‌گذاریم تا لاگ‌ها و فایل‌های موقت آنجا باشند
    os.chdir(app_base())


def open_browser_later(url: str, delay: float = 2.2) -> None:
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
    print("=" * 62)
    print("  سامانه هوشمند برنامه‌ریزی درسی — نسخه قابل حمل")
    print("  Intelligent University Scheduler — Portable Edition")
    print("=" * 62)

    prepare_database()

    import uvicorn  # بعد از ست‌کردن env ها

    port = find_free_port(8000)
    url = f"http://127.0.0.1:{port}"
    print(f"[i] آدرس برنامه: {url}")
    print("[i] برای خروج، این پنجره را ببندید یا Ctrl+C بزنید.")
    print("-" * 62)

    open_browser_later(url)

    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
            # در حالت Portable ریلود نداریم
        )
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[!] خطا در اجرای سرور: {exc}")
        # پنجره نبسته بماند تا پیام دیده شود
        time.sleep(8)
        raise


if __name__ == "__main__":
    main()
