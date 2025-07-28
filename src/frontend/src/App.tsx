import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import DailyAuthTokens from './components/pages/DailyAuthTokens';
import Dashboard from './components/pages/Dashboard';
import LiveIndices from './components/pages/LiveIndices';
import SystemHealth from './components/pages/SystemHealth';
import TradingControl from './components/pages/TradingControl';
import UserAnalytics from './components/pages/UserAnalytics';
import UserManagement from './components/pages/UserManagement';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="flex h-screen bg-gray-100">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-6">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/users" element={<UserManagement />} />
                <Route path="/analytics" element={<UserAnalytics />} />
                <Route path="/trading" element={<TradingControl />} />
                <Route path="/indices" element={<LiveIndices />} />
                <Route path="/auth-tokens" element={<DailyAuthTokens />} />
                <Route path="/system" element={<SystemHealth />} />
              </Routes>
            </main>
          </div>
        </div>
        <Toaster position="top-right" />
      </Router>
    </QueryClientProvider>
  );
}

export default App;

