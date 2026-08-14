// frontend/src/pages/OptimizationPage.jsx
import EditableDataTable from "../components/EditableDataTable";
import "./OptimizationPage.css";

export default function OptimizationPage({
  roomAllocationData,
  optimizedData,
  onProcess,
  onClear,
  loading,
}) {
  return (
    <div className="process-page optimization-page">
      <div className="process-header">
        <div className="process-title">
          <span className="process-icon">⚡</span>
          <h2>بهینه‌سازی برنامه</h2>
        </div>
        <p className="process-description">
          بهبود کیفیت برنامه با کاهش زمان‌های نامطلوب، تعادل روزها و استفاده بهتر از اتاق‌ها.
        </p>
      </div>
      <div className="process-body">
        <div className="controls-bar">
          <button
            onClick={onProcess}
            disabled={!roomAllocationData || loading}
            className="btn-process"
          >
            {loading ? "در حال اجرا..." : "بهینه‌سازی"}
          </button>
          {optimizedData && (
            <button onClick={onClear} className="btn-clear">
              پاک کردن نتایج
            </button>
          )}
        </div>
        {!roomAllocationData && (
          <div className="info-box info-warning">
            <span className="info-icon">⚠️</span>
            <p>لطفاً ابتدا تخصیص اتاق را انجام دهید.</p>
          </div>
        )}
        {optimizedData && (
          <div className="result-container">
            <EditableDataTable
              data={optimizedData}
              columns={[
                { key: "course_name", label: "درس" },
                { key: "instructor_name", label: "استاد" },
                { key: "day", label: "روز" },
                { key: "start", label: "شروع" },
                { key: "end", label: "پایان" },
                { key: "room_name", label: "اتاق" },
                { key: "group_number", label: "گروه" },
              ]}
              title="برنامه بهینه‌سازی شده"
              editable={false}
            />
            <div className="result-success">
              <p>✅ برنامه با موفقیت بهینه‌سازی شد.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}