# backend/check_db.py
import sqlite3
import json


def check_database():
    conn = sqlite3.connect('university_scheduler.db')
    cursor = conn.cursor()

    # دریافت لیست تمام جداول
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("=" * 60)
    print("📊 لیست جداول موجود در دیتابیس:")
    print("=" * 60)

    for table in tables:
        table_name = table[0]
        print(f"\n📋 جدول: {table_name}")
        print("-" * 40)

        # دریافت اطلاعات ستون‌ها
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        print(f"تعداد ستون‌ها: {len(columns)}")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''}")

        # تعداد رکوردها
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"تعداد رکوردها: {count}")

        # نمایش ۵ رکورد اول (اگر وجود داشته باشد)
        if count > 0:
            print("نمونه داده (۵ رکورد اول):")
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()
            col_names = [col[1] for col in columns]
            for row in rows:
                print(f"  {dict(zip(col_names, row))}")

    conn.close()


if __name__ == "__main__":
    check_database()