export default function Button({ 
  children, 
  size = 'md', 
  variant = 'primary',
  className = '',
  ...props 
}) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const variantClasses = {
    primary: 'bg-purple-500 hover:bg-purple-600 text-white',
    secondary: 'bg-slate-700 hover:bg-slate-600 text-white',
    outline: 'border border-purple-500 text-purple-500 hover:bg-purple-500 hover:text-white',
  };

  return (
    <button
      className={`
        ${sizeClasses[size] || sizeClasses.md}
        ${variantClasses[variant] || variantClasses.primary}
        font-semibold rounded-lg transition-colors duration-200
        focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-slate-900
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
}

