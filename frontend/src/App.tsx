import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './layouts/AppShell'
import { ForgotPage, LandingPage, LoginPage, ResetPage, SignUpPage } from './pages/Public'
import Onboarding from './pages/Onboarding'
import OverviewPage from './pages/Overview'
import WatchlistsPage from './pages/Watchlists'
import WatchlistDetailPage from './pages/WatchlistDetail'
import StockDetailPage from './pages/StockDetail'
import DiscoverPage from './pages/Discover'
import HistoryPage from './pages/History'
import { ErrorPage, NotFoundPage, NotificationsPage, PreferencesPage, ProfilePage, SettingsPage } from './pages/Account'
import { getToken } from './services/api'

function Guard({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignUpPage />} />
      <Route path="/forgot-password" element={<ForgotPage />} />
      <Route path="/reset-password" element={<ResetPage />} />
      <Route path="/onboarding" element={<Guard><Onboarding /></Guard>} />
      <Route path="/app" element={<Guard><AppShell /></Guard>}>
        <Route path="overview" element={<OverviewPage />} />
        <Route path="watchlists" element={<WatchlistsPage />} />
        <Route path="watchlists/:id" element={<WatchlistDetailPage />} />
        <Route path="stocks/:symbol" element={<StockDetailPage />} />
        <Route path="discover" element={<DiscoverPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="preferences" element={<PreferencesPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="error" element={<ErrorPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
