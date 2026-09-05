# app/models/schedule_change_log.py
class ScheduleChangeLog(Base):
    __tablename__ = "schedule_change_logs"
    id = Column(Integer, primary_key=True)
    schedule_version_id = Column(Integer, ForeignKey("schedule_versions.id"))
    action = Column(String(50))  # add, remove, move, swap
    course_id = Column(Integer, ForeignKey("courses.id"))
    old_room_id = Column(Integer, ForeignKey("rooms.id"))
    new_room_id = Column(Integer, ForeignKey("rooms.id"))
    old_time_slot = Column(String(50))
    new_time_slot = Column(String(50))
    reason = Column(Text)  # توضیح دلیل تغییر
    timestamp = Column(DateTime, default=datetime.utcnow)