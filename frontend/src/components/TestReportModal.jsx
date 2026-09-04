// frontend/src/components/TestReportModal.jsx
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import './TestReportModal.css';

// ============================================================
// نگاشت نام تست‌ها به توضیحات و گروه‌بندی
// ============================================================
const TEST_METADATA = {
  // ===== Edge Cases =====
  'test_edge_cases.py::TestEdgeCases::test_empty_basket_in_assigner': {
    name: 'سبد خالی در تخصیص استاد',
    description: 'بررسی رفتار تخصیص استاد هنگام دریافت سبد خالی',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_empty_basket_in_scheduler': {
    name: 'سبد خالی در زمان‌بندی',
    description: 'بررسی رفتار زمان‌بندی هنگام دریافت سبد خالی',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_empty_basket_in_orchestrator': {
    name: 'سبد خالی در ارکستراتور',
    description: 'بررسی رفتار ارکستراتور هنگام دریافت سبد خالی',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_instructor_with_zero_max_units': {
    name: 'استاد با سقف واحد صفر',
    description: 'استادی که سقف واحد ۰ دارد نباید هیچ درسی بگیرد',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_instructor_with_one_unit_capacity': {
    name: 'استاد با ظرفیت ۱ واحد',
    description: 'استاد با سقف ۱ واحد فقط باید یک درس ۱ واحدی بگیرد',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_duplicate_teaching_preferences': {
    name: 'ترجیحات تدریس تکراری',
    description: 'تکرار ترجیح تدریس نباید باعث خطا یا تخصیص اضافی شود',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_duplicate_time_preferences': {
    name: 'ترجیحات زمانی تکراری',
    description: 'تکرار مطلوبیت زمانی نباید باعث خطا شود',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_course_with_zero_units': {
    name: 'درس با واحد صفر',
    description: 'درس با واحد ۰ باید به‌عنوان ۲ واحد در نظر گرفته شود',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_course_with_negative_units': {
    name: 'درس با واحد منفی',
    description: 'درس با واحد منفی باید به‌عنوان ۲ واحد در نظر گرفته شود',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_instructor_without_time_preference': {
    name: 'استاد بدون مطلوبیت زمانی',
    description: 'استاد بدون مطلوبیت زمانی باید با اسلات پیش‌فرض زمان‌بندی شود',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_no_teaching_preferences': {
    name: 'بدون ترجیح تدریس',
    description: 'هیچ ترجیح تدریسی وجود نداشته باشد، همه دروس باید unassigned شوند',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_invalid_day_in_time_preference': {
    name: 'روز نامعتبر در مطلوبیت زمانی',
    description: 'روز نامعتبر باید نادیده گرفته شود و خطا ندهد',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_multiple_groups_same_course': {
    name: 'چند گروه از یک درس',
    description: 'گروه‌های مختلف یک درس باید به اساتید مختلف تخصیص داده شوند',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '🧪'
  },
  'test_edge_cases.py::TestEdgeCases::test_large_basket_performance': {
    name: 'عملکرد با سبد بزرگ',
    description: 'سبد ۱۰۰ درسی باید در کمتر از ۵ ثانیه پردازش شود',
    module: 'سناریوهای لبه (Edge Cases)',
    icon: '⚡'
  },

  // ===== Instructor Assigner =====
  'test_instructor_assigner.py::TestInstructorAssigner::test_assign_instructors_basic': {
    name: 'تخصیص پایه استاد',
    description: 'بررسی تخصیص اولیه استاد و عدم نقض سقف واحد',
    module: 'تخصیص استاد (Instructor Assigner)',
    icon: '👨‍🏫'
  },
  'test_instructor_assigner.py::TestInstructorAssigner::test_priority_respected': {
    name: 'رعایت اولویت تدریس',
    description: 'اساتید با اولویت بالاتر بیشتر انتخاب شوند',
    module: 'تخصیص استاد (Instructor Assigner)',
    icon: '👨‍🏫'
  },
  'test_instructor_assigner.py::TestInstructorAssigner::test_unassigned_reason': {
    name: 'دلیل تخصیص‌نیافتگی',
    description: 'دروس تخصیص‌نیافته باید دارای دلیل معتبر باشند',
    module: 'تخصیص استاد (Instructor Assigner)',
    icon: '👨‍🏫'
  },
  'test_instructor_assigner.py::TestInstructorAssigner::test_assigner_handles_empty_basket': {
    name: 'سبد خالی در تخصیص‌دهنده',
    description: 'تخصیص‌دهنده با سبد خالی باید بدون خطا برگردد',
    module: 'تخصیص استاد (Instructor Assigner)',
    icon: '👨‍🏫'
  },

  // ===== Schedule Service (Orchestrator) =====
  'test_schedule_service.py::TestScheduleQuality::test_orchestrator_runs_without_error': {
    name: 'اجرای ارکستراتور بدون خطا',
    description: 'ارکستراتور باید بدون خطا اجرا شود و خروجی معتبر برگرداند',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_no_overlap_constraint': {
    name: 'عدم تداخل زمانی',
    description: 'هیچ تداخل زمانی بین کلاس‌های یک استاد در یک روز نباید وجود داشته باشد',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_teaching_preference_match': {
    name: 'تطابق تدریس',
    description: 'اساتید تخصیص‌یافته باید حداقل در اولویت‌های تدریس باشند (با تساهل)',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_time_preference_match': {
    name: 'تطابق زمانی',
    description: 'زمان تخصیص‌یافته باید با مطلوبیت‌های زمانی استاد تطابق داشته باشد (تساهل ۶۰ دقیقه)',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_max_units_respected': {
    name: 'رعایت سقف واحد',
    description: 'هیچ استادی نباید بیش از سقف واحد خود تخصیص داشته باشد',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_quality_score_threshold': {
    name: 'امتیاز کیفیت',
    description: 'امتیاز کیفیت کلی نباید از حد مشخصی پایین‌تر باشد (≥ ۷۰٪)',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_unassigned_courses_reasons': {
    name: 'دلایل تخصیص‌نیافتگی در ارکستراتور',
    description: 'دروس تخصیص‌نیافته باید دارای دلیل معتبر باشند',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },
  'test_schedule_service.py::TestScheduleQuality::test_balanced_distribution': {
    name: 'توزیع متوازن روزها',
    description: 'توزیع دروس بین روزها برای استاد ۵۲ باید متوازن باشد (حداقل ۲ روز)',
    module: 'ارکستراتور (Orchestrator)',
    icon: '🎯'
  },

  // ===== Time Scheduler =====
  'test_time_scheduler.py::TestTimeScheduler::test_time_scheduler_no_overlap': {
    name: 'عدم تداخل در زمان‌بندی',
    description: 'زمان‌بندی نباید تداخل زمانی برای هیچ استاد و روزی ایجاد کند',
    module: 'زمان‌بندی (Time Scheduler)',
    icon: '⏰'
  },
  'test_time_scheduler.py::TestTimeScheduler::test_time_preference_match': {
    name: 'تطابق زمانی در زمان‌بندی',
    description: 'کلاس‌ها تا حد امکان در بازه‌های مطلوب قرار گیرند (با تساهل ۶۰ دقیقه)',
    module: 'زمان‌بندی (Time Scheduler)',
    icon: '⏰'
  },
  'test_time_scheduler.py::TestTimeScheduler::test_fallback_mechanism': {
    name: 'مکانیزم Fallback',
    description: 'مکانیزم fallback باید دروس باقی‌مانده را تخصیص دهد',
    module: 'زمان‌بندی (Time Scheduler)',
    icon: '⏰'
  },
  'test_time_scheduler.py::TestTimeScheduler::test_max_units_respected_in_time_scheduling': {
    name: 'رعایت سقف واحد در زمان‌بندی',
    description: 'زمان‌بندی نباید بیش از سقف واحد به استاد درس بدهد',
    module: 'زمان‌بندی (Time Scheduler)',
    icon: '⏰'
  },
};

