import { useRef } from "react";

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
        📤 بارگذاری اکسل
      </button>
    </div>
  );
}