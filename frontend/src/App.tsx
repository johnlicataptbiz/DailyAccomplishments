import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { BarChart3, Briefcase, CalendarClock, LineChart } from 'lucide-react';
import TodayPage from './pages/TodayPage';
import DashboardPage from './pages/DashboardPage';
import PlaceholderPage from './pages/PlaceholderPage';

const navLinkStyles = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors border shadow-sm ${
    isActive
      ? 'bg-soft text-slate-900 border-accent/40'
      : 'bg-panel text-slate-600 border-slate-200 hover:border-accent/40 hover:text-slate-900'
  }`;

function App() {
  return (
    <div className="app-shell">
      <div className="max-w-6xl mx-auto px-4 py-10 space-y-8">
        <header className="flex flex-col gap-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-accent font-semibold">Daily Accomplishments</p>
              <h1 className="text-3xl font-semibold text-slate-900 mt-2">Dashboard</h1>
              <p className="text-sm text-muted mt-1 max-w-2xl">Daily narrative, key metrics, timeline, and proof receipts.</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted bg-panel border border-slate-200 rounded-full px-3 py-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Static reports · Client-side edits saved locally</span>
            </div>
          </div>
          <nav className="flex gap-3 flex-wrap">
            <NavLink to="/dashboard" className={navLinkStyles}>
              <BarChart3 className="h-4 w-4" />
              Dashboard
            </NavLink>
            <NavLink to="/today" className={navLinkStyles}>
              <Briefcase className="h-4 w-4" />
              Today
            </NavLink>
            <NavLink to="/weekly" className={navLinkStyles}>
              <CalendarClock className="h-4 w-4" />
              Weekly
            </NavLink>
            <NavLink to="/trends" className={navLinkStyles}>
              <LineChart className="h-4 w-4" />
              Trends
            </NavLink>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/today" element={<TodayPage />} />
            <Route path="/weekly" element={<PlaceholderPage title="Weekly Review" />} />
            <Route path="/trends" element={<PlaceholderPage title="Trends" />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
