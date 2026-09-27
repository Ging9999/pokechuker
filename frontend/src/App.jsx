import { Routes, Route, NavLink } from "react-router-dom";
import SearchPage from "./pages/SearchPage.jsx";
import PortfolioPage from "./pages/PortfolioPage.jsx";
import CardDetailPage from "./pages/CardDetailPage.jsx";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? "bg-poke-blue text-white"
            : "text-gray-400 hover:text-white hover:bg-poke-border"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-poke-dark">
      {/* Nav */}
      <nav className="border-b border-poke-border bg-poke-card sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
          <span className="text-poke-yellow font-bold text-xl tracking-tight">
            ⚡ PokeChuker
          </span>
          <div className="flex gap-2">
            <NavItem to="/">Search</NavItem>
            <NavItem to="/portfolio">Portfolio</NavItem>
          </div>
          <span className="ml-auto text-xs text-poke-muted">UK Prices · eBay</span>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/cards/:slug" element={<CardDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
