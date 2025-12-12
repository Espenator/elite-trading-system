import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';

export default function NotFound() {
  return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-9xl font-bold text-purple-500 mb-4">404</h1>
          <h2 className="text-3xl font-semibold text-white mb-4">Page Not Found</h2>
          <p className="text-slate-400 mb-8 max-w-md">
            Oops! The page you're looking for doesn't exist or has been moved.
          </p>
          <Link to="/">
            <Button size="lg">Go Home</Button>
          </Link>
        </div>
      </div>
  );
}
