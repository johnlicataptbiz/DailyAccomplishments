import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { Briefcase, CalendarClock, LineChart } from 'lucide-react';
import TodayPage from './pages/TodayPage';
import PlaceholderPage from './pages/PlaceholderPage';

const navLinkStyles = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors border border-white/5 shadow-sm hover:border-accent/60 hover:text-white hover:bg-white/5 ${
    isActive ? 'bg-white/10 text-white border-accent/70' : 'text-gray-300'
  }`;

function App() {
  return (
    <div className="app-shell">
      <div className="max-w-6xl mx-auto px-4 py-10 space-y-8">
        <header className="flex flex-col gap-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-accent font-semibold">Today Brief</p>
              <h1 className="text-3xl font-semibold text-white mt-2">Daily Accomplishments Dashboard</h1>
              <p className="text-sm text-muted mt-1 max-w-2xl">
                A focused, proof-backed summary of today&apos;s work with inline editing and receipts for each highlight.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted bg-white/5 border border-white/10 rounded-full px-3 py-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span>Static reports served locally · Client-side edits preserved in your browser</span>
            </div>
          </div>
          <nav className="flex gap-3 flex-wrap">
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
            <Route path="/" element={<Navigate to="/today" replace />} />
            <Route path="/today" element={<TodayPage />} />
            <Route path="/weekly" element={<PlaceholderPage title="Weekly Review" />} />
            <Route path="/trends" element={<PlaceholderPage title="Trends" />} />
            <Route path="*" element={<Navigate to="/today" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
