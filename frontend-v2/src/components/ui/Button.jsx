import { forwardRef } from 'react';
import clsx from 'clsx';

const variantStyles = {
  primary: 'bg-primary text-white hover:bg-primary/90 border-primary/30 focus:ring-primary/40',
  success: 'bg-success text-white hover:bg-success/90 border-success/30 focus:ring-success/40',
  danger: 'bg-danger text-white hover:bg-danger/90 border-danger/30 focus:ring-danger/40',
  warning: 'bg-warning text-dark hover:bg-warning/90 border-warning/30 focus:ring-warning/40',
  secondary: 'bg-secondary/20 text-white hover:bg-secondary/30 border-secondary/40 focus:ring-secondary/40',
  ghost: 'bg-transparent text-secondary hover:bg-secondary/20 border-transparent focus:ring-secondary/30',
  outline: 'bg-transparent text-white border-secondary/50 hover:bg-secondary/10 focus:ring-secondary/40',
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-xs rounded-lg',
  md: 'px-4 py-2.5 text-sm rounded-md',
  lg: 'px-6 py-3 text-base rounded-md',
};

function Spinner({ className }) {
  return <svg className={clsx("animate-spin shrink-0", className)} viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".25" /><path d="M14 8a6 6 0 00-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>;
}

const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', type = 'button', disabled = false, loading = false, className, children, leftIcon: LeftIcon, rightIcon: RightIcon, fullWidth, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center gap-2 font-medium transition-colors outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-dark border disabled:opacity-50 disabled:pointer-events-none',
        variantStyles[variant] ?? variantStyles.primary,
        sizeStyles[size] ?? sizeStyles.md,
        fullWidth && 'w-full',
        className
      )}
      {...props}
    >
      {loading ? <Spinner className="w-4 h-4" /> : LeftIcon && <LeftIcon className="w-4 h-4 shrink-0" />}
      {children}
      {!loading && RightIcon && <RightIcon className="w-4 h-4 shrink-0" />}
    </button>
  );
});

export default Button;
