// frontend/src/pages/BasketPage.jsx
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import EditableDataTable from "../components/EditableDataTable";
import { getInitialBasket, addStatisticsToBasket } from "../api/workflowApi";
import "./BasketPage.css";

// ============================================================
// کامپوننت مودال ایجاد سبد جدید (مشترک)
// ============================================================
function CreateBasketModal({ onClose, onBasketCreated }) {
  const [title, setTitle] = useState("");
  const [semester, setSemester] = useState("mehr");
  const [year, setYear] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("لطفاً عنوان سبد را وارد کنید.");
      return;
    }
    if (!year.trim()) {
      setError("لطفاً سال را وارد کنید.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await axios.post("http://localhost:8000/api/baskets/", {
        title: title.trim(),
        semester,
        year: year.trim(),
      });
      const newBasket = res.data;
      if (onBasketCreated) onBasketCreated(newBasket.id);
      onClose();
    } catch (err) {
      setError("خطا در ایجاد سبد: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>➕ ایجاد سبد جدید</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="form-error">{error}</div>}
            <div className="form-group">
              <label>عنوان سبد</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="مثلاً سبد ترم مهر ۱۴۰۳"
                required
              />
            </div>
            <div className="form-group">
              <label>ترم</label>
              <select value={semester} onChange={(e) => setSemester(e.target.value)}>
                <option value="mehr">مهر</option>
                <option value="bahman">بهمن</option>
              </select>
            </div>
            <div className="form-group">
              <label>سال</label>
              <input
                type="text"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                placeholder="مثلاً ۱۴۰۳"
                required
              />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              انصراف
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "در حال ایجاد..." : "ایجاد سبد"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// کامپوننت انتخاب سبد (لیست سبدهای موجود به صورت جدول)
// ============================================================
function BasketSelector({ onSelectBasket }) {
  const [baskets, setBaskets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchBaskets = async () => {
    setLoading(true);
    try {
      const res = await axios.get("http://localhost:8000/api/baskets");
      setBaskets(res.data);
    } catch (err) {
      setError("خطا در دریافت لیست سبدها");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBaskets();
  }, []);

  const handleBasketCreated = (newBasketId) => {
    onSelectBasket(newBasketId);
    fetchBaskets();
  };

  if (loading) return <div className="loading-state">در حال بارگذاری سبدها...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="basket-selector">
      <div className="selector-header">
        <h3>📋 انتخاب سبد دروس</h3>
        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
          ➕ ایجاد سبد جدید
        </button>
      </div>
      {baskets.length === 0 ? (
        <div className="empty-state">
          <p>هیچ سبدی وجود ندارد. برای شروع، یک سبد جدید ایجاد کنید.</p>
        </div>
      ) : (
        <div className="basket-table-container">
          <table className="basket-table">
            <thead>
              <tr>
                <th>عنوان سبد</th>
                <th>ترم</th>
                <th>سال</th>
                <th>تاریخ ایجاد</th>
                <th>تعداد دروس</th>
                <th>عملیات</th>
              </tr>
            </thead>
            <tbody>
              {baskets.map((basket) => (
                <tr key={basket.id}>
                  <td className="basket-title">{basket.title}</td>
                  <td>{basket.semester === "mehr" ? "مهر" : "بهمن"}</td>
                  <td>{basket.year}</td>
                  <td>{new Date(basket.created_at).toLocaleDateString('fa-IR')}</td>
                  <td className="item-count">{basket.items?.length || 0}</td>
                  <td>
                    <button
                      onClick={() => onSelectBasket(basket.id)}
                      className="btn-view-details"
                    >
                      مشاهده جزئیات
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreateModal && (
        <CreateBasketModal
          onClose={() => setShowCreateModal(false)}
          onBasketCreated={handleBasketCreated}
        />
      )}
    </div>
  );
}

// ============================================================
// کامپوننت اصلی سبد (Wizard)
// ============================================================
function BasketWizard({
  semester,
  levels,
  onComplete,
  loading,
  uniqueCourses,
  termCourses,
  workflowId,
  initialBasketData,
  basketId: propBasketId,
  onBasketCreated,
}) {
  const [fullData, setFullData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedClasses, setExpandedClasses] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingFromDb, setIsLoadingFromDb] = useState(false);
  const [basketId, setBasketId] = useState(propBasketId);
  const [basketMeta, setBasketMeta] = useState({ title: "", semester: "", year: "" });

  const loadingRef = useRef(false);
  const initialLoadDone = useRef(false);

  // ----- حالت‌های مودال افزودن رکورد -----
  const [showModal, setShowModal] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [selectedLevel, setSelectedLevel] = useState("");
  const [availableLevels, setAvailableLevels] = useState([]);
  const [formError, setFormError] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  // استخراج مقاطع
  useEffect(() => {
    if (termCourses?.length) {
      setAvailableLevels([...new Set(termCourses.map(tc => tc.level))]);
    }
  }, [termCourses]);

  // ============================================================
  // تابع بارگذاری سبد از دیتابیس
  // ============================================================
  const loadBasketFromDb = async (force = false) => {
    if (loadingRef.current && !force) return;
    loadingRef.current = true;

    if (basketId) {
      setIsLoadingFromDb(true);
      setError(null);
      try {
        console.log(`📥 بارگذاری سبد با basketId: ${basketId}`);
        const response = await axios.get(`http://localhost:8000/api/baskets/${basketId}`);
        const basket = response.data;
        console.log("✅ پاسخ دریافتی:", basket);
        setBasketMeta({
          title: basket.title || "",
          semester: basket.semester || "",
          year: basket.year || "",
        });
        const items = basket.items || [];
        if (items.length > 0) {
          processBasketData(items);
        } else {
          setFullData([]);
          setExpandedClasses(null);
        }
      } catch (error) {
        console.error("❌ خطا در بارگذاری سبد:", error);
        if (error.response?.status === 404) {
          setFullData(null);
          setExpandedClasses(null);
          setBasketId(null);
          setBasketMeta({ title: "", semester: "", year: "" });
        } else {
          setError("خطا در بارگذاری سبد: " + (error.response?.data?.detail || error.message));
        }
      } finally {
        setIsLoadingFromDb(false);
        loadingRef.current = false;
        initialLoadDone.current = true;
      }
      return;
    }

    if (workflowId) {
      setIsLoadingFromDb(true);
      setError(null);
      try {
        console.log(`📥 بارگذاری سبد با workflowId: ${workflowId}`);
        const response = await axios.get(
          `http://localhost:8000/api/schedule/workflow/basket/${workflowId}`
        );
        const data = response.data;
        console.log("✅ پاسخ دریافتی:", data);
        const basketData = data.basket || data;
        if (data.basket_meta) {
          setBasketMeta(data.basket_meta);
        } else {
          setBasketMeta({ title: "", semester: semester || "", year: "1403" });
        }
        if (basketData && basketData.length > 0) {
          processBasketData(basketData);
        } else {
          setFullData([]);
          setExpandedClasses(null);
        }
      } catch (error) {
        console.error("❌ خطا در بارگذاری سبد:", error);
        if (error.response?.status === 404) {
          setFullData(null);
          setExpandedClasses(null);
        } else {
          setError("خطا در بارگذاری سبد: " + (error.response?.data?.detail || error.message));
        }
      } finally {
        setIsLoadingFromDb(false);
        loadingRef.current = false;
        initialLoadDone.current = true;
      }
      return;
    }

    if (initialBasketData && initialBasketData.length > 0) {
      console.log("📦 استفاده از داده اولیه (initialBasketData)");
      processBasketData(initialBasketData);
      loadingRef.current = false;
      initialLoadDone.current = true;
      return;
    }

    setFullData(null);
    setExpandedClasses(null);
    loadingRef.current = false;
    initialLoadDone.current = true;
  };

  // ============================================================
  // پردازش داده‌های دریافتی
  // ============================================================
  const processBasketData = (basketData) => {
    const hasGroups = basketData.some(item => item.group_number && item.group_number > 0);

    if (hasGroups) {
      setExpandedClasses(basketData);
      const uniqueMap = new Map();
      basketData.forEach(item => {
        const key = `${item.unique_code}_${item.level}_${item.term}`;
        if (!uniqueMap.has(key)) {
          const { group_number, ...rest } = item;
          const count = basketData.filter(
            i => `${i.unique_code}_${i.level}_${i.term}` === key
          ).length;
          uniqueMap.set(key, { ...rest, required_classes: count });
        }
      });
      setFullData(Array.from(uniqueMap.values()));
    } else {
      setFullData(basketData);
      setExpandedClasses(null);
    }
  };

  // ============================================================
  // بارگذاری اولیه و تغییر basketId
  // ============================================================
  useEffect(() => {
    if ((basketId || workflowId || (initialBasketData && initialBasketData.length > 0)) && !initialLoadDone.current) {
      loadBasketFromDb();
    }
  }, []);

  useEffect(() => {
    if (basketId && initialLoadDone.current) {
      initialLoadDone.current = false;
      loadBasketFromDb();
    }
  }, [basketId]);

  // ============================================================
  // حذف سبد
  // ============================================================
  const clearBasket = async () => {
    if (!basketId && !workflowId) {
      setFullData(null);
      setExpandedClasses(null);
      if (onComplete) onComplete([]);
      return;
    }

    if (!window.confirm("آیا از حذف کامل سبد دروس اطمینان دارید؟")) return;

    try {
      if (basketId) {
        await axios.delete(`http://localhost:8000/api/baskets/${basketId}`);
        setBasketId(null);
        setBasketMeta({ title: "", semester: "", year: "" });
        if (onBasketCreated) onBasketCreated(null);
      } else if (workflowId) {
        await axios.delete(`http://localhost:8000/api/schedule/workflow/basket/${workflowId}`);
      }
      setFullData(null);
      setExpandedClasses(null);
      if (onComplete) onComplete([]);
      alert("سبد دروس با موفقیت حذف شد.");
    } catch (error) {
      console.error("❌ خطا در حذف سبد:", error);
      setError("خطا در حذف سبد: " + (error.response?.data?.detail || error.message));
    }
  };

  // ============================================================
  // دریافت لیست دروس (ایجاد سبد جدید)
  // ============================================================
  const handleFetchData = async () => {
    if (!basketId) {
      setError("هیچ سبدی انتخاب نشده است. لطفاً ابتدا یک سبد ایجاد یا انتخاب کنید.");
      return;
    }

    if (!basketMeta.year) {
      setError("سال سبد مشخص نیست. لطفاً سبد را مجدداً بارگذاری کنید.");
      return;
    }

    if (fullData?.length) {
      if (!window.confirm("سبد موجود قبلاً ایجاد شده است. آیا می‌خواهید سبد جدیدی ایجاد کنید؟ سبد قبلی حذف خواهد شد.")) {
        return;
      }
      await clearBasket();
    }

    setIsLoading(true);
    setError(null);
    try {
      const initialResult = await getInitialBasket({
        semester: basketMeta.semester || semester,
        levels,
        year: basketMeta.year,
      });
      const initialData = initialResult.basket || initialResult;
      if (!initialData?.length) {
        setError("هیچ درسی برای این ترم و مقاطع پیدا نشد.");
        setIsLoading(false);
        return;
      }

      const statsResult = await addStatisticsToBasket({ basket: initialData });
      const statsData = statsResult.basket || statsResult;
      if (!statsData?.length) {
        setError("پاسخ سرور برای آمار خالی است.");
        setIsLoading(false);
        return;
      }

      const merged = statsData.map((item, idx) => ({
        ...initialData[idx],
        ...item,
      }));

      setFullData(merged);
      setExpandedClasses(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // ============================================================
  // ذخیره‌سازی سبد (فقط در صورتی که basketId وجود داشته باشد)
  // ============================================================
  const saveBasketToServer = async (classes) => {
    if (!classes?.length) return;

    if (!basketId) {
      setError("هیچ سبدی انتخاب نشده است. لطفاً ابتدا یک سبد ایجاد یا انتخاب کنید.");
      return;
    }

    setIsSaving(true);
    try {
      // حذف آیتم‌های قبلی
      try {
        await axios.delete(`http://localhost:8000/api/baskets/${basketId}/items`);
      } catch (e) {
        console.warn("حذف آیتم‌های قبلی ممکن است پشتیبانی نشود، ادامه می‌دهیم.");
      }

      // اضافه کردن آیتم‌های جدید - فیلدهای ناخواسته را حذف می‌کنیم
      for (const item of classes) {
        // فقط فیلدهای مورد نیاز را نگه می‌داریم
        const { basket_id, id, created_at, updated_at, ...cleanItem } = item;
        await axios.post(`http://localhost:8000/api/baskets/${basketId}/items`, cleanItem);
      }

      console.log("✅ سبد با موفقیت ذخیره شد");
      // بارگذاری مجدد
      initialLoadDone.current = false;
      await loadBasketFromDb(true);
    } catch (error) {
      console.error("❌ خطا در ذخیره سبد:", error);
      const msg = error.response?.data?.detail || error.message;
      setError(`خطا در ذخیره‌سازی: ${msg}`);
      alert(`خطا در ذخیره‌سازی: ${msg}`);
    } finally {
      setIsSaving(false);
    }
  };

  // ============================================================
  // تولید کلاس‌ها
  // ============================================================
  const handleGenerateClasses = async () => {
    if (!fullData?.length) {
      setError("ابتدا لیست دروس را دریافت کنید.");
      return;
    }

    if (expandedClasses?.length) {
      if (!window.confirm("کلاس‌ها قبلاً تولید شده‌اند. آیا می‌خواهید دوباره تولید کنید؟ رکوردهای قبلی بازنویسی می‌شوند.")) {
        return;
      }
    }

    const classes = [];
    fullData.forEach(course => {
      const count = course.required_classes || 1;
      for (let i = 1; i <= count; i++) {
        // حذف فیلدهای ناخواسته از course
        const { basket_id, id, created_at, updated_at, ...cleanCourse } = course;
        classes.push({ ...cleanCourse, group_number: i });
      }
    });

    setExpandedClasses(classes);
    await saveBasketToServer(classes);
    if (onComplete) onComplete(classes);
  };

  // ============================================================
  // توابع مدیریت جدول
  // ============================================================
  const handleToggleManager = (index, key, checked) => {
    if (!fullData) return;
    const newData = [...fullData];
    newData[index][key] = checked;
    setFullData(newData);
  };

  const handleDeleteRow = (index) => {
    if (!fullData) return;
    setFullData(fullData.filter((_, i) => i !== index));
  };

  const handleUpdateRequiredClasses = (index, newValue) => {
    if (!fullData) return;
    const newData = [...fullData];
    newData[index].required_classes = parseInt(newValue, 10) || 0;
    setFullData(newData);
  };

  // ============================================================
  // افزودن رکورد
  // ============================================================
  const handleAddRecord = async () => {
    if (!selectedCourse || !selectedLevel) {
      setFormError("لطفاً درس و مقطع را انتخاب کنید.");
      return;
    }

    const termCourse = termCourses.find(
      tc => tc.unique_course_code === selectedCourse && tc.level === selectedLevel
    );
    if (!termCourse) {
      setFormError("اطلاعات درس برای این مقطع یافت نشد.");
      return;
    }

    const uniqueCourse = uniqueCourses.find(uc => uc.code === selectedCourse);
    const estimatedCapacity = uniqueCourse?.estimated_capacity || 0;
    const hasPrereq = !!(termCourse.prerequisite_codes || termCourse.prerequisite_row_codes);

    const newRecord = {
      level: termCourse.level,
      term: termCourse.term,
      course_name: termCourse.course_name,
      unique_code: termCourse.unique_course_code,
      estimated_capacity: estimatedCapacity,
      units: termCourse.units || 0,
      course_type: termCourse.course_type || "",
      from_termic: true,
      from_prerequisite: hasPrereq,
      from_student_demand: false,
      from_manager: true,
      avg_in_mehr: 0,
      avg_in_bahman: 0,
      avg_capacity_in_mehr: 0,
      avg_capacity_in_bahman: 0,
      required_classes: 1,
    };

    const tempData = [...fullData, newRecord];
    setIsAdding(true);
    try {
      const statsResult = await addStatisticsToBasket({ basket: tempData });
      const statsData = statsResult.basket || statsResult;
      if (!statsData?.length) {
        setFormError("خطا در محاسبه آمار برای درس جدید.");
        setIsAdding(false);
        return;
      }

      const merged = statsData.map((item, idx) => ({
        ...tempData[idx],
        ...item,
      }));

      setFullData(merged);
      setShowModal(false);
      setSelectedCourse("");
      setSelectedLevel("");
      setFormError("");
    } catch (e) {
      setFormError("خطا در محاسبه آمار: " + e.message);
    } finally {
      setIsAdding(false);
    }
  };

  // ============================================================
  // ستون‌ها
  // ============================================================
  const columns = [
    { key: "level", label: "مقطع" },
    { key: "term", label: "ترم" },
    { key: "course_name", label: "نام درس" },
    { key: "unique_code", label: "کد یکتا" },
    { key: "estimated_capacity", label: "برآورد ظرفیت" },
    { key: "units", label: "واحد" },
    { key: "course_type", label: "نوع درس" },
    { key: "from_termic", label: "از ترمیک", isCheckbox: true },
    { key: "from_prerequisite", label: "از پیش‌نیاز", isCheckbox: true },
    { key: "from_student_demand", label: "تقاضای دانشجو", isCheckbox: true },
    { key: "avg_in_mehr", label: "میانگین فراوانی در مهر" },
    { key: "avg_in_bahman", label: "میانگین فراوانی در بهمن" },
    { key: "avg_capacity_in_mehr", label: "میانگین ظرفیت در مهر" },
    { key: "avg_capacity_in_bahman", label: "میانگین ظرفیت در بهمن" },
    {
      key: "required_classes",
      label: "تعداد کلاس مورد نیاز",
      render: (row, index) => (
        <input
          type="number"
          min="1"
          value={row.required_classes || 1}
          onChange={(e) => handleUpdateRequiredClasses(index, e.target.value)}
          className="editable-number-input"
        />
      ),
    },
    { key: "from_manager", label: "انتخاب مدیر", isCheckbox: true },
  ];

  const classColumns = [
    { key: "level", label: "مقطع" },
    { key: "term", label: "ترم" },
    { key: "course_name", label: "نام درس" },
    { key: "unique_code", label: "کد یکتا" },
    { key: "group_number", label: "شماره گروه" },
    { key: "estimated_capacity", label: "برآورد ظرفیت" },
    { key: "units", label: "واحد" },
    { key: "course_type", label: "نوع درس" },
    { key: "required_classes", label: "تعداد کلاس مورد نیاز" },
  ];

  // ============================================================
  // رندر
  // ============================================================
  const isBasketEmpty = fullData !== null && fullData.length === 0 && (basketId || workflowId);
  const hasData = fullData && fullData.length > 0;

  return (
    <div className="basket-page">
      <div className="basket-header">
        <div className="step-indicators" style={{ justifyContent: "flex-start" }}>
          <span className="step-badge active">
            <span className="step-num">📋</span>
            <span className="step-label">سبد دروس ترم جاری</span>
          </span>
          {basketMeta.title && (
            <span className="basket-meta" style={{ marginRight: "20px", fontSize: "0.9rem", color: "#666" }}>
              {basketMeta.title} ({basketMeta.semester === "mehr" ? "مهر" : "بهمن"} {basketMeta.year})
            </span>
          )}
        </div>
        <div className="wizard-actions">
          {hasData && (
            <>
              <button onClick={() => setShowModal(true)} className="btn-add-record">
                ➕ افزودن رکورد
              </button>
              <button onClick={clearBasket} className="btn-danger">
                🗑️ حذف سبد
              </button>
            </>
          )}
          <button
            onClick={handleFetchData}
            disabled={isLoading || isLoadingFromDb}
            className="btn-primary"
          >
            {isLoading ? "در حال دریافت..." : "دریافت لیست دروس"}
          </button>
          {hasData && (
            <button
              onClick={handleGenerateClasses}
              className="btn-success"
              disabled={isSaving || isLoadingFromDb}
            >
              {isSaving ? "در حال ذخیره..." : "🧩 ایجاد و ذخیره کلاس‌ها"}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-message">⚠️ {error}</div>}

      <div className="step-content">
        <div className="info-box">
          <span className="info-icon">ℹ️</span>
          <p>
            لیست دروس به همراه آمار فراوانی و ظرفیت از سوابق برنامه‌ریزی.
            ستون "تعداد کلاس مورد نیاز" قابل ویرایش است. با کلیک روی "ایجاد و ذخیره کلاس‌ها"،
            به ازای هر درس، به تعداد مشخص‌شده رکورد کلاس تولید شده و در دیتابیس ذخیره می‌شود.
            این رکوردها مبنای فرایندهای بعدی (زمان‌بندی، تخصیص اتاق و بهینه‌سازی) هستند.
          </p>
        </div>

        {isLoadingFromDb ? (
          <div className="loading-state">در حال بارگذاری سبد ذخیره‌شده...</div>
        ) : isBasketEmpty ? (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <h3>سبد دروس خالی است</h3>
            <p>این سبد هنوز هیچ درسی ندارد.</p>
            <p>برای افزودن درس، روی دکمه "دریافت لیست دروس" کلیک کنید یا با دکمه "➕ افزودن رکورد" درس جدید اضافه کنید.</p>
          </div>
        ) : hasData ? (
          <>
            <EditableDataTable
              data={fullData}
              columns={columns}
              title="سبد دروس با آمار تکمیلی"
              editable={true}
              onToggleCheck={handleToggleManager}
              onDeleteRow={handleDeleteRow}
            />
            <div className="statistics-summary">
              <h4>📊 خلاصه سبد</h4>
              <div className="summary-grid">
                <div className="summary-item">
                  <span className="label">تعداد دروس</span>
                  <span className="value">{fullData.length}</span>
                </div>
                <div className="summary-item">
                  <span className="label">کلاس‌های مورد نیاز (مجموع)</span>
                  <span className="value">
                    {fullData.reduce((s, c) => s + (c.required_classes || 0), 0)}
                  </span>
                </div>
                <div className="summary-item">
                  <span className="label">میانگین ظرفیت</span>
                  <span className="value">
                    {Math.round(
                      fullData.reduce((s, c) => s + (c.avg_capacity_in_mehr || 0), 0) /
                        fullData.length
                    )}
                  </span>
                </div>
              </div>
            </div>

            {expandedClasses?.length > 0 && (
              <div className="generated-classes-section">
                <div className="generated-header">
                  <h4 className="generated-title">
                    📋 کلاس‌های تولید شده (خروجی نهایی سبد)
                    <span className="generated-badge">{expandedClasses.length} کلاس</span>
                  </h4>
                  <p className="generated-hint">
                    این رکوردها به عنوان ورودی فرایندهای بعدی (زمان‌بندی استاد، تخصیص اتاق و بهینه‌سازی) استفاده می‌شوند
                    {basketId ? ` با شناسه سبد ${basketId}` : workflowId ? ` با شناسه ${workflowId}` : ''} در دیتابیس ذخیره شده‌اند.
                  </p>
                </div>
                <EditableDataTable
                  data={expandedClasses}
                  columns={classColumns}
                  title=""
                  editable={false}
                />
              </div>
            )}
          </>
        ) : (
          <div className="empty-state">
            <span className="empty-icon">📋</span>
            <p>برای شروع، روی دکمه "دریافت لیست دروس" کلیک کنید.</p>
          </div>
        )}
      </div>

      {/* مودال افزودن رکورد */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3><span className="modal-icon">➕</span> افزودن درس جدید</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              {formError && <div className="form-error">{formError}</div>}
              <div className="form-group">
                <label>انتخاب درس</label>
                <select
                  value={selectedCourse}
                  onChange={(e) => setSelectedCourse(e.target.value)}
                  disabled={isAdding}
                >
                  <option value="">انتخاب کنید...</option>
                  {uniqueCourses.map(uc => (
                    <option key={uc.code} value={uc.code}>
                      {uc.code} - {uc.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>مقطع ارائه</label>
                <select
                  value={selectedLevel}
                  onChange={(e) => setSelectedLevel(e.target.value)}
                  disabled={!selectedCourse || isAdding}
                >
                  <option value="">انتخاب کنید...</option>
                  {availableLevels.map(level => (
                    <option key={level} value={level}>{level}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowModal(false)} disabled={isAdding}>
                انصراف
              </button>
              <button className="btn-primary" onClick={handleAddRecord} disabled={isAdding}>
                {isAdding ? "در حال افزودن..." : "افزودن"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// کامپوننت اصلی صفحه سبد
// ============================================================
export default function BasketPage({
  semester,
  levels,
  onComplete,
  loading,
  basketData,
  onNext,
  uniqueCourses = [],
  termCourses = [],
  workflowId = null,
  basketId: propBasketId = null,
  onBasketCreated,
}) {
  const [selectedBasketId, setSelectedBasketId] = useState(propBasketId);
  const [showSelector, setShowSelector] = useState(!propBasketId && !workflowId);

  useEffect(() => {
    if (propBasketId) {
      setSelectedBasketId(propBasketId);
      setShowSelector(false);
    }
  }, [propBasketId]);

  const handleSelectBasket = (id) => {
    setSelectedBasketId(id);
    setShowSelector(false);
    if (onBasketCreated) onBasketCreated(id);
  };

  const handleBackToList = () => {
    setSelectedBasketId(null);
    setShowSelector(true);
    if (onBasketCreated) onBasketCreated(null);
  };

  if (showSelector && !selectedBasketId && !workflowId) {
    return (
      <div className="process-page">
        <div className="process-header">
          <div className="process-title">
            <span className="process-icon">📦</span>
            <h2>مدیریت سبدهای دروس</h2>
          </div>
          <p className="process-description">
            از بین سبدهای موجود انتخاب کنید یا یک سبد جدید ایجاد کنید.
          </p>
        </div>
        <div className="process-body">
          <BasketSelector onSelectBasket={handleSelectBasket} />
        </div>
      </div>
    );
  }

  return (
    <div className="process-page">
      <div className="process-header">
        <div className="process-title">
          <span className="process-icon">📦</span>
          <h2>شناسایی سبد دروس ترم جاری</h2>
        </div>
        <p className="process-description">
          در این فرایند، لیست دروس مورد نیاز برای ترم جاری با استفاده از داده‌های ترمیک،
          پیش‌نیازها و سوابق برنامه‌ریزی شناسایی می‌شود.
          پس از ایجاد کلاس‌ها، این رکوردها در دیتابیس ذخیره شده و به عنوان ورودی فرایندهای بعدی استفاده می‌شوند.
        </p>
        {selectedBasketId && (
          <button onClick={handleBackToList} className="btn-secondary" style={{ marginTop: '10px' }}>
            ← بازگشت به لیست سبدها
          </button>
        )}
      </div>
      <div className="process-body">
        <BasketWizard
          semester={semester}
          levels={levels}
          onComplete={onComplete}
          loading={loading}
          uniqueCourses={uniqueCourses}
          termCourses={termCourses}
          workflowId={workflowId}
          initialBasketData={basketData}
          basketId={selectedBasketId}
          onBasketCreated={(id) => {
            setSelectedBasketId(id);
            setShowSelector(false);
            if (onBasketCreated) onBasketCreated(id);
          }}
        />
      </div>
      {basketData && (
        <div className="process-result">
          <div className="result-header">
            <h3>✅ سبد نهایی تکمیل شد</h3>
            <span className="result-badge">{basketData.length} کلاس</span>
          </div>
          <div className="result-actions">
            <button onClick={onNext} className="btn-primary" disabled={loading}>
              {loading ? "در حال..." : "⏳ مرحله بعد: زمان‌بندی استاد"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}