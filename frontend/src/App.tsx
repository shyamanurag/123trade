import { Route, Routes, Navigate, Link } from 'react-router-dom';
import Orders from './pages/Orders';
import Positions from './pages/Positions';

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white shadow p-4 flex justify-between items-center">
        <h1 className="text-xl font-semibold text-indigo-600">123Trade</h1>
        <nav className="space-x-4">
          <Link to="/orders" className="text-gray-600 hover:text-indigo-600">Orders</Link>
          <Link to="/positions" className="text-gray-600 hover:text-indigo-600">Positions</Link>
        </nav>
      </header>
      <main className="flex-1 p-4">
        <Routes>
          <Route path="/orders" element={<Orders />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="*" element={<Navigate to="/orders" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
