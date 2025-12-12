
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import NotFound from '../pages/NotFound';


function RoutesContent() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function AppRoutes(){
  return (
    <BrowserRouter>
      <RoutesContent />
    </BrowserRouter>
  );
}
