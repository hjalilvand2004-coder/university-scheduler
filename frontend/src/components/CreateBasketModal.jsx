// frontend/src/components/CreateBasketModal.jsx
import { useState } from "react";
import axios from "axios";
import "./CreateBasketModal.css";

export default function CreateBasketModal({ onClose, onBasketCreated }) {
  const [title, setTitle] = useState("");
  const [semester, setSemester] = useState("mehr");
  const [year, setYear] = useState("1403");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("لطفاً عنوان سبد را وارد کنید.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await axios.post("http://localhost:8000/api/baskets/", {
        title: title.trim(),
        semester,
        year,
      });
      const newBasket = res.data;
      if (onBasketCreated) onBasketCreated(newBasket.id);
      onClose(); // بستن مودال
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