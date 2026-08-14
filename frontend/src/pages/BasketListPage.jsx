// frontend/src/pages/BasketListPage.jsx
import { useState, useEffect } from "react";
import axios from "axios";
import "./BasketListPage.css";

// ===== کامپوننت مودال ایجاد سبد جدید (درون‌خطی) =====
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

// ===== کامپوننت اصلی =====
export default function BasketListPage({ onNavigateToBasket, onNavigateToNewBasket }) {
  const [baskets, setBaskets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    fetchBaskets();
  }, []);

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

  const handleSelectBasket = (basketId) => {
    console.log("🔄 کلیک روی مشاهده جزئیات برای سبد با شناسه:", basketId);
    if (typeof onNavigateToBasket === "function") {
      onNavigateToBasket(basketId);
    } else {
      console.error("❌ onNavigateToBasket تعریف نشده است یا تابع نیست!");
      alert("خطا در هدایت به صفحه جزئیات. لطفاً با پشتیبانی تماس بگیرید.");
    }
  };

  const handleCreateNewBasket = () => {
    setShowCreateModal(true);
  };

  const handleBasketCreated = (newBasketId) => {
    console.log("✅ سبد جدید با شناسه ایجاد شد:", newBasketId);
    if (typeof onNavigateToNewBasket === "function") {
      onNavigateToNewBasket(newBasketId);
    } else {
      console.warn("⚠️ onNavigateToNewBasket تعریف نشده است یا تابع نیست.");
      alert("خطا در هدایت به صفحه سبد جدید. لطفاً با پشتیبانی تماس بگیرید.");
    }
    fetchBaskets();
  };

  if (loading) return <div className="loading-state">در حال بارگذاری...</div>;
  if (error) return <div className="error-state">{error}</div>;

  return (
    <div className="basket-list-page">
      <div className="basket-list-header">
        <h2>📋 لیست سبدهای دروس</h2>
        <button onClick={handleCreateNewBasket} className="btn-primary">
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
                      onClick={() => handleSelectBasket(basket.id)}
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