// ============================================================
// تابع کمکی برای استخراج کلید تست از nodeid
// ============================================================
function getTestKey(nodeid) {
  // nodeid معمولاً به شکل 'tests/test_file.py::TestClass::test_method'
  // ما بخش بعد از 'tests/' را به‌عنوان کلید استفاده می‌کنیم
  const parts = nodeid.split('::');
  if (parts.length >= 3) {
    // ترکیب نام فایل و کلاس و متد
    const file = parts[0].replace('tests/', '');
    const className = parts[1];
    const method = parts[2];
    return `${file}::${className}::${method}`;
  }
  return nodeid.replace('tests/', '');
}

// ============================================================
// کامپوننت اصلی
// ============================================================
const TestReportModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchReport();
    }
  }, [isOpen]);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('http://localhost:8000/api/test-report/');
      setReport(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'خطا در دریافت گزارش تست');
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // پردازش و گروه‌بندی تست‌ها
  // ============================================================
  const groupedTests = useMemo(() => {
    if (!report || !report.results) return {};

    const groups = {};
    report.results.forEach(test => {
      const key = getTestKey(test.nodeid);
      const metadata = TEST_METADATA[key] || {
        name: test.nodeid.split('::').pop() || test.nodeid,
        description: 'توضیحی برای این تست ثبت نشده است',
        module: 'سایر',
        icon: '📌'
      };

      const moduleName = metadata.module;
      if (!groups[moduleName]) {
        groups[moduleName] = [];
      }
      groups[moduleName].push({
        ...test,
        ...metadata,
        displayKey: key,
      });
    });

    // مرتب‌سازی هر گروه بر اساس نام تست
    Object.keys(groups).forEach(module => {
      groups[module].sort((a, b) => a.name.localeCompare(b.name));
    });

    return groups;
  }, [report]);

  // ============================================================
  // فیلتر بر اساس جستجو
  // ============================================================
  const filteredGroups = useMemo(() => {
    if (!searchTerm.trim()) return groupedTests;

    const term = searchTerm.trim().toLowerCase();
    const result = {};
    Object.keys(groupedTests).forEach(module => {
      const filtered = groupedTests[module].filter(test =>
        test.name.toLowerCase().includes(term) ||
        test.description.toLowerCase().includes(term) ||
        test.module.toLowerCase().includes(term)
      );
      if (filtered.length > 0) {
        result[module] = filtered;
      }
    });
    return result;
  }, [groupedTests, searchTerm]);

  // ============================================================
  // رندر
  // ============================================================
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>📊 گزارش تست‌ها</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {loading && <div className="loading-spinner">در حال بارگذاری...</div>}
          {error && <div className="error-message">❌ {error}</div>}

          {report && (
            <>
              {/* کارت‌های آماری */}
              <div className="stats-grid">
                <div className="stat-card total">
                  <span className="stat-label">مجموع تست‌ها</span>
                  <span className="stat-value">{report.total}</span>
                </div>
                <div className="stat-card passed">
                  <span className="stat-label">✅ موفق</span>
                  <span className="stat-value">{report.passed}</span>
                </div>
                <div className="stat-card failed">
                  <span className="stat-label">❌ شکست‌خورده</span>
                  <span className="stat-value">{report.failed}</span>
                </div>
                <div className="stat-card duration">
                  <span className="stat-label">⏱️ زمان اجرا</span>
                  <span className="stat-value">{report.duration.toFixed(2)}s</span>
                </div>
              </div>

              {/* نوار جستجو */}
              <div className="search-bar">
                <input
                  type="text"
                  placeholder="🔍 جستجو در تست‌ها (نام، توضیح، ماژول)..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                {searchTerm && (
                  <button
                    className="search-clear"
                    onClick={() => setSearchTerm('')}
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* نمایش گروه‌بندی شده */}
              <div className="test-results">
                {Object.keys(filteredGroups).length === 0 ? (
                  <div className="no-result">نتیجه‌ای برای جستجوی "{searchTerm}" یافت نشد.</div>
                ) : (
                  Object.keys(filteredGroups).map(module => (
                    <div key={module} className="module-group">
                      <h4 className="module-title">📂 {module}</h4>
                      <div className="table-responsive">
                        <table className="test-table">
                          <thead>
                            <tr>
                              <th style={{ width: '30%' }}>نام تست</th>
                              <th style={{ width: '45%' }}>توضیح</th>
                              <th style={{ width: '15%' }}>وضعیت</th>
                              <th style={{ width: '10%' }}>زمان (ثانیه)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredGroups[module].map((test, idx) => (
                              <tr key={idx} className={`status-${test.outcome}`}>
                                <td>
                                  <span className="test-icon">{test.icon}</span>
                                  <span className="test-name">{test.name}</span>
                                </td>
                                <td className="test-description">{test.description}</td>
                                <td>
                                  <span className={`badge badge-${test.outcome}`}>
                                    {test.outcome === 'passed' && '✅ موفق'}
                                    {test.outcome === 'failed' && '❌ شکست'}
                                    {test.outcome === 'skipped' && '⏭️ رد شده'}
                                    {test.outcome === 'error' && '⚠️ خطا'}
                                  </span>
                                </td>
                                <td>{test.duration.toFixed(3)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn-close">بستن</button>
        </div>
      </div>
    </div>
  );
};

export default TestReportModal;