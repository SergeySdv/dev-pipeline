import { useNavigate } from '@tanstack/react-router';
import { AlertCircle, Home } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-red-50 p-4">
            <AlertCircle className="h-12 w-12 text-red-600" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">404</h1>
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Page Not Found</h2>
        <p className="text-gray-600 mb-8 max-w-md">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex gap-3 justify-center">
          <Button
            variant="primary"
            onClick={() => navigate({ to: '/' })}
          >
            <Home className="mr-2 h-4 w-4" />
            Go Home
          </Button>
          <Button
            variant="default"
            onClick={() => window.history.back()}
          >
            Go Back
          </Button>
        </div>
      </div>
    </div>
  );
}
