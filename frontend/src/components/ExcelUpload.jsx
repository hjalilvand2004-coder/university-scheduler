import { useRef } from "react";
import { FiUpload } from "react-icons/fi";

export default function ExcelUpload({ onUpload, type }) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file, type);
    }
    e.target.value = "";
  };

  return (
    <div className="excel-upload">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".xlsx,.xls"
        style={{ display: "none" }}
      />
      <button
        className="btn-upload"
        onClick={() => fileInputRef.current?.click()}
      >
        <FiUpload /> بارگذاری اکسل
      </button>
    </div>
  );
}
