import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes, useParams, useSearchParams } from 'react-router-dom'
import AppShell from './layouts/AppShell'
import { LandingPage, LoginPage, ResetPage, SignUpPage } from './pages/Public'
import { RecoverPasswordPage, SecurityPage } from './pages/Security'
import Onboarding from './pages/Onboarding'
import OverviewPage from './pages/Overview'
import WatchlistsPage from './pages/Watchlists'
import WatchlistDetailPage from './pages/WatchlistDetail'
import DiscoverPage from './pages/Discover'
import HistoryPage from './pages/History'
import { NotFoundPage, NotificationsPage, SettingsPage } from './pages/Account'
import { Skeleton } from './components/ui'
import { getToken } from './services/api'
const StockDetailPage = lazy(() => import('./pages/StockDetail'))
function Guard({ children }: { children: React.ReactNode }) { if (!getToken()) return <Navigate to="/login" replace />; return children }
function StockRoute() { const { symbol } = useParams(); return <Suspense fallback={<Skeleton className="h-96" />}><StockDetailPage key={symbol} /></Suspense> }
function DiscoverRoute() { const [params] = useSearchParams(); const q = params.get('q') || ''; return <DiscoverPage key={q} initialQuery={q} /> }
export default function App() {
  return <Routes>
    <Route path="/" element={<LandingPage />} /><Route path="/login" element={<LoginPage />} /><Route path="/signup" element={<SignUpPage />} />
    <Route path="/forgot-password" element={<RecoverPasswordPage />} /><Route path="/recover-password" element={<RecoverPasswordPage />} /><Route path="/reset-password" element={<ResetPage />} />
    <Route path="/onboarding" element={<Guard><Onboarding /></Guard>} />
    <Route path="/app" element={<Guard><AppShell /></Guard>}><Route index element={<Navigate to="/app/overview" replace />} /><Route path="overview" element={<OverviewPage />} /><Route path="watchlists" element={<WatchlistsPage />} /><Route path="watchlists/:id" element={<WatchlistDetailPage />} /><Route path="stocks/:symbol" element={<StockRoute />} /><Route path="discover" element={<DiscoverRoute />} /><Route path="history" element={<HistoryPage />} /><Route path="settings" element={<SettingsPage />} /><Route path="security" element={<SecurityPage />} /><Route path="profile" element={<Navigate to="/app/settings" replace />} /><Route path="preferences" element={<Navigate to="/app/settings" replace />} /><Route path="notifications" element={<NotificationsPage />} /></Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
}
