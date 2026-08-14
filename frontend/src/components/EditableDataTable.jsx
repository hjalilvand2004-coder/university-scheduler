// frontend/src/components/EditableDataTable.jsx
import React, { useState, useRef, useEffect } from "react";
import "./EditableDataTable.css";

/**
 * کامپوننت جدول قابل ویرایش با قابلیت تغییر عرض ستون‌ها با کشیدن
 * و پشتیبانی از wrap text برای نمایش کامل عناوین
 *
 * @param {Array} data - داده‌های جدول
 * @param {Array} columns - تعریف ستون‌ها با کلید و برچسب و خصوصیات (isCheckbox, render)
 * @param {string} title - عنوان جدول
 * @param {Function} onUpdateRow - تابع به‌روزرسانی سطر (اختیاری)
 * @param {Function} onDeleteRow - تابع حذف سطر (اختیاری)
 * @param {boolean} editable - آیا جدول قابل ویرایش است (فعال/غیرفعال کردن چک‌باکس‌ها)
 * @param {Function} onToggleCheck - تابع تغییر وضعیت چک‌باکس (اختیاری)
 */
export default function EditableDataTable({
  data,
  columns,
  title,
  onUpdateRow,
  onDeleteRow,
  editable,
  onToggleCheck,
}) {
  // اطمینان از اینکه data همیشه آرایه است
  let dataArray = data;
  if (!Array.isArray(data)) {
    if (data && typeof data === "object") {
      dataArray = [data];
    } else {
      dataArray = [];
    }
  }

  // ستون‌های اضافی (دکمه حذف)
  const extraColumns = [];
  if (editable && onDeleteRow) {
    extraColumns.push({
      key: "delete",
      label: "حذف",
      render: (row, index) => (
        <button
          className="btn-delete-row"
          onClick={() => {
            const courseName = row.course_name || row.course_title || row.name || "این آیتم";
            if (window.confirm(`آیا از حذف "${courseName}" مطمئن هستید؟`)) {
              onDeleteRow(index);
            }
          }}
          title="حذف"
          aria-label="حذف ردیف"
        >
          ❌
        </button>
      ),
    });
  }

  const allColumns = [...columns, ...extraColumns];

  // وضعیت برای عرض ستون‌ها (مقدار اولیه از localStorage یا پیش‌فرض)
  const [columnWidths, setColumnWidths] = useState(() => {
    const saved = localStorage.getItem("editableTableColumnWidths");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // فقط کلیدهایی که در allColumns وجود دارند را نگه دار
        const validWidths = {};
        allColumns.forEach((col) => {
          if (parsed[col.key] !== undefined) {
            validWidths[col.key] = parsed[col.key];
          }
        });
        return validWidths;
      } catch {
        return {};
      }
    }
    // مقدار پیش‌فرض برای ستون‌ها (برای نمایش بهتر عناوین)
    const defaultWidths = {};
    allColumns.forEach((col) => {
      if (col.key === "course_name" || col.key === "unique_code" || col.key === "level") {
        defaultWidths[col.key] = 150;
      } else if (col.key === "from_termic" || col.key === "from_prerequisite" || col.key === "from_student_demand" || col.key === "from_manager") {
        defaultWidths[col.key] = 80;
      } else if (col.key === "estimated_capacity" || col.key === "units") {
        defaultWidths[col.key] = 80;
      } else if (col.key === "required_classes") {
        defaultWidths[col.key] = 90;
      } else if (col.key === "course_type") {
        defaultWidths[col.key] = 80;
      } else if (col.key === "term") {
        defaultWidths[col.key] = 60;
      } else {
        defaultWidths[col.key] = 100;
      }
    });
    return defaultWidths;
  });

  // ذخیره در localStorage هنگام تغییر
  useEffect(() => {
    localStorage.setItem("editableTableColumnWidths", JSON.stringify(columnWidths));
  }, [columnWidths]);

  // مرجع برای جدول
  const tableRef = useRef(null);

  // حالت کشیدن
  const [isDragging, setIsDragging] = useState(false);
  const [dragColumnKey, setDragColumnKey] = useState(null);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(0);

  // شروع کشیدن
  const handleMouseDown = (e, colKey) => {
    e.preventDefault();
    const th = e.target.closest("th");
    if (!th) return;

    const currentWidth = th.offsetWidth;
    setIsDragging(true);
    setDragColumnKey(colKey);
    setStartX(e.clientX);
    setStartWidth(currentWidth);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  // حرکت موس
  const handleMouseMove = (e) => {
    if (!isDragging || !dragColumnKey) return;
    const delta = e.clientX - startX;
    // برای راست‌چین (چون جهت RTL است، علامت برعکس است)
    const newWidth = Math.max(90, startWidth - delta); // حداقل عرض ۹۰ پیکسل
    setColumnWidths((prev) => ({
      ...prev,
      [dragColumnKey]: newWidth,
    }));
  };

  // پایان کشیدن
  const handleMouseUp = () => {
    setIsDragging(false);
    setDragColumnKey(null);
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  // نمایش پیام خالی
  if (!dataArray || dataArray.length === 0) {
    return (
      <div className="data-table-wrapper empty">
        <div className="empty-state">
          <span className="empty-icon">📭</span>
          <p className="no-data">هیچ داده‌ای برای نمایش وجود ندارد.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="data-table-wrapper">
      {title && <h4 className="table-title">{title}</h4>}
      <div className="table-scroll">
        <table className="workflow-table" ref={tableRef}>
          <colgroup>
            {allColumns.map((col) => (
              <col
                key={col.key}
                style={{
                  width: columnWidths[col.key] || "auto",
                  minWidth: columnWidths[col.key] || "90px",
                }}
              />
            ))}
          </colgroup>
          <thead>
            <tr>
              {allColumns.map((col) => (
                <th
                  key={col.key}
                  className="resizable-header"
                  style={{
                    position: "relative",
                    userSelect: "none",
                  }}
                >
                  <span className="th-content">{col.label}</span>
                  <span
                    className="resize-handle"
                    onMouseDown={(e) => handleMouseDown(e, col.key)}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "8px",
                      height: "100%",
                      cursor: "col-resize",
                      background: isDragging && dragColumnKey === col.key ? "rgba(99, 102, 241, 0.5)" : "transparent",
                      transition: "background 0.15s",
                      zIndex: 10,
                    }}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataArray.map((row, index) => (
              <tr key={index}>
                {allColumns.map((col) => {
                  if (col.render) {
                    return <td key={col.key}>{col.render(row, index)}</td>;
                  }
                  if (col.isCheckbox) {
                    return (
                      <td key={col.key} className="checkbox-cell">
                        <input
                          type="checkbox"
                          checked={!!row[col.key]}
                          onChange={(e) => {
                            const newRow = { ...row, [col.key]: e.target.checked };
                            if (onToggleCheck) {
                              onToggleCheck(index, col.key, e.target.checked);
                            }
                            if (onUpdateRow) {
                              onUpdateRow(index, newRow);
                            }
                          }}
                          className="modern-checkbox"
                          disabled={!editable}
                          aria-label={`انتخاب ${col.label}`}
                        />
                      </td>
                    );
                  }
                  let value = row[col.key];
                  if (typeof value === "boolean") {
                    return <td key={col.key}>{value ? "✅" : "❌"}</td>;
                  }
                  if (typeof value === "object" && value !== null) {
                    value = JSON.stringify(value);
                  }
                  return <td key={col.key}>{value ?? "—"}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>تعداد رکوردها: {dataArray.length}</span>
      </div>
    </div>
  );
}