import { cn } from '@/lib/cn';
import { forwardRef } from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline' | 'link';
  size?: 'default' | 'small' | 'tiny' | 'icon';
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', loading, children, disabled, ...props }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50';

    const variantClasses = {
      default: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
      primary: 'bg-blue-600 text-white hover:bg-blue-700',
      secondary: 'bg-gray-600 text-white hover:bg-gray-700',
      danger: 'bg-red-600 text-white hover:bg-red-700',
      ghost: 'text-gray-700 hover:bg-gray-100',
      outline: 'border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50',
      link: 'text-blue-600 underline-offset-4 hover:underline !p-0 !h-auto',
    };

    const sizeClasses = {
      default: 'h-9 px-4 py-2 text-sm',
      small: 'h-8 px-3 py-1.5 text-xs',
      tiny: 'h-6 px-2 py-1 text-xs',
      icon: 'h-9 w-9 p-0',
    };

    return (
      <button
        className={cn(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <span className="animate-spin">⟳</span>}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };