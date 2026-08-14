# check_frequency.py
import sqlite3
import pandas as pd

conn = sqlite3.connect('university_scheduler.db')
query = """
SELECT 
    sh.ref_unique_course_code,
    
    sh.semester,
    COUNT(*) as frequency
FROM schedule_history sh
WHERE sh.ref_unique_course_code IS NOT NULL
GROUP BY sh.ref_unique_course_code, sh.semester
ORDER BY sh.ref_unique_course_code, sh.semester;
"""
df = pd.read_sql_query(query, conn)
print(df)
conn.close()