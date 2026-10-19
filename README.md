# 🎓 سامانه هوشمند برنامه‌ریزی درسی دانشگاه

<div dir="rtl">

سامانه‌ای کامل برای تولید خودکار برنامه هفتگی کلاس‌های دانشگاه، مبتنی بر موتور بهینه‌سازی **Google OR-Tools (CP-SAT)** با رابط کاربری فارسی و راست‌به‌چپ.

> 🌐 **صفحه معرفی تعاملی سامانه** (بخش‌ها، فرایندها، فرم‌ها و منطق برنامه‌ریزی درسی): [docs/index.html](docs/index.html) — پس از فعال‌سازی GitHub Pages روی آدرس `https://hjalilvand2004-coder.github.io/university-scheduler/` در دسترس خواهد بود.

## ✨ امکانات

- 🚀 **تولید خودکار برنامه هفتگی** با الگوریتم بهینه‌سازی CP-SAT (عدم تداخل استاد/کلاس/گروه دانشجویی، رعایت ظرفیت، ترجیحات اساتید و...)
- 🔄 **فرایند گام‌به‌گام ۵ مرحله‌ای**: یکپارچه‌سازی دروس ترمیک → افزودن دروس گلوگاهی و پیش‌نیازها → امتیازدهی → زمان‌بندی → تخصیص کلاس
- 📦 مدیریت **سبدهای دروس** برای هر ترم
- 👨‍🏫 مدیریت اساتید، کلاس‌ها، دروس یکتا/ارائه/ترمیک، مطلوبیت‌های تدریس و زمان‌بندی
- 📊 داشبورد مدیریتی با نمودارهای آماری
- 🗳️ تعامل دانشجویی: پیشنهاد درس، نظرسنجی، امتیازدهی
- 📤 بارگذاری داده‌ها از فایل اکسل
- 📋 نمایش برنامه به دو صورت جدولی و شبکه هفتگی رنگی + خروجی

## 🖥️ اجرا به‌صورت قابل حمل (بدون نیاز به نصب هیچ‌چیز!)

**این روش برای رایانه‌ای که پایتون یا PyCharm ندارد، توصیه می‌شود:**

1. به بخش [Releases](../../releases) بروید و فایل `UniversityScheduler-Portable-win64.zip` را دانلود کنید
2. زیپ را استخراج کنید
3. `UniversityScheduler.exe` را اجرا کنید — مرورگر خودکار باز می‌شود ✅

> ✅ بدون Python | ✅ بدون Node.js | ✅ بدون اینترنت | 💾 دیتابیس در پوشه `data` کنار برنامه (قابل حمل روی فلش USB)

نسخه قابل حمل به‌صورت خودکار توسط [GitHub Actions](.github/workflows/build-portable.yml) ساخته می‌شود؛ کافی است برچسب جدید بزنید:

```bash
git tag v2.1.0
git push origin v2.1.0
```

## 🛠️ اجرا از سورس (حالت توسعه)

پیش‌نیازها: **Python 3.11+** و **Node.js 18+**

```bash
# ۱) بک‌اند
pip install -r backend/requirements.txt
python main.py
# → API روی http://127.0.0.1:8000 (مستندات: /docs)

# ۲) فرانت‌اند (ترمینال دوم)
cd frontend
npm install
npm run dev
# → رابط کاربری روی http://127.0.0.1:5173
```

> 💡 اگر `frontend/dist` از قبل ساخته شده باشد، `python main.py` به‌تنهایی **کل برنامه** (بک‌اند + رابط کاربری) را روی پورت 8000 سرو می‌کند.

## 🧪 تست‌ها

```bash
cd backend
DATABASE_URL="sqlite:///./university_scheduler.db" python -m pytest tests/ -v
```

## 🏗️ معماری

```
├── backend/                 # FastAPI + SQLAlchemy + OR-Tools
│   ├── app/
│   │   ├── api/             # مسیرهای REST (دروس، اساتید، سبد، ورک‌فلو، ...)
│   │   ├── models/          # مدل‌های ORM (21 جدول)
│   │   ├── services/
│   │   │   ├── schedule/    # ⭐ موتور اصلی: orchestrator، time_scheduler،
│   │   │   │                #   instructor_assigner، course_scorer، data_preparer
│   │   │   └── ...          # workflow_service، scheduler_service، optimization_service
│   │   ├── optimization/    # ⭐ حل‌کننده CP-SAT (solve_schedule با ۴ حالت هدف)
│   │   └── core/            # اتصال دیتابیس و مقداردهی اولیه
│   ├── university_scheduler.db   # دیتابیس نمونه (146 درس، 24 کلاس)
│   └── tests/               # تست‌های pytest
├── frontend/                # React 18 + Vite + recharts (RTL فارسی)
│   └── src/
│       ├── pages/           # داشبورد، سبدها، بهینه‌سازی، تخصیص کلاس، ...
│       ├── components/      # Sidebar، ScheduleTable، TimeSlotSelector، ...
│       └── api/             # کلاینت‌های axios (مسیر نسبی /api)
├── portable/                # ⭐ ساخت نسخه قابل حمل (PyInstaller)
│   ├── run_server.py        # نقطه ورود فایل اجرایی
│   └── scheduler_server.spec
└── .github/workflows/
    ├── build-portable.yml   # ⭐ ساخت و انتشار نسخه Portable در Releases
    └── test.yml             # اجرای تست‌ها
```

## 📌 سرو کردن رابط کاربری توسط بک‌اند

وقتی `frontend/dist` موجود باشد، بک‌اند به‌صورت خودکار آن را سرو می‌کند و کل برنامه روی یک پورت در دسترس است. مسیر پوشه را می‌توانید با متغیر محیطی `FRONTEND_DIST_DIR` نیز مشخص کنید.

## 🔧 عیب‌یابی رایج

| مشکل | راه‌حل |
|---|---|
| پورت 8000 اشغال است | نسخه Portable خودکار پورت بعدی را امتحان می‌کند؛ در حالت توسعه پورت را در `main.py` تغییر دهید |
| صفحه خالی است | مطمئن شوید `frontend/dist` ساخته شده یا از `npm run dev` استفاده کنید |
| خطای دیتابیس | متغیر محیطی `DATABASE_URL` را روی مسیر درست تنظیم کنید |

</div>
