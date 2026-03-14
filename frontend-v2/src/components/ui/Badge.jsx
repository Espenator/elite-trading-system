import React from 'react';
import clsx from 'clsx';

const variantStyles = {
  primary: 'bg-primary/20 text-primary border-primary/40',
  success: 'bg-success/20 text-success border-success/40',
  danger: 'bg-danger/20 text-danger border-danger/40',
  warning: 'bg-warning/20 text-warning border-warning/40',
  secondary: 'bg-secondary/20 text-secondary border-secondary/40',
};

const sizeStyles = {
  sm: 'px-1.5 py-0.5 text-[10px] rounded',
  md: 'px-2 py-1 text-xs rounded-md',
  lg: 'px-2.5 py-1.5 text-sm rounded-lg',
};

function Badge({ variant = 'secondary', size = 'md', className, children, ...props }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium border',
        variantStyles[variant] ?? variantStyles.secondary,
        sizeStyles[size] ?? sizeStyles.md,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export default React.memo(Badge);
