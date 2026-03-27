import { Routes, Route, NavLink } from "react-router-dom";
import InspectPage from "./pages/InspectPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <h1>박스라벨 AI 검사</h1>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            검사
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            기준값
          </NavLink>
        </nav>
      </header>

      <main className="main">
        <Routes>
          <Route path="/" element={<InspectPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
