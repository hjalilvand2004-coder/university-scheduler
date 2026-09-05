# app/models/schedule_version.py
class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"
    id = Column(Integer, primary_key=True)
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    status = Column(String(20))  # draft, published, archived
    total_score = Column(Float)  # امتیاز کلی این نسخه