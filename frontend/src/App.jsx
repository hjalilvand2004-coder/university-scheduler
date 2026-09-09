// frontend/src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ProposalForm from "./pages/ProposalForm";
import VoteForm from "./pages/VoteForm";
import RatingForm from "./pages/RatingForm";
import "./style.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<Dashboard />} />
        {/* مسیرهای جدید را به Dashboard می‌دهیم تا از همان ساختار استفاده کند */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;