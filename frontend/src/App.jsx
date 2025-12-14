import { ThemeProvider } from './context/ThemeContext';
import AppRoutes from './routes/AppRoutes';

export default function App() {
  return (

    <ThemeProvider>
      <AppRoutes />
    </ThemeProvider>

  );
}
