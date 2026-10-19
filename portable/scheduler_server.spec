# -*- mode: python ; coding: utf-8 -*-
r"""
=====================================================================
 PyInstaller Spec — نسخه قابل حمل سامانه هوشمند برنامه‌ریزی درسی
=====================================================================
 ساخت روی ویندوز:
     cd backend
     pyinstaller ..\portable\scheduler_server.spec --noconfirm

 خروجی:
     backend/dist/UniversityScheduler/  →  کل پوشه قابل حمل
=====================================================================
"""
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = SPECPATH                           # پوشه portable/ (SPECPATH خودش پوشه است)
REPO_ROOT = os.path.dirname(SPEC_DIR)         # ریشه مخزن
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")   # پوشه backend/
ROOT_DIR = REPO_ROOT

# پوشه backend باید روی sys.path باشد تا پکیج app تحلیل شود
sys.path.insert(0, BACKEND_DIR)

FE_DIST = os.path.join(BACKEND_DIR, "frontend_dist")
SEED_DB = os.path.join(BACKEND_DIR, "university_scheduler.db")

datas = []
if os.path.isdir(FE_DIST):
    datas.append((FE_DIST, "frontend_dist"))
else:
    raise SystemExit(
        f"[!] پوشه {FE_DIST} پیدا نشد.\n"
        "    ابتدا فرانت‌اند را بسازید و dist را به backend/frontend_dist کپی کنید:\n"
        "    (این کار در GitHub Actions به‌صورت خودکار انجام می‌شود)"
    )
if os.path.exists(SEED_DB):
    datas.append((SEED_DB, "."))

hiddenimports = (
    collect_submodules("app")
    + [
        # --- uvicorn ---
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        # --- سرور ---
        "anyio._backends._asyncio",
        "sqlalchemy.dialects.sqlite",
        # --- مسیرهای API که به‌صورت داینامیک import می‌شوند ---
        "app.api.routes_optimization",
        "app.api.test_report",
    ]
    + collect_submodules("sklearn.utils._weighting")
)

a = Analysis(
    [os.path.join(SPEC_DIR, "run_server.py")],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ماژول‌های سنگین و بی‌استفاده برای کوچک‌ماندن حجم
        "torch",
        "matplotlib",
        "seaborn",
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "jupyter",
        "pytest",
        "pytest_html",
        "alembic",
        "asyncpg",
        "psycopg2",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UniversityScheduler",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # پنجره کنسول برای دیدن لاگ‌ها و خروج تمیز با Ctrl+C
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="UniversityScheduler",
)
