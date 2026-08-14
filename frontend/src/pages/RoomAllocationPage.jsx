// frontend/src/pages/RoomAllocationPage.jsx
import EditableDataTable from "../components/EditableDataTable";
import "./RoomAllocationPage.css";

export default function RoomAllocationPage({
  instructorTimeData,
  roomAllocationData,
  onProcess,
  onClear,
  loading,
  onNext,
}) {
  return (
    <div className="process-page room-allocation-page">
      <div className="process-header">
        <div className="process-title">
          <span className="process-icon">🏢</span>
          <h2>تخصیص اتاق</h2>
        </div>
        <p className="process-description">
          تخصیص اتاق‌های مناسب با در نظر گرفتن ظرفیت، نوع، تجهیزات و عدم تداخل هم‌زمان.
        </p>
      </div>
      <div className="process-body">
        <div className="controls-bar">
          <button
            onClick={onProcess}
            disabled={!instructorTimeData || loading}
            className="btn-process"
          >
            {loading ? "در حال اجرا..." : "تخصیص اتاق"}
          </button>
          {roomAllocationData && (
            <button onClick={onClear} className="btn-clear">
              پاک کردن نتایج
            </button>
          )}
        </div>
        {!instructorTimeData && (
          <div className="info-box info-warning">
            <span className="info-icon">⚠️</span>
            <p>لطفاً ابتدا زمان‌بندی را انجام دهید.</p>
          </div>
        )}
        {roomAllocationData && (
          <div className="result-container">
            <EditableDataTable
              data={roomAllocationData}
              columns={[
                { key: "course_name", label: "درس" },
                { key: "instructor_name", label: "استاد" },
                { key: "day", label: "روز" },
                { key: "start", label: "شروع" },
                { key: "end", label: "پایان" },
                { key: "room_name", label: "اتاق" },
                { key: "capacity", label: "ظرفیت" },
                { key: "group_number", label: "گروه" },
              ]}
              title="برنامه نهایی با اتاق"
              editable={false}
            />
            <div className="result-actions">
              <button onClick={onNext} className="btn-primary" disabled={loading}>
                {loading ? "در حال..." : "⚡ مرحله بعد: بهینه‌سازی"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}